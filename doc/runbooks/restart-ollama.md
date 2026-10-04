# Runbook: Restart / verify Ollama

## How the application connects to Ollama

All LLM calls go through `OLLAMA_BASE_URL` (centralized in
`backend/services/llm_config.py`, defaulting to `http://127.0.0.1:11434` if
unset — but **this deployment's `.env` sets it explicitly**, so check the
real running value before assuming the default applies). The shared HTTP
client (`backend/services/http_client.py`, see
[ADR 0003](../adr/0003-shared-http-client-for-llm-calls.md)) is created once
at backend startup and reused for the process's lifetime.

## Local vs configured remote/proxy behavior

Confirm which of these applies to the deployment you're operating on —
**do not assume**:

- **Local Ollama**: `OLLAMA_BASE_URL` points at `127.0.0.1`/`localhost`.
  You control the Ollama process directly.
- **Remote/proxied Ollama**: `OLLAMA_BASE_URL` points at a non-local host
  (e.g. an `http://<ip>/OllamaProxy`-style address). In this case you
  **cannot restart the Ollama service from this repository or this
  machine** — it is operated elsewhere. Your available action is limited
  to verifying reachability and escalating to whoever operates that proxy.

The SQL Agent additionally resolves its own Ollama target
(`SQL_OLLAMA_MODEL` / the agent-local `.env` under `backend/sql_agent/`,
see `backend/sql_agent/_bootstrap.py`) — confirm whether it points at the
same endpoint as the main chatbot's `OLLAMA_BASE_URL` or a different one
before assuming a restart affects both.

## How to restart it safely (local Ollama only)

1. Check what's currently using it isn't mid-request if avoidable (there is
   no graceful-drain mechanism in this repo for Ollama itself — a restart
   will fail in-flight LLM calls, which the backend will report as request
   failures to the chat UI).
2. Restart the Ollama service using Ollama's own tooling for your platform
   (e.g. `ollama serve`, or your OS service manager if Ollama is installed
   as a service) — **this repository does not define or script that
   restart itself**; use Ollama's own documented restart procedure for the
   host OS.
3. Wait for Ollama to report ready (its own CLI/API indicates this; not
   covered by this repo).

If the deployment uses a remote/proxied Ollama, restarting is **not a
local operation** — contact whoever operates that proxy instead.

## How to verify model availability

The backend's own readiness check already tests exactly this:

```
GET /health/ready
```

Look at the `checks.ollama` field in the response (`backend/main.py`'s
`_check_ollama()` — a lightweight reachability GET against
`OLLAMA_BASE_URL`, not a full model-list check). `true` means Ollama
answered with a non-5xx status within the short readiness-check timeout
(`_READINESS_CHECK_TIMEOUT_S`, 2 seconds) — it does **not** confirm every
model this deployment needs is actually pulled.

To confirm specific models are available, use Ollama's own model-listing
mechanism (e.g. its CLI or `/api/tags` endpoint) against the same
`OLLAMA_BASE_URL`, and compare against the models this deployment's `.env`
configures: `OLLAMA_MODEL`, `OLLAMA_EXTRACT_MODEL`, `OLLAMA_COMPARE_MODEL`,
and the SQL Agent's own model setting.

## How to verify the chatbot afterward

1. `GET /health/ready` — confirm `checks.ollama` is `true`.
2. Send a simple chat message through the UI (or `POST /chat`) that is
   known to exercise the LLM path (e.g. a plain-language question that
   misses the regex classifier) and confirm a sensible response, not a
   generic failure message.
3. If the SQL Agent is in scope, run one known-good natural-language
   database question and confirm SQL is generated and executed
   successfully.
