# CONTEXT — SELISIH / RCIA

Dokumen konteks lengkap + rencana perbaikan. Tujuan file ini: **session baru bisa langsung
nyambung tanpa perlu dijelaskan ulang.**

Terakhir diperbarui: 2026-10-12

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
[Publik/cloud]            [Batas]            [Privat/lokal]
POJK + Astra DB  ──temuan.json──▶  app.py ──temuan.json──▶ IBM Bob + source code
+ Langflow (diff)                   │                        + patch + unit test
                                    ▼
                              Human Review (no auto-deploy)
```

- Astra DB **di dalam Langflow**; `app.py` tidak butuh kredensial Astra.
- **IBM Bob = MCP client**, tidak bisa dipanggil via REST. Jembatan nyata: **MCP server lokal** `mcp_server.py` (stdio ke Bob + HTTP admin `127.0.0.1:8765` ke dashboard).

## 5. Rencana Perbaikan (6 Fase)

Dari demo → alur nyata. Urutan eksekusi disarankan: **0 → 2 → 4 → 6**, lalu **1 → 3**.

### Fase 0 — Fondasi: kontrak data & konfigurasi — ✅ SELESAI
- JSON Schema `temuan.json` → `data/temuan_schema.json`.
- Endpoint/`flow_id`/token Langflow → `.env` + `.streamlit/secrets.toml` (loader `selisih/config.py`, priority: secrets→env→.env).
- `.env.example`.
- Loader dokumen regulasi TXT/PDF → `selisih/documents.py`:
  - `load_document_text()` membaca `.txt` dan PDF berbasis teks (`pypdf`).
  - `clean_pojk_text()` merapikan noise nomor halaman/whitespace.
  - `split_by_pasal()` menyiapkan chunk per pasal untuk calon ingest Astra (belum terhubung ke Langflow/Astra).
- Adapter `normalize_response()` / `run_analysis()` di `selisih/langflow.py`.
- Unit test mock HTTP di `tests/test_langflow_adapter.py` dan loader dokumen di `tests/test_documents.py`.

### Fase 1 — Perbaiki flow Langflow (di Langflow)
- Output **JSON terstruktur**, bukan chat text.
- LLM **Gemini → watsonx/Granite**.
- Tambah node validasi sitasi + abstention.
- Ingest dokumen lama ke Astra DB dari chunk `split_by_pasal()`; dukungan ekstraksi PDF lokal sudah ada, tapi koneksi ingest ke Langflow/Astra belum dikerjakan.
- Catat `flow_id`; ekspor tanpa ID Astra (repo publik).

### Fase 2 — Sambungkan `app.py` ke Langflow sungguhan — ✅ SELESAI
- Ganti `time.sleep`/status palsu dengan REST nyata `/api/v1/run/{flow_id}`.
- Health check sidebar (nyata).
- UI sekarang **Live Langflow REST only**; pilihan Mode Eksekusi di sidebar dihapus. Jika Langflow gagal, aplikasi menampilkan error jujur tanpa menjadikan demo sebagai hasil analisis.
- Sidebar tidak lagi menampilkan Astra DB karena Astra berada di dalam Langflow.
- License Gateway lokal `selisih/license.py`: `SELISIH_*` mengatur organisasi, paket, status, dan kuota repo; analisis/scan/handoff/apply dinonaktifkan bila lisensi tidak aktif atau kuota terlampaui.
- Tulis hasil live ke `data/temuan.json`.

### Fase 3 — Integrasi IBM Bob — ✅ SELESAI (jembatan MCP lokal & Bob Shell)
- Arsitektur hybrid D-015 & D-022: **MCP server lokal dual-pintu** (`mcp_server.py`, stdlib) + **Bob Shell CLI Runner**.
  - stdio JSON-RPC untuk Bob (`.bob/mcp.json` eksklusif): `get_temuan`, `list_artifacts`, `read_artifact`, `preview_patch`/`apply_patch` (wajib konfirmasi + backup), `run_repo_tests`.
  - HTTP admin `127.0.0.1:8765` (`MCP_ADMIN_PORT`; dashboard pakai `MCP_ADMIN_URL`): `GET /health`, `POST /handoff`.
- Artefak nyata: `selisih/artifacts.py` → `artifacts/impact_report.json`, `proposed_patch.diff`, `generated_tests.py` (draf uji dari `proposed_code`, literal dipertahankan).
- Tab 2: tombol Hybrid **"Jalankan Agen IBM Bob di Dashboard"** (eksekusi Bob Shell headless) dan **"Buka di IBM Bob Desktop"** (meluncurkan GUI) + kartu status IBM Bob V2.
- Allowlist akses: hanya `mock_fintech_repo/` + `artifacts/`; `artifacts/` di-gitignore.

### Fase 4 — Pemetaan dampak & patch aman — ✅ SELESAI
- Scanner deterministik `selisih/impact.py`: `kandidat_kode[].evidence` → file+baris+diff nyata (baseline sebelum Bob).
- Patch: **dry-run + backup `.bak.<ts>` + konfirmasi** sebelum menulis (Tab 3).
- Test via `pytest`, output asli (Tab 3).
- Unit test `tests/test_impact.py` + e2e AppTest (scan → dry-run → apply → backup → 3 passed).

### Fase 5 — Pengerasan & audit
- Verifikasi tidak ada secret di kode; redact flow saat ekspor.
- Autentikasi peran fungsional (`selisih/auth.py`): Administrator, Software Engineer, dan Compliance Officer tanpa emoji artifisial.
- Audit trail nyata (timestamp + hash file + nama & peran peninjau terautentikasi).

### Fase 6 — Testing & dokumentasi
- Unit test adapter/Langflow (mock HTTP).
- Perbaiki README (nama file, collection, cara jalankan Demo vs Live).
- Total saat ini: **41 unit test** (`pytest`) + e2e AppTest per fase (Fase 2 live mock/sidebar, Fase 4 patch, Fase 3 handoff MCP). `tests/test_documents.py` memvalidasi TXT, cleanup POJK, split pasal, dan PDF contoh bila tersedia; `tests/test_license.py` memvalidasi license gate lokal.

## 6. Pembagian Kerja

- **Kode Python (app/adapter/MCP/patch):** dikerjakan agent di repo ini.
- **Flow Langflow:** dikerjakan di UI Langflow (bisa dibantu via file ekspor).

## 7. Cara Konteks Dijaga Antar-Session

- `AGENTS.md` — auto-dibaca opencode tiap session baru.
- `docs/CONTEXT.md` (file ini) — konteks + rencana.
- `PROGRESS.md` — checklist status.
- `DECISIONS.md` — log keputusan.
- Semua ikut ter-push, jadi konteks ikut ke mesin mana pun.
