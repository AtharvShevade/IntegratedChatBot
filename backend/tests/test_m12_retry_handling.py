"""M-12: bounded, backoff-based retry for genuinely transient Ollama
failures (connection drop, connect/read/write/pool timeout, 502/503/504),
added at the single shared transport point (_post_with_retry(), used by both
_call_ollama() and extract_intent_entities_llm() in
backend/services/llm_service.py). Permanent/deterministic failures (any
other HTTP status, a JSON error, etc.) are never retried.

This does not touch or duplicate the pre-existing retry logic in
backend/i18n/translator.py or llm_service._normalize_llm_action, which are
left exactly as they were.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from backend.services import llm_service


def _response(status_code: int = 200, payload: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload or {"message": {"content": "ok"}},
        request=httpx.Request("POST", "http://fake/api/chat"),
    )


class _ScriptedClient:
    """Each call to .post() pops and executes the next scripted action:
    an exception to raise, or an httpx.Response to return."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def post(self, url, json=None, timeout=None):
        self.calls += 1
        action = self.script.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Deterministic, instant tests -- the backoff delay itself is not
    what's under test, only that it's bounded and that a sleep happens
    between retry attempts."""
    sleeps = []

    async def _fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(llm_service.asyncio, "sleep", _fake_sleep)
    return sleeps


def _patch_client(monkeypatch, client):
    @asynccontextmanager
    async def _scope():
        yield client
    monkeypatch.setattr(llm_service, "client_scope", _scope)


class TestTransientFailureThenSuccess:
    def test_connect_error_then_success_returns_the_successful_response(self, monkeypatch):
        client = _ScriptedClient([httpx.ConnectError("refused"), _response()])
        _patch_client(monkeypatch, client)

        resp = asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))

        assert resp.status_code == 200
        assert client.calls == 2

    def test_503_then_success_returns_the_successful_response(self, monkeypatch):
        bad = _response(503)
        try:
            bad.raise_for_status()
        except httpx.HTTPStatusError as exc:
            bad_exc = exc
        client = _ScriptedClient([bad_exc, _response()])
        # _post_with_retry calls raise_for_status() itself on each attempt's
        # response -- simulate that by scripting the raised exception directly.
        _patch_client(monkeypatch, client)

        resp = asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))
        assert resp.status_code == 200
        assert client.calls == 2


class TestRetriesExhausted:
    def test_persistent_transient_failure_fails_cleanly_after_max_retries(self, monkeypatch):
        failures = [httpx.ConnectError("refused")] * (llm_service.OLLAMA_MAX_RETRIES + 1)
        client = _ScriptedClient(failures)
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.ConnectError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))

        # Exactly max_retries+1 attempts were made -- no more, no fewer.
        assert client.calls == llm_service.OLLAMA_MAX_RETRIES + 1

    def test_call_ollama_fails_cleanly_and_raises_after_retries_exhausted(self, monkeypatch):
        """End-to-end through _call_ollama(): existing final error behavior
        (raise, with a warning logged) is preserved after retries exhaust."""
        failures = [httpx.ConnectError("refused")] * (llm_service.OLLAMA_MAX_RETRIES + 1)
        client = _ScriptedClient(failures)
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.ConnectError):
            asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))


class TestPermanentFailureNotRetried:
    def test_400_bad_request_is_not_retried(self, monkeypatch):
        bad = _response(400)
        try:
            bad.raise_for_status()
        except httpx.HTTPStatusError as exc:
            bad_exc = exc
        client = _ScriptedClient([bad_exc, _response()])  # a retry would "succeed" -- it must not happen
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))

        assert client.calls == 1  # no retry attempted

    def test_json_decode_error_is_not_retried(self, monkeypatch):
        class _BadJsonClient:
            calls = 0
            async def post(self, url, json=None, timeout=None):
                _BadJsonClient.calls += 1
                raise ValueError("not json")

        client = _BadJsonClient()
        _patch_client(monkeypatch, client)

        with pytest.raises(ValueError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))
        assert client.calls == 1


class TestTimeoutHandling:
    def test_read_timeout_is_retried_like_other_transient_errors(self, monkeypatch):
        client = _ScriptedClient([httpx.ReadTimeout("slow"), _response()])
        _patch_client(monkeypatch, client)

        resp = asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))
        assert resp.status_code == 200
        assert client.calls == 2

    def test_per_attempt_timeout_value_is_passed_through_unchanged(self, monkeypatch):
        captured = []

        class _CapturingClient:
            async def post(self, url, json=None, timeout=None):
                captured.append(timeout)
                return _response()

        _patch_client(monkeypatch, _CapturingClient())
        asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 42.0, flow="test"))
        assert captured == [42.0]


class TestBoundedRetryCount:
    def test_retry_count_is_bounded_and_configurable(self, monkeypatch):
        monkeypatch.setattr(llm_service, "OLLAMA_MAX_RETRIES", 3)
        failures = [httpx.ConnectError("refused")] * 4
        client = _ScriptedClient(failures)
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.ConnectError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))
        assert client.calls == 4  # 1 initial + 3 retries, never more


class TestBackoffIsBoundedAndDeterministic:
    def test_backoff_delay_is_capped(self, _no_real_sleep, monkeypatch):
        monkeypatch.setattr(llm_service, "OLLAMA_MAX_RETRIES", 5)
        failures = [httpx.ConnectError("refused")] * 6
        client = _ScriptedClient(failures)
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.ConnectError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))

        assert len(_no_real_sleep) == 5  # one sleep between each of the 6 attempts
        for delay in _no_real_sleep:
            # base*2^attempt capped at _RETRY_MAX_DELAY_S, plus up to 25% jitter
            assert 0 <= delay <= llm_service._RETRY_MAX_DELAY_S * 1.25

    def test_no_sleep_after_the_final_failed_attempt(self, _no_real_sleep, monkeypatch):
        failures = [httpx.ConnectError("refused")] * (llm_service.OLLAMA_MAX_RETRIES + 1)
        client = _ScriptedClient(failures)
        _patch_client(monkeypatch, client)

        with pytest.raises(httpx.ConnectError):
            asyncio.run(llm_service._post_with_retry("http://fake/api/chat", {}, 5.0, flow="test"))

        # sleeps happen strictly BETWEEN attempts, never after the last one
        assert len(_no_real_sleep) == llm_service.OLLAMA_MAX_RETRIES


class TestNoDuplicateSideEffects:
    def test_retry_never_double_invokes_the_caller_on_eventual_success(self, monkeypatch):
        """_call_ollama() must return exactly once with exactly one parsed
        result, even though the underlying transport was called twice."""
        client = _ScriptedClient([httpx.ConnectError("refused"), _response(
            payload={"message": {"content": "single-result"}},
        )])
        _patch_client(monkeypatch, client)

        result = asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))
        assert result == "single-result"
        assert client.calls == 2  # the retry happened once, transparently


class TestExistingTimeoutConfigurationRespected:
    def test_chat_fallback_timeout_still_used_per_attempt(self, monkeypatch):
        captured = []

        class _CapturingClient:
            async def post(self, url, json=None, timeout=None):
                captured.append(timeout)
                return _response()

        _patch_client(monkeypatch, _CapturingClient())
        asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))
        assert captured == [llm_service.CHAT_FALLBACK_TIMEOUT]

    def test_extract_timeout_still_used_per_attempt(self, monkeypatch):
        captured = []

        class _CapturingClient:
            async def post(self, url, json=None, timeout=None):
                captured.append(timeout)
                return _response(payload={"message": {"content": '{"intent": null}'}})

        _patch_client(monkeypatch, _CapturingClient())
        asyncio.run(llm_service.extract_intent_entities_llm("some query"))
        assert captured == [llm_service.EXTRACT_TIMEOUT]
