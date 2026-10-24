# AGENTS.md — SELISIH / RCIA

Panduan untuk AI coding agent yang bekerja di repo ini. **Baca ini dulu sebelum mengubah apa pun.**

## Ringkasan Proyek

**SELISIH** (Regulatory Change & Code Impact System) adalah dashboard Streamlit untuk
hackathon **IBM x Hacktiv8 (IT-Finance)**. Tujuan: menjembatani **dokumen regulasi OJK**
dengan **repositori kode fintech**, lalu memetakan dampak perubahannya secara
human-in-the-loop.

Alur inti:
1. **Ingest & vector DB (Astra DB, di dalam Langflow)** — pasal regulasi lama disimpan.
2. **Regulatory Diff (Langflow)** — bandingkan aturan lama vs baru, validasi sitasi, hasilkan `temuan.json`.
3. **Code Impact (IBM Bob, lokal)** — petakan kewajiban hukum ke baris kode + draf patch & unit test.
4. **Human Review** — developer/compliance meninjau, terima/tolak. **Tidak ada auto-deploy.**

## Status Saat Ini (PENTING)

- **Fase 0 (fondasi) SELESAI** — kontrak data (`data/temuan_schema.json`), loader konfigurasi
  (`selisih/config.py`), loader dokumen TXT/PDF (`selisih/documents.py`), klien+normalizer Langflow
  (`selisih/langflow.py`), unit test adapter/dokumen.
- **Fase 2 (app → Langflow REST) SELESAI** — Tab 1 memanggil `run_analysis()` nyata,
  health check sidebar jujur, UI Live-only (tanpa mode demo di sidebar), hasil live → `data/temuan.json`,
  License Gateway lokal (`selisih/license.py`) menonaktifkan aksi bila lisensi/kuota invalid.
- **Fase 3 (jembatan IBM Bob — MCP lokal & Bob Shell) SELESAI** — `mcp_server.py` stdlib dual-pintu
  (stdio JSON-RPC untuk Bob + HTTP admin `127.0.0.1:8765` untuk dashboard), ekspor artefak
  `selisih/artifacts.py` (`impact_report.json`, `proposed_patch.diff`, `generated_tests.py`),
  Tombol Tab 2 Hybrid (eksekusi Bob Shell di dashboard + peluncuran IBM Bob Desktop), registrasi `.bob/mcp.json` eksklusif.
- **Fase 4 (dampak kode & patch aman) SELESAI** — scanner deterministik `selisih/impact.py`
  (evidence -> file+baris+diff), dry-run + backup `.bak.<ts>` + konfirmasi sebelum menulis,
  test via pytest output asli.
- **Fase 7 (platform web enterprise & sinkronisasi live OJK) SELESAI** — server FastAPI (`api.py`),
  frontend Next.js 15 (`frontend/`), pemantau JDIH OJK (`selisih/ojk.py`), dan vector store lokal ChromaDB (`selisih/vector_store.py`).
- **Fase 8 (UX presisi & lisensi B2B) SELESAI** — pemetaan baris dinamis, pemulihan rollback `.bak.<ts>`,
  alur bertahap progressive review, B2B Multi-Company Licensing (Enterprise, Professional, Starter) dengan repo quota gating,
  dan pengaman sesi antar-tab terpadu.
- `flows/` **selisih_regulatory_flow.json** telah terintegrasi — mendukung eksekusi Embedded Langflow Engine mandiri maupun REST API.
- Baca `PROGRESS.md` untuk status per fase dan `docs/CONTEXT.md` untuk konteks penuh.

## Struktur Repo

```
rcia-app/
├── api.py                     # Server backend FastAPI (REST & SSE streaming Bob Shell)
├── frontend/                  # Dashboard Next.js 15 (React 19, TypeScript, Tailwind CSS)
│   ├── src/app/               # App Router Next.js (page.tsx, layout.tsx, globals.css)
│   ├── src/components/        # Komponen Tab 1-4, Sidebar, Header, Modal Dialog
│   └── src/lib/               # Klien API typed & utilitas frontend
├── app.py                     # Dashboard Streamlit monolitik (legacy baseline)
├── mcp_server.py              # Jembatan MCP lokal ke Bob: stdio JSON-RPC + HTTP admin 127.0.0.1:8765
├── selisih/                   # Paket inti Python
│   ├── config.py              # Loader konfigurasi (st.secrets -> env -> .env)
│   ├── documents.py           # Loader regulasi TXT/PDF + cleanup + split_by_pasal
│   ├── langflow.py            # Klien + normalizer respons Langflow (Embedded & REST)
│   ├── license.py             # License Gateway & B2B Profile Manager (status/kuota)
│   ├── impact.py              # Scanner dampak, engine patch aman, & rollback backup
│   ├── artifacts.py           # Ekspor artefak Bob & runner Bob Shell
│   ├── ojk.py                 # Sinkronisasi & pemantau regulasi portal resmi JDIH OJK
│   └── vector_store.py        # Vector store lokal ChromaDB untuk klausul acuan offline
├── tests/
│   ├── test_api.py               # Unit test RESTful FastAPI
│   ├── test_ojk.py               # Unit test crawler/sinkronisasi JDIH OJK
│   ├── test_vector_store.py      # Unit test ChromaDB lokal
│   ├── test_langflow_adapter.py  # Unit test adapter Langflow (mock HTTP & embedded)
│   ├── test_documents.py         # Unit test loader TXT/PDF + split pasal
│   ├── test_license.py           # Unit test license gateway lokal
│   ├── test_impact.py            # Unit test scanner dampak, patch, & rollback
│   ├── test_artifacts.py         # Unit test ekspor artefak Bob & runner Bob Shell
│   ├── test_mcp_server.py        # Unit test protokol JSON-RPC MCP lokal
│   └── test_app_integration.py   # Pengujian integrasi antarmuka Streamlit
├── data/
│   ├── pojk_lama_77_2016.txt  # Teks regulasi acuan (publik)
│   ├── pojk_baru_22_2023.txt  # Teks regulasi pembaruan (publik)
│   ├── temuan_golden_path.json# Kontrak data contoh (skema temuan)
│   └── temuan_schema.json     # JSON Schema resmi kontrak temuan
├── mock_fintech_repo/         # Repo fintech dummy (target patch)
│   ├── app/core/config.py     # Konstanta batas (MAX_LOAN_AMOUNT, dll)
│   ├── app/services/loan_service.py
│   └── tests/test_compliance.py
├── artifacts/                 # Artefak handoff Bob (RUNTIME, di-gitignore)
├── .bob/mcp.json              # Registrasi MCP server untuk IBM Bob
├── flows/                     # Ekspor flow Langflow (selisih_regulatory_flow.json)
├── docs/CONTEXT.md            # Konteks & rencana lengkap
├── PROGRESS.md                # Checklist fase
├── DECISIONS.md               # Log keputusan arsitektur
├── .env.example               # Templat konfigurasi (salini sebagai .env)
├── requirements.txt
├── run_api.bat                # Script peluncur FastAPI backend port 8000
├── run_web.bat                # Script peluncur Web Enterprise port 3000
├── run_app.bat                # Script peluncur Streamlit baseline port 8501
└── .streamlit/config.toml     # Tema Streamlit (secrets.toml TIDAK di-commit)
```

## Cara Menjalankan

### Platform Web Enterprise (Utama)
```bash
# Terminal 1: Backend FastAPI
run_api.bat
# atau: python -m uvicorn api:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend Web
run_web.bat
# atau: cd frontend && npm run start
```
Buka peramban di `http://localhost:3000`.

### Dashboard Streamlit (Legacy Baseline)
```bash
pip install -r requirements.txt
streamlit run app.py
```

Jalankan unit test repo mock:
```bash
python -m pytest mock_fintech_repo/tests
# atau: python mock_fintech_repo/tests/test_compliance.py
```

Jalankan seluruh unit test (termasuk `selisih/`):
```bash
python -m pytest
```

## Arsitektur & Batas Kepercayaan (JANGAN DILANGGAR)

Dua domain terpisah:
- **Domain publik (boleh cloud):** teks POJK + Astra DB + Langflow. **Tidak ada kode perusahaan.**
- **Domain privat (WAJIB lokal):** source code + IBM Bob + patch + test. **Kode tidak pernah dikirim ke Langflow/cloud.**

Satu-satunya artefak yang menyeberang adalah `temuan.json` (turunan regulasi publik, bukan kode).

Implikasi teknis:
- **Astra DB ada di dalam Langflow**, bukan dipanggil `app.py`. App tidak perlu kredensial Astra.
- **IBM Bob adalah MCP *client*** (IDE lokal), **bukan service yang bisa dipanggil REST**. Arah integrasi:
  dashboard/Langflow menyiapkan `temuan.json`, lalu Bob menariknya **via MCP server** atau membaca file lokal.

## Keputusan Kunci

Lihat `DECISIONS.md`. Yang paling penting:
- Output Langflow harus **JSON terstruktur** (bukan chat text).
- LLM target **watsonx/Granite** (bukan Gemini).
- Bob diintegrasikan lewat **MCP**, bukan REST.
- Semua konfigurasi rahasia lewat `.env` / `.streamlit/secrets.toml`, **tidak ada secret di kode**.

## Konvensi

- Bahasa komentar/dokumentasi: Indonesia (ikut kode yang ada).
- **JANGAN** commit secret/token/ID infrastruktur. Repo ini **PUBLIK**.
- `.gitignore` sudah menangani `__pycache__`, `.env`, `.streamlit/secrets.toml`, dll.
- **JANGAN** tambahkan komentar ke kode kecuali diminta.
- Setelah menyelesaikan tugas: jalankan test, update `PROGRESS.md`.

## Gotcha yang Sering Bikin Salah

- File kontrak bernama `temuan_golden_path.json`; hasil live ditulis ke `data/temuan.json` (keduanya mengikuti `data/temuan_schema.json`).
- Sidebar app menyebut collection `pojk_idx`, flow lama memakai `Regulasi_Lama` (perlu diselaraskan).
- **Akses `st.secrets` menimpa `os.environ` untuk semua kunci sekaligus** (bahkan nilai kosong). Di runtime streamlit, isi nilai nyata di `.streamlit/secrets.toml`; `.env`/env baru berguna di konteks non-streamlit (CLI/test).
- {→} `data/temuan.json` = artefak runtime hasil mode Live (dibuat saat berhasil); jangan salah kira sebagai kontrak statis.
- PDF POJK berbasis teks bisa dibaca via `selisih.documents.load_document_text()`; PDF scan/foto belum OCR. `split_by_pasal()` hanya menyiapkan calon chunk, belum otomatis ingest ke Astra/Langflow.
- Sidebar tidak menampilkan Astra DB dan tidak punya Mode Eksekusi. Tab 1 selalu Live Langflow; jika gagal tidak fallback sebagai hasil analisis. Demo/golden tetap ada untuk test/internal fallback scanner.
- License Gateway lokal membaca `SELISIH_*` dari env/secrets. Karena `st.secrets` dapat menimpa env, app memanggil `_langflow_health()` sebelum `get_license_state(st.secrets)`.
- Ekspor flow Langflow **memuat `org_id`/`database_id`/endpoint Astra DB** → redact sebelum commit (repo publik).
- `mcp_server.py`: dashboards memanggil `GET /health` & `POST /handoff` di `127.0.0.1:8765` (`MCP_ADMIN_URL` di app; `MCP_ADMIN_PORT` di server). Setelah stdin EOF server tetap hidup (keep-alive) demi HTTP admin; hentikan manual (Ctrl-C/SIGTERM).
- `.gitignore` mem-ignore runtime artefacts, folder `.vscode/`, `.env`, dan database/token rahasia. Registrasi MCP eksklusif di `.bob/mcp.json`.
- `tests/test_documents.py` mencari PDF contoh lewat env `SELISIH_SAMPLE_PDF` atau path relatif `../../NPL/SELISIH_demo_paket/RCIA/data/raw/`; test otomatis skip bila tidak ditemukan (portable lintas mesin).

