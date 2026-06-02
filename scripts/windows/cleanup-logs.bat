@echo off
rem Cleanup old logs older than specified days (default 30)
rem Usage: cleanup-logs.bat [days]
set REPO_ROOT=%~dp0..\..
set REPO_ROOT=%REPO_ROOT:~0,-1%
set LOG_DIR=%REPO_ROOT%\logs
if "%1"=="" ( set DAYS=-30 ) else ( set DAYS=-%1 )

echo Deleting log files older than %DAYS% days from %LOG_DIR% ...
forfiles /p "%LOG_DIR%" /s /m *.log /d %DAYS% /c "cmd /c echo Deleting @path & del @path"

echo Log cleanup complete.
exit /b 0
