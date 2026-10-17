# DECISIONS — SELISIH / RCIA

Log keputusan arsitektur. Format: **D-XXX** — keputusan, alasan, konsekuensi.
Tambahkan entri baru di bawah; jangan hapus yang lama.

Terakhir diperbarui: 2026-10-12

---

## D-001 — Output Langflow harus JSON terstruktur
- **Keputusan:** Flow Langflow mengeluarkan JSON sesuai skema `temuan.json`, bukan chat text.
- **Alasan:** `app.py` dan IBM Bob butuh data terparse. Text bebas tidak stabil.
- **Konsekuensi:** Perlu node/format JSON di flow; skema (`data/temuan_golden_path.json`) jadi kontrak.

## D-002 — LLM target watsonx/Granite (bukan Gemini)
- **Keputusan:** Ganti provider LLM dari Google Gemini ke IBM watsonx (Granite).
- **Alasan:** Hackathon mensyaratkan teknologi IBM; flow lama memakai Gemini.
- **Konsekuensi:** Ganti node model + embedding di flow; sesuaikan API key.

## D-003 — IBM Bob diintegrasikan via MCP, bukan REST
- **Keputusan:** Bob mengonsumsi `temuan.json` lewat **MCP server lokal** atau pembacaan file.
- **Alasan:** Bob adalah **MCP client** (IDE lokal), bukan service REST yang bisa dipanggil dashboard.
- **Konsekuensi:** Arah integrasi terbalik: dashboard menyiapkan data, Bob menariknya.

## D-004 — Astra DB berada di dalam Langflow
- **Keputusan:** `app.py` tidak memanggil Astra DB langsung.
- **Alasan:** Vector store sudah jadi node di flow; kredensial cukup di server Langflow.
- **Konsekuensi:** App hanya perlu endpoint + `flow_id` + token Langflow.

## D-005 — Batas kepercayaan privasi (publik vs privat)
- **Keputusan:** Regulasi + Astra + Langflow = domain publik; source code + Bob + patch = domain lokal.
- **Alasan:** Privasi data perusahaan. Kode tidak boleh keluar.
- **Konsekuensi:** Hanya `temuan.json` yang menyeberang; dashboard dilarang mengirim kode ke Langflow.

## D-006 — Human-in-the-loop, tanpa auto-deploy
- **Keputusan:** AI hanya menghasilkan draf; penerapan patch wajib persetujuan manusia.
- **Alasan:** Standar enterprise + nilai "Responsible AI".
- **Konsekuensi:** Tab 3 jadi gerbang wajib; patch diberi pengaman dry-run/backup.

## D-007 — Repo PUBLIK: redact rahasia & ID infrastruktur
- **Keputusan:** Jangan commit token/`org_id`/`database_id`/endpoint Astra DB.
- **Alasan:** Repo publik.
- **Konsekuensi:** Ekspor flow wajib di-redact; secret lewat `.env`/`secrets.toml`.

## D-008 — `flows/` dikosongkan, akan dibangun ulang
- **Keputusan:** Hapus isi `flows/` lama; bangun flow yang sesuai dari awal.
- **Alasan:** Flow lama tidak cocok (Gemini, output tak terstruktur, memuat ID Astra).
- **Konsekuensi:** Fase 1 dikerjakan ulang di Langflow.

## D-009 — Kontrak data didahulukan sebelum integrasi
- **Keputusan:** Finalkan skema `temuan.json` dulu, baru sambungkan komponen.
- **Alasan:** Integrasi tanpa kontrak stabil akan rapuh.
- **Konsekuensi:** Fase 0 dikerjakan sebelum Fase 2/3.

## D-010 — Konteks antar-session disimpan di file repo
- **Keputusan:** Gunakan `AGENTS.md`, `docs/CONTEXT.md`, `PROGRESS.md`, `DECISIONS.md`.
- **Alasan:** Session opencode tidak menyimpan memori; `AGENTS.md` otomatis dibaca tiap session.
- **Konsekuensi:** Update file-file ini setiap akhir tugas.

## D-011 — Konfigurasi rahasia lewat env / secrets loader
- **Keputusan:** Buat `selisih/config.py`; nilai dibaca dari `st.secrets` → env → `.env` (python-dotenv). Tidak ada secret di kode.
- **Alasan:** URL/`flow_id`/token Langflow tidak boleh hardcoded (repo publik).
- **Konsekuensi:** Sediakan `.env.example`; `.env` dan `.streamlit/secrets.toml` di-gitignore.

## D-012 — Normalizer Langflow toleran (scan, bukan parse kaku)
- **Keputusan:** `normalize_response()` mencari findings di mana pun di tree respons Langflow, termasuk JSON yang terkubur dalam string text hasil LLM.
- **Alasan:** Bentuk respons Langflow bervariasi per versi; flow belum final.
- **Konsekuensi:** Respons tak dikenal → `LangflowError` (jujur, bukan diam-diam kosong).

## D-013 — Env disnapshot sebelum sentuh `st.secrets`
- **Keputusan:** `get_langflow_config()` memfoto nilai env semua kunci lebih dulu, baru membaca `st.secrets`.
- **Alasan:** Akses `st.secrets` (saat ada `secrets.toml`) menimpa `os.environ` untuk semua kunci sekaligus — bahkan dengan nilai kosong — sehingga env yang set lebih awal bisa "menghilang". Snapshot dulu membuat env tetap terbaca.
- **Konsekuensi:** Saat runtime streamlit, nilai nyata disarankan ditaruh di `.streamlit/secrets.toml` (env mungkin ditimpa). Env/`.env` tetap berfungsi di konteks non-streamlit (mis. CLI/test).

## D-014 — Patch aman: dry-run + backup sebelum tulis
- **Keputusan:** Semua perubahan ke repo melewati `selisih/impact.py`: scanner berbasis `kandidat_kode[].evidence`, pratinjau `dry-run`, konfirmasi peninjau, lalu tulis dengan backup `<file>.bak.<stamp>`.
- **Alasan:** Baseline deterministik sebelum IBM Bob, dan mencegah penimpaan tanpa jejak.
- **Konsekuensi:** `data/temuan.json` & `*.bak.*` masuk `.gitignore`; repo mock dijaga tetap baseline POJK 77/2016.

## D-015 — Jembatan privat Bob: MCP server lokal dual-pintu
- **Keputusan:** Satu proses `mcp_server.py` (stdlib, tanpa dependency) dengan dua pintu:
  - **stdio (JSON-RPC 2.0 MCP)** untuk IBM Bob, didaftarkan via `.bob/mcp.json` / `.vscode/mcp.json`; tools: `get_temuan`, `list_artifacts`, `read_artifact` (antipath-traversal), `preview_patch`/`apply_patch` (wajib `confirm` + backup), `run_repo_tests`.
  - **HTTP admin** (interfaces `127.0.0.1`, default port `8765`, env `MCP_ADMIN_PORT`) untuk dashboard: `GET /health`, `POST /handoff` (bangun ulang `artifacts/` dari sumber `live`|`golden`).
- **Alasan:** Bob adalah **MCP client**, bukan REST service — jadi integrasi "langsung tapi privat" butuh jembatan lokal; kode tetap tidak pernah keluar mesin.
- **Konsekuensi:** Aplikasi hanya boleh membangun artefak dari `temuan.json` (domain publik). Akses server di-allowlist ke `mock_fintech_repo/` + `artifacts/`; semua tulis via engine dry-run/backup. `artifacts/` masuk `.gitignore` (runtime).

## D-016 — Artefak ekspor & uji generatif yang bisa dijalankan
- **Keputusan:** `selisih/artifacts.py` mengekspor `impact_report.json`, `proposed_patch.diff`, dan `generated_tests.py`; uji dibuat via AST dari `proposed_code`, token literal dipertahankan (mis. `50_000_000`, bukan `50000000`), path repo dibuat relatif agar portabel.
- **Alasan:** Bob butuh paket yang dibuka-reviu, bukan sekadar teks; nilai angka regresi harus readable & pengujiannya lulus terhadap repo yang sudah dipatch.
- **Konsekuensi:** File sementara di `tests/` memakai encode `utf-8` + `sys.executable`; `mcp_server.py` mulai dengan keep-alive setelah stdin EOF agar HTTP admin tetap hidup saat dipakai headless/terputus.

## D-017 — Loader dokumen lokal mendukung TXT/PDF sebelum ingest Langflow
- **Keputusan:** Tambahkan `selisih/documents.py` untuk membaca `.txt` dan PDF berbasis teks (`pypdf`), cleanup noise dasar POJK, infer `doc_id`, dan `split_by_pasal()` untuk chunk calon ingest. App memakai loader ini lewat `_load_text()`, tetapi ingest Astra/Langflow belum diintegrasikan.
- **Alasan:** File regulasi asli sering berupa PDF POJK; pipeline SELISIH tetap berbasis teks, jadi ekstraksi lokal diperlukan sebelum Fase 1 flow/injest. Ini menjaga perubahan minimal dan tidak mengubah batas kepercayaan.
- **Konsekuensi:** Tambah dependency `pypdf`; PDF scan/foto belum didukung (butuh OCR). Test `tests/test_documents.py` memvalidasi TXT, cleanup, splitter pasal, dan PDF contoh bila tersedia.

## D-018 — Sidebar Live-only dan License Gateway lokal
- **Keputusan:** Hilangkan indikator Astra DB dari sidebar (Astra tetap berada di dalam Langflow), hilangkan pilihan Mode Eksekusi, dan jadikan Tab 1 **Live Langflow REST API only**. Tambahkan `selisih/license.py` untuk membaca `SELISIH_*` dari env/secrets dan menonaktifkan aksi analisis/scan/handoff/apply bila lisensi tidak aktif atau kuota repo terlampaui.
- **Alasan:** Sidebar sebelumnya masih dekoratif (mode demo/live dan lisensi statis). Untuk demo enterprise, status yang terlihat harus memengaruhi perilaku aplikasi.
- **Konsekuensi:** Tidak ada fallback demo otomatis saat Langflow gagal; error ditampilkan jujur. `temuan_golden_path.json` tetap ada untuk unit test/internal fallback Tab 2, tetapi bukan mode UI. `get_langflow_config()` dipanggil sebelum akses secrets lisensi agar env Langflow tetap aman dari gotcha `st.secrets`.
