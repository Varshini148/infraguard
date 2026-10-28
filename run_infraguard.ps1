# InfraGuard PowerShell Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      INFRAGUARD INFRASTRUCTURE PLATFORM LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".env")) {
    Write-Host "[.env] not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host "Starting InfraGuard Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Open http://127.0.0.1:8000 in your browser to view the Authority Portal." -ForegroundColor White
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray
Write-Host ""

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
