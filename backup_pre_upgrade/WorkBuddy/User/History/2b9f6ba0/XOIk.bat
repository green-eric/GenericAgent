@echo off
chcp 65001 >nul
title 恢复系统默认设置
color 0C
echo ==========================================
echo      恢复系统默认设置
echo ==========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

echo [1/4] 正在恢复虚拟内存自动管理...
wmic computersystem where name="%computername%" set AutomaticManagedPagefile=True >nul 2>&1
echo      完成！
echo.

echo [2/4] 正在恢复 SysMain 服务...
sc config SysMain start= auto >nul 2>&1
sc start SysMain >nul 2>&1
echo      完成！
echo.

echo [3/4] 正在恢复 Windows Search 服务...
sc config WSearch start= auto >nul 2>&1
sc start WSearch >nul 2>&1
echo      完成！
echo.

echo [4/4] 正在清理临时文件...
del /q/f/s %TEMP%\* >nul 2>&1
echo      完成！
echo.

echo ==========================================
echo        恢复完成！
echo ==========================================
echo.
echo 系统已恢复到默认设置。
echo 请重启电脑使更改生效。
echo.
pause
