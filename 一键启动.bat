@echo off
chcp 65001 >nul

:: 配置参数
set "DEFAULT_PORT=5002"
set "DEFAULT_HOST=127.0.0.1"

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

:: Load configuration if exists
if exist "config\startup_config.bat" (
    call "config\startup_config.bat"
) else (
    echo [INFO] 使用默认配置
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
set "PYTHONPATH=%CD%;%PYTHONPATH%"
echo [OK] 已设置环境变量
echo.

:: Show Python version
echo [INFO] Python版本信息：
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python command failed
    pause
    exit /b 1
)
echo.

:: Get port from environment or use default
if not defined STARTUP_PORT set "STARTUP_PORT=%DEFAULT_PORT%"
if not defined STARTUP_HOST set "STARTUP_HOST=%DEFAULT_HOST%"

:: Check port occupancy
echo [INFO] 正在检查端口：%STARTUP_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%STARTUP_PORT% ^| findstr LISTENING') do (
    set "PORT_PID=%%a"
)
if defined PORT_PID (
    echo [WARN] 端口 %STARTUP_PORT% 已被占用，PID: %PORT_PID%
    set /p USER_CHOICE="是否终止该进程? [Y/N]: "
    if /i "%USER_CHOICE%"=="Y" (
        echo [INFO] 终止占用端口的进程...
        taskkill /PID %PORT_PID% /F >nul 2>&1
        if %errorlevel% equ 0 (
            echo [OK] 进程已终止
        ) else (
            echo [ERROR] 无法终止进程，可能需要管理员权限
            pause
            exit /b 1
        )
    ) else (
        echo [INFO] 用户选择不终止进程，尝试使用备用端口...
        set /a "STARTUP_PORT=%STARTUP_PORT%+1"
        echo [INFO] 尝试使用端口: %STARTUP_PORT%
    )
)
echo.

:: Wait for port availability
echo [INFO] 等待端口可用...
timeout /t 2 /nobreak >nul
echo.

:: Start GUI application in background
echo [INFO] 启动图形用户界面应用程序 (端口: %STARTUP_PORT%)...
echo [HINT] 按 Ctrl+C 键或者关闭窗口以停止操作
echo.

:: Detect and open in default browser
echo [INFO] 尝试打开默认浏览器...
start "" "http://%STARTUP_HOST%:%STARTUP_PORT%"

:: Start the application with port parameter (only --port is supported, not --host)
echo [CMD] python GUI\app.py --port=%STARTUP_PORT%
python GUI\app.py --port=%STARTUP_PORT%

:: Handle application exit
if %errorlevel% neq 0 (
    echo [ERROR] 应用程序异常退出
) else (
    echo [INFO] 应用程序已正常退出
)

pause