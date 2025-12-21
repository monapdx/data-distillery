@echo off
setlocal

REM Always run the suite router (Home + navigation)
cd /d "%~dp0"

echo.
echo ==========================================
echo   Data Distillery - launching suite home
echo ==========================================
echo.

python -m streamlit run suite_home.py

echo.
echo Streamlit exited. Press any key to close.
pause >nul
