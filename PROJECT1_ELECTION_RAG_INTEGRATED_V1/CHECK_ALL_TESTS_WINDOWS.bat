@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Python virtual environment is missing.
  echo Run START_PROJECT1_WINDOWS.bat once to set up dependencies.
  pause
  exit /b 1
)
echo [1/3] NEWSROOM LAB regression tests (60 expected)
pushd newsroom
"%PY%" -m pytest -q tests
if errorlevel 1 goto failed
popd
echo [2/3] STAT WORKBENCH regression tests (44 expected)
pushd workbench
"%PY%" -m pytest -q tests
if errorlevel 1 goto failed
popd
echo [3/3] PROJECT 1 integration tests (17 expected)
"%PY%" -m pytest -q tests
if errorlevel 1 goto failed
echo [PASS] All 121 automated tests passed.
pause
exit /b 0
:failed
echo [FAIL] Stop: at least one test failed. Review error lines above.
pause
exit /b 1
