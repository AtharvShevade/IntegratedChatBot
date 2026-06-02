@echo off
rem Start a local AI model server (ollama) or Docker image. Configure via env vars.
rem Usage: start-llm.bat
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set PID_DIR=%REPO_ROOT%\scripts\pids
set LOG_DIR=%REPO_ROOT%\logs
if not exist "%PID_DIR%" mkdir "%PID_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set PIDFILE=%PID_DIR%\llm.pid
set LOGFILE=%LOG_DIR%\llm.log

rem If ollama is installed, prefer it
where ollama >nul 2>&1
if %ERRORLEVEL%==0 (
  echo Found ollama. Starting model server via ollama serve...
  for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Start-Process -FilePath 'ollama' -ArgumentList 'serve' -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -WindowStyle Minimized -PassThru | Select-Object -ExpandProperty Id"`) do set PID=%%P
  if defined PID ( echo %PID% > "%PIDFILE%" & echo Ollama started (PID=%PID%) ) else echo Failed to start ollama.
  exit /b 0
)

rem Otherwise, check DOCKER_LLM_IMAGE env var
if not defined DOCKER_LLM_IMAGE (
  echo No local LLM configured (ollama not found and DOCKER_LLM_IMAGE not set). Skipping.
  exit /b 0
)

echo Starting LLM docker image: %DOCKER_LLM_IMAGE%
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Start-Process -FilePath 'docker' -ArgumentList 'run','--rm','-p','11434:11434','--name','local_llm', '%DOCKER_LLM_IMAGE%' -RedirectStandardOutput '%LOGFILE%' -RedirectStandardError '%LOGFILE%' -WindowStyle Minimized -PassThru | Select-Object -ExpandProperty Id"`) do set PID=%%P
if defined PID ( echo %PID% > "%PIDFILE%" & echo Docker LLM started (PID=%PID%) ) else echo Failed to start Docker LLM.
exit /b 0
