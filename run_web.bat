@echo off
title SELISIH - Enterprise Web Platform
cd /d "%~dp0"
echo ========================================================
echo  Menjalankan SELISIH Enterprise Platform (Next.js + FastAPI)
echo ========================================================

echo [1/2] Menjalankan Backend API Server di jendela terpisah...
start "SELISIH API Server" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 >nul

echo [2/2] Menyiapkan Frontend Next.js di http://localhost:3000 ...
cd frontend
if not exist ".next" (
    echo Membangun artefak produksi Next.js...
    call npm.cmd run build
)

start http://localhost:3000
npm.cmd run start
