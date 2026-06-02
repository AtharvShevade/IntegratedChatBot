@echo off
rem Build frontend for production
rem Usage: build-frontend.bat
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set FRONTEND_DIR=%REPO_ROOT%\frontend
set LOG_DIR=%REPO_ROOT%\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

pushd "%FRONTEND_DIR%"
set LOGFILE=%LOG_DIR%\frontend_build.log

echo Running production build (npm run build)...
npm run build > "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo Frontend build failed. Check %LOGFILE%
  popd
  exit /b 1
)

echo Build completed. Artifacts in %FRONTEND_DIR%\dist or build folder depending on config.
popd
exit /b 0
