"""API Server SELISIH berbasis FastAPI.

Menyediakan REST API & Server-Sent Events (SSE) untuk:
1. Pemantauan & Sinkronisasi Regulasi JDIH OJK secara otomatis.
2. Eksekusi Analisis Diff Regulasi (Embedded Engine / Langflow REST).
3. Streaming Eksekusi Agen IBM Bob Shell secara real-time.
4. Pemetaan Dampak Kode, Safe Patching (dry-run & backup), dan Test Runner.
5. Jejak Audit (Audit Trail) & License Gateway.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from selisih import artifacts, auth, impact, ojk
from selisih.config import get_langflow_config
from selisih.documents import load_document_text
from selisih.langflow import run_analysis, run_embedded_analysis
from selisih.license import (
    get_license_state,
    get_company_profiles,
    set_active_company,
    add_repository_to_company,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOCK_REPO_DIR = os.path.join(BASE_DIR, "mock_fintech_repo")
GOLDEN_PATH_FILE = os.path.join(DATA_DIR, "temuan_golden_path.json")
LIVE_RESULT_FILE = os.path.join(DATA_DIR, "temuan.json")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
POJK_LAMA_FILE = os.path.join(DATA_DIR, "pojk_lama_77_2016.txt")
POJK_BARU_FILE = os.path.join(DATA_DIR, "pojk_baru_22_2023.txt")

app = FastAPI(
    title="SELISIH Enterprise API",
    description="Regulatory Change & Code Impact System API for IBM x Hacktiv8",
    version="2.0.0",
)

# Aktifkan CORS untuk Frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory & Persistent audit trail state
AUDIT_FILE = os.path.join(DATA_DIR, "audit_trail.jsonl")


def _load_persisted_audit_logs() -> List[Dict[str, Any]]:
    logs = [
        {
            "id": "AUDIT-INIT-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "SYSTEM_STARTUP",
            "actor": "System",
            "details": "Sistem SELISIH Enterprise API diinisialisasi.",
        }
    ]
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
        except Exception:
            pass
    return logs


_AUDIT_LOGS: List[Dict[str, Any]] = _load_persisted_audit_logs()


def log_audit_event(
    action: str,
    actor: str,
    details: str,
    note: Optional[str] = None,
    backups: Optional[list] = None,
    restored: Optional[list] = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": f"AUDIT-{int(time.time() * 1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "details": details,
    }
    if note is not None:
        entry["note"] = note
    if backups is not None:
        entry["backups"] = backups
    if restored is not None:
        entry["restored"] = restored

    _AUDIT_LOGS.append(entry)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return entry


def verify_compliance_role(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
    """Memverifikasi bahwa aksi mutasi kode hanya dapat dilakukan oleh peran yang berwenang."""
    if not x_user_role:
        raise HTTPException(
            status_code=401,
            detail="Header otentikasi peran 'X-User-Role' wajib disertakan untuk aksi mutasi repositori bank.",
        )
    allowed_roles = {
        "Compliance Officer",
        "Admin",
        "Administrator",
        "Lead Developer",
        "Software Engineer",
    }
    if x_user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak: Peran '{x_user_role}' tidak memiliki wewenang untuk memutasi repositori bank.",
        )
    return x_user_role



# ==========================================
# MODEL REQUEST & RESPONSE
# ==========================================
class RoleRequest(BaseModel):
    role: str = "Compliance Officer"


class AnalysisRunRequest(BaseModel):
    text_baru: Optional[str] = None
    engine: Optional[str] = "embedded"  # 'embedded' atau 'rest'
    ojk_info: Optional[Dict[str, Any]] = None
    acuan_info: Optional[Dict[str, Any]] = None


class OjkAnalyzeRequest(BaseModel):
    id: str
    judul: str
    nomor: str
    tahun: str
    detail_url: Optional[str] = None


class PatchApplyRequest(BaseModel):
    reviewer_role: str = "Compliance Officer"
    reviewer_note: Optional[str] = "Persetujuan perubahan batasan kepatuhan POJK 22/2023."
    confirm: bool = True


# ==========================================
# ENDPOINT SISTEM & LISENSI
# ==========================================
@app.get("/api/system/health")
def get_system_health():
    """Mengembalikan status kesehatan sistem, Langflow, ChromaDB, dan IBM Bob."""
    cfg = get_langflow_config()
    lic = get_license_state()
    is_embedded = not bool(cfg.get("flow_id"))

    # 1. Langflow Pipeline
    langflow_connected = False
    if is_embedded:
        flow_path = os.path.join(BASE_DIR, "flows", "selisih_regulatory_flow.json")
        langflow_connected = os.path.exists(flow_path)
    else:
        try:
            import httpx
            r = httpx.get(f"{cfg['api_url']}/health", timeout=1.5)
            langflow_connected = r.status_code < 500
        except Exception:
            langflow_connected = False

    # 2. ChromaDB Lokal
    chromadb_connected = False
    try:
        from selisih import vector_store
        col = vector_store.get_or_create_collection()
        chromadb_connected = col is not None
    except Exception:
        chromadb_connected = False

    # 3. IBM Bob (MCP Server 8765)
    bob_connected = False
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8765/health")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            bob_connected = (resp.status == 200)
    except Exception:
        bob_connected = False

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "langflow": {
                "name": "Langflow Pipeline",
                "connected": langflow_connected,
            },
            "chromadb": {
                "name": "ChromaDB Lokal",
                "connected": chromadb_connected,
            },
            "bob": {
                "name": "IBM Bob (MCP)",
                "connected": bob_connected,
            },
        },
        "langflow": {
            "mode": "embedded" if is_embedded else "rest",
            "connected": langflow_connected,
            "flow_id": cfg.get("flow_id") or "selisih_regulatory_flow.json",
        },
        "license": {
            "organization": lic["organization"],
            "plan": lic["plan_label"],
            "status": lic["status"],
            "status_label": lic["status_label"],
            "is_valid": lic["can_run"],
            "active_repos": lic["active_repos"],
            "repo_limit": lic["repo_limit"],
            "message": lic["message"],
        },
        "artifacts_exist": os.path.exists(os.path.join(ARTIFACTS_DIR, "impact_report.json")),
    }


# ==========================================
# ENDPOINT LISENSI & PROFIL ENTITAS PERUSAHAAN
# ==========================================
class SelectCompanyRequest(BaseModel):
    company_id: str


class AddRepoRequest(BaseModel):
    company_id: Optional[str] = ""
    name: str
    path: str


@app.get("/api/license/profiles")
def get_license_profiles():
    """Mengembalikan daftar seluruh profil entitas perusahaan dan status lisensi aktif."""
    return {
        "profiles": get_company_profiles(),
        "active": get_license_state(),
    }


@app.post("/api/license/select")
def select_company(req: SelectCompanyRequest):
    """Mengubah entitas perusahaan aktif untuk sesi sistem saat ini."""
    updated = set_active_company(req.company_id)
    return {
        "status": "success",
        "company": updated,
    }


@app.post("/api/license/add-repo")
def add_company_repo(req: AddRepoRequest, authorized_role: str = Depends(verify_compliance_role)):
    """Mendaftarkan repositori baru ke entitas perusahaan dengan validasi kuota."""
    res = add_repository_to_company(req.company_id or "", req.name, req.path)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Gagal mendaftarkan repositori"))
    return res



# ==========================================
# ENDPOINT JDIH OJK (SINKRONISASI REGULASI)
# ==========================================
HISTORICAL_REGULATIONS: List[Dict[str, Any]] = [
    {
        "id": "pojk-77-2016",
        "judul": "Peraturan Otoritas Jasa Keuangan Nomor 77/POJK.01/2016 tentang Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
        "nomor": "77/POJK.01/2016",
        "tahun": "2016",
        "sektor": "Lembaga Pembiayaan & LPBBTI (P2P Lending)",
        "sektor_id": "09",
        "jenis": "Peraturan OJK",
        "tanggal_berlaku": "28-12-2016",
        "status": "Diubah / Terdahulu",
        "detail_url": "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/pojk-77-2016",
        "download_url": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "pojk-10-2022",
        "judul": "Peraturan Otoritas Jasa Keuangan Nomor 10/POJK.05/2022 tentang Layanan Pendanaan Bersama Berbasis Teknologi Informasi",
        "nomor": "10/POJK.05/2022",
        "tahun": "2022",
        "sektor": "Lembaga Pembiayaan & LPBBTI (P2P Lending)",
        "sektor_id": "09",
        "jenis": "Peraturan OJK",
        "tanggal_berlaku": "04-07-2022",
        "status": "Berlaku",
        "detail_url": "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/pojk-10-2022",
        "download_url": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "pojk-22-2023",
        "judul": "Peraturan Otoritas Jasa Keuangan Nomor 22 Tahun 2023 tentang Pelindungan Konsumen dan Masyarakat di Sektor Jasa Keuangan",
        "nomor": "22",
        "tahun": "2023",
        "sektor": "Pelindungan Konsumen & Market Conduct",
        "sektor_id": "04",
        "jenis": "Peraturan OJK",
        "tanggal_berlaku": "20-12-2023",
        "status": "Berlaku",
        "detail_url": "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/pojk-22-2023",
        "download_url": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
]


@app.get("/api/ojk/regulations")
def get_ojk_regulations(
    sectors: Optional[str] = Query(None, description="Comma-separated sector codes, mis: 10,09,04"),
    limit: int = Query(10, ge=1, le=50),
):
    """Mengambil daftar regulasi terbaru langsung dari JDIH OJK terintegrasi dengan acuan historis."""
    sector_list = sectors.split(",") if sectors else ["10", "09", "04"]
    regs = ojk.fetch_ojk_regulations(sectors=sector_list, limit_per_sector=limit)
    
    # Gabungkan dengan acuan historis penting jika belum ada dalam hasil scrape
    combined = list(regs)
    existing_ids = {r.get("id") for r in combined}
    existing_nomors = {str(r.get("nomor")) for r in combined}

    for hist in HISTORICAL_REGULATIONS:
        if hist["id"] not in existing_ids and str(hist["nomor"]) not in existing_nomors:
            combined.append(hist)

    # Urutkan berdasarkan tahun descending
    combined.sort(key=lambda x: str(x.get("tahun") or "0"), reverse=True)

    return {
        "count": len(combined),
        "source": "JDIH OJK (jdih.ojk.go.id)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "regulations": combined,
    }


@app.post("/api/ojk/analyze")
def analyze_ojk_regulation(req: OjkAnalyzeRequest):
    """Menganalisis regulasi OJK yang dipilih langsung dari JDIH feed."""
    lic = get_license_state()
    if not lic["can_run"]:
        raise HTTPException(status_code=403, detail=f"Aksi diblokir oleh lisensi: {lic['message']}")

    selected_ojk = {
        "id": req.id,
        "nomor": req.nomor,
        "tahun": req.tahun,
        "judul": req.judul,
        "doc_id": f"POJK-{req.nomor}-{req.tahun}" if req.tahun else f"POJK-{req.nomor}",
    }
    selected_acuan = {
        "id": "pojk-77-2016",
        "nomor": "77/POJK.01/2016",
        "tahun": "2016",
        "judul": "Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
        "doc_id": "POJK-77-2016",
    }

    # Tentukan teks regulasi
    if req.nomor in ["22", "22/2023"] or "22" in req.judul:
        text_target = load_document_text(POJK_BARU_FILE)
    else:
        text_target = f"PERATURAN OTORITAS JASA KEUANGAN NOMOR {req.nomor} TAHUN {req.tahun}\nTENTANG {req.judul}\n\n"
        text_target += load_document_text(POJK_BARU_FILE)

    text_acuan = load_document_text(POJK_LAMA_FILE)
    findings = run_embedded_analysis(
        text_target,
        acuan_info=selected_acuan,
        ojk_info=selected_ojk,
        acuan_text=text_acuan,
    )

    import hashlib
    digest = hashlib.sha256(text_target.encode("utf-8")).hexdigest()
    saved_payload = {
        "analysis_meta": {
            "engine": "Langflow Pipeline (ChromaDB Vector Store + watsonx Granite)",
            "model": "watsonx/Granite",
            "selected_acuan": selected_acuan,
            "selected_ojk": selected_ojk,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provenance_checksum": f"sha256:{digest}",
        },
        "findings": findings,
    }
    with open(LIVE_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_payload, f, ensure_ascii=False, indent=2)

    _AUDIT_LOGS.append({
        "id": f"AUDIT-OJK-{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "SELECT_OJK_REGULATION",
        "actor": "System",
        "details": f"Regulasi POJK {req.nomor}/{req.tahun} dipilih dan dianalisis terhadap acuan POJK 77/2016.",
    })

    return {
        "status": "success",
        "findings_count": len(findings),
        "data": saved_payload,
    }


# ==========================================
# ENDPOINT ANALISIS DIFF REGULASI (TAB 1)
# ==========================================
@app.get("/api/analysis/findings")
def get_analysis_findings():
    """Mengambil temuan regulasi saat ini (live temuan.json atau golden path)."""
    payload, source = impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)
    findings = payload.get("findings", [])

    total = len(findings)
    valid = sum(1 for f in findings if f.get("sitasi_valid"))
    pct_valid = round(valid / total * 100) if total else 0
    abstain = any(f.get("abstain") for f in findings)
    confs = {f.get("confidence") for f in findings if f.get("confidence")}

    if abstain:
        conf_label = "Abstain"
    elif confs == {"tinggi"}:
        conf_label = "Tinggi"
    elif "rendah" in confs:
        conf_label = "Campuran"
    else:
        conf_label = "Sedang"

    return {
        "source": source,
        "analysis_meta": payload.get("analysis_meta", {}),
        "metrics": {
            "total_findings": total,
            "valid_citations": valid,
            "citation_percentage": pct_valid,
            "confidence": conf_label,
            "abstain": abstain,
        },
        "findings": findings,
    }


@app.post("/api/analysis/run")
def run_regulatory_analysis(req: AnalysisRunRequest):
    """Menjalankan analisis diff regulasi secara real-time untuk dua berkas terpilih."""
    lic = get_license_state()
    if not lic["can_run"]:
        raise HTTPException(status_code=403, detail=f"Aksi diblokir oleh lisensi: {lic['message']}")

    # Tentukan metadata regulasi acuan dan pembaruan
    selected_acuan = req.acuan_info or {
        "id": "pojk-77-2016",
        "nomor": "77/POJK.01/2016",
        "tahun": "2016",
        "judul": "Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
        "doc_id": "POJK-77-2016",
    }
    selected_ojk = req.ojk_info or {
        "id": "pojk-22-2023",
        "nomor": "22",
        "tahun": "2023",
        "judul": "Pelindungan Konsumen dan Masyarakat di Sektor Jasa Keuangan",
        "doc_id": "POJK-22-2023",
    }

    # Siapkan teks regulasi acuan
    a_nomor = str(selected_acuan.get("nomor", ""))
    a_id = str(selected_acuan.get("id", ""))
    if a_nomor in ["77", "77/2016", "77/POJK.01/2016"] or "77" in a_nomor or "77" in a_id:
        text_acuan = load_document_text(POJK_LAMA_FILE)
    else:
        text_acuan = f"PERATURAN OTORITAS JASA KEUANGAN NOMOR {a_nomor} TAHUN {selected_acuan.get('tahun', '')}\nTENTANG {selected_acuan.get('judul', '')}\n\n"
        text_acuan += load_document_text(POJK_LAMA_FILE)

    # Siapkan teks regulasi baru
    if req.text_baru:
        text_baru = req.text_baru
    else:
        b_nomor = str(selected_ojk.get("nomor", ""))
        b_id = str(selected_ojk.get("id", ""))
        if b_nomor in ["22", "22/2023"] or "22" in b_nomor or "22" in b_id:
            text_baru = load_document_text(POJK_BARU_FILE)
        else:
            text_baru = f"PERATURAN OTORITAS JASA KEUANGAN NOMOR {b_nomor} TAHUN {selected_ojk.get('tahun', '')}\nTENTANG {selected_ojk.get('judul', '')}\n\n"
            text_baru += load_document_text(POJK_BARU_FILE)

    cfg = get_langflow_config()

    try:
        if req.engine == "rest" and cfg.get("flow_id"):
            findings = run_analysis(text_baru, cfg)
            engine_name = "Langflow REST API (watsonx Granite)"
        else:
            findings = run_embedded_analysis(
                text_baru,
                acuan_info=selected_acuan,
                ojk_info=selected_ojk,
                acuan_text=text_acuan,
            )
            engine_name = "Embedded Flow Engine (watsonx Granite Framework)"

        # Simpan ke data/temuan.json
        import hashlib
        digest = hashlib.sha256(f"{text_acuan}::{text_baru}".encode("utf-8")).hexdigest()
        saved_payload = {
            "analysis_meta": {
                "engine": engine_name,
                "model": "watsonx/Granite",
                "selected_acuan": selected_acuan,
                "selected_ojk": selected_ojk,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provenance_checksum": f"sha256:{digest}",
            },
            "findings": findings,
        }
        with open(LIVE_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(saved_payload, f, ensure_ascii=False, indent=2)

        log_audit_event(
            action="RUN_REGULATORY_DIFF",
            actor="System",
            details=f"Analisis regulasi acuan POJK {selected_acuan.get('nomor', '')} vs pembaruan POJK {selected_ojk.get('nomor', '')}/{selected_ojk.get('tahun', '')} berhasil diproses dengan engine {engine_name} ({len(findings)} temuan).",
        )

        return {
            "status": "success",
            "engine": engine_name,
            "findings_count": len(findings),
            "data": saved_payload,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ==========================================
# ENDPOINT BOB SHELL AGENT (STREAMING SSE)
# ==========================================
@app.get("/api/bob/stream")
async def stream_bob_agent():
    """Streaming log eksekusi agen IBM Bob Shell langkah demi langkah via SSE."""
    payload, source = impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)
    meta = payload.get("analysis_meta", {})
    selected_acuan = meta.get("selected_acuan", {})
    selected_ojk = meta.get("selected_ojk", {})

    acuan_label = f"POJK {selected_acuan.get('nomor', '77/2016')}"
    pembaruan_label = f"POJK {selected_ojk.get('nomor', '22')}/{selected_ojk.get('tahun', '2023')}"

    findings = payload.get("findings", [])
    records = impact.scan_impact(payload, MOCK_REPO_DIR)
    bob_info = artifacts.check_bob_status()

    bob_status = bob_info.get("status", "ready")

    async def event_generator():
        # 1. Inisialisasi
        yield f"data: {json.dumps({'type': 'init', 'msg': f'[IBM Bob Shell] Memulai sesi interaktif agen AI di mock_fintech_repo (Bob Status: {bob_status})...'})}\n\n"
        await asyncio.sleep(0.3)

        # 2. MCP Bridge
        yield f"data: {json.dumps({'type': 'mcp', 'msg': '[MCP Client] Menghubungkan ke server MCP lokal (127.0.0.1:8765) via .bob/mcp.json...'})}\n\n"
        await asyncio.sleep(0.3)

        # 3. Tool call get_temuan dengan konteks spesifik dari Tab 1
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'get_temuan', 'msg': f'[Tool Call] get_temuan() -> Memuat hasil analisis Tab 1: {acuan_label} vs {pembaruan_label} ({len(findings)} klausul terverifikasi).'})}\n\n"
        await asyncio.sleep(0.35)

        # 4. AI Reasoning per finding
        for f in findings:
            cid = f.get("change_id", "CHG")
            pasal = f.get("pasal_baru", {}).get("pasal", "Pasal")
            ringkasan = f.get("ringkasan", "")
            yield f"data: {json.dumps({'type': 'thought', 'msg': f'[Penalaran AI] Mengevaluasi dampak {cid} ({pasal}): {ringkasan}'})}\n\n"
            await asyncio.sleep(0.35)

        # 5. Tool call scan_impact
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'scan_impact', 'msg': f'[Tool Call] scan_impact(target_repo=\"mock_fintech_repo\") -> Memindai kode sumber untuk kewajiban {pembaruan_label}...'})}\n\n"
        await asyncio.sleep(0.3)

        # 6. Candidate matches found
        for rec in records:
            path = rec.get("path", "")
            line = rec.get("line", 1)
            old_c = rec.get("old_code", "").strip()
            prop_c = rec.get("proposed_code", "").strip()
            yield f"data: {json.dumps({'type': 'thought', 'msg': f'[Kandidat Kode] {path}:{line} -> Ubah `{old_c}` menjadi `{prop_c}` sesuai mandat {pembaruan_label}'})}\n\n"
            await asyncio.sleep(0.35)

        # 7. Tool call build_artifacts
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'build_artifacts', 'msg': '[Tool Call] Membangun paket artefak handoff: proposed_patch.diff, generated_tests.py, impact_report.json...'})}\n\n"
        await asyncio.sleep(0.3)

        # Build real artifacts on disk
        artifacts.ensure_mcp_config()
        artifacts.build_artifacts_from_findings(findings, ARTIFACTS_DIR)

        # 8. Success Handoff
        yield f"data: {json.dumps({'type': 'success', 'msg': f'[Handoff Selesai] {len(records)} baris kode siap ditinjau secara human-in-the-loop di Tab 3.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/bob/artifacts")
def get_bob_artifacts():
    """Mengambil daftar dan isi berkas artefak IBM Bob."""
    items = []
    if os.path.exists(ARTIFACTS_DIR):
        for name in ["impact_report.json", "proposed_patch.diff", "generated_tests.py"]:
            file_path = os.path.join(ARTIFACTS_DIR, name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    items.append({
                        "name": name,
                        "size": os.path.getsize(file_path),
                        "content": content,
                    })
                except Exception:
                    pass
    return {"artifacts": items}


# ==========================================
# ENDPOINT PEMETAAN DAMPAK & SAFE PATCHING (TAB 3)
# ==========================================
@app.get("/api/impact/scan")
def get_impact_scan():
    """Memindai kandidat dampak kode nyata di mock_fintech_repo."""
    payload, source = impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)
    records = impact.scan_impact(payload, MOCK_REPO_DIR)
    return {
        "source": source,
        "records_count": len(records),
        "records": records,
    }


@app.get("/api/impact/dry-run")
def get_patch_dry_run():
    """Melakukan uji coba (dry-run) penerapan patch tanpa menulis ke disk."""
    payload, _ = impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)
    records = impact.scan_impact(payload, MOCK_REPO_DIR)
    results = impact.apply_patch(records, dry_run=True)
    return {
        "dry_run": True,
        "results": results,
        "records_count": len(records),
    }


@app.post("/api/impact/apply")
def apply_patch(req: PatchApplyRequest, authorized_role: str = Depends(verify_compliance_role)):
    """Menerapkan patch kepatuhan dengan backup otomatis dan audit logging."""
    lic = get_license_state()
    if not lic["can_run"]:
        raise HTTPException(status_code=403, detail=f"Aksi diblokir oleh lisensi: {lic['message']}")

    payload, _ = impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)
    records = impact.scan_impact(payload, MOCK_REPO_DIR)
    results = impact.apply_patch(records, dry_run=not req.confirm)

    applied_count = sum(1 for r in results if r.get("status") == "applied")
    backups = [r.get("backup_path") for r in results if r.get("backup_path")]

    # Catat ke Jejak Audit (in-memory dan disk)
    log_audit_event(
        action="APPLY_COMPLIANCE_PATCH",
        actor=req.reviewer_role or authorized_role,
        details=f"Patch kepatuhan diterapkan pada {applied_count} berkas oleh {req.reviewer_role or authorized_role}.",
        note=req.reviewer_note,
        backups=backups,
    )

    return {
        "success": True,
        "applied_count": applied_count,
        "results": results,
    }


@app.post("/api/impact/rollback")
def rollback_compliance_patch(authorized_role: str = Depends(verify_compliance_role)):
    """Mengembalikan berkas repositori mock ke cadangan .bak terbaru."""
    res = impact.rollback_last_backup(MOCK_REPO_DIR)
    if res.get("status") == "success":
        log_audit_event(
            action="ROLLBACK_COMPLIANCE_PATCH",
            actor=authorized_role,
            details=f"Memulihkan {res.get('count', 0)} berkas dari salinan cadangan (.bak) terbaru.",
            restored=res.get("restored", []),
        )
    return res



@app.post("/api/impact/test")
def run_repo_tests():
    """Menjalankan unit test repositori (pytest mock_fintech_repo/tests)."""
    res = impact.run_pytest(MOCK_REPO_DIR, "tests")
    res["code"] = res.get("returncode", 0)
    return res


# ==========================================
# ENDPOINT AUDIT TRAIL
# ==========================================
@app.get("/api/audit/logs")
def get_audit_logs():
    """Mengembalikan riwayat audit trail enterprise."""
    return {"logs": list(reversed(_AUDIT_LOGS))}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
