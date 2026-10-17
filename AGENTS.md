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
- **Fase 3 (jembatan IBM Bob — MCP lokal) SELESAI** — `mcp_server.py` stdlib dual-pintu
  (stdio JSON-RPC untuk Bob + HTTP admin `127.0.0.1:8765` untuk dashboard), ekspor artefak
  `selisih/artifacts.py` (`impact_report.json`, `proposed_patch.diff`, `generated_tests.py`),
  Tombol Tab 2 "Siapkan & Kirim Analisis ke Bob", registrasi `.bob/mcp.json` & `.vscode/mcp.json`.
- **Fase 4 (dampak kode & patch aman) SELESAI** — scanner deterministik `selisih/impact.py`
  (evidence → file+baris+diff), dry-run + backup `.bak.<ts>` + konfirmasi sebelum menulis,
  test via pytest output asli.
- `flows/` **masih kosong** — Fase 1 (flow Langflow) belum dibangun; menunggu dikerjakan di aplikasi Langflow.
- Baca `PROGRESS.md` untuk status per fase dan `docs/CONTEXT.md` untuk konteks penuh.

## Struktur Repo

```
rcia-app/
├── app.py                     # Seluruh UI Streamlit + CSS (monolitik)
├── mcp_server.py              # Jembatan MCP lokal ke Bob: stdio JSON-RPC + HTTP admin 127.0.0.1:8765
├── selisih/                   # Paket inti (Fase 0 + 3 + 4)
│   ├── config.py              # Loader konfigurasi (st.secrets → env → .env)
│   ├── documents.py           # Loader regulasi TXT/PDF + cleanup + split_by_pasal (tanpa ingest Astra)
│   ├── langflow.py            # Klien + normalizer respons Langflow
│   ├── license.py             # License Gateway lokal (status/kuota → gating aksi UI)
│   ├── impact.py              # Scanner dampak & engine patch aman (dry-run + backup)
│   └── artifacts.py           # Ekspor artefak Bob (impact_report.json, .diff, generated_tests.py)
├── tests/
│   ├── test_langflow_adapter.py  # Unit test Fase 0 (mock HTTP)
│   ├── test_documents.py         # Unit test Fase 0 (loader TXT/PDF + split pasal)
│   ├── test_license.py           # Unit test Fase 2 (license gate lokal)
│   ├── test_impact.py            # Unit test Fase 4 (scanner + patch)
│   ├── test_artifacts.py         # Unit test Fase 3 (ekspor artefak + uji generatif)
│   └── test_mcp_server.py        # Unit test Fase 3 (protokol JSON-RPC MCP lokal)
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
├── .vscode/mcp.json           # Registrasi MCP server untuk VS Code
├── flows/                     # Ekspor flow Langflow (SAAT INI KOSONG)
├── docs/CONTEXT.md            # Konteks & rencana lengkap
├── PROGRESS.md                # Checklist fase
├── DECISIONS.md               # Log keputusan arsitektur
├── .env.example               # Templat konfigurasi (salini sebagai .env)
├── requirements.txt
├── run_app.bat
└── .streamlit/config.toml     # Tema (secrets.toml TIDAK di-commit)
```

## Cara Menjalankan

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
- `artifacts/` = runtime (di-gitignore), dibuat oleh tombol Tab 2 atau `POST /handoff`.
- `.gitignore` mem-ignore seluruh `.vscode/` **kecuali** `.vscode/mcp.json` (pola `.vscode/*` + `!.vscode/mcp.json`) — registrasi MCP boleh ikut commit.
- `tests/test_documents.py` mencari PDF contoh lewat env `SELISIH_SAMPLE_PDF` atau path relatif `../../NPL/SELISIH_demo_paket/RCIA/data/raw/`; test otomatis skip bila tidak ditemukan (portable lintas mesin).
