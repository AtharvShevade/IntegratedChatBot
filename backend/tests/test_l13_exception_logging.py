"""L-13: /health/ready's dependency checks already failed safe (an exception
means "report not ready", never a crash, never anything beyond a boolean in
the client-facing response) -- what they were missing was the traceback an
operator needs to distinguish "Oracle is down" from "a bug in this check
itself". `logger.debug("... %s", exc)` (no traceback, and at a level that
may not even be enabled in production) is now `logger.warning(..., exc_info=True)`.

Also confirms the genuinely-expected control-flow exception swallows
elsewhere (e.g. "does this text parse as a date?") were deliberately left
untouched, since turning those into noisy errors is explicitly out of scope.
"""
from __future__ import annotations

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _reset_readiness_cache():
    main_module._READINESS_CACHE["result"] = None
    main_module._READINESS_CACHE["checked_at"] = 0.0
    yield
    main_module._READINESS_CACHE["result"] = None
    main_module._READINESS_CACHE["checked_at"] = 0.0


class TestReadinessChecksLogWithTraceback:
    def test_oracle_check_failure_logs_with_exc_info(self, monkeypatch, caplog):
        def _boom():
            raise RuntimeError("connection refused")
        # Patch what _check_oracle_sync() itself calls, not the function
        # being tested -- replacing _check_oracle_sync directly would skip
        # its own try/except+logging entirely.
        import backend.sql_agent.sqlcore.executor as executor_module
        monkeypatch.setattr(executor_module, "get_connection", _boom)
        with caplog.at_level(logging.WARNING, logger="backend.main"):
            result = main_module._check_oracle_sync()
        assert result is False
        matching = [r for r in caplog.records if "Oracle check failed" in r.message]
        assert matching, "expected a warning log for the Oracle check failure"
        assert matching[0].exc_info is not None, "traceback must be attached via exc_info"

    def test_ollama_check_failure_logs_with_exc_info(self, monkeypatch, caplog):
        class _FailingClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                return False
            async def get(self, *a, **k):
                raise RuntimeError("connection refused")

        monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda **k: _FailingClient())
        with caplog.at_level(logging.WARNING):
            result = asyncio.run(main_module._check_ollama())
        assert result is False
        matching = [r for r in caplog.records if "Ollama check failed" in r.message]
        assert matching
        assert matching[0].exc_info is not None

    def test_data_repo_path_unexpected_failure_logs_with_exc_info(self, monkeypatch, caplog):
        def _boom():
            raise AttributeError("boom")
        monkeypatch.setattr(main_module.os.path, "isdir", _boom)
        with caplog.at_level(logging.WARNING):
            result = main_module._check_data_repo_path()
        assert result is False
        matching = [r for r in caplog.records if "Data repo path check failed" in r.message]
        assert matching
        assert matching[0].exc_info is not None

    def test_check_oracle_wrapper_timeout_logs_with_exc_info(self, monkeypatch, caplog):
        """L-13: _check_oracle()'s own except (a timeout from
        asyncio.wait_for, distinct from _check_oracle_sync()'s own already-
        logged except) previously returned False with zero logging."""
        async def _never_finishes():
            await asyncio.sleep(10)
            return True

        monkeypatch.setattr(main_module.asyncio, "wait_for",
                             lambda coro, timeout: _raise_timeout(coro))
        with caplog.at_level(logging.WARNING):
            result = asyncio.run(main_module._check_oracle())
        assert result is False
        matching = [r for r in caplog.records if "Oracle check timed out" in r.message]
        assert matching, "expected a warning log for the _check_oracle wrapper's own failure"
        assert matching[0].exc_info is not None


async def _raise_timeout(coro):
    coro.close()
    raise asyncio.TimeoutError()


class TestFailOpenBehaviorUnchanged:
    """The readiness endpoint must still report not_ready/503 on a
    dependency failure -- L-13 only changes logging, not this behavior."""

    def test_oracle_failure_still_reports_not_ready_with_503(self, monkeypatch):
        monkeypatch.setattr(main_module, "_check_oracle", lambda: _async_false())
        monkeypatch.setattr(main_module, "_check_ollama", lambda: _async_true())
        monkeypatch.setattr(main_module, "_check_stt", lambda: _async_none())
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)

        res = client.get("/health/ready")
        assert res.status_code == 503
        body = res.json()
        assert body["ready"] is False
        assert body["checks"]["oracle"] is False

    def test_response_body_never_contains_a_traceback(self, monkeypatch):
        monkeypatch.setattr(main_module, "_check_oracle", lambda: _async_false())
        monkeypatch.setattr(main_module, "_check_ollama", lambda: _async_true())
        monkeypatch.setattr(main_module, "_check_stt", lambda: _async_none())
        monkeypatch.setattr(main_module, "_check_data_repo_path", lambda: True)

        res = client.get("/health/ready")
        body_text = res.text.lower()
        assert "traceback" not in body_text
        assert "file \"" not in body_text


async def _async_false():
    return False


async def _async_true():
    return True


async def _async_none():
    return None


class TestExpectedControlFlowExceptionsUntouched:
    """These are genuine "try to parse, fall back if it doesn't parse"
    control-flow paths (not unexpected bugs) -- confirm their existing
    silent-fallback behavior still works, since L-13 deliberately does not
    touch them."""

    def test_unparseable_date_text_returns_false_not_raise(self):
        from backend.agent.conversational import _is_plausible_date
        assert _is_plausible_date("not a date at all, just words, zzz qqq") is False

    def test_guided_boundary_classifier_falls_through_silently_on_error(self, monkeypatch):
        from backend.i18n import boundary
        # Force the inner try block to raise -- must still return None
        # (the documented "optimisation, not a gate" fallback) rather than
        # propagating.
        import backend.guided as guided_module
        monkeypatch.setattr(guided_module, "GUIDED_ACTIONS", None)  # `in None` raises TypeError
        result = boundary._inbound_skip_reason("some alphabetic text")
        assert result is None
