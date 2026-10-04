"""L-03: token usage and response truncation are now recorded consistently
across every Ollama call site, via the shared `backend.tools.llm_telemetry`
helper (and an equivalent inline version in the vendored
`backend/sql_agent/sqlcore/sql_generator.py`, which stays self-contained rather
than importing from `backend.*`).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from backend.tools.llm_telemetry import TokenInfo, extract_token_info


def _fake_client_scope(fake_client):
    """Matches backend.services.http_client.client_scope()'s async
    context-manager shape, for monkeypatching llm_service.client_scope."""
    @asynccontextmanager
    async def _scope():
        yield fake_client
    return _scope


class TestExtractTokenInfo:
    def test_full_response_extracts_both_counts_and_not_truncated(self):
        info = extract_token_info({
            "prompt_eval_count": 150, "eval_count": 42, "done_reason": "stop",
        })
        assert info.prompt_tokens == 150
        assert info.completion_tokens == 42
        assert info.done_reason == "stop"
        assert info.truncated is False

    def test_done_reason_length_means_truncated(self):
        info = extract_token_info({
            "prompt_eval_count": 150, "eval_count": 256, "done_reason": "length",
        })
        assert info.truncated is True

    def test_missing_fields_degrade_to_none_not_an_exception(self):
        info = extract_token_info({})
        assert info.prompt_tokens is None
        assert info.completion_tokens is None
        assert info.done_reason is None
        assert info.truncated is False

    def test_none_input_does_not_crash(self):
        info = extract_token_info(None)
        assert info == TokenInfo(None, None, None, False)

    def test_malformed_input_does_not_crash(self):
        info = extract_token_info({"prompt_eval_count": "not-an-int", "eval_count": None})
        assert info.prompt_tokens is None
        assert info.completion_tokens is None

    def test_as_log_str_never_raises_and_includes_all_fields(self):
        info = extract_token_info({"prompt_eval_count": 10, "eval_count": 5, "done_reason": "stop"})
        s = info.as_log_str()
        assert "prompt_tokens=10" in s
        assert "completion_tokens=5" in s
        assert "truncated=False" in s


class TestLlmServiceLogsTokenInfo:
    def test_call_ollama_logs_token_info_on_success(self, monkeypatch, caplog):
        import backend.services.llm_service as llm_service

        class _FakeResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "message": {"content": "hello"},
                    "prompt_eval_count": 20, "eval_count": 5, "done_reason": "stop",
                }

        class _FakeClient:
            async def post(self, *a, **kw): return _FakeResponse()

        # L-01: _call_ollama() now gets its client via client_scope() (the
        # shared app-lifespan client) instead of constructing its own
        # httpx.AsyncClient per call.
        monkeypatch.setattr(llm_service, "client_scope", _fake_client_scope(_FakeClient()))

        import asyncio
        with caplog.at_level(logging.INFO, logger="backend.services.llm_service"):
            result = asyncio.run(llm_service._call_ollama("hi", "system prompt"))
        assert result == "hello"
        assert any("prompt_tokens=20" in r.message for r in caplog.records)
        assert any("completion_tokens=5" in r.message for r in caplog.records)

    def test_call_ollama_does_not_crash_when_ollama_omits_token_fields(self, monkeypatch):
        import backend.services.llm_service as llm_service

        class _FakeResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "hello"}}  # no token fields at all

        class _FakeClient:
            async def post(self, *a, **kw): return _FakeResponse()

        monkeypatch.setattr(llm_service, "client_scope", _fake_client_scope(_FakeClient()))

        import asyncio
        result = asyncio.run(llm_service._call_ollama("hi", "system prompt"))
        assert result == "hello"  # must not crash despite missing token metadata


class TestExistingLlmOutputUnchanged:
    def test_call_ollama_return_value_unaffected_by_telemetry(self, monkeypatch):
        """Confirms L-03 is purely observability -- the actual LLM output
        returned to callers is byte-for-byte identical to before."""
        import backend.services.llm_service as llm_service

        class _FakeResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {
                    "message": {"content": "the exact same response text"},
                    "prompt_eval_count": 1, "eval_count": 1, "done_reason": "stop",
                }

        class _FakeClient:
            async def post(self, *a, **kw): return _FakeResponse()

        monkeypatch.setattr(llm_service, "client_scope", _fake_client_scope(_FakeClient()))

        import asyncio
        result = asyncio.run(llm_service._call_ollama("hi", "system prompt"))
        assert result == "the exact same response text"
