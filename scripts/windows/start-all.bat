@echo off
rem Start backend, frontend, and optional AI model. Non-blocking.
rem Usage: start-all.bat [--prod]
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%

echo Starting backend...
call "%REPO_ROOT%\scripts\windows\start-backend.bat" %1

timeout /t 2 >nul

echo Starting frontend...
call "%REPO_ROOT%\scripts\windows\start-frontend.bat"

timeout /t 2 >nul

echo Starting AI model (if configured)...
call "%REPO_ROOT%\scripts\windows\start-llm.bat"

echo All start commands issued.
exit /b 0
