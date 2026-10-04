"""L-01: shared httpx.AsyncClient for outbound LLM (Ollama) calls.

Before this module, each async LLM call site opened its own
`httpx.AsyncClient` per request (`async with httpx.AsyncClient(...) as
client:`), paying full TCP (+ TLS, for an https OLLAMA_BASE_URL) connection
setup on every single call instead of reusing a warm connection pool. This
module creates one client at FastAPI startup (see backend/main.py's
`lifespan`) and closes it at shutdown; call sites use
`async with client_scope() as client:` instead of constructing their own.

Falls back to a freshly-created, per-call client if accessed before
`init()` has run -- e.g. a unit test or script that calls an LLM helper
directly without the FastAPI app's lifespan ever running. This is
deliberate: an httpx.AsyncClient is bound to the event loop active when it's
created, and a caller outside the app's lifespan typically drives each call
through its own `asyncio.run()` (a fresh event loop every time) -- caching a
client across those would hand back a client bound to an already-closed
loop on the second call ("RuntimeError: Event loop is closed"). Only
`init()` (called once from the app's own long-lived event loop) produces
the persistent, reused client described above.

`client_scope()` is the single entry point callers use (an async context
manager) so that fallback case's temporary client is always closed when the
`async with` block exits -- a bare `get_client()` function returning that
same temporary client could never express "close this when you're done" to
a caller that (correctly, for the shared-client case) must NOT close what
it gets back. The context manager tells the difference itself: it closes
the client it yielded only when that client was created just for this one
call, never when it handed back the shared, persistent one.

Timeouts are split (connect/read/write/pool) via httpx.Timeout instead of
the single scalar every prior call site used, so a slow DNS/TCP handshake
and a slow model response are distinguished rather than sharing one budget.
Each LLM call site still passes its OWN read timeout (CHAT_FALLBACK_TIMEOUT,
EXTRACT_TIMEOUT, etc. -- unchanged) via `client.post(..., timeout=...)`,
since those per-call-site budgets encode real, already-tuned behavior
differences (e.g. the 12s chat-fallback leash vs. a 180s summary call) that
this shared-client change must not collapse into one value.
"""
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

_client: httpx.AsyncClient | None = None
_lock = threading.Lock()


def _default_timeout() -> httpx.Timeout:
    """Connect/write/pool timeouts are deliberately short and configurable
    -- these bound how long it takes to even START a call (DNS+TCP, or
    sending the request body), which should never need anywhere near as
    long as waiting for a model to finish generating. The read timeout here
    is just a client-level ceiling; per-call-site timeouts (passed to
    client.post(..., timeout=...)) remain the real, already-tuned budget
    for each endpoint and take precedence over this default."""
    return httpx.Timeout(
        connect=float(os.environ.get("LLM_HTTP_CONNECT_TIMEOUT", "5")),
        read=float(os.environ.get("LLM_HTTP_READ_TIMEOUT", "180")),
        write=float(os.environ.get("LLM_HTTP_WRITE_TIMEOUT", "30")),
        pool=float(os.environ.get("LLM_HTTP_POOL_TIMEOUT", "5")),
    )


def init() -> httpx.AsyncClient:
    """Called once from backend/main.py's lifespan at startup, from the
    app's own long-lived event loop. Replaces any existing client (idempotent
    for uvicorn --reload's double-startup, same guard convention as
    backend/utils/logger.py's _configured flag)."""
    global _client
    with _lock:
        _client = httpx.AsyncClient(timeout=_default_timeout())
        return _client


@asynccontextmanager
async def client_scope() -> AsyncIterator[httpx.AsyncClient]:
    """Yield a client for the duration of one call:

        async with client_scope() as client:
            resp = await client.post(...)

    If `init()` has run, yields the shared, persistent client and does NOT
    close it on exit (it outlives this one call -- see aclose(), called once
    at app shutdown). Otherwise (init() never ran -- a test or script using
    an LLM helper outside the FastAPI app's lifespan) creates a temporary
    client for just this call and closes it on exit, so it can never leak
    regardless of how many separate `asyncio.run()` event loops the caller
    drives its calls through."""
    client = _client
    if client is not None:
        yield client
        return
    temp_client = httpx.AsyncClient(timeout=_default_timeout())
    try:
        yield temp_client
    finally:
        await temp_client.aclose()


async def aclose() -> None:
    """Called once from backend/main.py's lifespan at shutdown."""
    global _client
    with _lock:
        client, _client = _client, None
    if client is not None:
        await client.aclose()
