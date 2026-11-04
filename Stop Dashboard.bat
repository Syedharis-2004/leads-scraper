@echo off
chcp 65001 >nul 2>&1
title AI Lead Generator - Stop

REM ============================================
REM   AI Lead Generator - Stop Dashboard
REM   Stops ONLY this application's backend process.
REM   Does NOT terminate unrelated Python/Node processes.
REM   Preserves CSV data and configuration.
REM ============================================

cd /d "%~dp0"

echo.
echo   ============================================
echo     AI Lead Generator - Stopping Dashboard
echo   ============================================
echo.

set "stopped=0"

REM --- Method 1: Kill by PID file ---
if exist "data\backend.pid" (
    set /p "BACKEND_PID=" < "data\backend.pid"
    if defined BACKEND_PID (
        echo   Stopping backend process (PID: %BACKEND_PID%)...
        taskkill /PID %BACKEND_PID% /F >nul 2>&1
        if not errorlevel 1 (
            echo   Process stopped.
            set "stopped=1"
        )
    )
    del "data\backend.pid" >nul 2>&1
)

REM --- Method 2: Kill by port (fallback) ---
if "%stopped%"=="0" (
    echo   Looking for process on port 8765...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING" 2^>nul') do (
        echo   Found process on port 8765 (PID: %%p)
        taskkill /PID %%p /F >nul 2>&1
        if not errorlevel 1 (
            echo   Process stopped.
            set "stopped=1"
        )
    )
)

REM --- Result ---
if "%stopped%"=="0" (
    echo   No running dashboard instance was found.
    echo   It may have already been stopped.
) else (
    echo.
    echo   Data and configuration have been preserved.
)

echo.
echo   ============================================
echo     Done.
echo   ============================================
echo.
timeout /t 3 >nul
