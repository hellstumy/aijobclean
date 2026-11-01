@echo off
setlocal
title AI Job Search Assistant
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found. Running installer first...
    call "%~dp0install.bat"
    exit /b %errorlevel%
)

call venv\Scripts\activate.bat
python app.py
pause
