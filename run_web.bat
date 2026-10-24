@echo off
title SELISIH - Enterprise Web Platform
cd /d "%~dp0"
echo ========================================================
echo  Menjalankan SELISIH Enterprise Platform (Next.js + FastAPI)
echo ========================================================

echo [1/3] Menjalankan Backend API Server di jendela terpisah...
start "SELISIH API Server" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 >nul

echo [2/3] Memeriksa dependensi dan artefak Frontend Next.js...
cd frontend
if not exist "node_modules" (
    echo Paket dependensi frontend belum terpasang. Menjalankan npm install...
    call npm.cmd install
)

if not exist ".next" (
    echo Membangun artefak produksi Next.js...
    call npm.cmd run build
)

echo [3/3] Membuka Frontend Next.js di http://localhost:3000...
start http://localhost:3000
npm.cmd run start
