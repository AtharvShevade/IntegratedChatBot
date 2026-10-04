"""L-01: a shared httpx.AsyncClient for outbound LLM (Ollama) calls, created
at FastAPI startup (backend/main.py's lifespan) and closed at shutdown,
instead of each async call site (backend/services/llm_service.py's
_call_ollama / extract_intent_entities_llm) opening a brand-new AsyncClient
per request.

Cleanup (post-review): the original `get_client()` function returned an
uncached, never-closed client in the fallback (non-lifespan) case --
leaking it. `client_scope()` (an async context manager) replaces it: it
yields the shared client without closing it when init() has run, or a
temporary client it closes on exit otherwise, so the fallback case can
never leak regardless of how it's called.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from backend.services import http_client


@pytest.fixture(autouse=True)
def _reset_shared_client():
    http_client._client = None
    yield
    http_client._client = None


class TestLifecycle:
    def test_init_creates_a_client(self):
        client = http_client.init()
        assert isinstance(client, httpx.AsyncClient)
        assert http_client._client is client

    def test_init_replaces_any_existing_client(self):
        first = http_client.init()
        second = http_client.init()
        assert first is not second

    def test_aclose_closes_and_clears_the_client(self):
        client = http_client.init()
        assert client.is_closed is False
        asyncio.run(http_client.aclose())
        assert client.is_closed is True
        assert http_client._client is None

    def test_aclose_is_a_no_op_when_never_initialized(self):
        assert http_client._client is None
        asyncio.run(http_client.aclose())  # must not raise


class TestConfigurableTimeouts:
    def test_default_timeout_values(self, monkeypatch):
        monkeypatch.delenv("LLM_HTTP_CONNECT_TIMEOUT", raising=False)
        monkeypatch.delenv("LLM_HTTP_READ_TIMEOUT", raising=False)
        monkeypatch.delenv("LLM_HTTP_WRITE_TIMEOUT", raising=False)
        monkeypatch.delenv("LLM_HTTP_POOL_TIMEOUT", raising=False)
        timeout = http_client._default_timeout()
        assert timeout.connect == 5.0
        assert timeout.read == 180.0
        assert timeout.write == 30.0
        assert timeout.pool == 5.0

    def test_env_override_is_applied(self, monkeypatch):
        monkeypatch.setenv("LLM_HTTP_CONNECT_TIMEOUT", "2.5")
        monkeypatch.setenv("LLM_HTTP_READ_TIMEOUT", "60")
        timeout = http_client._default_timeout()
        assert timeout.connect == 2.5
        assert timeout.read == 60.0

    def test_client_is_created_with_the_configured_timeout(self, monkeypatch):
        monkeypatch.setenv("LLM_HTTP_CONNECT_TIMEOUT", "3")
        client = http_client.init()
        assert client.timeout.connect == 3.0


class TestAppStartupAndShutdownWireUpTheSharedClient:
    """The real `lifespan()` also warms up Ollama/SentenceTransformer/FAISS
    (slow, network-dependent) -- not re-run here. This confirms its own
    source wires init()/aclose() at the right points instead, which is the
    actual L-01 behavior under test."""

    def test_lifespan_source_calls_init_on_startup_and_aclose_on_shutdown(self):
        import inspect
        from backend import main as main_module
        source = inspect.getsource(main_module.lifespan)
        assert "_http_client.init()" in source
        assert "_http_client.aclose()" in source
        # aclose() must run in the `finally` block so it still runs if
        # startup raises partway through.
        finally_block = source.split("finally:", 1)[1]
        assert "_http_client.aclose()" in finally_block


class TestClientScopeSharedCase:
    """client_scope() during the normal FastAPI-app lifespan (init() has
    run): yields the shared client and must NOT close it."""

    def test_yields_the_shared_client(self):
        shared = http_client.init()

        async def _run():
            async with http_client.client_scope() as client:
                assert client is shared

        asyncio.run(_run())

    def test_does_not_close_the_shared_client_on_exit(self):
        shared = http_client.init()

        async def _run():
            async with http_client.client_scope() as client:
                pass

        asyncio.run(_run())
        assert shared.is_closed is False

    def test_repeated_calls_reuse_the_same_shared_client(self):
        shared = http_client.init()
        seen = []

        async def _run():
            async with http_client.client_scope() as client:
                seen.append(client)
            async with http_client.client_scope() as client:
                seen.append(client)

        asyncio.run(_run())
        assert seen[0] is seen[1] is shared


class TestClientScopeFallbackCase:
    """client_scope() before init() has run: must create a temporary client
    AND close it when the `async with` block exits -- this is exactly the
    leak the cleanup fixes."""

    def test_yields_a_usable_client(self):
        assert http_client._client is None

        async def _run():
            async with http_client.client_scope() as client:
                assert isinstance(client, httpx.AsyncClient)
                assert client.is_closed is False

        asyncio.run(_run())

    def test_closes_the_temporary_client_on_exit(self):
        assert http_client._client is None
        captured = {}

        async def _run():
            async with http_client.client_scope() as client:
                captured["client"] = client

        asyncio.run(_run())
        assert captured["client"].is_closed is True

    def test_closes_the_temporary_client_even_on_exception(self):
        assert http_client._client is None
        captured = {}

        async def _run():
            with pytest.raises(ValueError):
                async with http_client.client_scope() as client:
                    captured["client"] = client
                    raise ValueError("boom")

        asyncio.run(_run())
        assert captured["client"].is_closed is True

    def test_never_mutates_the_module_level_shared_client(self):
        """The fallback temporary client must never be cached into
        _client -- otherwise it would be reused (and found already closed)
        on a later call, reproducing the original cross-event-loop bug."""
        asyncio.run(_run_noop_scope())
        assert http_client._client is None


async def _run_noop_scope():
    async with http_client.client_scope():
        pass


class TestCrossEventLoopRegression:
    """Deterministic regression test for the originally reported bug: a
    cached client bound to one asyncio.run() event loop must never be
    handed back after that loop has closed and a second, independent
    asyncio.run() call starts. No Ollama/network access required -- each
    "call" below is just entering/exiting client_scope() inside its own
    asyncio.run(), matching exactly how a test or script outside the
    FastAPI app's lifespan drives llm_service's async helpers."""

    def test_fallback_client_survives_across_separate_event_loops(self):
        assert http_client._client is None  # init() never ran -- fallback path

        results = []

        async def _one_call():
            async with http_client.client_scope() as client:
                # client_scope()'s own __aexit__ closes this client before
                # _one_call() returns -- if that client were secretly the
                # one created (and already closed) by a PRIOR asyncio.run()
                # call, closing it again here would surface the loop
                # mismatch (httpx/anyio operations on a transport bound to
                # a different, already-closed loop raise "Event loop is
                # closed" rather than silently succeeding).
                results.append(client)

        # Each asyncio.run() creates a brand-new event loop and fully closes
        # it when the call returns, closing every loop-bound resource with it.
        asyncio.run(_one_call())
        asyncio.run(_one_call())
        asyncio.run(_one_call())

        assert len(results) == 3
        # Each call got its own client (never reused across loops) and each
        # one is independently closed -- proving no stale, loop-bound client
        # was ever handed back to a later, unrelated event loop.
        assert results[0] is not results[1]
        assert results[1] is not results[2]
        for client in results:
            assert client.is_closed is True

    def test_shared_client_is_exempt_because_it_lives_in_one_loop_only(self):
        """Contrast case: once init() has run (the real production path),
        the SAME client is correctly reused across calls -- this is safe
        ONLY because the whole FastAPI app (and therefore every call to
        client_scope()) runs inside that one single long-lived event loop
        for the process's entire lifetime; init() is never called again
        mid-loop the way the fallback path's asyncio.run() boundary
        recreates a loop per call."""
        shared = http_client.init()

        async def _one_call():
            async with http_client.client_scope() as client:
                return client

        async def _two_calls_same_loop():
            first = await _one_call()
            second = await _one_call()
            return first, second

        first, second = asyncio.run(_two_calls_same_loop())
        assert first is second is shared
        assert shared.is_closed is False


class TestLlmServiceUsesTheSharedClient:
    def test_call_ollama_uses_client_scope_not_a_fresh_asyncclient(self, monkeypatch):
        """Reuses the SAME client object across two calls -- proving a new
        AsyncClient is not constructed per request."""
        from backend.services import llm_service

        seen_clients = []

        class _FakeResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "hi"}, "eval_count": 1, "prompt_eval_count": 1}

        class _FakeClient:
            async def post(self, *a, **k):
                seen_clients.append(self)
                return _FakeResponse()

        fake_client = _FakeClient()

        @asynccontextmanager
        async def _fake_scope():
            yield fake_client

        monkeypatch.setattr(llm_service, "client_scope", _fake_scope)

        asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))
        asyncio.run(llm_service._call_ollama(prompt="hi again", system="sys"))

        assert len(seen_clients) == 2
        assert seen_clients[0] is seen_clients[1] is fake_client

    def test_call_ollama_still_passes_its_own_timeout_budget(self, monkeypatch):
        from backend.services import llm_service

        captured = {}

        class _FakeResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {"message": {"content": "hi"}}

        class _FakeClient:
            async def post(self, url, json=None, timeout=None):
                captured["timeout"] = timeout
                return _FakeResponse()

        @asynccontextmanager
        async def _fake_scope():
            yield _FakeClient()

        monkeypatch.setattr(llm_service, "client_scope", _fake_scope)
        asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))
        assert captured["timeout"] == llm_service.CHAT_FALLBACK_TIMEOUT

    def test_call_ollama_against_the_real_fallback_client_scope_does_not_leak(self):
        """End-to-end (no mocking of client_scope itself): _call_ollama()
        run outside any FastAPI lifespan must still close whatever
        temporary client it used, even though it never calls aclose()
        itself -- client_scope()'s own cleanup must do it."""
        import httpx as _httpx
        from backend.services import llm_service

        assert http_client._client is None  # fallback path, like a bare script/test

        created_clients = []
        real_init = _httpx.AsyncClient

        class _TrackedClient(real_init):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                created_clients.append(self)

            async def post(self, *a, **k):
                class _FakeResponse:
                    def raise_for_status(self):
                        pass
                    def json(self):
                        return {"message": {"content": "hi"}}
                return _FakeResponse()

        import backend.services.http_client as http_client_module
        orig = http_client_module.httpx.AsyncClient
        http_client_module.httpx.AsyncClient = _TrackedClient
        try:
            asyncio.run(llm_service._call_ollama(prompt="hi", system="sys"))
        finally:
            http_client_module.httpx.AsyncClient = orig

        assert len(created_clients) == 1
        assert created_clients[0].is_closed is True
