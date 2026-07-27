@echo off
REM One-time setup: create venv, install deps, install Chromium for Playwright.
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtualenv...
    py -3 -m venv .venv
    if errorlevel 1 goto :err
)

call ".venv\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :err

echo Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :err

echo Installing Playwright Chromium browser (~300MB)...
python -m playwright install chromium
if errorlevel 1 goto :err

echo.
echo === Setup complete ===
echo Start the bot:    run.bat
echo One-shot scrape:  python scheduler.py
exit /b 0

:err
echo.
echo Setup FAILED. See messages above.
exit /b 1
