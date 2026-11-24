@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHON_RUN="
if exist ".venv\Scripts\python.exe" set "PYTHON_RUN=.venv\Scripts\python.exe"
if not defined PYTHON_RUN (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_RUN=python"
)
if not defined PYTHON_RUN (
  where py >nul 2>nul
  if not errorlevel 1 set "PYTHON_RUN=py"
)
if not defined PYTHON_RUN (
  echo [ERROR] Python을 찾을 수 없습니다.
  echo 기존 V5 프로젝트에 Python 또는 .venv를 준비해 주세요.
  echo 바로보는 미리보기: V5_2차_브라우저_미리보기.html 을 더블클릭하세요.
  pause
  exit /b 1
)
"%PYTHON_RUN%" -c "import fastapi,uvicorn" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 이 Python 환경에는 fastapi 및 uvicorn이 설치되어 있지 않습니다.
  echo 기존 V5에서 사용한 가상환경을 사용하거나 기존 requirements.txt 설치를 확인해 주세요.
  echo 브라우저 미리보기는 V5_2차_브라우저_미리보기.html 을 더블클릭하세요.
  pause
  exit /b 1
)
echo ======================================================
echo  V5 2차 디자인 검토용 서버 - 운영 DB 접근 안 함
echo ======================================================
echo  전국 확정 개표: http://127.0.0.1:8550/safe2024?page=final
echo  지역구 탐색    : http://127.0.0.1:8550/safe2024?page=district
echo  서버 종료: 이 창에서 Ctrl+C
start "" "http://127.0.0.1:8550/safe2024?page=final"
"%PYTHON_RUN%" -m uvicorn review_preview2024:app --host 127.0.0.1 --port 8550 --no-access-log
pause
