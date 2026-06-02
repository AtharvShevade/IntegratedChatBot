@echo off
rem Stop backend, frontend, and AI model if running. Uses PID files in scripts\pids.
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set PID_DIR=%REPO_ROOT%\scripts\pids
set LOG_DIR=%REPO_ROOT%\logs
if not exist "%PID_DIR%" (
  echo No PID directory found. Nothing to stop.
  exit /b 0
)

set ERR=0
for %%S in (backend frontend llm) do (
  set PIDFILE=%PID_DIR%\%%S.pid
  if exist "%%PIDFILE%%" (
    for /f "usebackq tokens=*" %%P in (`type "%%PIDFILE%%"`) do set PIDVAL=%%P
    if defined PIDVAL (
      echo Stopping %%S (PID=%%PIDVAL%%)...
      taskkill /PID %%PIDVAL%% /F > "%LOG_DIR%\stop-%%S.log" 2>&1
      if errorlevel 1 (
        echo Failed to kill PID %%PIDVAL%% for %%S. Check %LOG_DIR%\stop-%%S.log
        set ERR=1
      ) else (
        del "%%PIDFILE%%"
        echo Stopped %%S.
      )
    ) else (
      del "%%PIDFILE%%" >nul 2>&1
    )
    set PIDVAL=
  )
)

if %ERR%==1 (
  echo Some services failed to stop cleanly.
  exit /b 1
)

echo All stop commands completed.
exit /b 0
