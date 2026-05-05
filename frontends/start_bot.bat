@echo off
chcp 65001 >nul 2>&1
title WeChat Bot
set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897
set http_proxy=http://127.0.0.1:7897
set https_proxy=http://127.0.0.1:7897
cd /d D:\GenericAgent\frontends
echo [%date% %time%] WeChat Bot starting...
:RESTART
python -u D:\GenericAgent\frontends\wechatapp.py
echo [%date% %time%] bot exited, restart in 5s...
timeout /t 5 /nobreak >nul
goto RESTART
