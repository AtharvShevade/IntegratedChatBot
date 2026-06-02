Windows BAT scripts for Chat-SystemWorking

Location: scripts\windows

Overview:
This folder contains production-ready Windows batch (.bat) scripts to automate development and deployment tasks for the Chat-SystemWorking project. Scripts adopt safe, enterprise-friendly patterns: PID files, log redirection, clear exit codes, and minimal assumptions about host state.

Files created:
- start-backend.bat        : Start uvicorn backend (dev/prod)
- start-frontend.bat       : Start frontend dev server (npm run dev)
- start-all.bat            : Start backend, frontend, and AI model
- install-backend-deps.bat : Create venv and install Python deps
- install-frontend-deps.bat: Install npm dependencies
- setup-env.bat            : Orchestrates environment setup
- build-frontend.bat       : Run production build for frontend
- restart-all.bat          : Stop then start all services
- stop-all.bat             : Stop running services using PID files
- cleanup-logs.bat         : Remove old logs (forfiles)
- db-migrate.bat           : Run database migrations (alembic or backend migrate helper)
- health-check.bat         : HTTP health checks for backend and frontend
- start-llm.bat            : Start local LLM server (ollama or Docker image)
- docker-start.bat         : Start docker-compose stack (if present)

Folder expectations:
- Repository root contains `backend\`, `frontend\`, `.venv` (after setup), `logs\` (created if missing), and `scripts\pids\` for PID files.
- Scripts assume Windows cmd.exe environment with PowerShell available for some operations.

Naming conventions:
- Use verbs first: start-*, stop-*, install-*, build-*, db-*
- Keep file names lowercase with dashes for readability

Auto-start recommendations:
- To run services after boot, register `start-all.bat` in Task Scheduler as a "Run whether user is logged on or not" task.
- For backend production, consider using NSSM or Windows Service wrappers to run the uvicorn process as a Windows Service.

Task Scheduler integration (quick steps):
1. Open Task Scheduler → Create Task
2. Set Name: ChatSystem - Start All
3. Trigger: At startup (or on logon)
4. Action: Start a program → Program/script: C:\Windows\System32\cmd.exe
   Add arguments: /c "C:\path\to\repo\scripts\windows\start-all.bat"
5. Set "Run whether user is logged on or not" and supply credentials

Best practices:
- Run setup-env.bat once on a clean host to create .venv and install deps.
- Ensure Docker and/or Ollama are installed before enabling model startup.
- Use logs for debugging; rotate with cleanup-logs.bat regularly (via Task Scheduler).
- Prefer `docker-compose` in production where full-stack reproducibility is required.

Contact:
For questions about these scripts, please reach out to the devops team and include the failing log file under `logs\\` when filing issues.
