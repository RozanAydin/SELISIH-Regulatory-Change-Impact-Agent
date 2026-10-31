@echo off
title SELISIH Enterprise - 1-Click Launcher
cd /d "%~dp0"

echo =======================================================================
echo   SELISIH: Regulatory Change Impact Agent
echo   1-Click Enterprise Platform Launcher (FastAPI Backend + Next.js UI)
echo =======================================================================
echo.

if not exist "%~dp0run_demo.py" goto fallback

echo Menjalankan Smart Launcher via Python...
python "%~dp0run_demo.py"
if %ERRORLEVEL% EQU 0 goto :eof

echo.
echo [!] Launcher Python keluar atau terhenti.
echo.
pause
exit /b

:fallback
set TARGET_DIR=%~dp0repo_audit_latest
if not exist "%TARGET_DIR%\api.py" set TARGET_DIR=%~dp0repo_enterprise_web
if not exist "%TARGET_DIR%\api.py" set TARGET_DIR=%~dp0

echo [1/4] Direktori Kerja: %TARGET_DIR%...
cd /d "%TARGET_DIR%"

echo [2/4] Membersihkan port 8000 dan 3000 jika sedang terpakai...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [3/4] Menjalankan Backend FastAPI di port 8000...
start "SELISIH - Backend FastAPI (Port 8000)" cmd /k "cd /d %TARGET_DIR% && python -m uvicorn api:app --host 127.0.0.1 --port 8000"

timeout /t 3 >nul

echo [4/4] Menjalankan Frontend Next.js di port 3000...
start "SELISIH - Frontend Next.js (Port 3000)" cmd /k "cd /d %TARGET_DIR%\frontend && npm run start"

timeout /t 3 >nul

echo.
echo =======================================================================
echo   SISTEM SELISIH BERHASIL DIJALANKAN!
echo   - Web Dashboard : http://localhost:3000
echo   - API Swagger   : http://localhost:8000/docs
echo   - Benchmark API : http://localhost:8000/api/benchmark
echo =======================================================================
echo.
echo Membuka browser otomatis...
start http://localhost:3000
pause
