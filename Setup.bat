@echo off
chcp 65001 >nul 2>&1
title AI Lead Generator - Setup

REM ============================================
REM   AI Lead Generator - Setup Script
REM   Checks prerequisites, installs dependencies,
REM   builds frontend, and initializes storage.
REM ============================================

cd /d "%~dp0"

echo.
echo   ============================================
echo     AI Lead Generator - Setup
echo   ============================================
echo.

REM --- [1/9] Check Python 3.12 ---
echo   [1/9] Checking Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Python 3.12 is not installed or not in PATH.
    echo   Please install Python 3.12 from https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('py -3.12 --version 2^>^&1') do set "PY_VER=%%v"
echo   Found: %PY_VER%
echo.

REM --- [2/9] Check Node.js ---
echo   [2/9] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Node.js is not installed or not in PATH.
    echo   Please install Node.js LTS from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version 2^>^&1') do set "NODE_VER=%%v"
echo   Found: Node.js %NODE_VER%
echo.

REM --- [3/9] Create Python virtual environment ---
echo   [3/9] Creating Python virtual environment...
if exist "venv\Scripts\python.exe" (
    echo   Virtual environment already exists. Skipping creation.
) else (
    py -3.12 -m venv venv
    if errorlevel 1 (
        echo.
        echo   ERROR: Failed to create Python virtual environment.
        pause
        exit /b 1
    )
    echo   Virtual environment created.
)
echo.

REM --- [4/9] Install Python dependencies ---
echo   [4/9] Installing Python dependencies...
echo   This may take several minutes on first run...
echo.
"venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel >nul 2>&1
"venv\Scripts\pip.exe" install -r backend\requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: Failed to install Python dependencies.
    echo   Check your internet connection and try again.
    pause
    exit /b 1
)
echo   Python dependencies installed.
echo.

REM --- [5/9] Install Playwright browser ---
echo   [5/9] Installing Playwright browser (Chromium)...
echo   This may take a few minutes...
echo.
"venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo.
    echo   WARNING: Playwright browser installation had issues.
    echo   Web scraping may not work without a browser.
    echo   You can retry with: venv\Scripts\playwright install chromium
) else (
    echo   Playwright browser installed.
)
echo.

REM --- [6/9] Install frontend dependencies ---
echo   [6/9] Installing frontend dependencies...
echo   This may take a few minutes...
echo.
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 (
    echo.
    echo   ERROR: Failed to install frontend dependencies.
    pause
    exit /b 1
)
echo   Frontend dependencies installed.
echo.

REM --- [7/9] Build Angular frontend ---
echo   [7/9] Building Angular frontend...
call npm run build
if errorlevel 1 (
    echo.
    echo   ERROR: Failed to build the frontend.
    pause
    exit /b 1
)
cd /d "%~dp0"
echo   Frontend built successfully.
echo.

REM --- [8/9] Create required directories ---
echo   [8/9] Creating required directories...
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"
echo   Directories ready.
echo.

REM --- [9/9] Initialize CSV storage and validate ---
echo   [9/9] Initializing data storage and validating...
set "PYTHONPATH=%~dp0backend"
"venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'backend'); from services.csv_service import init_csv; from config.settings import ensure_dirs; ensure_dirs(); init_csv(); print('  CSV storage initialized.')"
if errorlevel 1 (
    echo.
    echo   WARNING: CSV initialization had an issue, but the app will create
    echo   the file automatically on first run.
) else (
    echo   Validation passed.
)
echo.

echo   ============================================
echo     Setup Complete!
echo   ============================================
echo.
echo   You can now start the dashboard by double-clicking:
echo     Start Dashboard.bat
echo.
echo   To stop the dashboard, double-click:
echo     Stop Dashboard.bat
echo.
pause
