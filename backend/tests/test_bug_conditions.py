"""Bug condition exploration tests — run on UNFIXED code to confirm bugs exist.

Property 1: Bug Condition — Four Backend Bugs
These tests are EXPECTED TO FAIL on unfixed code. Failure confirms the bugs exist.
After the fix is applied, all tests should PASS.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Bug 1: Syntax Error in hindsight.py ──────────────────────────────────────

class TestBug1SyntaxError:
    """Property 1: Bug Condition — hindsight.py parses without SyntaxError."""

    def test_hindsight_imports_without_syntax_error(self):
        """isBugCondition_1: 'async def query_memory' missing from source.
        EXPECTED OUTCOME on unfixed code: SyntaxError raised.
        EXPECTED OUTCOME after fix: import succeeds.
        """
        # Remove cached module to force re-import
        for key in list(sys.modules.keys()):
            if "hindsight" in key:
                del sys.modules[key]
        try:
            import agent.hindsight as hindsight  # noqa: F401
        except SyntaxError as exc:
            pytest.fail(
                f"Bug 1 confirmed: SyntaxError on import — {exc}\n"
                "Counterexample: 'async def query_memory' signature line is missing."
            )

    def test_query_memory_is_coroutine_function(self):
        """query_memory must be an awaitable coroutine function after fix."""
        import agent.hindsight as hindsight
        assert inspect.iscoroutinefunction(hindsight.query_memory), (
            "Bug 1 confirmed: query_memory is not a coroutine function."
        )


# ── Bug 2: Blocking Event Loop in groq_client.py ─────────────────────────────

class TestBug2BlockingEventLoop:
    """Property 1: Bug Condition — Groq calls do not block the event loop."""

    def test_concurrent_calls_run_in_parallel(self):
        """isBugCondition_2: client.chat.completions.create not wrapped in asyncio.to_thread.
        EXPECTED OUTCOME on unfixed code: total time ~200ms (sequential).
        EXPECTED OUTCOME after fix: total time ~100ms (concurrent).
        """
        import agent.groq_client as groq_client

        call_count = 0

        def slow_create(**kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # simulate 100ms Groq latency
            mock_resp = MagicMock()
            mock_resp.choices[0].message.tool_calls = None
            mock_resp.choices[0].message.content = '{"critical_issues":[],"convention_violations":[],"contributor_patterns":[],"positive_signals":[],"summary":"ok"}'
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = slow_create

        async def run():
            with patch.object(groq_client, "_client", return_value=mock_client):
                start = time.monotonic()
                await asyncio.gather(
                    groq_client.call_with_tools("sys", "user", []),
                    groq_client.call_with_tools("sys", "user", []),
                )
                elapsed = time.monotonic() - start
            return elapsed

        elapsed = asyncio.get_event_loop().run_until_complete(run())
        assert elapsed < 0.15, (
            f"Bug 2 confirmed: two concurrent calls took {elapsed:.3f}s (expected <0.15s). "
            "Counterexample: calls are sequential — event loop is blocked."
        )


# ── Bug 3: inject-memory Continues After Failure ─────────────────────────────

class TestBug3InjectMemoryContinuesAfterFailure:
    """Property 1: Bug Condition — inject-memory halts on first write failure."""

    def test_loop_halts_after_first_failure(self):
        """isBugCondition_3: write(batch[N])=False AND write(batch[N+1]) was attempted.
        EXPECTED OUTCOME on unfixed code: write_memory called 3 times.
        EXPECTED OUTCOME after fix: write_memory called exactly 2 times.
        """
        from models.review import MemoryEntryInput

        call_log: list[int] = []

        async def mock_write(entry: MemoryEntryInput) -> bool:
            call_log.append(len(call_log))
            # entry index 1 (second entry) fails
            return len(call_log) != 2

        entries = [
            MemoryEntryInput(category="Team Convention", description=f"entry {i}")
            for i in range(3)
        ]

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write):
                from fastapi.testclient import TestClient
                # Import app after patching
                import main as app_module
                from main import inject_memory
                from models.review import InjectRequest
                req = InjectRequest(entries=entries)
                result = await inject_memory(req)
            return result, len(call_log)

        result, calls = asyncio.get_event_loop().run_until_complete(run())
        assert calls == 2, (
            f"Bug 3 confirmed: write_memory called {calls} times (expected 2). "
            "Counterexample: loop continued past the first failure."
        )
        assert result.written == 1
        assert result.failed == 1

    def test_all_success_batch_unchanged(self):
        """Preservation: all-success batch still returns written=N, failed=0."""
        from models.review import MemoryEntryInput

        async def mock_write_success(entry: MemoryEntryInput) -> bool:
            return True

        entries = [
            MemoryEntryInput(category="Team Convention", description=f"entry {i}")
            for i in range(3)
        ]

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write_success):
                from main import inject_memory
                from models.review import InjectRequest
                req = InjectRequest(entries=entries)
                return await inject_memory(req)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.written == 3
        assert result.failed == 0
        assert result.errors == []


# ── Bug 4: Silent Failure in Stage 7 ─────────────────────────────────────────

class TestBug4SilentFailureStage7:
    """Property 1: Bug Condition — _update_memory surfaces write failures."""

    def test_update_memory_returns_failure_count(self):
        """isBugCondition_4: write_result=False AND failure not surfaced to caller.
        EXPECTED OUTCOME on unfixed code: _update_memory returns None.
        EXPECTED OUTCOME after fix: _update_memory returns non-zero int.
        """
        from models.review import ReviewOutput, ReviewRequest

        async def mock_write_fail(entry) -> bool:
            return False

        request = ReviewRequest(code="x = 1", contributor="alice")
        review = ReviewOutput(
            critical_issues=["issue1"],
            convention_violations=[],
            contributor_patterns=[],
            positive_signals=[],
            summary="Test review. Fix this.",
        )

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write_fail):
                from agent.workflow import _update_memory
                return await _update_memory(request, review)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result is not None and result > 0, (
            f"Bug 4 confirmed: _update_memory returned {result!r} (expected non-zero int). "
            "Counterexample: write failures are silently discarded."
        )

    def test_update_memory_returns_zero_on_all_success(self):
        """Preservation: all-success path returns 0."""
        from models.review import ReviewOutput, ReviewRequest

        async def mock_write_success(entry) -> bool:
            return True

        request = ReviewRequest(code="x = 1", contributor="alice")
        review = ReviewOutput(
            critical_issues=["issue1"],
            convention_violations=[],
            contributor_patterns=[],
            positive_signals=[],
            summary="Test review. Fix this.",
        )

        async def run():
            import agent.hindsight as hindsight
            with patch.object(hindsight, "write_memory", side_effect=mock_write_success):
                from agent.workflow import _update_memory
                return await _update_memory(request, review)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result == 0, (
            f"Preservation violated: _update_memory returned {result!r} on all-success (expected 0)."
        )
