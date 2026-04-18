"""ReviewMind AI — 7-stage review pipeline.

Stages:
  1. Code Ingestion      — parse raw code into structured ParsedCode
  2. Context Retrieval   — query Hindsight for relevant memory entries
  3. Prompt Construction — build system + user prompts with memory context
  4. LLM Analysis        — call Groq with function calling
  5. Error Handling      — validate response; produce fallback on GroqError
  6. Output Formatting   — map to ReviewOutput with all 4 sections
  7. Memory Update       — write new findings back to Hindsight
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agent import hindsight, groq_client
from agent.groq_client import GroqError
from agent.parser import ParsedCode, parse_code
from models.review import (
    MemoryEntry,
    MemoryEntryInput,
    ReviewOutput,
    ReviewRequest,
    ReviewResponse,
)

logger = logging.getLogger(__name__)

# ── Tool schema for Groq function calling ────────────────────────────────────

_REVIEW_TOOL: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "submit_review",
            "description": "Submit a structured code review with categorised findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "critical_issues": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bugs, security issues, or correctness problems.",
                    },
                    "convention_violations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Violations of team conventions or architectural decisions.",
                    },
                    "contributor_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recurring patterns specific to this contributor.",
                    },
                    "positive_signals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Good practices worth reinforcing.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Exactly 2 sentences: overall quality assessment and top priority action.",
                    },
                },
                "required": [
                    "critical_issues",
                    "convention_violations",
                    "contributor_patterns",
                    "positive_signals",
                    "summary",
                ],
            },
        },
    }
]


# ── Pipeline ─────────────────────────────────────────────────────────────────


async def run_review(request: ReviewRequest, force_memory_mode: str | None = None) -> ReviewResponse:
    """Execute the full 7-stage review pipeline for a given ReviewRequest."""

    # ── Stage 1: Code Ingestion ──────────────────────────────────────────────
    parsed: ParsedCode = parse_code(request.code)
    logger.info(
        "Stage 1 complete: %d functions, %d patterns detected",
        len(parsed.functions),
        len(parsed.detected_patterns),
    )

    # ── Stage 2: Context Retrieval ───────────────────────────────────────────
    if force_memory_mode == "without":
        recalled: list[MemoryEntry] = []
    else:
        recalled = await hindsight.query_memory(
            contributor=request.contributor,
            file_path=request.file_path,
            tags=parsed.detected_patterns[:5],
        )
    memory_mode = "with" if recalled else "without"
    logger.info("Stage 2 complete: %d memory entries recalled (mode=%s)", len(recalled), memory_mode)

    # ── Stage 3: Prompt Construction ─────────────────────────────────────────
    system_prompt, user_prompt = _build_prompts(request, parsed, recalled)
    logger.info("Stage 3 complete: prompts constructed")

    # ── Stage 4: LLM Analysis ────────────────────────────────────────────────
    llm_result = await groq_client.call_with_tools(system_prompt, user_prompt, _REVIEW_TOOL)
    logger.info("Stage 4 complete: LLM response received (type=%s)", type(llm_result).__name__)

    # ── Stage 5: Error Handling ──────────────────────────────────────────────
    review_output = _parse_llm_response(llm_result, parsed, recalled)
    logger.info("Stage 5 complete: review output validated")

    # ── Stage 6: Output Formatting ───────────────────────────────────────────
    # review_output is already a ReviewOutput from stage 5
    logger.info("Stage 6 complete: output formatted")

    # ── Stage 7: Memory Update ───────────────────────────────────────────────
    memory_failures = await _update_memory(request, review_output)
    if memory_failures:
        logger.warning("Stage 7: %d memory write(s) failed", memory_failures)
    logger.info("Stage 7 complete: memory updated")

    return ReviewResponse(
        review=review_output,
        memory_mode=memory_mode,
        recalled_entries=recalled,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_prompts(
    request: ReviewRequest,
    parsed: ParsedCode,
    recalled: list[MemoryEntry],
) -> tuple[str, str]:
    """Build system and user prompts, injecting all recalled memory entries."""

    memory_context = ""
    if recalled:
        lines = ["## Team Memory Context\n"]
        for entry in recalled:
            tag = f"[{entry.category}]"
            who = f" — {entry.contributor}" if entry.contributor else ""
            lines.append(f"- {tag}{who}: {entry.description}")
        memory_context = "\n".join(lines)

    system_prompt = f"""You are ReviewMind AI, a senior code reviewer for Crestline Software's Orion API project.
You have access to the team's institutional memory and must use it to produce precise, team-aware feedback.

Reviewer persona: Priya Nair (Tech Lead)
Contributor being reviewed: {request.contributor}

{memory_context if memory_context else "## No prior memory context available — provide generic best-practice feedback."}

When memory context is available:
- Reference specific past decisions by name (e.g. "Per the team decision in PR #1...")
- Flag recurring patterns for this contributor explicitly
- Note approved exceptions where applicable

Always structure your review using the submit_review tool with all required fields.
The summary must be exactly 2 sentences: one quality assessment, one top priority action."""

    detected_str = "\n".join(f"  - {p}" for p in parsed.detected_patterns) if parsed.detected_patterns else "  (none detected by static analysis)"
    functions_str = ", ".join(parsed.functions) if parsed.functions else "(none)"

    user_prompt = f"""Please review the following code submitted by {request.contributor}:

```python
{request.code}
```

Static analysis detected:
{detected_str}

Functions found: {functions_str}
{"File: " + request.file_path if request.file_path else ""}

Provide a thorough code review using the submit_review tool."""

    return system_prompt, user_prompt


def _parse_llm_response(
    llm_result: dict[str, Any] | str | GroqError,
    parsed: ParsedCode,
    recalled: list[MemoryEntry],
) -> ReviewOutput:
    """Stage 5: validate LLM response and produce ReviewOutput.

    On GroqError or unparseable response, returns a fallback ReviewOutput with error set.
    """
    if isinstance(llm_result, GroqError):
        return _fallback_review(parsed, recalled, error=llm_result.message)

    if isinstance(llm_result, str):
        # Text-only fallback response — wrap it
        return ReviewOutput(
            critical_issues=[],
            convention_violations=[],
            contributor_patterns=[],
            positive_signals=[],
            summary=llm_result[:500] if llm_result else "Review could not be structured. Please try again.",
        )

    if isinstance(llm_result, dict):
        try:
            return ReviewOutput(
                critical_issues=llm_result.get("critical_issues", []),
                convention_violations=llm_result.get("convention_violations", []),
                contributor_patterns=llm_result.get("contributor_patterns", []),
                positive_signals=llm_result.get("positive_signals", []),
                summary=llm_result.get("summary", "Review generated. Please check the findings above."),
            )
        except Exception as exc:
            logger.error("Failed to parse LLM dict response: %s", exc)
            return _fallback_review(parsed, recalled, error=str(exc))

    return _fallback_review(parsed, recalled, error="Unexpected LLM response type")


def _fallback_review(
    parsed: ParsedCode,
    recalled: list[MemoryEntry],
    error: str = "",
) -> ReviewOutput:
    """Produce a best-effort review from static analysis when LLM fails."""
    critical: list[str] = []
    conventions: list[str] = []
    patterns: list[str] = []

    for p in parsed.detected_patterns:
        if "mutable-default-arg" in p:
            conventions.append(f"Static analysis: {p}")
        elif "missing-try-except" in p:
            critical.append(f"Static analysis: {p}")
        elif "direct-orm" in p:
            conventions.append(f"Static analysis: {p}")
        else:
            critical.append(f"Static analysis: {p}")

    for entry in recalled:
        if entry.category == "Recurring Mistake":
            patterns.append(f"Known recurring issue: {entry.description}")

    return ReviewOutput(
        critical_issues=critical or ["LLM unavailable — static analysis only"],
        convention_violations=conventions,
        contributor_patterns=patterns,
        positive_signals=[],
        summary="LLM review failed; static analysis findings shown above. Please retry for full AI-powered review.",
        error=error or "LLM review failed",
    )


async def _update_memory(request: ReviewRequest, review: ReviewOutput) -> int:
    """Stage 7: write new findings from this review back to Hindsight.

    Returns the number of failed writes (0 on full success).
    """
    if review.error:
        return 0  # don't persist failed reviews

    new_entries: list[MemoryEntryInput] = []

    for issue in review.critical_issues:
        new_entries.append(MemoryEntryInput(
            category="Recurring Mistake",
            contributor=request.contributor,
            file_path=request.file_path,
            description=issue,
        ))

    for violation in review.convention_violations:
        new_entries.append(MemoryEntryInput(
            category="Team Convention",
            contributor=request.contributor,
            file_path=request.file_path,
            description=violation,
        ))

    for entry in new_entries[:5]:  # cap at 5 new entries per review
        success = await hindsight.write_memory(entry)
        if not success:
            logger.error("Failed to write memory entry: %s", entry.description[:80])
            return 1
    return 0
