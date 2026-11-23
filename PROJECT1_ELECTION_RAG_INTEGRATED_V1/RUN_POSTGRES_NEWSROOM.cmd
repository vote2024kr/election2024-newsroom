@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [1/3] Preparing Python 3.12 environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] Checking Python packages...
"%PY%" -c "import pypdf,fastapi,pandas,sklearn,bs4,tzdata,uvicorn,httpx,pytest,multipart,scipy,openpyxl,psycopg" 2>nul
if errorlevel 1 (
  echo Installing packages. Internet connection is required.
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
echo [3/3] Checking PostgreSQL and starting dashboard...
"%PY%" postgres_start.py
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo.
echo Launch did not complete. Please capture this screen for troubleshooting.
pause
exit /b 1
