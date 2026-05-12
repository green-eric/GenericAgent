@echo off
chcp 65001 >nul
cd /d D:\Project\AnnualScorer
echo [%date% %time%] 开始运行 annual_scorer.py --force-refresh
python annual_scorer.py --force-refresh
echo [%date% %time%] 运行结束，退出码: %errorlevel%
pause
