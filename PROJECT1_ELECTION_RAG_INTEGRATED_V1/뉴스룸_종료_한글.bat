@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "newsroom_stop.py"
  goto finished
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "newsroom_stop.py"
  goto finished
)
where python >nul 2>nul
if not errorlevel 1 (
  python "newsroom_stop.py"
  goto finished
)
powershell -NoProfile -ExecutionPolicy Bypass -File "patch_problem.ps1"
:finished
pause
