@echo off
rem Install frontend dependencies (npm)
rem Usage: install-frontend-deps.bat
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set FRONTEND_DIR=%REPO_ROOT%\frontend
pushd "%FRONTEND_DIR%"
if exist package-lock.json (
  echo Detected package-lock.json — running npm ci
  npm ci
) else (
  echo Running npm install
  npm install
)
if errorlevel 1 (
  echo npm install failed. Check the output.
  popd
  exit /b 1
)

echo Frontend dependencies installed.
popd
exit /b 0
