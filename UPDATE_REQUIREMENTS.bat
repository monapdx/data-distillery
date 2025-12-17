@echo off
setlocal

cd /d "%~dp0"
call ".venv\Scripts\activate"

pip freeze > requirements.txt

echo.
echo Updated requirements.txt
pause
