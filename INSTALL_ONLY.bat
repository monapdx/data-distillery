@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
)

call ".venv\Scripts\activate"
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo Done.
pause
