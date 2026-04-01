@echo off
chcp 65001 > nul
echo ==========================================
echo    AGIAgent Windows 自动化安装脚本
echo ==========================================
echo.
echo 正在启动安装程序...
echo.

REM 检查PowerShell是否可用
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到PowerShell，无法运行安装脚本
    pause
    exit /b 1
)

REM 使用PowerShell执行安装脚本
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 安装脚本执行失败
    pause
    exit /b 1
)

echo.
echo 安装程序已退出
pause
