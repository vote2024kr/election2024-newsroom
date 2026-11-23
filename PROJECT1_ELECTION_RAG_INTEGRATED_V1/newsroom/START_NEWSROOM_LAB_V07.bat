@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PORT=8512"
set "PY=.venv\Scripts\python.exe"
echo =====================================================
echo  NEWSROOM LAB V0.7 - Election Data Analysis (DEMO)
echo  Local mode ONLY. Real election/live feed NOT connected.
echo =====================================================
if not exist "%PY%" (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Python 3.12 is missing.
    pause
    exit /b 1
  )
)
"%PY%" -c "import fastapi, uvicorn, bs4, tzdata"
if errorlevel 1 (
  echo [INFO] Installing project requirements including tzdata...
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Package installation failed. See the console above.
    pause
    exit /b 1
  )
)
echo [OK] Opening http://127.0.0.1:%PORT%
echo [INFO] Keep the server terminal window open while using the app.
start "NEWSROOM_LAB_V07_SERVER" cmd /k ""%PY%" server.py"
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:%PORT%"
endlocal
