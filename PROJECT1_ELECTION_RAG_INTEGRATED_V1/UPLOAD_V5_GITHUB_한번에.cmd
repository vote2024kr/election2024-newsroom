@echo off
chcp 65001 >nul
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "SRC=%~dp0"
set "SRC=%SRC:~0,-1%"
set "DEST=%TEMP%\V5_GH_SYNC_%RANDOM%%RANDOM%"
set "REPO=https://github.com/vote2024kr/election2024-newsroom.git"
set "SUB=PROJECT1_ELECTION_RAG_INTEGRATED_V1"
echo.
echo === 2024 V5 3rd revision: upload entire verified source ===
echo Repository: %REPO%  (branch: main)
echo This merges the provided latest project files into a fresh remote clone.
echo Existing files and documentation are kept, except the old unused UI module.
echo.
where git.exe >nul 2>&1
if errorlevel 1 goto NOGIT
if not exist "%SRC%\newsroom_district_explorer2024.py" goto NOSOURCE
if not exist "%SRC%\V5_3차_브라우저_미리보기.html" goto NOSOURCE
if not exist "%SRC%\screenshots_2024\v5_r3_replay_final.png" goto NOSOURCE

echo [1/6] Cloning latest repository...
git clone --depth 1 --branch main "%REPO%" "%DEST%"
if errorlevel 1 goto FAILED
echo [2/6] Copying latest V5 into clone (no mirror deletion)...
robocopy "%SRC%" "%DEST%\%SUB%" /E /R:1 /W:1 /NP /NFL /NDL /XD .git .venv .venv_pg venv __pycache__ .pytest_cache .idea .vscode /XF *.sqlite *.sqlite3 *.db *.pyc *.pyo *.log *.tmp .env .env.* *.pem *.key
if errorlevel 8 goto FAILED
echo [3/6] Removing ONLY the erroneous, now-unused previous UI overlay...
if exist "%DEST%\%SUB%\newsroom_election_layout_v2.py" del /f /q "%DEST%\%SUB%\newsroom_election_layout_v2.py"
echo [4/6] Staging latest code, documents, and six data-CG PNGs...
git -C "%DEST%" add -A -- "%SUB%"
if errorlevel 1 goto FAILED
git -C "%DEST%" status --short
if errorlevel 1 goto FAILED
git -C "%DEST%" diff --cached --quiet
if not errorlevel 1 goto NOCHANGE

echo [5/6] Creating a single commit...
git -C "%DEST%" commit -m "fix(v5): publish real third revision and enlarged national explorer layout"
if errorlevel 1 goto FAILED
echo [6/6] Pushing to GitHub main (without force)...
git -C "%DEST%" push origin HEAD:main
if errorlevel 1 goto FAILED
for /f "tokens=*" %%i in ('git -C "%DEST%" rev-parse HEAD') do set "NEW_COMMIT=%%i"
for /f "tokens=1" %%i in ('git -C "%DEST%" ls-remote origin refs/heads/main') do set "REMOTE_COMMIT=%%i"
if not "%NEW_COMMIT%"=="%REMOTE_COMMIT%" goto FAILED
echo.
echo [COMMIT COMPLETE] %NEW_COMMIT%
echo https://github.com/vote2024kr/election2024-newsroom/commit/%NEW_COMMIT%
goto FINISH

:NOCHANGE
echo [NO CHANGES] Same files are already in the remote repository.
goto FINISH
:NOGIT
echo [ERROR] Git for Windows was not found. Install it from https://git-scm.com/download/win
goto FAILED
:NOSOURCE
echo [ERROR] Place this CMD inside the fully extracted PROJECT1_ELECTION_RAG_INTEGRATED_V1 folder.
echo V5_3차_브라우저_미리보기.html and screenshots_2024 must exist next to it.
goto FAILED
:FAILED
echo.
echo [FAILED] GitHub was not confirmed as updated.
echo Temporary working folder: %DEST%
echo If there are login or Git name/email errors, copy the error text for diagnosis.
echo No forced push and no remote hard reset were performed.
endlocal
pause
exit /b 1
:FINISH
endlocal
pause
exit /b 0
