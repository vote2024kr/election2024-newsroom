@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PORT=8510"
echo -----------------------------------------------
echo   NEWSROOM LAB V0.6 - Election Data Analyzer
 echo   Demo samples, charts, methods and tables
 echo   This is NOT a live election-result feed
 echo -----------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Python 3.12 not found. Please install it.
        pause
        exit /b 1
    )
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)
echo.
echo Opening http://127.0.0.1:%PORT%
echo Keep the NEWSROOM server window open while using the site.
start "NEWSROOM_LAB_V06_SERVER" cmd /k ".venv\Scripts\python.exe server.py"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:%PORT%"
exit /b 0
