@echo off
title InfraGuard Authority Server
echo ========================================================
echo       INFRAGUARD INFRASTRUCTURE PLATFORM LAUNCHER
echo ========================================================
echo.
cd /d "%~dp0"

if not exist ".env" (
    echo [.env] not found. Copying from .env.example...
    copy .env.example .env >nul
)

echo Starting InfraGuard Server on http://127.0.0.1:8000 ...
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
