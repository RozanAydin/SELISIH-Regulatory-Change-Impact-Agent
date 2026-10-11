# app/core/config.py
"""
Konfigurasi Batas Finansial & Kepatuhan Bank / Fintech.
Catatan: File ini saat ini masih menggunakan aturan lama (POJK 77/2016).
"""

APP_NAME = "FintechCore Banking API"
VERSION = "1.4.2"
ENVIRONMENT = "production"

# ==========================================
# ATURAN KEPATUHAN FINANSIAL (POJK 77/2016)
# ==========================================
# Batas Maksimum Pemberian Pinjaman per Nasabah (Rp 20 Juta)
MAX_LOAN_AMOUNT = 20_000_000

# Batas Maksimum Suku Bunga Harian (0.4% per hari)
MAX_DAILY_INTEREST_RATE = 0.004

# Level Verifikasi KYC Minimum (1: Basic, 2: Biometric, 3: Full In-Person)
MIN_KYC_LEVEL = 2

# Batas Waktu Pelaporan Transaksi Mencurigakan (dalam jam)
SUSPICIOUS_REPORTING_WINDOW_HOURS = 72
