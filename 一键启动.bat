@echo off
chcp 65001 >nul

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ===========================================
echo AGI Agent 一键启动
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

echo [INFO] 正在激活虚拟环境...
call .\.venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] 虚拟环境已激活
echo.

:: Set environment variables
echo [INFO] 设置环境变量...
set "PATH=%CD%\.venv\Scripts\;%PATH%"
set "PLAYWRIGHT_BROWSERS_PATH=%CD%\Extend-dependenc\playwright"
echo [OK] 已设置环境变量
echo.

:: Show Python version
python --version
echo.

:: Check port occupancy
echo [INFO] 正在检查端口：5002...
for /f "tokens=5" %%a in ('powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5002 -ErrorAction SilentlyContinue ^| Select-Object -ExpandProperty OwningProcess"') do (
    echo [INFO] Killing process %%a using port 5002...
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo.

:: Start GUI application
echo [INFO] 启动图形用户界面应用程序...
echo [HINT] 按 Ctrl+C 键或者关闭窗口以停止操作
echo.
start msedge http://127.0.0.1:5002
python GUI\app.py
