# SELISIH — Regulatory Change & Code Impact System

Aplikasi Dashboard Terpadu untuk Proyek Hackathon **IBM x Hacktiv8 (IT-Finance)**.
Menghubungkan **Klausul Regulasi OJK**, **Astra DB**, **Langflow**, dan **IBM Bob (watsonx Agent)** ke dalam satu antarmuka kontrol kepatuhan yang bersih dan minimalis.

---

## Cara Menjalankan Aplikasi

### Opsi 1: Klik Ganda
Klik ganda file **`run_app.bat`**. Browser akan otomatis terbuka di `http://localhost:8501`.

### Opsi 2: Lewat Terminal (PowerShell / CMD)
Masuk ke folder `rcia-app`:
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Modul Utama pada Dashboard

1. **Tab 1: Analisis Regulasi (Diff)**
   * Membandingkan POJK 77/2016 vs POJK 22/2023.
   * Menampilkan ringkasan perubahan kewajiban hukum, validitas sitasi pasal, dan status abstention.
   * Inspeksi kontrak data terstruktur `temuan.json`.

2. **Tab 2: Pemetaan Dampak Kode (IBM Bob)**
   * Memindai berkas pada repositori `mock_fintech_repo`.
   * Menampilkan titik kode terdampak di `app/core/config.py`.
   * Menampilkan perbandingan kode sebelum dan sesudah usulan patch.
   * Draf pengujian unit test regresi otomatis.

3. **Tab 3: Tata Kelola & Tinjauan Manusia**
   * Jejak audit (*audit trail*) kepatuhan formal.
   * Tombol verifikasi manusia untuk menerapkan patch ke berkas repositori secara nyata.
   * Tombol eksekusi pengujian unit test lokal.
