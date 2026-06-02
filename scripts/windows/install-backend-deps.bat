@echo off
rem Install backend Python dependencies into .venv
rem Usage: install-backend-deps.bat
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set VENV_DIR=%REPO_ROOT%\.venv
set PY_EXE=%VENV_DIR%\Scripts\python.exe
set PIP=%VENV_DIR%\Scripts\pip.exe

if not exist "%VENV_DIR%" (
  echo Creating python virtualenv at %VENV_DIR%...
  python -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo Failed to create virtualenv. Ensure python is on PATH.
    exit /b 1
  )
)

if not exist "%PIP%" (
  echo pip executable not found in %VENV_DIR%\Scripts. Aborting.
  exit /b 1
)

if exist "%REPO_ROOT%\requirements.txt" (
  echo Installing backend requirements from requirements.txt...
  "%PIP%" install --upgrade pip
  "%PIP%" install -r "%REPO_ROOT%\requirements.txt"
  if errorlevel 1 (
    echo pip install exited with errors. Check output above.
    exit /b 2
  )
) else (
  echo No requirements.txt found at %REPO_ROOT%. Skipping.
)

echo Backend dependencies installed.
exit /b 0
