# SELISIH — Regulatory Change & Code Impact System

Aplikasi dashboard **Streamlit** untuk Hackathon **IBM x Hacktiv8 (IT-Finance)**.
Menjembatani **dokumen regulasi OJK** dengan **repositori kode fintech**, lalu memetakan
dampak perubahannya secara *human-in-the-loop*.

Alur inti: **Ingest & vector DB (Astra DB di dalam Langflow)** → **Regulatory Diff (Langflow)**
→ **Code Impact (scanner deterministik / IBM Bob)** → **Human Review (tanpa auto-deploy)**.

---

## Cara Menjalankan

### Opsi 1: Klik Ganda
Klik ganda file **`run_app.bat`**. Browser terbuka otomatis di `http://localhost:8501`.

### Opsi 2: Lewat Terminal
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Konfigurasi Langflow (opsional, untuk mode Live)
Salin `.env.example` menjadi `.env`, atau isi `.streamlit/secrets.toml`:

| Variabel            | Keterangan                                  |
|---------------------|---------------------------------------------|
| `LANGFLOW_API_URL`  | Base URL Langflow (default `http://localhost:7860`) |
| `LANGFLOW_FLOW_ID`  | ID flow analisis regulasi                   |
| `LANGFLOW_API_TOKEN`| API key Langflow (bila memakai auth)        |
| `MCP_ADMIN_PORT`    | Port HTTP admin `mcp_server.py` (default `8765`) |
| `MCP_ADMIN_URL`     | Alamat yang dipakai dashboard (`http://127.0.0.1:8765`) |
| `SELISIH_ORG_NAME`  | Nama organisasi pada License Gateway lokal  |
| `SELISIH_PLAN`      | `starter`, `professional`, atau `enterprise` |
| `SELISIH_LICENSE_STATUS` | `active`, `trial`, `expired`, atau `suspended` |
| `SELISIH_ACTIVE_REPOS` | Jumlah repo aktif organisasi              |
| `SELISIH_REPO_LIMIT` | Override kuota repo (opsional)             |

> Saat dijalankan lewat `streamlit`, nilai sebaiknya ditaruh di `.streamlit/secrets.toml`
> (bukan `.env`) karena `st.secrets` ikut menimpa environment variable.

### Eksekusi Live
Dashboard sekarang memakai **Live Langflow REST API** saja (tanpa pilihan mode di sidebar).
Tab 1 memanggil `{api_url}/api/v1/run/{flow_id}` dengan teks `data/pojk_baru_22_2023.txt`;
hasil ditulis ke `data/temuan.json`. Jika Langflow belum siap, aplikasi menampilkan error jujur
dan tidak memakai fallback demo sebagai hasil analisis.

### Lisensi Lokal
Sidebar **Langganan & Lisensi** membaca konfigurasi `SELISIH_*` dan benar-benar menjadi gate:
analisis, scan dampak, handoff Bob, dan apply patch dinonaktifkan bila status lisensi tidak aktif
atau kuota repositori terlampaui.

### Dukungan Dokumen Regulasi
- Loader lokal `selisih/documents.py` dapat membaca `.txt` dan PDF berbasis teks (`pypdf`).
- Cleanup dasar POJK menghapus noise nomor halaman dan merapikan whitespace.
- `split_by_pasal()` menyiapkan chunk per `Pasal` untuk calon ingest Astra DB, tetapi integrasi ingest Langflow/Astra **belum dikerjakan**.
- PDF hasil scan/foto butuh OCR terpisah; saat ini tidak termasuk.

## Modul Utama pada Dashboard

1. **Tab 1 — Analisis Regulasi (Diff)**
   - Membandingkan POJK 77/2016 vs POJK 22/2023 via Langflow (atau data demo terverifikasi).
   - Ringkasan perubahan, validitas sitasi, keyakinan, dan status abstention.
   - Inspeksi JSON: `data/temuan_schema.json` (kontrak), `data/temuan.json` (hasil live), `data/temuan_golden_path.json` (contoh).

2. **Tab 2 — Pemetaan Dampak Kode & Integrasi IBM Bob (MCP / Bob Shell)**
   - Scanner deterministik dari `temuan.json` memetakan `kandidat_kode[].evidence` ke file & baris nyata di `mock_fintech_repo`.
   - Menampilkan diff lama → usulan per kandidat.
   - Pendekatan **Hybrid**:
     - **"Jalankan Agen IBM Bob di Dashboard"**: Menjalankan Bob Shell di latar belakang (*headless*), merender penalaran agen AI langsung di web.
     - **"Buka di IBM Bob Desktop"**: Meluncurkan GUI IBM Bob langsung membuka repositori target.
   - Ekspor artefak `artifacts/` (`impact_report.json`, `proposed_patch.diff`, `generated_tests.py`) dan handoff ke server MCP lokal di `localhost`.

3. **Tab 3 — Tata Kelola & Tinjauan Manusia**
   - Jejak audit + prinsip *draft-only* (tanpa auto-deploy).
   - **Dry-run** pratinjau patch → konfirmasi peninjau → penerapan dengan **backup otomatis** `.bak.<stamp>`.
   - Eksekusi **unit test asli via `pytest`**; tombol tolak untuk mengembalikan catatan ke penelaahan.

## IBM Bob (MCP) — alur privat

Bob adalah **MCP client** di IDE lokal (bukan service REST yang bisa dipanggil aplikasi).
Jembatan yang aman: **dashboard → server MCP lokal → Bob**, semuanya di `localhost`.

```bash
python mcp_server.py          # stdio (untuk Bob) + HTTP admin /health & /handoff (untuk dashboard)
```

- Registrasi server: eksklusif di `.bob/mcp.json`.
- Tool untuk Bob: `get_temuan`, `list_artifacts`, `read_artifact`, `preview_patch`, `apply_patch`, `run_repo_tests`.
- Akses di-allowlist ke `mock_fintech_repo/` + `artifacts/`; semua tulis lewat dry-run + backup.

## Menjalankan Unit Test

```bash
python -m pytest              # seluruh test (selisih/ + mock repo)
python -m pytest mock_fintech_repo/tests   # hanya repo mock
```

## Arsitektur & Batas Kepercayaan

- **Domain publik (cloud):** teks POJK, Astra DB, Langflow — **tidak ada kode perusahaan**.
- **Domain privat (lokal):** source code, IBM Bob, patch, unit test — **tidak pernah dikirim ke cloud**.
- Satu-satunya artefak yang menyeberang: `data/temuan.json` (turunan regulasi publik).
- Astra DB berada **di dalam Langflow**; aplikasi tidak memegang kredensial Astra.

## Status Fase

Selesai: Fase 0 (kontrak, konfigurasi, loader dokumen TXT/PDF), Fase 2 (app → Langflow REST), Fase 3 (jembatan MCP lokal ke Bob), Fase 4 (dampak kode & patch aman), Fase 6 (testing & dokumentasi).
Menunggu: Fase 1 (flow Langflow — dibangun di UI Langflow), Fase 5 (pengerasan & audit).

Rincian di `PROGRESS.md` dan `docs/CONTEXT.md`.
