@echo off
title ADAS Vision Cockpit Launcher
echo =========================================================================
echo               STARTING REAL-TIME ADAS VISION COCKPIT
echo =========================================================================
echo.

cd /d "%~dp0"

:: 1. Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating Python virtual environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [!] No local venv found, using system Python...
)

:: 2. Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found on your PATH. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: 3. Launch Backend in a separate window
echo [*] Starting FastAPI Backend on port 8000...
start "ADAS Backend (FastAPI + Vision Pipeline)" cmd /k "python -m uvicorn src.api.main:app --port 8000"

:: 4. Check if frontend node_modules exist, if not run npm install
cd frontend
if not exist "node_modules\" (
    echo [*] Installing frontend dependencies...
    call npm install
)

:: 5. Launch Frontend in a separate window
echo [*] Starting React + Vite Frontend Dashboard on port 5173...
start "ADAS Frontend Dashboard (Vite)" cmd /k "npm run dev"

cd ..

:: 6. Wait 3 seconds and open the dashboard in default browser
timeout /t 3 /nobreak >nul
echo [*] Opening Cockpit Dashboard in browser...
start http://localhost:5173

echo.
echo =========================================================================
echo ADAS Vision Cockpit is now running!
echo - Web Dashboard:  http://localhost:5173
echo - Backend API:    http://localhost:8000
echo - Swagger Docs:   http://localhost:8000/docs
echo.
echo Keep the two opened terminal windows running while using the cockpit.
echo =========================================================================
pause

