@echo off
REM Start the FastAPI server. Leave this window open — APScheduler triggers
REM the daily scrape at 09:00 from inside this process.
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Virtualenv missing. Run setup.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Opening http://localhost:8000 ...
start "" "http://localhost:8000"

python -m uvicorn main:app --host 127.0.0.1 --port 8000
