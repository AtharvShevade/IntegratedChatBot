# IntegratedChatBot — App Overview & Local Setup

## What this app is

A chatbot embedded as an **iframe** inside a .NET regulatory-reporting web app called **"iDEAL"** (versions 5.5 and 6.0). Users chat with it (text or voice) to ask about reports, compare XBRL instances, query application metadata (users/roles/schedules), or ask natural-language questions against a banking regulatory database (e.g. South Indian Bank's CIMS system).

Architecture at a glance:

```
.NET "iDEAL" web app (5.5 / 6.0)
        │  embeds as <iframe>
        ▼
React/Vite frontend  ──HTTP──▶  FastAPI backend  ──▶  Intent routing (local LLM via Ollama)
                                                       ├─ XBRL report tools ──▶ external .NET APIs
                                                       ├─ App "DB" Q&A ──▶ XML files (Users/Roles/Returns/...)
                                                       └─ SQL Agent (FAISS + Ollama) ──▶ Oracle DB
Voice input ──▶ Whisper service (speech-to-text, remote)
```

---

## Frontend (`frontend/`)

- **React 18 + Vite 5**, plain JSX (no TypeScript, no Redux/Router).
- Entry: `index.html` → `src/main.jsx` → `src/App.jsx`.
- Key components (`src/components/`):
  - `ChatWindow.jsx` — main chat message list/input
  - `MessageBubble.jsx` — individual message rendering
  - `VarianceChartModal.jsx` — chart popup for XBRL instance comparison (recharts)
  - `VoiceInput.jsx` — microphone recording UI, feeds `/speech-to-text`
    (mounted in the composer; the transcript lands in the chat input for
    review before Send, never auto-sent)
- **Dual version support**: `App.5.5.css` vs `App.6.0.css`, chosen at runtime based on whether a `tenant_id` URL param is present (6.0 = multi-tenant).
- **Identity**: v5.5 reads `loginId`/`uid`/`roleId`/`aspSession` from URL query params; v6.0 uses a `postMessage` handshake (`CHATBOT_READY` → parent replies `CHATBOT_AUTH`) to receive a JWT.
- **Backend calls** — all through `src/services/api.js` via `fetch`, base URL from `VITE_API_BASE_URL`:
  - `POST /chat`, `POST /guided`, `POST /compare-execute`, `POST /explain-category`, `POST /speech-to-text`, `POST /stop`, `POST /feedback`, `GET /allowed-actions`
- `frontend/dist.zip` — a prebuilt production bundle checked into the repo.

## Backend (`backend/`, FastAPI)

- Entry point: `backend/main.py` — `FastAPI(title="Report Assistant", version="3.0.0")`.
- Alt dev launcher: root `dev_server.py` (runs on port 8001, watches only `backend/`).
- **Startup lifespan** pre-loads SentenceTransformer/FAISS indexes and pings Ollama models so the first real request isn't slow.
- **Routes**: `/chat`, `/guided`, `/compare-execute`, `/explain-category`, `/speech-to-text`, `/stop`, `/feedback`, `/health`, `/download-file`, `/reports`, `/allowed-actions`, `/status-errors/{job_id}`.
- **Core pipeline** (`backend/agent/`): intent detection + entity extraction (LLM via `backend/llm_extractor.py` + rule-based fuzzy matching) → routes to one of three subsystems:
  1. **XBRL report tools** (`backend/tools/`) — comparisons, formula/dimension error explanations; triggers report-instance generation via external **.NET APIs** (`DOTNET_API_URL` session-cookie auth for 5.5, `DOTNET_V6_API_URL` JWT auth for 6.0).
  2. **App "database" Q&A** (`backend/db_qa/`) — queries **flat XML files** (Users, Roles, Returns, Schedules) from the iDEAL app's filesystem — not a real DB. Version-aware path resolution in `backend/config.py`.
  3. **SQL Agent** (`backend/sql_agent/`, vendored from the standalone `sql_agent/` project at repo root) — natural-language-to-SQL over an **Oracle** banking database. Pipeline: query → FAISS retrieval of relevant tables/columns → Ollama generates SQL → SQL validator (blocks dangerous DDL/DML) → executed via `oracledb`.
- **LLM**: entirely local via **Ollama** — no OpenAI/Azure OpenAI/LangChain anywhere in the codebase. Models used: `phi3:mini` (intent/extraction, DB Q&A beautify), `mistral` (XBRL variance summaries), `sqlcoder`/`gpt-oss`/`llama3.1` (SQL generation, configurable).
- **Voice**: uploaded audio forwarded to a **remote Whisper service**
  (`STT_BASE_URL`, default `http://3.109.51.228/whisper-api`), reached through
  `backend/stt/` — a thin client mirroring `backend/i18n/translator.py`. No model,
  no torch and no ffmpeg on the FastAPI host. The selected UI language is sent as
  the STT language hint, and `task` is pinned to `transcribe` so speech is never
  translated — translation stays the job of `backend/i18n/`.
- **No Docker** — deployment is direct-on-Windows (uvicorn + IIS/.NET-hosted iframe embed).

## Standalone `sql_agent/` project (repo root)

The original, independent NL-to-SQL project ("CIMS Banking Regulatory Reporting" query generator). Has its own FastAPI app (`sql_agent/api/main.py`), its own `src/` pipeline, schema-embedding builder (`embedding_building/`), and docs: `README.md`, `ARCHITECTURE.md`, `DEVELOPER_DOCUMENTATION.md`. A copy of its logic is vendored into `backend/sql_agent/` for use inside the main chatbot.

## Databases

1. **Oracle DB** — used only by the SQL Agent, via the `oracledb` Python driver (thin mode, no Oracle client install needed).
2. **XML flat-file "database"** — powers the App DB Q&A feature; not a real database, just XML files (`XML_User.xml`, `XML_Role.xml`, `Returns.xml`, `XML_InstanceLog.xml`, etc.) under the iDEAL repo path.

---

## Running Locally

### Prerequisites

- **Python 3.10+** and **Node.js 18+**
- **[Ollama](https://ollama.com/)** installed and running locally, with the models you intend to use pulled, e.g.:
  ```
  ollama pull phi3:mini
  ollama pull mistral
  ollama pull llama3.1
  ```
- (Optional, only if using the SQL Agent) an **Oracle DB** instance/credentials, and a SQL-generation model such as `sqlcoder-7b` pulled into Ollama.
- (Optional, only if using voice input) network access to the **Whisper service** at `STT_BASE_URL`.
- Access to an iDEAL repo folder on disk (XML files) if you want the App DB Q&A / XBRL tooling to work — otherwise those features gracefully degrade/disable.

### 1. Backend setup

```powershell
cd D:\POC_Work\IntegratedChatBot

# create & activate a virtual env (if not already present as .venv)
python -m venv .venv
.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt
```

Copy and edit the environment file:

```powershell
copy .env.example .env
```

Edit `.env` and set at minimum:
- `APP_VERSION` (5.5 or 6.0)
- `BASE_REPO_PATH` (5.5) or `APP_600_REPO_ROOT` (6.0) — path to the iDEAL repo, if available
- `OLLAMA_BASE_URL` / `OLLAMA_MODEL`
- `CORS_ORIGINS=http://localhost:3000` (or whatever port the frontend dev server uses)
- `STT_BASE_URL` / `STT_ENABLED` if testing voice input

If you want the **SQL Agent** working too:

```powershell
copy sql_agent\.env.example sql_agent\.env
```
and fill in `DB_HOST`/`DB_PORT`/`DB_SERVICE`/`DB_USER`/`DB_PASSWORD` and the Ollama model names for SQL generation/table selection.

Start the backend (either works):

```powershell
# Option A — via the root dev launcher (port 8001)
python dev_server.py

# Option B — directly with uvicorn (port 8000, per main.py header comment)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's up: open `http://localhost:8000/health` (or `:8001/health` if using `dev_server.py`).

### 2. Frontend setup

```powershell
cd D:\POC_Work\IntegratedChatBot\frontend
npm install
```

Set `VITE_API_BASE_URL` in `frontend\.env.development` to match wherever your backend is running (e.g. `http://localhost:8000`), or leave it empty and configure a Vite proxy in `vite.config.js` for `/chat`, `/guided`, etc.

Start the dev server:

```powershell
npm run dev
```

This serves the chat UI (default Vite port, typically `http://localhost:5173` or `:3000` depending on config).

### 3. Using it standalone (outside the iDEAL iframe)

Since the app expects identity via URL params or a `postMessage` handshake from a parent .NET app, when testing standalone locally you'll typically need to pass identity params directly in the URL, e.g.:

```
http://localhost:5173/?loginId=1&uid=1&roleId=101
```

(for 5.5-style testing), or add a `tenant_id` param to force 6.0 mode. Without a real parent app, some identity/auth-dependent features (JWT-based 6.0 flows, .NET instance-generation calls) will not fully function — this is expected in a local dev-only setup.

### 4. Optional: standalone SQL Agent project

The vendored SQL agent runs inside the main backend already. If you want to run the **original standalone** `sql_agent/` project on its own (e.g. for schema-embedding rebuilds or isolated testing):

```powershell
cd D:\POC_Work\IntegratedChatBot\sql_agent
pip install -r requirements.txt
copy .env.example .env   # fill in Oracle + Ollama settings
uvicorn api.main:app --reload --port <port>
```

See `sql_agent/README.md` and `sql_agent/ARCHITECTURE.md` for details on rebuilding FAISS indexes from the schema.
