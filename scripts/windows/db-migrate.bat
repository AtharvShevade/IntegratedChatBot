@echo off
rem Run database migrations. Uses Alembic if present, otherwise runs backend-specific migration command.
rem Usage: db-migrate.bat
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set VENV=%REPO_ROOT%\.venv\Scripts\activate
if exist "%REPO_ROOT%\alembic.ini" (
  echo Running alembic upgrade head...
  call "%VENV%"
  pushd "%REPO_ROOT%"
  "%REPO_ROOT%\.venv\Scripts\alembic.exe" upgrade head
  if errorlevel 1 (
    echo Alembic migration failed.
    popd
    exit /b 1
  )
  popd
) else (
  echo No alembic.ini found. Running backend's migration helper if available.
  if exist "%REPO_ROOT%\backend\migrate.py" (
    call "%VENV%"
    python "%REPO_ROOT%\backend\migrate.py"
    if errorlevel 1 (
      echo Backend migration helper failed.
      exit /b 2
    )
  ) else (
    echo No migration tool found. Please implement migrations or add alembic.ini.
    exit /b 3
  )
)

echo Migrations completed.
exit /b 0
