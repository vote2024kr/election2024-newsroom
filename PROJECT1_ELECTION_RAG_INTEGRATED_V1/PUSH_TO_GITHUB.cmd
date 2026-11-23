@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "REMOTE=https://github.com/vote2024kr/election2024-newsroom.git"
set "SRC=%~dp0PROJECT1_ELECTION_RAG_INTEGRATED_V1"
set "DEST=%USERPROFILE%\Documents\election2024-newsroom"
echo [1/5] Checking Git for Windows...
where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git for Windows not installed: https://git-scm.com/download/win
  pause
  exit /b 1
)
if not exist "%SRC%\RUN_POSTGRES_NEWSROOM.cmd" (
  echo ERROR: Extract the complete ZIP first.
  pause
  exit /b 1
)
echo [2/5] Downloading current shared repository...
if exist "%DEST%\.git" (
  git -C "%DEST%" diff --quiet
  if errorlevel 1 goto dirty
  git -C "%DEST%" diff --cached --quiet
  if errorlevel 1 goto dirty
  git -C "%DEST%" pull --ff-only origin main
  if errorlevel 1 goto failed
) else (
  git clone "%REMOTE%" "%DEST%"
  if errorlevel 1 goto failed
)
if exist "%DEST%\PROJECT1_ELECTION_RAG_INTEGRATED_V1\project1_app.py" (
  echo ERROR: The shared repository already has project code.
  echo This one-time installer will NOT overwrite teammate changes.
  echo Ask ChatGPT for a versioned update/merge instead.
  pause
  exit /b 2
)
echo [3/5] Copying NEWSROOM LAB PostgreSQL V5 to a new project directory...
robocopy "%SRC%" "%DEST%\PROJECT1_ELECTION_RAG_INTEGRATED_V1" /E /R:1 /W:1 /XD .venv .venv_pg venv __pycache__ .pytest_cache .git /XF *.log *.tmp *.bak *.pyc *.pem *.key .env *.sqlite3 *.db GITHUB_TEAM_GUIDE.md >nul
if errorlevel 8 goto failed
for /f "delims=" %%a in ('git -C "%DEST%" config user.name') do set "GIT_AUTHOR_FOUND=1"
if not defined GIT_AUTHOR_FOUND git -C "%DEST%" config user.name "belokang90"
for /f "delims=" %%a in ('git -C "%DEST%" config user.email') do set "GIT_EMAIL_FOUND=1"
if not defined GIT_EMAIL_FOUND git -C "%DEST%" config user.email "330756025+belokang90@users.noreply.github.com"
echo [4/5] Committing additions without deleting original repository files...
git -C "%DEST%" add -- "PROJECT1_ELECTION_RAG_INTEGRATED_V1"
if errorlevel 1 goto failed
git -C "%DEST%" diff --cached --quiet
if not errorlevel 1 goto done
git -C "%DEST%" commit -m "Add NEWSROOM LAB PostgreSQL 2024 historical replay V5"
if errorlevel 1 goto failed
echo [5/5] Publishing to GitHub...
git -C "%DEST%" push origin main
if errorlevel 1 goto failed
:done
echo.
echo SUCCESS: https://github.com/vote2024kr/election2024-newsroom
pause
exit /b 0
:dirty
echo ERROR: Uncommitted local changes found. No files were changed.
pause
exit /b 3
:failed
echo.
echo ERROR: Upload stopped. Please share the last lines of this window.
pause
exit /b 1
