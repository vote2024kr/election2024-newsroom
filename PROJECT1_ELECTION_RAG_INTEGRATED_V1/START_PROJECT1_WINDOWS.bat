@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo NEWSROOM LAB Project 1 - Education Mode
echo Not connected to any official live election feed.
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  py -3.12 -m venv .venv
  if errorlevel 1 ( echo Python 3.12 is required. & pause & exit /b 1 )
)
"%PY%" -c "import pypdf,fastapi,pandas,sklearn,bs4,tzdata,uvicorn" 2>nul
if errorlevel 1 (
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 ( echo Package install failed. & pause & exit /b 1 )
)
start "" cmd /c "ping 127.0.0.1 -n 6 >nul && start http://127.0.0.1:8541/"
echo Main 2024 election results: http://127.0.0.1:8541/
echo Original training panel: http://127.0.0.1:8541/project1
"%PY%" -m uvicorn project1_app:app --host 127.0.0.1 --port 8541
pause
endlocal
