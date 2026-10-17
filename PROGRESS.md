# PROGRESS — SELISIH / RCIA

Checklist status pekerjaan. Update setelah tiap tugas selesai.
Legenda: `[ ]` belum, `[~]` sedang dikerjakan, `[x]` selesai.

Terakhir diperbarui: 2026-10-12

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
- [x] Pengujian integrasi antarmuka Streamlit (`tests/test_app_integration.py`, 4 tes lolos): memvalidasi gerbang login, navigasi tab, eksekusi Bob Shell di dashboard, dan peluncuran IBM Bob Desktop.
- [x] Dokumentasi akhir: README + PROGRESS + DECISIONS + AGENTS + CONTEXT.

---

## Catatan

- Status proyek: **demo menuju nyata**; Fase 0, 2, 3, 4, 5, 6 selesai. Fase 1 (flow Langflow + ingest Astra) menunggu dibangun di UI Langflow.
- Struktur baru: paket `selisih/` (config + documents + langflow client + impact scanner + artifacts), `mcp_server.py` (jembatan MCP lokal ke Bob), `tests/` (unit test), `.env.example`.
- `app.py` sudah memakai `selisih.langflow` (live REST + fallback demo jujur), `selisih.impact` (scan → dry-run → backup → apply), dan `selisih.artifacts` + HTTP admin MCP (handoff ke Bob).
- Para Bob: jalankan `python mcp_server.py`; dashboard memanggil `GET /health` & `POST /handoff` di `127.0.0.1:8765`.
- Backup patch `.bak.<ts>` dibuat otomatis; repo mock dikembalikan ke POJK 77/2016 sebagai baseline.
- `flows/` **kosong** (target Fase 1, menunggu dibangun di Langflow).
- Loader PDF sudah ada untuk PDF berbasis teks seperti `POJK_08_2023_APU_PPT_PPPSPM.pdf` / `POJK_12_2017_APU_PPT.pdf`, tetapi app masih memakai file default `data/pojk_baru_22_2023.txt` sampai konfigurasi/uploader dokumen ditambahkan.
