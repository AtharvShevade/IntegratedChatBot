@echo off
rem Start backend (uvicorn) in a background process and record PID
rem Usage: start-backend.bat [--prod]

:: Resolve repo root (script is in repo scripts\windows)
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%

rem Adjust paths
set VENV=%REPO_ROOT%\.venv\Scripts\activate
set BACKEND_DIR=%REPO_ROOT%\backend
set LOG_DIR=%REPO_ROOT%\logs
set PID_DIR=%REPO_ROOT%\scripts\pids

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"

rem Determine mode
set MODE_ARG=%1
if "%MODE_ARG%"=="--prod" (
  set UVICORN_ARGS=backend.main:app --host 0.0.0.0 --port 8001 --workers 4
  set USE_DEV_SERVER=0
) else (
  rem Dev mode: use dev_server.py which configures reload_dirs/reload_excludes
  rem to prevent log writes from triggering an infinite reload loop.
  set USE_DEV_SERVER=1
)

rem Activate venv then start uvicorn via PowerShell to capture PID
pushd "%BACKEND_DIR%"
if not exist "%VENV%" (
  echo WARNING: virtualenv activate not found at %VENV%
) else (
  call "%VENV%"
)

set LOGFILE=%LOG_DIR%\backend.log
set PIDFILE=%PID_DIR%\backend.pid

rem Use PowerShell Start-Process to launch uvicorn/dev_server and capture PID
if "%USE_DEV_SERVER%"=="1" (
  rem Dev: run dev_server.py (handles reload_dirs + reload_excludes internally)
  for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Start-Process -FilePath 'python' -ArgumentList '%REPO_ROOT%\dev_server.py' -WorkingDirectory '%REPO_ROOT%' -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -WindowStyle Minimized -PassThru | Select-Object -ExpandProperty Id"`) do set PID=%%P
) else (
  rem Prod: standard uvicorn multi-worker (no reload)
  for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn',%UVICORN_ARGS% -WorkingDirectory '%BACKEND_DIR%' -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -WindowStyle Minimized -PassThru | Select-Object -ExpandProperty Id"`) do set PID=%%P
)
if defined PID (
  echo %PID% > "%PIDFILE%"
  echo Backend started (PID=%PID%), log: %LOGFILE%
) else (
  echo Failed to start backend. See %LOGFILE% for details.
)
popd
exit /b 0
