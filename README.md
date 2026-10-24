# SELISIH — Regulatory Change & Code Impact System

Platform Enterprise Kepatuhan Regulasi untuk Hackathon **IBM x Hacktiv8 (IT-Finance)**.
Menjembatani **dokumen regulasi OJK** dengan **repositori kode perbankan dan fintech**, lalu memetakan
dampak perubahannya secara *human-in-the-loop* menggunakan teknologi IBM watsonx Granite dan IBM Bob.

Alur inti: **Sinkronisasi JDIH OJK / Ingest Vector DB (ChromaDB Lokal / Langflow)** -> **Regulatory Diff (watsonx Granite Framework)**
-> **Code Impact (IBM Bob & MCP Server Lokal)** -> **Human Review (Dry-run, Patch Aman, Rollback, Real Pytest)**.

---

## Arsitektur Platform

Platform SELISIH terdiri atas arsitektur dual-stack modern:
1. **Frontend**: Next.js 15 (React 19, TypeScript, Tailwind CSS, Lucide Icons) di port `3000`.
2. **Backend**: FastAPI REST & Server-Sent Events (SSE) Streaming di port `8000`.
3. **Local MCP Server**: Python stdlib JSON-RPC dual-pintu di port `8765` untuk IBM Bob.
4. **Vector Store**: ChromaDB lokal offline tersimpan di `data/chroma_db/`.
5. **Dashboard Legacy**: Streamlit monolitik di port `8501` (`app.py`).

---

## Cara Menjalankan

### Opsi 1: Platform Web Enterprise (Direkomendasikan)

1. Jalankan Backend FastAPI:
   Klik ganda **`run_api.bat`** atau jalankan via terminal:
   ```bash
   python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```

2. Jalankan Frontend Next.js:
   Klik ganda **`run_web.bat`** atau jalankan via terminal:
   ```bash
   cd frontend
   npm run start
   # atau untuk mode pengembangan: npm run dev
   ```
   Buka peramban di `http://localhost:3000`.

### Opsi 2: Dashboard Streamlit (Legacy Baseline)

Klik ganda **`run_app.bat`** atau jalankan:
```bash
streamlit run app.py
```
Buka peramban di `http://localhost:8501`.

---

## Modul Utama pada Platform Web

1. **Tab 1 — Analisis Perubahan Regulasi (Diff)**
   - Pemilih regulasi acuan dan pembaruan dinamis dari katalog JDIH OJK.
   - Komparasi dua arah berbasis watsonx Granite Framework.
   - 4 Metrik Validasi Kepatuhan: Klausul Terdampak, Validitas Sitasi (Anti-Halusinasi), Tingkat Keyakinan, dan Status Abstention.
   - Kartu perbandingan berdampingan (*side-by-side*) antara klausul acuan dan usulan pembaruan beserta kandidat kode terdampak.

2. **Tab 2 — Konsol Agen IBM Bob Shell & Integrasi MCP**
   - Terminal interaktif IBM Bob Shell dengan streaming penalaran agen AI secara real-time via Server-Sent Events (SSE).
   - Pengaman sesi (*session guard*): Tombol eksekusi terlindungi dan hanya aktif setelah analisis Tab 1 dijalankan pada sesi aktif.
   - Penampil berkas artefak handoff (`proposed_patch.diff`, `generated_tests.py`, `impact_report.json`) dengan *syntax highlighting* dan fitur unduh berkas.
   - Tombol peluncuran IBM Bob Desktop langsung ke repositori target lokal.

3. **Tab 3 — Tata Kelola & Tinjauan Dampak Kode (Human-in-the-Loop)**
   - Alur kerja bertahap bebas risiko (*Progressive Workflow*): Simulasi Dry-Run -> Tinjauan Diff Baris Kode -> Konfirmasi Patch -> Pengujian Otomatis Pytest Asli.
   - Deteksi nomor baris nyata secara dinamis (`selisih/impact.py`).
   - Pencadangan berkas otomatis (`.bak.<timestamp>`) sebelum penulisan kode.
   - Fitur Pemulihan Cadangan 1-Klik (*Rollback*) yang mencatat setiap tindakan ke Jejak Audit Enterprise.
   - Penegakan lisensi paket (*License Gating*): otomatis menonaktifkan penerapan patch bila kuota repositori penuh.

4. **Tab 4 — Katalog & Pemantau Regulasi OJK (JDIH)**
   - Sinkronisasi langsung ke portal resmi JDIH OJK (`jdih.ojk.go.id`).
   - Pemantauan POJK sektor Fintech (LPBBTI), Inovasi Teknologi (ITSK), dan Pelindungan Konsumen.
   - Tombol aksi cepat *"Analisis Dampak"* yang mengintegrasikan dokumen terpilih langsung ke Tab 1.

---

## Sistem Lisensi B2B & Manajemen Repositori

Sidebar menyediakan pengalih profil entitas perusahaan secara langsung:
- **PT Bank Digital Nusantara (Enterprise Plan)**: Kuota repositori tanpa batas, status lisensi aktif.
- **PT Dana Mandiri Fintech (Professional Plan)**: Kuota 25 repositori (terpakai 18), status lisensi aktif.
- **PT Pinjaman Kilat Indonesia (Starter Plan)**: Kuota 5 repositori (terpakai 5/5, kuota penuh), memicu *license gate* di mana tombol patch Tab 3 dikunci secara aman.

Modal **Manajer Repositori Terpadu** memungkinkan pendaftaran repositori lokal baru dengan verifikasi kuota paket secara instan.

---

## IBM Bob & Jembatan MCP Lokal

IBM Bob adalah *MCP client* di IDE lokal (bukan layanan REST eksternal). Jembatan komunikasi:
**Dashboard -> Server MCP Lokal (`mcp_server.py`) -> IBM Bob**, seluruhnya berjalan privat di `localhost`.

```bash
python mcp_server.py
```
- Registrasi server: `.bob/mcp.json`.
- Tools MCP: `get_temuan`, `list_artifacts`, `read_artifact`, `preview_patch`, `apply_patch`, `run_repo_tests`.
- Keamanan: Akses dibatasi ketat (*allowlist*) ke `mock_fintech_repo/` dan `artifacts/`.

---

## Menjalankan Pengujian Unit Test

```bash
# Seluruh unit test (FastAPI, Langflow, Vector Store, License, OJK, Impact, MCP, Mock Repo)
python -m pytest

# Hanya pengujian kepatuhan repo mock
python -m pytest mock_fintech_repo/tests
```

---

## Arsitektur Batas Kepercayaan (Trust Boundaries)

- **Domain Publik (Cloud):** Teks regulasi publik POJK, referensi hukum JDIH, Langflow/watsonx diff. **Kode perusahaan tidak pernah dikirim ke cloud.**
- **Domain Privat (Lokal):** Repositori kode sumber, IBM Bob, patch aman, dan unit test berjalan 100% lokal di mesin perusahaan.
- Satu-satunya artefak yang menyeberang adalah kontrak temuan regulasi publik (`data/temuan.json`).
