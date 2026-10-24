@echo off
title SELISIH - FastAPI Backend Server
cd /d "%~dp0"
echo ========================================================
echo  Menjalankan SELISIH Enterprise API (Port 8000)
echo ========================================================
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
pause
