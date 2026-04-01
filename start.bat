@echo off
chcp 65001 >nul

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ===========================================
echo AGIAgent One-Click Start
echo ===========================================
echo.

:: Change to script directory
cd /d "%SCRIPT_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to switch to script directory
    pause
    exit /b 1
)

:: Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

echo [INFO] Activating virtual environment...
call .\.venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

:: Set environment variables
echo [INFO] Setting environment variables...
set "PATH=%CD%\.venv\Scripts\;%PATH%"
set "PLAYWRIGHT_BROWSERS_PATH=%CD%\Extend-dependenc\playwright"
echo [OK] Environment variables set
echo.

:: Show Python version
python --version
echo.

:: Check port occupancy
echo [INFO] Checking port 5002...
for /f "tokens=5" %%a in ('powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5002 -ErrorAction SilentlyContinue ^| Select-Object -ExpandProperty OwningProcess"') do (
    echo [INFO] Killing process %%a using port 5002...
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo.

:: Start GUI application
echo [INFO] Starting GUI application...
echo [HINT] Press Ctrl+C or close window to stop
echo.
start msedge http://127.0.0.1:5002
python GUI\app.py
