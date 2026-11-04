@echo off
chcp 65001 >nul 2>&1
title AI Lead Generator - Dashboard

REM ============================================
REM   AI Lead Generator - Start Dashboard
REM   Starts the backend, opens the browser,
REM   and keeps running until a key is pressed.
REM ============================================

cd /d "%~dp0"

echo.
echo   ============================================
echo     AI Lead Generator - Starting Dashboard
echo   ============================================
echo.

REM --- Check setup ---
echo   Checking setup...
if not exist "venv\Scripts\python.exe" (
    echo.
    echo   ERROR: Setup has not been completed.
    echo   Please run Setup.bat first.
    echo.
    pause
    exit /b 1
)
if not exist "frontend\dist\browser\index.html" (
    echo.
    echo   ERROR: Frontend has not been built.
    echo   Please run Setup.bat first.
    echo.
    pause
    exit /b 1
)
echo   Setup OK.
echo.

REM --- Check if already running ---
echo   Checking for existing instance...
netstat -ano | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo   Dashboard is already running.
    echo   Opening browser...
    start "" "http://127.0.0.1:8765"
    timeout /t 3 >nul
    exit /b 0
)
echo   No existing instance found.
echo.

REM --- Start backend ---
echo   Starting backend...
powershell -Command "$proc = Start-Process -FilePath '%~dp0venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8765','--log-level','info' -WorkingDirectory '%~dp0backend' -WindowStyle Minimized -PassThru; $proc.Id | Out-File -FilePath '%~dp0data\backend.pid' -Encoding ascii -NoNewline"

REM --- Wait for backend to start ---
echo   Waiting for backend to start...
set "attempts=0"
:health_loop
set /a attempts+=1
timeout /t 1 >nul 2>&1
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    if %attempts% lss 20 (
        goto health_loop
    ) else (
        echo.
        echo   ERROR: Backend failed to start within 20 seconds.
        echo   Check logs\app.log for details.
        echo.
        pause
        exit /b 1
    )
)
echo   Backend started successfully.
echo.

REM --- Open browser ---
echo   Opening dashboard in browser...
start "" "http://127.0.0.1:8765"

echo.
echo   ============================================
echo     Dashboard is running at:
echo     http://127.0.0.1:8765
echo   ============================================
echo.
echo   Press any key to STOP the dashboard...
pause >nul

REM --- Stop backend ---
echo.
echo   Stopping dashboard...
call "%~dp0Stop Dashboard.bat" >nul 2>&1
echo   Dashboard stopped.
echo.
timeout /t 2 >nul
