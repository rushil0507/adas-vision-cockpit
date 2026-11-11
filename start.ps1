# ADAS Vision Cockpit PowerShell Launcher
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "             STARTING REAL-TIME ADAS VISION COCKPIT                      " -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# 1. Activate Python virtual environment if it exists
$VenvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "[*] Activating virtual environment..." -ForegroundColor Green
    & $VenvActivate
} else {
    Write-Host "[!] No venv found; using environment Python..." -ForegroundColor Yellow
}

# 2. Check Python
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "[*] Python available: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python could not be found. Please ensure Python 3.10+ is on your PATH." -ForegroundColor Red
    exit 1
}

# 3. Start Backend in a new window
Write-Host "[*] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; if (Test-Path 'venv\Scripts\Activate.ps1') { & 'venv\Scripts\Activate.ps1' }; python -m uvicorn src.api.main:app --port 8000"

# 4. Start Frontend
$FrontendDir = Join-Path $ProjectRoot "frontend"
if (Test-Path $FrontendDir) {
    Write-Host "[*] Launching React Dashboard on http://localhost:5173..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$FrontendDir'; npm run dev"
}

# 5. Open browser after brief delay
Start-Sleep -Seconds 3
Write-Host "[*] Opening browser to ADAS Cockpit..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "ADAS Vision Cockpit is launching!" -ForegroundColor Green
Write-Host "  - Frontend Cockpit: http://localhost:5173"
Write-Host "  - Backend API:      http://localhost:8000"
Write-Host "  - Swagger Docs:     http://localhost:8000/docs"
Write-Host "=========================================================================" -ForegroundColor Cyan

