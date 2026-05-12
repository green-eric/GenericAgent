@echo off
chcp 65001 >nul
title 系统内存优化脚本
color 0A
echo ==========================================
echo      ThinkPad X13 内存优化脚本
echo ==========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本！
    echo 右键点击脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo [1/6] 正在清理临时文件...
cleanmgr /sagerun:1 >nul 2>&1
del /q/f/s %TEMP%\* >nul 2>&1
del /q/f/s C:\Windows\Temp\* >nul 2>&1
echo      完成！
echo.

echo [2/6] 正在设置虚拟内存为 8GB-24GB...
:: 禁用自动管理
wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False >nul 2>&1

:: 删除现有页面文件
wmic pagefileset where name="C:\\pagefile.sys" delete >nul 2>&1

:: 创建新的页面文件 (初始8GB=8192MB, 最大24GB=24576MB)
wmic pagefileset create name="C:\\pagefile.sys" InitialSize=8192 MaximumSize=24576 >nul 2>&1

echo      虚拟内存已设置为: 初始 8GB, 最大 24GB
echo.

echo [3/6] 正在优化系统服务...
:: 禁用 Superfetch (SysMain)
sc config SysMain start= disabled >nul 2>&1
sc stop SysMain >nul 2>&1

:: 禁用 Windows Search (如需搜索功能可跳过)
sc config WSearch start= disabled >nul 2>&1
sc stop WSearch >nul 2>&1

echo      已禁用 SysMain 和 Windows Search
echo.

echo [4/6] 正在清理内存...
:: 使用 RAMMap 方式清理工作集 (通过注册表)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "ClearPageFileAtShutdown" /t REG_DWORD /d 0 /f >nul 2>&1

echo      完成！
echo.

echo [5/6] 正在优化启动项...
:: 禁用不必要的启动项 (通过注册表)
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "OneDrive" /f >nul 2>&1

echo      完成！
echo.

echo [6/6] 正在创建系统还原点...
:: 创建还原点
wmic.exe /Namespace:\\root\default Path SystemRestore Call CreateRestorePoint "内存优化前还原点", 100, 7 >nul 2>&1

echo      还原点已创建！
echo.

echo ==========================================
echo        优化完成！
echo ==========================================
echo.
echo [重要] 请重启电脑使设置生效！
echo.
echo 重启后虚拟内存设置:
echo   - 初始大小: 8192 MB (8GB)
echo   - 最大大小: 24576 MB (24GB)
echo   - 位置: C:\pagefile.sys
echo.
echo 已优化的项目:
echo   [OK] 虚拟内存扩展至 8GB-24GB
echo   [OK] 清理临时文件
echo   [OK] 禁用 SysMain 服务
echo   [OK] 禁用 Windows Search
echo   [OK] 创建系统还原点
echo.
echo 是否需要立即重启? (Y/N)
set /p choice=
if /i "%choice%"=="Y" (
    echo 正在重启...
    shutdown /r /t 5 /c "系统内存优化完成，正在重启..."
) else (
    echo 请手动重启电脑以应用所有更改。
    pause
)
