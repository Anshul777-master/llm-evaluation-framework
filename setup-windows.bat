@echo off
setlocal
echo Setting up Sentinel AI for VS Code...

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11-3.13 and try again.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install Node.js 22 LTS and try again.
  pause
  exit /b 1
)

if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
call npm install
if not exist .env copy .env.example .env >nul

echo.
echo Setup complete. Run start-windows.bat to open the app.
pause
