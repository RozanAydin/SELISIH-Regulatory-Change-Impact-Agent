@echo off
title SELISIH - Regulatory Change and Code Impact System
echo ========================================================
echo  Menjalankan SELISIH Control Plane Dashboard
echo ========================================================
cd /d "%~dp0"

echo Memeriksa instalasi streamlit...
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo Menginstal streamlit dan requests...
    pip install -r requirements.txt
)

echo Membuka aplikasi di browser...
streamlit run app.py
pause
