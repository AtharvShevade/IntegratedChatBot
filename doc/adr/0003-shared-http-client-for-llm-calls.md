# 3. Shared httpx.AsyncClient for outbound LLM calls

## Status
Accepted

## Date
2026-10-04 (ADR written retroactively, describing a decision already
implemented in the codebase; the original decision date is not recorded
anywhere in the repository)

## Context

Every outbound call to Ollama from the async parts of the backend
(`backend/services/llm_service.py`'s `_call_ollama()` and
`extract_intent_entities_llm()`) originally opened a brand-new
`httpx.AsyncClient` per request (`async with httpx.AsyncClient(timeout=...)
as client:`), paying full TCP (and TLS, for an `https` `OLLAMA_BASE_URL`)
connection setup on every single call instead of reusing a warm connection
pool. Each call site also used a single scalar timeout value, which does
not distinguish "time to establish a connection" from "time to receive a
response" from "time to send the request body."

## Decision

Introduce one shared `httpx.AsyncClient`, created once in
`backend/main.py`'s FastAPI `lifespan` at process startup
(`backend/services/http_client.py`'s `init()`) and closed once at shutdown
(`aclose()`), instead of each call site constructing and tearing down its
own client per request. Call sites use `async with client_scope() as
client:` (an async context manager) rather than holding a plain reference
to the client directly.

Timeouts are split into four separate values — connect, read, write, pool
— via `httpx.Timeout`, configurable through
`LLM_HTTP_CONNECT_TIMEOUT`/`LLM_HTTP_READ_TIMEOUT`/`LLM_HTTP_WRITE_TIMEOUT`/
`LLM_HTTP_POOL_TIMEOUT` environment variables, while each call site still
passes its own existing, already-tuned total-timeout value
(`OLLAMA_CHAT_FALLBACK_TIMEOUT`, `OLLAMA_EXTRACT_TIMEOUT`, etc.) as a
per-request override, so the shared client's defaults are a ceiling, not a
replacement for call-site-specific budgets.

`client_scope()` exists specifically because a plain "get the client"
function cannot safely express two different lifetimes from one call: when
the FastAPI app's lifespan has run, the yielded client is the shared,
persistent one and must **not** be closed by the caller; when it hasn't
(a test or script invoking an LLM helper directly, without the app's
lifespan), a temporary client is created for that one call and **must** be
closed on exit, since an `httpx.AsyncClient` is bound to the event loop
active when it is constructed and cannot safely be reused across separate
`asyncio.run()` calls (each of which tears down its own event loop).
`client_scope()` picks the correct behavior automatically.

## Alternatives considered

No in-repo record of alternatives considered was found for the original
per-request-client pattern being replaced. For the shared-client design
itself, the two discarded intermediate designs are visible directly in the
module's own commit history within this session's work (not a
pre-existing historical record): a bare `get_client()` function that
cached a fallback (non-lifespan) client at module level was found to
self-deadlock on a non-reentrant lock, and a later version of the same
function was found to leak that fallback client (never closed) and, in a
different revision, to hand back a client bound to an already-closed event
loop across separate `asyncio.run()` calls. `client_scope()`'s
context-manager design was adopted specifically to eliminate both failure
modes structurally rather than patching them case by case.

## Consequences

- Production LLM calls (which always run inside the FastAPI app's single
  long-lived event loop) reuse one warm connection pool for the life of
  the process, reducing per-call connection-setup overhead.
- Any test or script that calls `_call_ollama()`/`extract_intent_entities_llm()`
  outside the FastAPI app's lifespan gets a correct, non-leaking,
  non-cross-loop-reused client automatically, at the cost of not
  benefiting from connection reuse in that context (acceptable, since
  that path is not the production hot path).
- `backend/i18n/translator.py`'s own, separate retry/timeout logic was
  deliberately **not** migrated onto this shared client — it is a
  different, already-tuned mechanism (shares one wall-clock budget across
  a bounded retry) and migrating it was judged to carry more regression
  risk than benefit without also re-validating its specific timeout
  behavior.
- A small number of retries for genuinely transient failures (connection
  drop, timeout, `502`/`503`/`504`) were later layered on top of this
  shared-client infrastructure (`_post_with_retry()` in
  `llm_service.py`), rather than introducing a second retry/backoff
  library or a second HTTP client abstraction.
