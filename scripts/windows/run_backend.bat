@echo off
REM ---------------------------------------------------------------------------
REM run_backend.bat  -  start ONE ChatBot backend instance (service_server.py).
REM
REM   run_backend.bat 55   ->  ChatBot 5.5  (BACKEND_PORT 8001 by default)
REM   run_backend.bat 60   ->  ChatBot 6.0  (BACKEND_PORT 8002 by default)
REM
REM Meant for the Task Scheduler (task "ChatBot-5.5" / "ChatBot-6.0", run at boot)
REM and fine to run by hand. Self-contained: no other script is needed.
REM
REM How the version is chosen
REM   This script sets the real process variable APP_VERSION. backend/env_loader.py
REM   lets a real environment variable win over .env, then loads the matching
REM   overlay .env.5.5 / .env.6.0 (BACKEND_PORT, LOG_DIR, BASE_REPO_PATH, ...).
REM   So the root .env can stay as it is and both instances can run side by side.
REM   The overlay is created from .env.<ver>.example on first run when it is missing.
REM
REM Logs
REM   This script's own console log:  logs\55\service-console.log  (logs\60\ for 6.0).
REM   The application's own logs still go where LOG_DIR says (logs_5.5 / logs_6.0).
REM
REM Stop on purpose: create logs\55\STOP (or logs\60\STOP), then End the task.
REM Delete the file again to allow starts.
REM ---------------------------------------------------------------------------
setlocal

set "VER=%~1"
if /I not "%VER%"=="55" if /I not "%VER%"=="60" (
    echo Usage: %~nx0 55^|60
    exit /b 2
)
if "%VER%"=="55" (set "APP_VERSION=5.5") else (set "APP_VERSION=6.0")

REM Project root = two levels above this script (scripts\windows\ -> root).
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

REM Per-version overlay: created from the tracked template on first run.
set "OVERLAY=%ROOT%\.env.%APP_VERSION%"
if not exist "%OVERLAY%" if exist "%OVERLAY%.example" copy /Y "%OVERLAY%.example" "%OVERLAY%" >nul

REM Port (only used to free a stale listener): BACKEND_PORT from .env, the overlay wins, else the default.
if "%VER%"=="55" (set "PORT=8001") else (set "PORT=8002")
for %%F in ("%ROOT%\.env" "%OVERLAY%") do if exist "%%~F" (
    for /f "tokens=2 delims==# " %%P in ('findstr /r /b /c:"BACKEND_PORT *=" "%%~F"') do set "PORT=%%P"
)

set "CONSOLE_DIR=%ROOT%\logs\%VER%"
if not exist "%CONSOLE_DIR%" mkdir "%CONSOLE_DIR%"

REM service_server.py never autoreloads (reload=False). Keep it that way under Task Scheduler:
REM a reloader's child process survives "End task" and keeps the port (WinError 10048).

REM Python: prefer the project venv, then backend\.venv, then PATH.
set "PY=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PY=%ROOT%\.venv\Scripts\python.exe"
if exist "%ROOT%\backend\.venv\Scripts\python.exe" if not exist "%ROOT%\.venv\Scripts\python.exe" set "PY=%ROOT%\backend\.venv\Scripts\python.exe"

REM Restart loop. It never gives up on its own: a slow boot (database, network or disk not
REM ready yet) must not leave the backend down until the next reboot. The pause grows
REM 10 s -> 60 s so a long outage does not spin.
set "LOG=%CONSOLE_DIR%\service-console.log"
set "STOPFILE=%CONSOLE_DIR%\STOP"
set /a ATTEMPT=0
set /a PAUSE=10

:run
if exist "%STOPFILE%" (
    echo [%DATE% %TIME%] STOP file present - not starting >> "%LOG%"
    exit /b 0
)
REM Roll the console log at ~20 MB so it can never fill the disk.
for %%F in ("%LOG%") do if exist "%%~F" if %%~zF GTR 20000000 move /Y "%LOG%" "%LOG%.old" >nul
REM Free the port when a stale python copy still holds it ("address already in use" / WinError 10048).
REM Only python is stopped; anything else is left alone.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %PORT% -State Listen -EA SilentlyContinue | ForEach-Object { $p = Get-Process -Id $_.OwningProcess -EA SilentlyContinue; if ($p -and $p.ProcessName -like 'python*') { Add-Content -Path '%LOG%' -Value ('port %PORT% held by stale python PID ' + $p.Id + ' - stopping it'); Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 2 } }"
echo [%DATE% %TIME%] starting APP_VERSION=%APP_VERSION% on port %PORT% with %PY% (attempt %ATTEMPT%) >> "%LOG%"
"%PY%" service_server.py >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo [%DATE% %TIME%] exited with code %RC% - restarting in %PAUSE% s >> "%LOG%"
set /a ATTEMPT+=1
REM ping is the pause: timeout.exe refuses to run without a console (Task Scheduler)
set /a PINGS=PAUSE+1
ping -n %PINGS% 127.0.0.1 >nul
set /a PAUSE=PAUSE*2
if %PAUSE% GTR 60 set /a PAUSE=60
goto run
