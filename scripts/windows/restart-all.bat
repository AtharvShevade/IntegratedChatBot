@echo off
rem Restart all services: stop then start (preserves --prod arg for backend)
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%

call "%REPO_ROOT%\scripts\windows\stop-all.bat"
if errorlevel 1 (
  echo Warning: stop-all reported errors, continuing to start anyway.
)

call "%REPO_ROOT%\scripts\windows\start-all.bat" %1
exit /b 0
