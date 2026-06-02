@echo off
rem One-shot environment setup for developer or deployment host
rem Creates venv, installs backend and frontend deps, prepares logs and pid dirs.
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%

echo Creating directories and installing dependencies...
if not exist "%REPO_ROOT%\logs" mkdir "%REPO_ROOT%\logs"
if not exist "%REPO_ROOT%\scripts\pids" mkdir "%REPO_ROOT%\scripts\pids"

call "%REPO_ROOT%\scripts\windows\install-backend-deps.bat"
if errorlevel 1 (
  echo Backend deps installation failed. Aborting.
  exit /b 1
)

call "%REPO_ROOT%\scripts\windows\install-frontend-deps.bat"
if errorlevel 1 (
  echo Frontend deps installation failed. Aborting.
  exit /b 2
)

echo Environment setup completed.
exit /b 0
