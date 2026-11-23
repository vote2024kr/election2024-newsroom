@echo off
setlocal
cd /d "%~dp0"
title 통합 통계분석 툴 - 로컬 실행
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Python 3.12 가상환경 만들기...
  py -3.12 -m venv .venv
  if errorlevel 1 (echo Python 3.12 설치 여부를 확인하세요.& pause& exit /b 1)
)
echo [2/3] 필수 통계 패키지 확인 및 설치...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo 설치 오류가 발생했습니다.& pause& exit /b 1)
echo [3/3] 실행 및 브라우저 열기...
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 (echo 서버 실행 오류가 발생했습니다.& pause& exit /b 1)
endlocal
