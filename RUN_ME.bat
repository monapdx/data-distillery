@echo off
setlocal ENABLEDELAYEDEXPANSION

REM =====================================================
REM Streamlit Takeout Toolkit - Local launcher (Windows)
REM =====================================================

REM Always run from the folder where this .bat lives
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Python not found. Please install Python 3.12+ from python.org
  echo Then re-run RUN_ME.bat
  pause
  exit /b 1
)

echo.
echo ================================================
echo   Streamlit Takeout Toolkit (Local-first)
echo ================================================
echo.

REM Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  py -3.12 -m venv .venv

)

REM Activate venv
call ".venv\Scripts\activate"

REM Install deps
echo.
echo [2/3] Installing dependencies (requirements.txt)...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [3/3] Choose an app to run:
echo   1) Inbox Archeology
echo   2) InboxGPT
echo   3) Category Viewer
echo   4) MBOX Viewer
echo   5) Search History Explorer
echo   6) WordLab
echo   Q) Quit
echo.

set /p choice=Enter choice (1-6 or Q): 

if /i "%choice%"=="Q" goto :eof

set "APP="
if "%choice%"=="1" set "APP=apps\inbox_archeology_app.py"
if "%choice%"=="2" set "APP=apps\inboxGPT_app.py"
if "%choice%"=="3" set "APP=apps\category_viewer.py"
if "%choice%"=="4" set "APP=apps\mbox_viewer_streamlit.py"
if "%choice%"=="5" set "APP=apps\search_history_app.py"
if "%choice%"=="6" set "APP=apps\wordlab_streamlit_app.py"

if "%APP%"=="" (
  echo.
  echo Invalid choice. Exiting.
  pause
  goto :eof
)

if not exist "%APP%" (
  echo.
  echo ERROR: Could not find "%APP%"
  echo Edit RUN_ME.bat and update the filename(s) if needed.
  pause
  goto :eof
)

echo.
echo Launching: %APP%
echo (Close the Streamlit tab or press Ctrl+C here to stop.)
echo.

streamlit run "%APP%"
pause
