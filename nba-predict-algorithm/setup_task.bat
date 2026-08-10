@echo off
chcp 65001 >/dev/null
echo ========================================
echo NBA Predict System - Task Scheduler Setup
echo ========================================
echo.

:: Check admin privileges
net session >/dev/null 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator privileges required
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Get project path
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%

:: Create logs directory
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

:: Create VBS script for silent execution
echo Set WshShell = CreateObject("WScript.Shell") > "%PROJECT_DIR%\run_daily_update.vbs"
echo WshShell.Run "cmd /c cd /d ""%PROJECT_DIR%"" && python scripts\daily_update.py >> logs\daily_update.log 2>&1", 0, False >> "%PROJECT_DIR%\run_daily_update.vbs"

:: Create scheduled task (runs daily at 8:00 AM)
schtasks /create /tn "NBA_Predict_DailyUpdate" /tr "wscript.exe \"%PROJECT_DIR%\run_daily_update.vbs\"" /sc daily /st 08:00 /f

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Scheduled task created
    echo Task Name: NBA_Predict_DailyUpdate
    echo Run Time: Daily at 08:00
    echo Log File: %PROJECT_DIR%\logs\daily_update.log
    echo.
    echo Management commands:
    echo   View: schtasks /query /tn "NBA_Predict_DailyUpdate"
    echo   Delete: schtasks /delete /tn "NBA_Predict_DailyUpdate" /f
    echo   Run Now: schtasks /run /tn "NBA_Predict_DailyUpdate"
) else (
    echo.
    echo [ERROR] Failed to create scheduled task
)

echo.
pause
