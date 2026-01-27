@echo off
REM Breaktime Tracker Bot - Start Script
REM This script sets environment variables and runs the bot

echo ========================================
echo   Breaktime Tracker Bot Starting...
echo ========================================
echo.

REM Set environment variables
set BOT_TOKEN=8417145929:AAGW8uDSrK_VrRN4NIadLf9bOwcTXWabgEo
set BASE_DIR=C:\Users\us\Desktop\breaktime_tracker_bot

REM Change to bot directory
cd /d C:\Users\us\Desktop\breaktime_tracker_bot

echo Bot Token: Set
echo Base Directory: %BASE_DIR%
echo.
echo Starting bot...
echo Press Ctrl+C to stop the bot
echo ========================================
echo.

REM Run the bot
python breaktime_tracker_bot.py

REM If bot stops, pause so you can see the error
echo.
echo ========================================
echo Bot has stopped
echo ========================================
pause
