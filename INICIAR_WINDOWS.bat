@echo off
cd /d "%~dp0"
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 app.py --open-browser
    pause
    exit /b
)
python --version >nul 2>&1
if not errorlevel 1 (
    python app.py --open-browser
    pause
    exit /b
)
python3 --version >nul 2>&1
if not errorlevel 1 (
    python3 app.py --open-browser
    pause
    exit /b
)
echo Python nao encontrado. Solicite a instalacao aprovada do Python 3.12 ou superior.
pause
