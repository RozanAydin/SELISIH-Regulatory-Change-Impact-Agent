@echo off
title SELISIH - 1-Click Enterprise Launcher
cd /d "%~dp0"
echo ========================================================
echo  SELISIH — Regulatory Change & Code Impact System
echo  Peluncur 1-Klik Platform Enterprise (Next.js + FastAPI)
echo ========================================================

echo [1/2] Menjalankan Backend FastAPI Server di port 8000...
start "SELISIH - FastAPI Server" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 >nul

echo [2/2] Membuka Frontend Next.js di http://localhost:3000...
cd frontend
if not exist ".next" (
    echo Membangun artefak produksi Next.js...
    call npm.cmd run build
)

start http://localhost:3000
npm.cmd run start
