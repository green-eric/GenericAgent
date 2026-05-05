@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Need Admin! Right click - Run as administrator
    pause
    exit /b 1
)
echo Creating WeChat Bot scheduled task...
schtasks /delete /tn "WeChatBot" /f >nul 2>&1
schtasks /create /tn "WeChatBot" /tr "D:\GenericAgent\frontends\start_bot.bat" /sc onlogon /rl highest /f
if %errorlevel% equ 0 (
    echo OK! Task created. Bot will start at logon.
) else (
    echo FAILED! Error: %errorlevel%
)
pause
