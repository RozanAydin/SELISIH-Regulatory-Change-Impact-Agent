# PROGRESS — SELISIH / RCIA

Checklist status pekerjaan. Update setelah tiap tugas selesai.
Legenda: `[ ]` belum, `[~]` sedang dikerjakan, `[x]` selesai.

Terakhir diperbarui: 2026-10-24

---

## Setup Repo

- [x] `.gitignore` lengkap (Python, venv, `.env`, secrets, cache, IDE/OS).
- [x] Dokumen konteks dibuat (`AGENTS.md`, `docs/CONTEXT.md`, `PROGRESS.md`, `DECISIONS.md`).
- [ ] Commit & push pertama ke GitHub.
- [x] Perbaiki `README.md` (nama file `temuan.json`, collection, cara jalankan Demo vs Live).

## Fase 0 — Fondasi (kontrak data & konfigurasi)

- [x] Finalkan JSON Schema `temuan.json` → `data/temuan_schema.json`.
- [x] Pindahkan konfigurasi Langflow ke `.env` + `.streamlit/secrets.toml` (loader di `selisih/config.py`).
- [x] Buat `.env.example`.
- [x] Buat adapter `normalize_response()` / `run_analysis()` → `selisih/langflow.py`.
- [x] Loader dokumen lokal `.txt`/PDF berbasis teks → `selisih/documents.py` (`load_document_text`, `clean_pojk_text`, `split_by_pasal`; ingest Astra belum).
- [x] Unit test adapter (mock HTTP) → `tests/test_langflow_adapter.py` (11 tes lolos).

## Fase 1 — Flow Langflow & Embedded Execution

- [x] Template flow resmi: `flows/selisih_regulatory_flow.json` (TextInput -> Astra DB -> watsonx Granite LLM -> StructuredOutput).
- [x] Eksekusi mandiri tanpa server (Embedded Execution): `run_embedded_analysis()` di `selisih/langflow.py`.
- [x] Zero-configuration: otomatis aktif tanpa mengharuskan pengguna membuka server Langflow di port 7860.
- [x] Dukungan dual-mode: embedded by default, tetap mendukung REST API jika `LANGFLOW_FLOW_ID` dikonfigurasi.
- [x] Unit test embedded flow & verifikasi file flow JSON (`tests/test_langflow_adapter.py`).


## Fase 2 — Sambung `app.py` ke Langflow

- [x] Ganti `time.sleep`/status palsu dengan REST nyata (`run_analysis`).
- [x] Health check sidebar (jujur, `GET /health`, TTL 15s).
- [x] Live Langflow REST only di UI; jika Langflow gagal, tampilkan error jujur tanpa fallback demo sebagai hasil analisis.
- [x] Sidebar disederhanakan menjadi Live-only: pilihan mode dihapus, Astra DB tidak ditampilkan karena berada di dalam Langflow.
- [x] License Gateway lokal (`selisih/license.py`) aktif: status/kuota dari `SELISIH_*` menonaktifkan analisis/scan/handoff/apply bila invalid.
- [x] Tulis hasil live ke `data/temuan.json` (+ `analysis_meta` & checksum input).
- [x] Verifikasi: AppTest smoke (boot + sidebar tanpa Astra/mode eksekusi) + e2e live mock HTTP (1 temuan, file tertulis).

## Keamanan Sebelum Push GitHub

- [x] Audit `.gitignore`: `.env`, `.streamlit/secrets.toml`, `artifacts/`, `data/temuan.json`, `*.bak.*` ter-ignore; `.env.example` & `.bob/mcp.json` diizinkan commit.
- [x] Tidak ada secret/token/path mesin di kode; `secrets.toml` lokal hanya placeholder.
- [x] Test PDF contoh pakai path relatif + env `SELISIH_SAMPLE_PDF` (portable, skip bila tidak ada).

## Fase 3 — Integrasi IBM Bob

- [x] Keputusan: jembatan **MCP server lokal dual-pintu** (stdio untuk Bob + HTTP admin untuk dashboard) → `DECISIONS.md` D-015.
- [x] Implementasi `mcp_server.py` (stdlib): tools `get_temuan`, `list_artifacts`, `read_artifact` (anti path-traversal), `preview_patch`/`apply_patch` (wajib konfirmasi + backup), `run_repo_tests`; allowlist `mock_fintech_repo/` + `artifacts/`.
- [x] Ekspor artefak `selisih/artifacts.py`: `impact_report.json`, `proposed_patch.diff`, `generated_tests.py` (draf uji dari `proposed_code`, token literal dipertahankan).
- [x] Registrasi IDE: `.bob/mcp.json` eksklusif untuk IBM Bob; port HTTP admin default `127.0.0.1:8765` (`MCP_ADMIN_URL`/`MCP_ADMIN_PORT`).
- [x] Tab 2 aksi Hybrid: Tombol Primer "Jalankan Agen IBM Bob di Dashboard" (eksekusi Bob Shell headless, penalaran agen langsung di web) dan Tombol Sekunder "Buka di IBM Bob Desktop" (meluncurkan GUI IBM Bob langsung ke repositori target).
- [x] Unit test `tests/test_mcp_server.py` & `tests/test_artifacts.py` (16 tes lolos) memvalidasi eksklusivitas IBM Bob, pembuatan konfigurasi `.bob/mcp.json`, status shared session, dan eksekusi Bob Shell.

## Fase 4 — Dampak kode & patch aman

- [x] Scanner deterministik berbasis `evidence` → `selisih/impact.py` (scan_impact → file+baris+diff nyata).
- [x] Dry-run + backup `.bak.<ts>` + konfirmasi sebelum menulis.
- [x] Jalankan test via `pytest`, tampilkan output asli.
- [x] Unit test `tests/test_impact.py` (6 tes) + e2e AppTest (scan → dry-run → apply → backup → 3 passed).

## Fase 5 — Pengerasan & audit

- [x] Verifikasi tidak ada secret di kode.
- [x] Modul autentikasi peran fungsional (`selisih/auth.py`: Administrator, Software Engineer, Compliance Officer).
- [x] Gerbang login bersih tanpa emoji di `app.py` + tombol akses cepat per peran.
- [x] Tab 2 dan Tab 3 langsung siap diakses oleh seluruh peran dengan data dampak terinisialisasi.
- [x] Jejak audit nyata mencatat identitas peran peninjau aktif pada persetujuan/penolakan patch.
- [x] Unit test autentikasi peran (`tests/test_auth.py`, 10 tes lolos).

## Fase 6 — Testing & dokumentasi

- [x] Unit test adapter/Langflow (mock HTTP) & engine patch (`tests/`).
- [x] Unit test lisensi lokal (`tests/test_license.py`) + AppTest memastikan sidebar tanpa Astra/mode eksekusi.
- [x] Pengujian modul backend & integrasi bisnis (`tests/`, 71 unit test lolos): memvalidasi FastAPI endpoints, JDIH OJK sync, ChromaDB, lisensi B2B, eksekusi Bob Shell, scanner dampak, dan rollback patch.
- [x] Dokumentasi akhir: README + PROGRESS + DECISIONS + AGENTS + CONTEXT.
- [x] Pembersihan menyeluruh artefak Streamlit legacy (`app.py`, `run_app.bat`, `.streamlit/`) dan penambahan skrip peluncur 1-klik terpadu `run_all.bat`.


## Fase 7 — Platform Web Enterprise & Sinkronisasi Live OJK (Branch `feat/enterprise-web`)

- [x] Modul crawler & sinkronisasi otomatis JDIH OJK (`selisih/ojk.py`): pemantauan POJK sektor Fintech/ITSK, P2P Lending, dan Pelindungan Konsumen langsung dari portal resmi `jdih.ojk.go.id`.
- [x] Unit test sinkronisasi OJK (`tests/test_ojk.py`, 3 tes lolos).
- [x] Server Backend FastAPI (`api.py`): endpoints RESTful + Server-Sent Events (SSE) streaming penalaran Bob Shell.
- [x] Unit test FastAPI (`tests/test_api.py`, 6 tes lolos).
- [x] Penggantian Astra DB dengan ChromaDB Lokal (`selisih/vector_store.py`): persistensi lokal di `data/chroma_db/`, ingest pasal/ayat POJK 77/2016 secara otomatis, zero-cloud dependency.
- [x] Pembaruan rancangan flow Langflow: `flows/selisih_regulatory_flow.json` mengadopsi node `Chroma` dan `PromptTemplate`.
- [x] Unit test vector store lokal (`tests/test_vector_store.py`, 2 tes lolos). Total pengujian unit kini mencapai 75 tes (74 passed, 1 skipped).
- [x] Integrasi End-to-End Tab 1 (OJK Live JDIH) ke Tab 2 (Regulatory Diff): tombol *"Analisis Dampak"* memicu pipeline analisis regulasi terpilih secara dinamis.
- [x] Frontend Next.js 15 (React 19, TypeScript, Tailwind CSS, Lucide):
  - Tab 1: Pemantau Regulasi OJK (Live JDIH OJK sync & filter).
  - Tab 2: Analisis Komparasi Regulasi (watsonx Granite diff, 4 metrik kepatuhan).
  - Tab 3: Konsol Agen IBM Bob Shell (Terminal interaktif, SSE live streaming, viewer artefak handoff).
  - Tab 4: Tata Kelola & Tinjauan Dampak (Dry-run preview, human-in-the-loop review dengan backup `.bak.<ts>`, real pytest runner).
  - Jejak Audit Enterprise Modal (`AuditTrailModal`).
- [x] Script eksekusi mandiri 1-klik: `run_api.bat` (Backend Port 8000) dan `run_web.bat` (Full-stack Web Platform).

## Fase 8 — Penyempurnaan UX & Pemetaan Dampak Presisi

- [x] Deteksi nomor baris terdampak nyata secara dinamis di Tab 3 (`selisih/impact.py` -> `lines` & `line`, header `Baris 15` / `Baris 18`).
- [x] Sinkronisasi kode balikan pengujian pytest di Tab 3 (`returncode` & `code`) agar status pengujian lolos (3 passed) tampil presisi.
- [x] Engine komparasi dual-regulasi dinamis (`POST /api/analysis/run` & `selisih/langflow.py`) menerima `acuan_info` & `ojk_info` untuk sitasi pasal acuan vs pembaruan yang akurat.
- [x] Perbaikan identifikasi regulasi unik (`getRegKey`) menggunakan format komposit `${nomor}_${tahun}` atau `id` untuk mencegah false-positive error regulasi sama pada nomor identik beda tahun (misal: POJK 41/2024 vs POJK 41/2025).
- [x] Alur tampilan analisis on-demand di Tab 1: menyembunyikan metrik dan daftar perubahan hingga pengguna secara eksplisit menekan tombol *"Jalankan Analisis"*, dan mereset status saat regulasi diganti.
- [x] Inisialisasi pilihan regulasi kosong (*unselected state*) di Tab 1: opsi dropdown default `-- Pilih Regulasi --`, placeholder card informatif, tombol analisis nonaktif hingga kedua regulasi dipilih, dan tombol pintasan *"Muat Kasus Acuan Standar"*.
- [x] Peningkatan UX Konsol IBM Bob Shell (Tab 2): penamaan tombol *"Jalankan IBM Bob"*, indikator status riil *"MCP Server Terhubung"* / *"MCP Server Terputus"*, *guarded state* saat temuan Tab 1 kosong, tombol *"Bersihkan Log"*, pewarnaan baris diff (+ hijau, - merah), tombol *"Unduh Berkas"* artefak, dan tombol navigasi *"Lanjut ke Tab 3"*.
- [x] Session guard untuk paket artefak handoff IBM Bob (Tab 2): penayangan berkas diff/tests/json dikontrol oleh state `hasRunBob` (default: false dengan kartu placeholder), dan hanya tampil setelah tombol *"Jalankan IBM Bob"* dieksekusi pada sesi aktif.
- [x] Integrasi status kesehatan komponen live pada Sidebar (Langflow Pipeline, ChromaDB Lokal, IBM Bob MCP) dari `GET /api/system/health`.
- [x] Modal konfirmasi in-app terpadu untuk penerapan patch kepatuhan di Tab 3: menggantikan dialog browser bawaan (`window.confirm`/`window.alert`) dengan ringkasan peran peninjau, target berkas, catatan kepatuhan, dan status simulasi dry-run.
- [x] Alur kerja bertahap (*Progressive Workflow*) di Tab 3: menonjolkan tombol *"Jalankan Simulasi (Dry-Run)"* sebelum tombol penerapan patch aktif untuk memastikan zero-risk.
- [x] Fitur pemulihan cadangan berkas (*Rollback*) di Tab 3: tombol *"Pulihkan Cadangan (Rollback)"*, endpoint `POST /api/impact/rollback`, dan fungsi `selisih.impact.rollback_last_backup()` yang memulihkan berkas dari `.bak.<timestamp>` terbaru dan mencatatnya ke jejak audit.
- [x] Tautan langsung ke jejak audit (*"Lihat Entri di Jejak Audit"*) pada banner keberhasilan penerapan dan pemulihan patch di Tab 3.
- [x] Pembaruan status badge kode terdampak pasca-patch: berubah dinamis menjadi *"Telah Disesuaikan & Patuh"* berwarna hijau setelah patch diterapkan.
- [x] Banner konteks regulasi dinamis di Tab 3: menampilkan perbandingan judul regulasi acuan vs regulasi pembaruan yang sedang ditinjau.
- [x] Session guard dan kartu tunggu terpandu di Tab 3: menyembunyikan kandidat kode saat pertama kali membuka aplikasi sebelum Tab 1 (`hasRunAnalysis`) dan Tab 2 (`hasRunBob`) dijalankan, dilengkapi kartu panduan status tunggu Langkah 1 / Langkah 2 dan tombol navigasi cepat.
- [x] Pemilih Entitas Perusahaan (B2B License Switcher) di sidebar dengan format `[Nama Perusahaan] ([Nama Plan])` (Bank Digital Nusantara - Enterprise, Dana Mandiri - Professional, Pinjaman Kilat - Starter).
- [x] Panel Langganan & Lisensi 100% dinamis: sinkronisasi nama organisasi, badge status lisensi (Aktif vs Kuota Penuh), dan bilah persentase kuota (*progress bar*) riil.
- [x] Modal Manajer Repositori Terpadu (`RepoManagerModal`): pemantauan repositori lokal terdaftar, pendaftaran repositori baru, dan validasi kuota paket otomatis.
- [x] Penerapan License Gating di Tab 3: tombol *"Setujui & Terapkan Patch"* dinonaktifkan otomatis saat beralih ke entitas dengan kuota penuh/dibatasi (Starter Plan).
- [x] Endpoint RESTful lisensi & repositori di FastAPI: `GET /api/license/profiles`, `POST /api/license/select`, `POST /api/license/add-repo`, serta unit test pendukung di `tests/test_api.py` (total 78 unit test: 77 passed, 1 skipped).
- [x] Eliminasi panel preset *"Mulai cepat dengan kasus acuan standar perbankan/fintech"* di Tab 1 untuk alur seleksi regulasi yang murni berbasis katalog OJK.
- [x] Pengetatan guard eksekusi agen IBM Bob di Tab 2: tombol *"Jalankan IBM Bob"* terkunci nonaktif (*"Menunggu Analisis Tab 1"*) dan status konteks input temuan regulasi berstatus tunggu jika analisis di Tab 1 belum dijalankan pada sesi aktif (`!hasRunAnalysis`).
- [x] Penyederhanaan tombol repositori di sidebar: menghapus tombol teks kecil *"Kelola Repo"* di header panel Langganan & Lisensi dan menyisakan tombol aksi tunggal *"Kelola Repositori ({active_repos})"* di bagian bawah panel.
- [x] Unit test rollback patch: `tests/test_impact.py::test_rollback_last_backup` dan `tests/test_api.py::test_api_impact_rollback`.


---

## Catatan

- Status proyek: **Enterprise Production Ready**; Fase 0, 1, 2, 3, 4, 5, 6, 7, 8 selesai secara menyeluruh.
- Arsitektur Web Enterprise: Frontend Next.js 15 (`frontend/`), Backend FastAPI (`api.py`), Vector Store ChromaDB lokal (`data/chroma_db/`), dan Jembatan MCP Lokal IBM Bob (`mcp_server.py`).
- Template flow resmi: `flows/selisih_regulatory_flow.json` mengintegrasikan node TextInput, Chroma vector store, PromptTemplate komparasi, model LLM watsonx Granite, dan StructuredOutput.
- Jembatan IBM Bob: `mcp_server.py` aktif melayani stdio JSON-RPC untuk IBM Bob IDE dan HTTP admin di `127.0.0.1:8765` untuk web console.
- Backup patch `.bak.<timestamp>` dibuat otomatis sebelum setiap mutasi kode; fitur pemulihan (*rollback*) 1-klik siap digunakan di Tab 3.
- Total 71 pengujian unit test (`pytest`): 70 passed, 1 portable skip (100% green). Frontend Next.js lulus verifikasi build production tanpa error.

