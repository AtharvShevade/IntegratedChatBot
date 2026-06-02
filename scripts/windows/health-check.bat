@echo off
rem Health check script for backend and frontend services.
rem Usage: health-check.bat [backend_url] [frontend_url]
set BACKEND_URL=%1
if "%BACKEND_URL%"=="" set BACKEND_URL=http://127.0.0.1:8001/health
set FRONTEND_URL=%2
if "%FRONTEND_URL%"=="" set FRONTEND_URL=http://127.0.0.1:5173/

echo Checking backend: %BACKEND_URL%
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%BACKEND_URL%' -TimeoutSec 6; Write-Host 'BACKEND OK ('+$r.StatusCode+')'; exit 0 } catch { Write-Host 'BACKEND FAILED: ' $_.Exception.Message; exit 2 }"
if errorlevel 2 (
  echo Backend health check failed.
) else (
  echo Backend healthy.
)

echo Checking frontend: %FRONTEND_URL%
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%FRONTEND_URL%' -TimeoutSec 6; Write-Host 'FRONTEND OK ('+$r.StatusCode+')'; exit 0 } catch { Write-Host 'FRONTEND FAILED: ' $_.Exception.Message; exit 2 }"
if errorlevel 2 (
  echo Frontend health check failed.
) else (
  echo Frontend healthy.
)

exit /b 0
