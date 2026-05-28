# Deployment Guide — Chat-SystemWorking

## 1. Project Overview

### Architecture
- Frontend: React SPA (Vite) embedded via iframe in an existing ASP.NET application or served separately.
- Backend: FastAPI (ASGI) application exposing chat and management endpoints (entry: `backend/main.py`).
- Data: XML files (Returns.xml, XML_InstanceLog.xml) plus `logs/period.xml` for PeriodMaster.
- LLM: Ollama local inference server integrated via `backend/services/llm_service.py`.
- Integration: .NET app integration via iframe and optional ASP.NET session forwarding for instance generation.

### Components
- Backend: routing & session management (`backend/agent/__init__.py`), deterministic entity extraction (`backend/llm_extractor.py`), Ollama client (`backend/services/llm_service.py`), report matching (`backend/tools/report_lookup.py`), instance generation (`backend/tools/instance_generator.py`).
- Frontend: React components under `frontend/src/` and API client `frontend/src/services/api.js`.
- SQL Agent: `sql_agent/` (FAISS indexes) for database queries.

### Technology stack
- Python 3.11+, FastAPI, Uvicorn
- React (Vite), Node.js
- Ollama for local LLMs
- rapidfuzz, python-dateutil
- Optional: Arelle (XBRL), sentence-transformers + FAISS for SQL agent

---

## 2. System Requirements

- OS: Linux (recommended) or Windows Server.
- Python: 3.11+ (3.11 or 3.12 recommended).
- Node: 18.x+
- Hardware: allocate 2+ vCPU, 4+ GB RAM for web server; Ollama model requirements vary (3–16+ GB RAM depending on model).
- Software: Docker recommended; Ollama installed if using local models.

Key Python packages: see `requirements.txt` (project root).

---

## 3. Folder Structure Explanation
- `backend/` — Python backend and business logic.
- `frontend/` — React app (Vite).
- `logs/` — `period.xml` and taxonomy files.
- `sql_agent/` — FAISS and SQL agent code + outputs.
- `DEPLOYMENT.md` — this file.

Important files:
- `backend/main.py`, `backend/config.py`, `backend/tools/report_lookup.py`, `backend/tools/instance_generator.py`, `backend/services/llm_service.py`.

---

## 4. Backend Deployment Steps

### 4.1 Virtual environment
Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 4.2 Install dependencies

```bash
pip install -r requirements.txt
```

### 4.3 Environment variables (`.env`)
Sample variables (set to production values):

```
DOTNET_API_URL=https://dotnet-host/CreateInstance
DOTNET_CONTROLLER=CreateInstance
DOTNET_SESSION_COOKIE=
RETURNS_XML_PATH=...\Returns.xml
INSTANCE_LOG_XML_PATH=...\XML_InstanceLog.xml
INSTANCE_BASE_DIR=...\Instance
RENDER_BASE_DIR=...\Render
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EXTRACT_MODEL=phi3:mini
OLLAMA_MODEL=phi3:mini
OLLAMA_TIMEOUT=180
OLLAMA_KEEP_ALIVE=30m
```

### 4.4 Run dev server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

### 4.5 Production server
- Recommended: nginx reverse-proxy + systemd service running `uvicorn`/Gunicorn with Uvicorn workers or Docker/Kubernetes deployment.
- Example nginx snippet:

```
server {
  listen 443 ssl;
  server_name chat.example.com;
  ssl_certificate /path/to/fullchain.pem;
  ssl_certificate_key /path/to/privkey.pem;
  location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

### 4.6 Logging
- Backend uses Python `logging`. Route logs to files or to centralized logging (ELK/Datadog). Configure rotation.

---

## 5. Frontend Deployment Steps

### 5.1 Install & build

```bash
cd frontend
npm ci
npm run build
```

### 5.2 Env
Use `VITE_API_BASE_URL` to point to production backend.

### 5.3 Serve
- Serve `dist/` using nginx or copy into ASP.NET static files and embed via iframe.

---

## 6. .NET Integration

### 6.1 Embed iframe

```html
<iframe src="https://chat-ui.example.com" width="100%" height="600" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
```

### 6.2 Session/auth
- For generating instances, the backend may need `.AspNetCore.Session`. The frontend or .NET host should securely provide a short-lived token or forward the cookie to backend calls as `asp_session` parameter (the project supports forwarding — see `backend/tools/instance_generator.py`).
- Ensure `SameSite=None; Secure` for cookies used in cross-site contexts.

---

## 7. Configuration Files
- `.env` (sample above)
- `backend/config.py` contains default paths — override via env vars.
- CORS: configure FastAPI `CORSMiddleware` to allow frontend origin and credentials when required.

---

## 8. Database / XML Configuration
- `RETURNS_XML_PATH` and `INSTANCE_LOG_XML_PATH` point to authoritative XML files. Ensure correct paths and permissions.
- Caches: `Returns.xml` TTL default 3600s; `period.xml` TTL default 86400s. To force refresh, restart backend.
- Note: `resolve_return_exact()` prefers PeriodMaster `Frequency` (from `period.xml`) over `RepFreq` on the Return row — ensure PeriodId mapping in `Returns.xml` is correct.

---

## 9. LLM Setup (Ollama)

### 9.1 Install
Follow Ollama docs. Example:

```bash
# macOS
brew install ollama
# Pull model
ollama pull phi3:mini
```

### 9.2 Config
Ensure `OLLAMA_BASE_URL` points to running ollama server. Pull recommended models for `OLLAMA_EXTRACT_MODEL` and `OLLAMA_MODEL`.

---

## 10. Production Deployment Notes
- IIS: use ARR to reverse-proxy to uvicorn or run uvicorn as a Windows service.
- Reverse proxy: nginx recommended; terminate TLS at proxy.
- Ensure firewall only exposes necessary ports.

---

## 11. Security Recommendations
- Authenticate API endpoints; use tokens or integrate with .NET auth.
- Forward session securely; avoid exposing raw session cookies to JS.
- Restrict CORS to allowed origins and enable credentials only when necessary.
- Use env-based secrets and secret managers.

---

## 12. Troubleshooting
- Validate `RETURNS_XML_PATH` and `INSTANCE_LOG_XML_PATH` for load errors.
- Date/frequency mismatches: run resolver locally:

```bash
.\.venv\Scripts\python.exe -c "from backend.tools.instance_generator import resolve_return_exact; import json; print(json.dumps(resolve_return_exact('CIMS_ALE_SEC'), indent=2))"
```

- Ollama connectivity: `curl http://127.0.0.1:11434/api/info`.
- CORS & iframe cookie issues: ensure `SameSite=None; Secure` and correct CORS settings.

---

## 13. Logging & Monitoring
- Centralize logs; expose health and metrics endpoints; monitor LLM latency.

---

## 14. Performance Optimization
- Tune uvicorn worker count; keep Ollama models warm; pre-build FAISS indexes and cache them.

---

## 15. Backup & Recovery
- Backup XML files daily; store Ollama model manifests so you can re-pull models.

---

## 16. Deployment Checklist
- [ ] Env vars configured
- [ ] Ollama models pulled
- [ ] XML paths set and accessible
- [ ] Backend dependencies installed
- [ ] Frontend built and deployed
- [ ] Reverse proxy and TLS configured
- [ ] Logging and monitoring enabled

---

### Appendix: Useful commands

Build backend & test resolver:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Build frontend:

```bash
cd frontend
npm ci
npm run build
```

Ollama model pull:

```bash
ollama pull phi3:mini
```

---

For any follow-up I can:
- Run `resolve_return_exact('CIMS_ALE_SEC')` and paste output locally (no code changes).
- Convert this `DEPLOYMENT.md` to PDF and add it to the repo.


