@echo off
title SELISIH - Enterprise Web Platform
cd /d "%~dp0"

echo ========================================================
echo  SELISIH - Regulatory Change and Code Impact System
echo  Peluncur 1-Klik Platform Enterprise: Next.js + FastAPI
echo ========================================================

echo [1/3] Menyalakan Backend FastAPI Server di port 8000...
start "SELISIH - FastAPI Server" cmd /k "python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Menyalakan Frontend Next.js di port 3000...
cd frontend
start "SELISIH - Next.js Frontend" cmd /k "npm.cmd run dev"

echo [3/3] Menunggu server siap...
timeout /t 4 >nul

echo Membuka peramban di http://localhost:3000...
start http://localhost:3000

echo.
echo ========================================================
echo  Platform SELISIH Enterprise Berhasil Dijalankan!
echo   - Frontend : http://localhost:3000
echo   - Backend  : http://127.0.0.1:8000/docs
echo ========================================================
echo  Catatan: Jangan tutup jendela terminal server yang terbuka.
echo.
timeout /t 3 >nul
exit
