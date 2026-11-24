@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo 최초 실행: Python 3.12 가상환경을 설치합니다.
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
"%PY%" -c "import fastapi,pandas,sklearn,bs4,tzdata,uvicorn,httpx,pytest,multipart,scipy,openpyxl" 2>nul
if errorlevel 1 (
  echo 필요한 패키지를 설치합니다. 인터넷 연결이 필요합니다.
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
"%PY%" "newsroom_launch.py"
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo 실행에 실패했습니다. Python 3.12 설치 및 인터넷 연결을 확인하세요.
pause
exit /b 1
