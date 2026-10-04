# IntegratedChatBot

A chatbot embedded as an **iframe** inside a .NET regulatory-reporting web
app ("iDEAL", versions **5.5** and **6.0**). Users chat (text or voice) to
check report status, compare XBRL instances, query application metadata
(users/roles/schedules) stored as XML, or ask natural-language questions
against an Oracle banking-regulatory database via a vendored NL-to-SQL
agent.

This file is a short, practical entry point. For the full architecture
picture, read **[`doc/APP_OVERVIEW.md`](doc/APP_OVERVIEW.md)** first — most
of what's below links back to it rather than repeating it.

## 1. Project overview

```
.NET "iDEAL" web app (5.5 / 6.0)
        │  embeds as <iframe>
        ▼
React/Vite frontend  ──HTTP──▶  FastAPI backend  ──▶  Intent routing (local LLM via Ollama)
                                                       ├─ XBRL report tools ──▶ external .NET APIs
                                                       ├─ App "DB" Q&A ──▶ XML files (Users/Roles/Returns/...)
                                                       └─ SQL Agent (FAISS + Ollama) ──▶ Oracle DB
Voice input ──▶ remote Whisper service (speech-to-text)
```

See `doc/APP_OVERVIEW.md` for the full breakdown of each piece, and
`doc/adr/` for the architectural decisions behind the dual-dispatch intent
system, the vendored SQL Agent, the shared LLM HTTP client, and the 5.5/6.0
version split.

## 2. Repository structure

| Path | What it is |
|---|---|
| `backend/` | FastAPI app — entry point `backend/main.py` |
| `backend/sql_agent/` | Vendored NL-to-SQL engine (see [ADR 0002](doc/adr/0002-sql-agent-vendoring.md)) |
| `backend/db_qa/` | App "database" Q&A over XML files, incl. the intent taxonomy (see [ADR 0001](doc/adr/0001-dual-dispatch-taxonomy-migration.md)) |
| `backend/tools/` | XBRL comparison, formula/dimension error explanation |
| `backend/tests/`, `backend/**/tests/` | pytest suite (see §9) |
| `frontend/` | React 18 + Vite 5 chat UI (plain JSX, no TypeScript/Redux/Router) |
| `eval/` | Offline self-tests for the evaluation harnesses themselves, plus live benchmark scripts (see §10) |
| `doc/` | Architecture notes, ADRs, runbooks, historical fix logs |
| `doc/adr/` | Architecture Decision Records |
| `doc/runbooks/` | Step-by-step operational procedures |
| `.github/workflows/ci.yml` | CI pipeline (lint, backend tests, eval self-tests, security scans) |

## 3. Prerequisites

- **Python 3.13** (pinned — see `.python-version` and `requirements-lock.txt`)
- **Node.js** (for the Vite frontend — no specific version is pinned in
  `frontend/package.json`; a current LTS is expected to work)
- **[Ollama](https://ollama.com/)** reachable (locally, or via a configured
  remote proxy — see `OLLAMA_BASE_URL` below) with the models this
  deployment uses already pulled.
- Optional, only if exercising the SQL Agent: an **Oracle DB** instance and
  credentials.
- Optional, only if exercising voice input: network access to the
  configured **Whisper** service.
- Access to an iDEAL repo folder on disk (the XML "database") if you want
  App DB Q&A / XBRL tooling to work locally — these features degrade
  gracefully without it.

## 4. Local setup

```powershell
# from the repo root
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # runtime deps
pip install -r requirements-dev.txt      # pytest/ruff/bandit/pip-audit, for local dev
copy .env.example .env
```

Then edit `.env` — see §5/§6 below for what matters.

## 5. Environment configuration

`.env.example` is the authoritative, commented list of every environment
variable this backend reads — read it directly rather than relying on a
summary here, since it is kept current by the same changes that add new
variables. `requirements-lock.txt` documents the exact dependency set this
project was last verified against (`requirements.txt` itself only states
loose minimum versions).

## 6. Important environment variables

A non-exhaustive highlight list — `.env.example` is authoritative:

| Variable | Purpose |
|---|---|
| `APP_VERSION` | `"5.5"` or `"6.0"` — see [ADR 0004](doc/adr/0004-version-scoping-5.5-and-6.0.md) |
| `BASE_REPO_PATH` / `APP_600_REPO_ROOT` | Path to the iDEAL XML "database" repo (5.5 / 6.0 respectively) |
| `BACKEND_PORT` | Port this backend instance listens on |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` / `OLLAMA_EXTRACT_MODEL` / `OLLAMA_COMPARE_MODEL` | Ollama endpoint and model selection — centralized in `backend/services/llm_config.py` |
| `LLM_HTTP_CONNECT_TIMEOUT` / `_READ_TIMEOUT` / `_WRITE_TIMEOUT` / `_POOL_TIMEOUT` | Shared HTTP client timeouts (see [ADR 0003](doc/adr/0003-shared-http-client-for-llm-calls.md)) |
| `CORS_ORIGINS` | Allowed frontend origin(s) |
| `STT_ENABLED` / `STT_BASE_URL` | Voice input (remote Whisper service) |
| `REQUIRE_AUTH` / `AUTHORIZATION_ENABLED` | Auth enforcement — leave `true` outside local dev |
| `LOG_DIR` / `LOG_RETENTION_DAYS` | Log location/rotation — see [log maintenance runbook](doc/runbooks/log-maintenance.md) |
| `ORACLE_*`, `SQL_OLLAMA_MODEL`, `EMBEDDING_DIR` | SQL Agent settings, translated internally — see `backend/sql_agent/_bootstrap.py` |

**Never commit a real `.env`.** Only `.env.example` (with placeholder
values) belongs in version control.

## 7. Running the backend

```powershell
python dev_server.py                                     # option A — watches backend/ only
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # option B
```

Verify it's up: `GET /health` (liveness only) and `GET /health/ready`
(checks Oracle/Ollama/STT/the data repo path — see `backend/main.py`).

## 8. Running the frontend

```powershell
cd frontend
npm install
npm run dev     # vite dev server; proxies API calls per vite.config.js
```

Set `VITE_API_BASE_URL` (in `frontend/.env.development` for local dev,
`frontend/.env.production` for a build) to point at your backend. The
deployment base path (the IIS virtual directory this is served under) is
configurable via `VITE_BASE_PATH` — see `frontend/vite.config.js`.

Since the app normally receives identity via URL params (5.5) or a
`postMessage` handshake from the parent .NET app (6.0), standalone local
testing typically needs identity passed directly in the URL, e.g.
`http://localhost:5173/?loginId=1&uid=1&roleId=101`.

## 9. Running tests

```powershell
python -m pytest backend --ignore=backend/scripts -q
```

`pytest.ini` restricts default collection to `backend/` and excludes tests
marked `live` or `realdata` by default (see the marker descriptions in
`pytest.ini`) — these need a reachable Ollama endpoint or the real iDEAL
data tree respectively, and self-skip when that dependency is absent. Run
them explicitly with `-m live` / `-m realdata` when you have that
infrastructure available.

## 10. Running evaluation checks

```powershell
python -m pytest eval -q
```

This runs the **evaluation harnesses' own self-tests** (`eval/model_bench/`,
`eval/multilingual/`, `eval/stt/`) — all explicitly offline, no Ollama/Oracle
required (see each suite's own module docstring). It does **not** run the
live benchmark scripts themselves (`eval/model_bench/run_bench.py`,
`eval/multilingual/pipeline.py`, etc.), which drive a real model/DB and
produce the result files under `eval/*/results/` (including
`eval/results/hallucination_log.jsonl`, a manually-curated record, not an
automated regression gate) — those require live infrastructure this
environment may not have and are run manually/offline. See
`.github/workflows/ci.yml`'s "Evaluation harness self-tests" step for the
exact current CI integration, including why it's report-only for now.

## 11. Build / deployment overview

There is **no Docker** in this project — deployment is direct-on-Windows
(uvicorn process + IIS hosting/reverse-proxying the .NET app that embeds
this chatbot's iframe). `frontend/public/web.config` carries the IIS
configuration for the built frontend. Beyond what's captured here and in
`doc/APP_OVERVIEW.md`, treat deployment specifics not found in this repo
(the exact IIS site setup, process supervision, TLS termination) as
**must-confirm-with-ops**, not something to infer.

## 12. 5.5 vs 6.0 considerations

A single running backend process serves **one** version for its entire
lifetime (`APP_VERSION`), not both at once — see
[ADR 0004](doc/adr/0004-version-scoping-5.5-and-6.0.md) for the full
reasoning and consequences (separate repo layouts, separate identity
mechanisms, separate SQL Agent embedding sets, separate frontend
stylesheets). When testing a change, check whether it's version-specific
before assuming it behaves the same under both.

## 13. Common troubleshooting

| Symptom | Likely cause / where to look |
|---|---|
| `/health/ready` reports `not_ready` | Check which dependency failed in its `checks` field; see the corresponding runbook below |
| DB Q&A / XBRL tools silently disabled | `BASE_REPO_PATH` / `APP_600_REPO_ROOT` not set or not reachable |
| SQL Agent returns "unable to process" | Check Oracle reachability and `backend/sql_agent/_bootstrap.py`'s startup log line (`[SQL_AGENT] bootstrapped ...`) |
| Voice input unavailable | `STT_ENABLED=false`, or `STT_BASE_URL` unreachable |
| Chatbot doesn't receive identity when embedded | Check the parent-origin allowlist (`VITE_TRUSTED_PARENT_ORIGINS`) and the `postMessage` handshake — see `frontend/src/App.jsx` |
| New log files growing unbounded | See [log maintenance runbook](doc/runbooks/log-maintenance.md) |

## 14. Further reading

- [`doc/APP_OVERVIEW.md`](doc/APP_OVERVIEW.md) — full architecture and local-setup detail
- [`doc/adr/`](doc/adr/) — architecture decision records
- [`doc/runbooks/`](doc/runbooks/) — operational procedures
- [`doc/CRITICAL_FIXES_LOG.md`](doc/CRITICAL_FIXES_LOG.md) — historical hardening/fix record
- [`doc/IdealChatBot-Technical-Handover.md`](doc/IdealChatBot-Technical-Handover.md) — technical handover notes
