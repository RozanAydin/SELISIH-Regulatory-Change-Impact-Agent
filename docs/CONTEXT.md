# CONTEXT — SELISIH / RCIA

Dokumen konteks lengkap + rencana perbaikan. Tujuan file ini: **session baru bisa langsung
nyambung tanpa perlu dijelaskan ulang.**

Terakhir diperbarui: 2026-10-30

---

## 1. Masalah & Solusi

**Masalah:** Saat regulator (OJK) merilis aturan baru, tim Legal butuh berminggu-minggu membaca
PDF, dan tim Engineer bingung baris kode mana yang harus diubah. Proses manual 3–4 minggu,
rawan denda.

**Solusi (RCIA/SELISIH):** Agen AI yang menjembatani dokumen hukum OJK dengan repositori kode:
1. Ingest regulasi lama ke vector DB (Astra DB, di dalam Langflow).
2. Langflow membandingkan aturan lama vs baru → `temuan.json` (tervalidasi, anti-halusinasi).
3. IBM Bob (lokal) membaca `temuan.json` → menemukan kode terdampak → draf patch + unit test.
4. Human review (accept/reject). **Tidak ada auto-deploy.**

## 2. Golden Path Demo

- **Regulasi acuan:** POJK 77/POJK.01/2016 Pasal 8 (plafon Rp 20 jt, bunga 0,4%/hari).
- **Regulasi baru:** POJK 22/2023 Pasal 12 (plafon Rp 50 jt, bunga 0,1%/hari, tenggat 30 hari).
- **Kode terdampak:** `mock_fintech_repo/app/core/config.py` → `MAX_LOAN_AMOUNT`, `MAX_DAILY_INTEREST_RATE`.
- **Verifikasi:** `mock_fintech_repo/tests/test_compliance.py`.

## 3. Kontrak Data (`temuan.json`)

Skema acuan ada di `data/temuan_golden_path.json`. Bentuk penting:

```
{
  "analysis_meta": { "engine", "model", "timestamp", "provenance_checksum" },
  "findings": [
    {
      "change_id": "CHG-POJK-001",
      "jenis_perubahan": "diubah",
      "pasal_baru": { "doc_id", "pasal", "ayat", "kutipan" },
      "pasal_lama": { "doc_id", "pasal", "ayat", "kutipan" },
      "ringkasan": "...",
      "sitasi_valid": true,
      "confidence": "tinggi",
      "abstain": false,
      "alasan_abstain": null,
      "kandidat_kode": [
        { "path", "lokasi", "evidence", "alasan", "confidence",
          "patch_status", "test_status", "old_code", "proposed_code" }
      ]
    }
  ]
}
```

**Aturan:** Langflow menulis temuan; app menormalkan (via `selisih/langflow.py`); Bob mengonsumsi.
Jangan ubah skema tanpa memperbarui ketiganya. Schema resmi: `data/temuan_schema.json`.

## 4. Arsitektur & Batas Kepercayaan

```
[Publik/cloud]                 [Batas]                 [Privat/lokal]
POJK + ChromaDB        ──temuan.json──▶  FastAPI / Next.js  ──temuan.json──▶ IBM Bob + source code
+ Langflow/Granite                        │                                   + patch + unit test
                                          ▼
                                    Human Review (no auto-deploy)
```

- ChromaDB dan model fondasi berada di domain publik/pipeline Langflow; kode sumber tidak pernah dikirim ke luar.
- **IBM Bob = MCP client**, tidak bisa dipanggil via REST. Jembatan nyata: **MCP server lokal** `mcp_server.py` (stdio ke Bob + HTTP admin `127.0.0.1:8765` ke dashboard).

## 5. Rencana Perbaikan (8 Fase)

Dari demo -> arsitektur Web Enterprise produksi.

### Fase 0 — Fondasi: kontrak data & konfigurasi — SELESAI
- JSON Schema `temuan.json` -> `data/temuan_schema.json`.
- Endpoint/`flow_id`/token Langflow -> `.env` (loader `selisih/config.py`).
- `.env.example`.
- Loader dokumen regulasi TXT/PDF -> `selisih/documents.py`:
  - `load_document_text()` membaca `.txt` dan PDF berbasis teks (`pypdf`).
  - `clean_pojk_text()` merapikan noise nomor halaman/whitespace.
  - `split_by_pasal()` menyiapkan chunk per pasal untuk calon ingest Astra.
- Adapter `normalize_response()` / `run_analysis()` di `selisih/langflow.py`.
- Unit test mock HTTP di `tests/test_langflow_adapter.py` dan loader dokumen di `tests/test_documents.py`.

### Fase 1 — Flow Langflow & Embedded Execution — SELESAI
- Output **JSON terstruktur** sesuai `data/temuan_schema.json`.
- Adopsi model fondasi **watsonx/Granite**.
- Template flow resmi: `flows/selisih_regulatory_flow.json` (TextInput -> ChromaDB -> PromptTemplate -> watsonx Granite LLM -> StructuredOutput).
- Eksekusi mandiri tanpa server (Embedded Flow Engine): `run_embedded_analysis()` di `selisih/langflow.py` menggunakan ChromaDB offline lokal di `data/chroma_db/`.

### Fase 2 — Sambungkan app ke Langflow sungguhan — SELESAI
- Ganti status tiruan dengan REST nyata `/api/v1/run/{flow_id}` atau Embedded Engine.
- Health check jujur (`GET /health`).
- UI Live-only: hasil analisis langsung disinkronkan ke `data/temuan.json` (+ `analysis_meta` & checksum SHA-256 input).
- License Gateway lokal `selisih/license.py`.

### Fase 3 — Integrasi IBM Bob — SELESAI (jembatan MCP lokal & Bob Shell)
- Arsitektur hybrid D-015 & D-022: **MCP server lokal dual-pintu** (`mcp_server.py`, stdlib) + **Bob Shell CLI Runner**.
  - stdio JSON-RPC untuk Bob (`.bob/mcp.json` eksklusif): `get_temuan`, `list_artifacts`, `read_artifact`, `preview_patch`/`apply_patch` (wajib konfirmasi + backup), `run_repo_tests`.
  - HTTP admin `127.0.0.1:8765` (`MCP_ADMIN_PORT`; dashboard pakai `MCP_ADMIN_URL`): `GET /health`, `POST /handoff`.
- Artefak nyata: `selisih/artifacts.py` -> `artifacts/impact_report.json`, `proposed_patch.diff`, `generated_tests.py` (draf uji dari `proposed_code`, literal dipertahankan).
- Tab 2: Tombol Hybrid **"Jalankan IBM Bob"** (eksekusi Bob Shell headless via SSE) dan **"Buka di IBM Bob Desktop"** (meluncurkan GUI) + kartu status IBM Bob V2.
- Allowlist akses: hanya `mock_fintech_repo/` + `artifacts/`; `artifacts/` di-gitignore.

### Fase 4 — Pemetaan dampak & patch aman — SELESAI
- Scanner deterministik `selisih/impact.py`: `kandidat_kode[].evidence` -> file+baris+diff nyata (baseline sebelum Bob).
- Patch: **dry-run + backup `.bak.<ts>` + konfirmasi** sebelum menulis (Tab 3).
- Test via `pytest`, output asli (Tab 3).
- Unit test `tests/test_impact.py` + e2e AppTest (scan -> dry-run -> apply -> backup -> 3 passed).

### Fase 5 — Pengerasan & jejak audit — SELESAI
- Verifikasi tidak ada secret di kode; redact flow saat ekspor.
- Modul autentikasi peran fungsional (`selisih/auth.py`): Administrator, Software Engineer, dan Compliance Officer tanpa emoji artifisial.
- Audit trail nyata (timestamp + hash file + nama & peran peninjau terautentikasi) via `AuditTrailModal`.

### Fase 6 — Testing & dokumentasi — SELESAI
- Unit test adapter/Langflow (mock HTTP), engine patch, lisensi, dokumen, dan MCP server.
- Dokumentasi teknis: README, PROGRESS, DECISIONS, AGENTS, CONTEXT.

### Fase 7 — Platform Web Enterprise & Sinkronisasi JDIH OJK — SELESAI
- Server FastAPI (`api.py`): RESTful endpoints + Server-Sent Events (SSE) streaming Bob Shell di port 8000.
- Frontend Next.js 15 modern (`frontend/`): React 19, TypeScript, Tailwind CSS, Lucide icons di port 3000.
- Modul crawler & sinkronisasi otomatis JDIH OJK (`selisih/ojk.py`): pemantauan regulasi resmi portal `jdih.ojk.go.id`.
- Vector store lokal ChromaDB (`selisih/vector_store.py`) tersimpan di `data/chroma_db/`.

### Fase 8 — UX Presisi & Manajemen Lisensi B2B — SELESAI
- Deteksi nomor baris nyata secara dinamis di Tab 3 (`selisih/impact.py` -> `lines` & `line`).
- Alur kerja bertahap bebas risiko (*Progressive Workflow*) di Tab 3: Dry-run -> Tinjauan Patch -> Konfirmasi Dialog In-App -> Pengujian Pytest.
- Fitur Pemulihan Cadangan (*Rollback*) 1-klik via `POST /api/impact/rollback` dan pemulihan dari salinan `.bak.<timestamp>`.
- Pemilih Entitas Perusahaan (B2B Multi-Company Licensing) di sidebar: Enterprise (Unlimited), Professional (25 repo), Starter (5/5 repo, lisensi penuh/gating).
- Modal Manajer Repositori Terpadu (`RepoManagerModal`) untuk pendaftaran repositori mikroservis lokal dengan verifikasi kuota paket.
- Guard siklus eksekusi antar-tab: Tab 2 dan Tab 3 terlindungi dari eksekusi tanpa analisis hulu.

### Fase 9 — Hardening Keamanan, Ketahanan Runtime, & Pengujian RBAC — SELESAI
- Runtime segfault bypass untuk isolasi crash Rust ChromaDB di Windows Python 3.13 (`FallbackVectorIndex` berbasis NumPy).
- Pengetatan header RBAC `X-User-Role` dan CORS eksplisit (`localhost:3000` & `127.0.0.1:3000`).
- Opsi peran auditor eksternal read-only untuk demonstrasi penolakan mutasi kode.

### Fase 10 — Pipeline Analisis Regulasi OJK Terintegrasi — SELESAI
- Pemasangan parser `pdfplumber` dan cache SQLite lokal `data/regulations.db` (`selisih/regulation_cache.py`).
- Ingest ChromaDB dinamis (`ingest_regulation_dynamic`) dan modul pipeline terpadu (`selisih/pipeline.py`).

### Fase 11 — Integrasi Tab 2 IBM Bob Code Impact & Remediation Pipeline — SELESAI
- Injeksi metadata sesi klien ke `data/temuan.json` (`company_id`, `organization`, `target_repository`).
- Resolusi direktori dinamis repositori klien sasaran di `api.py` via `_resolve_target_repo()`.
- Pemindai kode dinamis `scan_repo_for_compliance_targets()` di `selisih/impact.py` untuk deteksi konstanta finansial.

### Fase 12 — Tab 3 Tata Kelola Human-in-the-Loop & Berita Acara Kepatuhan — SELESAI
- Tinjauan selektif & patching granular berbasis checkbox (`selected_change_ids`).
- Pemisahan temuan `code_patchable` vs `policy_action_required` (kartu panduan SOP tata kelola).
- Pembuatan Berita Acara Kepatuhan resmi (*Compliance Sign-off Certificate*) berformat Markdown (`GET /api/impact/compliance-report`).

### Fase 13 — Penyelarasan Rantai Pipeline Tab 2 ke Tab 3 — SELESAI
- Eliminasi pemindaian prematur di Tab 1 dan penghapusan terminal CLI tiruan di Tab 2.
- IBM Bob Shell berjalan murni background dengan SSE streaming status riil dan penampil artefak handoff resmi.

### Fase 14 — Flow Langflow Visual Siap Import & Perbaikan Tautan Resmi OJK — SELESAI
- Template visual Langflow `flows/selisih_regulatory_flow_v2.json` dan panduan impor `docs/LANGFLOW_IMPORT_GUIDE.md`.
- Perbaikan tautan dokumentasi statutori dan berkas PDF resmi POJK 77/2016, 10/2022, dan 22/2023.

### Fase 15 — Standardisasi Flow Langflow 1.12.5 (LFX) & Gerbang Autentikasi Klien Enterprise — SELESAI
- Standarisasi flow v2 untuk engine Langflow 1.12.5 (LFX) dengan serialisasi handle `œ`, `custom_fields` dinamis, dan 5 node lengkap (`TextInput`, `Chroma`, `PromptTemplate`, `GoogleGenerativeAI`, `ChatOutput`).
- Gerbang Masuk Klien Enterprise (`LoginPage.tsx`): 3 paket klien (Enterprise, Professional, Starter) dengan login 1-klik dan validasi `password == username`.
- Penyederhanaan tampilan kuota aktif Enterprise menjadi "3" dan penyembunyian tombol desktop Tab 2 untuk fokus pada headless Bob Shell.
- Total pengujian saat ini: **90 unit tests** (`pytest`): 89 passed, 1 portable skip (100% green). Frontend Next.js build: lolos kompilasi tanpa error.

## 6. Pembagian Kerja

- **Kode Python (app/adapter/MCP/patch):** dikerjakan agent di repo ini.
- **Flow Langflow:** dikerjakan di UI Langflow (bisa dibantu via file ekspor).

## 7. Cara Konteks Dijaga Antar-Session

- `AGENTS.md` — auto-dibaca opencode tiap session baru.
- `docs/CONTEXT.md` (file ini) — konteks + rencana.
- `PROGRESS.md` — checklist status.
- `DECISIONS.md` — log keputusan.
- Semua ikut ter-push, jadi konteks ikut ke mesin mana pun.
