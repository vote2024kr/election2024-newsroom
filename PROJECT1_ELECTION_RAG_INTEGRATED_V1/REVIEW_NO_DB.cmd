@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
 echo Python 가상환경(.venv)이 없습니다.
 echo 기존 V5에서 가상환경을 준비하거나 Python 및 requirements.txt를 먼저 설치하세요.
 pause
 exit /b 1
)
echo [V5 개편 검토용] 운영 PostgreSQL은 연결하지 않습니다.
start "" "http://127.0.0.1:8550/safe2024"
"%PYTHON%" -m uvicorn review_preview2024:app --host 127.0.0.1 --port 8550 --no-access-log
pause
