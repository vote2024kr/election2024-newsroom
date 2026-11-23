@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo V1.0을 먼저 START_WINDOWS.bat 으로 설치/실행하세요.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pytest -q
pause
