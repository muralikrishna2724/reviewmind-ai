"""Preservation property tests — run on UNFIXED code to confirm baseline behavior.

Property 2: Preservation — Non-Buggy Code Paths Unchanged
These tests MUST PASS on unfixed code (for non-buggy paths) and MUST STILL PASS after the fix.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Preservation 3.4: query_memory return contract ───────────────────────────

class TestPreservationQueryMemory:
    """Property 2: Preservation — query_memory return contract unchanged (req 3.4)."""

    def test_query_memory_returns_memory_entries(self):
        """For any call to query_memory with a mocked SDK, returns list[MemoryEntry] or []."""
        import agent.hindsight as hindsight
        from models.review import MemoryEntry

        mock_mem = MagicMock()
        mock_mem.text = "Use repository pattern for DB access"
        mock_mem.metadata = {"category": "Team Convention", "contributor": "alice"}

        mock_result = MagicMock()
        mock_result.results = [mock_mem]

        mock_client = MagicMock()
        mock_client.arecall = AsyncMock(return_value=mock_result)
        mock_client.aclose = AsyncMock()

        async def run():
            with patch.object(hindsight, "_client", return_value=mock_client):
                return await hindsight.query_memory(
                    contributor="alice",
                    file_path="api/routes.py",
                    tags=["direct-orm"],
                )

        result = asyncio.get_event_loop().run_until_complete(run())
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], MemoryEntry)
        assert result[0].description == "Use repository pattern for DB access"

    def test_query_memory_returns_empty_on_error(self):
        """query_memory returns [] on any SDK error — never raises."""
        import agent.hindsight as hindsight

        mock_client = MagicMock()
        mock_client.arecall = AsyncMock(side_effect=RuntimeError("SDK error"))
        mock_client.aclose = AsyncMock()

        async def run():
            with patch.object(hindsight, "_client", return_value=mock_client):
                return await hindsight.query_memory(contributor="bob")

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result == []


# ── Preservation 3.2 / 3.3: Groq return types and retry logic ────────────────

class TestPreservationGroqReturnTypes:
    """Property 2: Preservation — Groq return types and retry logic unchanged (req 3.2, 3.3)."""

    def test_call_with_tools_returns_dict_on_valid_tool_call(self):
        """call_with_tools returns dict when Groq returns a valid tool call."""
        import agent.groq_client as groq_client

        expected = {
            "critical_issues": ["missing error handling"],
            "convention_violations": [],
            "contributor_patterns": [],
            "positive_signals": ["good naming"],
            "summary": "Solid code. Fix error handling.",
        }

        mock_tool_call = MagicMock()
        mock_tool_call.function.arguments = json.dumps(expected)

        mock_message = MagicMock()
        mock_message.tool_calls = [mock_tool_call]

        mock_resp = MagicMock()
        mock_resp.choices[0].message = mock_message

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        async def run():
            with patch.object(groq_client, "_client", return_value=mock_client):
                return await groq_client.call_with_tools("sys", "user", [])

        result = asyncio.get_event_loop().run_until_complete(run())
        assert isinstance(result, dict)
        assert result["critical_issues"] == ["missing error handling"]

    def test_call_with_tools_returns_groq_error_on_api_error(self):
        """call_with_tools returns GroqError (never raises) on APIError."""
        import agent.groq_client as groq_client
        from groq import APIError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            "rate limit", response=MagicMock(status_code=429), body={}
        )

        async def run():
            with patch.object(groq_client, "_client", return_value=mock_client):
                return await groq_client.call_with_tools("sys", "user", [])

        result = asyncio.get_event_loop().run_until_complete(run())
        assert isinstance(result, groq_client.GroqError)

    def test_call_text_only_returns_string_on_success(self):
        """call_text_only returns str on success."""
        import agent.groq_client as groq_client

        mock_message = MagicMock()
        mock_message.content = "This is a text review."

        mock_resp = MagicMock()
        mock_resp.choices[0].message = mock_message

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        async def run():
            with patch.object(groq_client, "_client", return_value=mock_client):
                return await groq_client.call_text_only("sys", "user")

        result = asyncio.get_event_loop().run_until_complete(run())
        assert isinstance(result, str)
        assert result == "This is a text review."

    def test_call_with_tools_retries_on_json_parse_failure(self):
        """call_with_tools retries once on JSON parse failure (req 3.3)."""
        import agent.groq_client as groq_client

        call_count = 0

        def create_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_tool_call = MagicMock()
            if call_count == 1:
                mock_tool_call.function.arguments = "not valid json {"
            else:
                mock_tool_call.function.arguments = '{"critical_issues":[],"convention_violations":[],"contributor_patterns":[],"positive_signals":[],"summary":"ok ok"}'
            mock_message = MagicMock()
            mock_message.tool_calls = [mock_tool_call]
            mock_resp = MagicMock()
            mock_resp.choices[0].message = mock_message
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = create_side_effect

        async def run():
            with patch.object(groq_client, "_client", return_value=mock_client):
                return await groq_client.call_with_tools("sys", "user", [])

        result = asyncio.get_event_loop().run_until_complete(run())
        assert call_count == 2, f"Expected 2 attempts (retry on JSON failure), got {call_count}"
        assert isinstance(result, dict)


# ── Preservation 3.1: inject-memory all-success path ─────────────────────────

class TestPreservationInjectMemoryAllSuccess:
    """Property 2: Preservation — inject-memory all-success path unchanged (req 3.1)."""

    def test_all_success_returns_correct_response(self):
        """For any batch where all writes succeed, returns InjectResponse(written=N, failed=0, errors=[])."""
        from models.review import MemoryEntryInput

        async def mock_write_success(entry) -> bool:
            return True

        entries = [
            MemoryEntryInput(category="Team Convention", description=f"entry {i}")
            for i in range(5)
        ]

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write_success):
                from main import inject_memory
                from models.review import InjectRequest
                return await inject_memory(InjectRequest(entries=entries))

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.written == 5
        assert result.failed == 0
        assert result.errors == []

    def test_empty_batch_returns_zero_written(self):
        """Edge case: empty batch returns written=0, failed=0."""
        async def run():
            from main import inject_memory
            from models.review import InjectRequest
            return await inject_memory(InjectRequest(entries=[]))

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.written == 0
        assert result.failed == 0
        assert result.errors == []


# ── Preservation 3.5: _update_memory all-success path ────────────────────────

class TestPreservationUpdateMemoryAllSuccess:
    """Property 2: Preservation — _update_memory all-success path unchanged (req 3.5)."""

    def test_all_success_returns_zero(self):
        """When all writes succeed, _update_memory returns 0 (no failures)."""
        from models.review import ReviewOutput, ReviewRequest

        async def mock_write_success(entry) -> bool:
            return True

        request = ReviewRequest(code="x = 1", contributor="alice")
        review = ReviewOutput(
            critical_issues=["issue1"],
            convention_violations=["violation1"],
            contributor_patterns=[],
            positive_signals=[],
            summary="Good code. Minor issues.",
        )

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write_success):
                from agent.workflow import _update_memory
                return await _update_memory(request, review)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result == 0

    def test_skips_failed_reviews(self):
        """_update_memory skips writing when review.error is set (existing behavior)."""
        from models.review import ReviewOutput, ReviewRequest

        write_calls = []

        async def mock_write(entry) -> bool:
            write_calls.append(entry)
            return True

        request = ReviewRequest(code="x = 1", contributor="alice")
        review = ReviewOutput(
            critical_issues=[],
            convention_violations=[],
            contributor_patterns=[],
            positive_signals=[],
            summary="Failed review.",
            error="LLM unavailable",
        )

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write):
                from agent.workflow import _update_memory
                return await _update_memory(request, review)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert len(write_calls) == 0, "Should not write entries for failed reviews"
        # After fix, returns 0 (no failures attempted)
        assert result == 0
