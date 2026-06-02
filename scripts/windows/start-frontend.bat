@echo off
rem Start frontend dev server (npm run dev) and record PID
rem Usage: start-frontend.bat

set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set FRONTEND_DIR=%REPO_ROOT%\frontend
set LOG_DIR=%REPO_ROOT%\logs
set PID_DIR=%REPO_ROOT%\scripts\pids
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"

pushd "%FRONTEND_DIR%"
set LOGFILE=%LOG_DIR%\frontend.log
set PIDFILE=%PID_DIR%\frontend.pid

rem Prefer npm ci in CI, but for dev we use npm run dev
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Start-Process -FilePath 'cmd' -ArgumentList '/c','npm','run','dev' -WorkingDirectory '%FRONTEND_DIR%' -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -WindowStyle Minimized -PassThru | Select-Object -ExpandProperty Id"`) do set PID=%%P
if defined PID (
  echo %PID% > "%PIDFILE%"
  echo Frontend started (PID=%PID%), log: %LOGFILE%
) else (
  echo Failed to start frontend. See %LOGFILE% for details.
)
popd
exit /b 0
