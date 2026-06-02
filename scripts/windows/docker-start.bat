@echo off
rem Optional: start services via docker-compose if docker-compose.yml present
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set DC=%REPO_ROOT%\docker-compose.yml
if exist "%DC%" (
  echo Starting docker-compose services...
  pushd "%REPO_ROOT%"
  docker-compose up -d
  if errorlevel 1 (
    echo docker-compose failed. Ensure Docker Desktop is running.
    popd
    exit /b 1
  )
  popd
) else (
  echo No docker-compose.yml found at repo root. Nothing to do.
)
exit /b 0
