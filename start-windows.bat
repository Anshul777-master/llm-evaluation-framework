@echo off
if not exist .venv\Scripts\python.exe (
  echo Please run setup-windows.bat first.
  pause
  exit /b 1
)
if not exist node_modules (
  echo Please run setup-windows.bat first.
  pause
  exit /b 1
)
start "Sentinel AI Backend" cmd /k "call .venv\Scripts\activate.bat && cd backend && python -m uvicorn app.main:app --reload --port 8000"
start "Sentinel AI Frontend" cmd /k "npm run dev"
echo Sentinel AI is starting.
echo Dashboard: http://localhost:3000
echo API docs:  http://localhost:8000/docs
timeout /t 3 >nul
start http://localhost:3000
