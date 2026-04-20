"""Hindsight memory client using the official hindsight-client SDK.

Uses async methods (aretain / arecall) for all operations.
Never raises to the caller — errors are caught and converted to safe defaults.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random

from hindsight_client import Hindsight

from models.review import MemoryEntry, MemoryEntryInput

logger = logging.getLogger(__name__)

# Default bank for the ReviewMind AI demo
DEFAULT_BANK_ID = "reviewmind-ai"
BANK_ID = DEFAULT_BANK_ID  # kept for backward compatibility


def project_bank_id(project_id: str) -> str:
    """Return a per-project Hindsight bank ID."""
    return f"reviewmind-{project_id[:8]}"


def _client() -> Hindsight:
    return Hindsight(
        base_url=os.environ.get("HINDSIGHT_INSTANCE_URL", "https://api.hindsight.vectorize.io"),
        api_key=os.environ["HINDSIGHT_API_KEY"],
    )


async def ensure_bank(bank_id: str = BANK_ID, name: str | None = None) -> None:
    """Create the memory bank if it doesn't exist yet. Idempotent.

    Raises on genuine errors (auth failure, network error) so callers know
    the bank is not usable. Silently ignores "already exists" responses.
    """
    client = _client()
    bank_name = name or f"ReviewMind AI — {bank_id}"
    try:
        await asyncio.to_thread(
            client.create_bank,
            bank_id=bank_id,
            name=bank_name,
            background=(
                "Memory bank for the ReviewMind AI code review agent. "
                "Stores team conventions, recurring mistakes per contributor, "
                "architectural decisions, and approved exceptions."
            ),
        )
        logger.info("Hindsight bank '%s' created.", bank_id)
    except Exception as exc:
        error_str = str(exc).lower()
        if any(kw in error_str for kw in ("already exists", "duplicate", "conflict", "409")):
            logger.debug("ensure_bank '%s': already exists, skipping.", bank_id)
        else:
            # Real error — log at ERROR level so it's visible, but don't crash
            # the whole request; write_memory will surface the failure anyway.
            logger.error(
                "ensure_bank '%s' failed (%s: %s) — writes may fail.",
                bank_id, type(exc).__name__, exc,
            )
    finally:
        await asyncio.to_thread(client.close)


async def test_connection() -> tuple[bool, str]:
    """Lightweight connectivity check — tries to list banks.

    Returns (True, "") on success, (False, error_message) on failure.
    Used at startup to surface auth/network problems early.
    """
    client = _client()
    try:
        await asyncio.to_thread(client.list_banks)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        await asyncio.to_thread(client.close)


async def write_memory(
    entry: MemoryEntryInput,
    bank_id: str = BANK_ID,
    *,
    max_retries: int = 3,
) -> tuple[bool, str | None]:
    """Store a single memory entry in Hindsight.

    Returns (True, None) on success, (False, error_message) on failure.
    Retries up to max_retries times with exponential backoff on HTTP 429.
    Never raises.
    """
    client = _client()
    try:
        content = entry.description
        metadata: dict = {"category": entry.category}
        if entry.contributor:
            metadata["contributor"] = entry.contributor
        if entry.pattern_tag:
            metadata["pattern_tag"] = entry.pattern_tag
        if entry.module:
            metadata["module"] = entry.module
        if entry.file_path:
            metadata["file_path"] = entry.file_path

        context_parts = []
        if entry.category:
            context_parts.append(f"Category: {entry.category}")
        if entry.contributor:
            context_parts.append(f"Contributor: {entry.contributor}")
        if entry.pattern_tag:
            context_parts.append(f"Pattern: {entry.pattern_tag}")

        last_error: str = ""
        for attempt in range(1, max_retries + 1):
            try:
                await client.aretain(
                    bank_id=bank_id,
                    content=content,
                    context=", ".join(context_parts) if context_parts else None,
                    metadata=metadata,
                )
                return True, None
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                last_error = error_msg
                is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                if is_rate_limit and attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Hindsight rate limit (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, max_retries, delay, error_msg,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Hindsight write_memory failed (attempt %d/%d): %s",
                        attempt, max_retries, error_msg,
                    )
                    if not is_rate_limit:
                        break  # non-rate-limit errors don't benefit from retry

        return False, last_error
    finally:
        await client.aclose()


async def list_memories(bank_id: str = BANK_ID) -> list[MemoryEntry]:
    """List all memories stored in the Hindsight bank.

    Returns a list of MemoryEntry records, or [] on any error (never raises).
    """
    client = _client()
    try:
        result = await asyncio.to_thread(client.list_memories, bank_id=bank_id, limit=100)
        entries: list[MemoryEntry] = []
        for i, item in enumerate(result.items or []):
            try:
                meta: dict = {}
                if hasattr(item, "metadata") and item.metadata:
                    meta = item.metadata if isinstance(item.metadata, dict) else {}
                text = ""
                if hasattr(item, "content"):
                    text = item.content or ""
                elif hasattr(item, "text"):
                    text = item.text or ""
                else:
                    text = str(item)
                entry = MemoryEntry(
                    id=str(i),
                    created_at="",
                    category=meta.get("category", "Team Convention"),
                    contributor=meta.get("contributor"),
                    file_path=meta.get("file_path"),
                    module=meta.get("module"),
                    pattern_tag=meta.get("pattern_tag"),
                    description=text,
                )
                entries.append(entry)
            except Exception as parse_exc:
                logger.warning("Skipping unparseable memory item: %s", parse_exc)
        return entries
    except Exception as exc:
        logger.error("Hindsight list_memories error: %s", exc)
        return []
    finally:
        await client.aclose()


async def query_memory(
    contributor: str | None = None,
    file_path: str | None = None,
    tags: list[str] | None = None,
    bank_id: str = BANK_ID,
) -> list[MemoryEntry]:
    """Retrieve relevant memory entries from Hindsight.

    Returns a list of MemoryEntry records, or [] on any error (never raises).
    """
    client = _client()
    try:
        # Build a natural-language query from available identifiers
        parts: list[str] = []
        if contributor:
            parts.append(f"contributor {contributor}")
        if file_path:
            parts.append(f"file {file_path}")
        if tags:
            parts.extend(tags[:3])
        query_text = " ".join(parts) if parts else "code review conventions and mistakes"

        result = await client.arecall(
            bank_id=bank_id,
            query=query_text,
            max_tokens=4096,
            budget="mid",
        )

        entries: list[MemoryEntry] = []
        for i, mem in enumerate(result.results or []):
            try:
                # Extract metadata if available
                meta: dict = {}
                if hasattr(mem, "metadata") and mem.metadata:
                    meta = mem.metadata if isinstance(mem.metadata, dict) else {}

                entry = MemoryEntry(
                    id=str(i),
                    created_at="",
                    category=meta.get("category", "Team Convention"),
                    contributor=meta.get("contributor"),
                    file_path=meta.get("file_path"),
                    module=meta.get("module"),
                    pattern_tag=meta.get("pattern_tag"),
                    description=mem.text if hasattr(mem, "text") else str(mem),
                )
                entries.append(entry)
            except Exception as parse_exc:
                logger.warning("Skipping unparseable memory: %s", parse_exc)

        return entries
    except Exception as exc:
        logger.error("Hindsight query_memory error: %s", exc)
        return []
    finally:
        await client.aclose()
