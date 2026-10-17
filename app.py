import streamlit as st
import json
import os
import requests
from selisih import artifacts, impact
from selisih.config import get_langflow_config
from selisih.documents import DocumentLoadError, load_document_text
from selisih.langflow import run_analysis, LangflowError
from selisih.license import get_license_state

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="SELISIH — Regulatory Change & Code Impact System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Direktori Dasar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOCK_REPO_DIR = os.path.join(BASE_DIR, "mock_fintech_repo")
GOLDEN_PATH_FILE = os.path.join(DATA_DIR, "temuan_golden_path.json")
LIVE_RESULT_FILE = os.path.join(DATA_DIR, "temuan.json")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
MCP_ADMIN_URL = os.environ.get("MCP_ADMIN_URL", "http://127.0.0.1:8765")

# Inisialisasi Session State
if "diff_analyzed" not in st.session_state:
    st.session_state.diff_analyzed = False
if "patch_applied" not in st.session_state:
    st.session_state.patch_applied = False
if "test_output" not in st.session_state:
    st.session_state.test_output = None
if "analysis_source" not in st.session_state:
    st.session_state.analysis_source = "live"
if "live_findings" not in st.session_state:
    st.session_state.live_findings = []
if "impact_records" not in st.session_state:
    st.session_state.impact_records = []
if "impact_scanned" not in st.session_state:
    st.session_state.impact_scanned = False
if "dry_run_report" not in st.session_state:
    st.session_state.dry_run_report = None
if "patch_report" not in st.session_state:
    st.session_state.patch_report = None
if "artifacts_built" not in st.session_state:
    st.session_state.artifacts_built = False
if "artifacts_summary" not in st.session_state:
    st.session_state.artifacts_summary = None


def _source_findings():
    if st.session_state.analysis_source == "live" and st.session_state.live_findings:
        return {"analysis_meta": {}, "findings": st.session_state.live_findings}, "session live"
    return impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)


def _load_text(path):
    return load_document_text(path)


def _save_live_result(findings, input_path):
    import hashlib
    from datetime import datetime, timezone

    digest = hashlib.sha256()
    with open(input_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    payload = {
        "analysis_meta": {
            "engine": "Langflow (live REST)",
            "model": "watsonx/Granite",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provenance_checksum": f"sha256:{digest.hexdigest()}",
        },
        "findings": findings,
    }
    with open(LIVE_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


@st.cache_data(ttl=15, show_spinner=False)
def _langflow_health():
    cfg = get_langflow_config()
    if not cfg["flow_id"]:
        return {"status": "not_configured", "msg": "flow_id kosong (.env / secrets.toml)"}
    try:
        res = requests.get(f"{cfg['api_url']}/health", timeout=5)
        if res.status_code < 500:
            return {"status": "ok", "msg": f"HTTP {res.status_code}"}
        return {"status": "down", "msg": f"HTTP {res.status_code}"}
    except requests.RequestException as exc:
        return {"status": "down", "msg": str(exc)}


@st.cache_data(ttl=5, show_spinner=False)
def _mcp_health():
    try:
        res = requests.get(f"{MCP_ADMIN_URL}/health", timeout=2)
        if res.status_code == 200:
            return {"status": "ok", "data": res.json()}
        return {"status": "down", "data": {}, "msg": f"HTTP {res.status_code}"}
    except requests.RequestException as exc:
        return {"status": "down", "data": {}, "msg": str(exc)}


def _render_metrics(findings):
    total = len(findings)
    valid = sum(1 for f in findings if f.get("sitasi_valid"))
    pct = round(valid / total * 100) if total else 0
    abstain = any(f.get("abstain") for f in findings)
    confs = {f.get("confidence") for f in findings if f.get("confidence")}
    if abstain:
        conf = "Abstain"
    elif confs == {"tinggi"}:
        conf = "Tinggi"
    elif "rendah" in confs:
        conf = "Campuran"
    else:
        conf = "Sedang"
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Klausul Terdampak", f"{total} Pasal")
    col_m2.metric("Validitas Sitasi", f"{pct}%", "Tervalidasi" if valid == total else "Perlu Cek")
    col_m3.metric("Tingkat Keyakinan", conf, "Kualitatif")
    col_m4.metric("Status Abstention", str(abstain).lower(), "Bukti Cukup" if not abstain else "Data Kurang")


def _render_findings(findings):
    for f in findings:
        tag, tag_cls = "Sitasi Valid", "tag tag-success"
        if f.get("abstain"):
            tag, tag_cls = "Abstain", "tag"
        elif not f.get("sitasi_valid"):
            tag, tag_cls = "Sitasi Tidak Valid", "tag"
        pb = f.get("pasal_baru") or {}
        pl = f.get("pasal_lama") or {}
        ref_b = f"{pb.get('doc_id', '')} {pb.get('pasal', '')} {pb.get('ayat', '')}".strip()
        ref_l = f"{pl.get('doc_id', '')} {pl.get('pasal', '')} {pl.get('ayat', '')}".strip()
        cite_b = (pb.get("kutipan") or "-").replace('"', "'")
        cite_l = (pl.get("kutipan") or "-").replace('"', "'")
        st.markdown(f"""
        <div class="clean-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <strong>{f.get('change_id', 'N/A')} — {f.get('ringkasan', 'Tanpa ringkasan')}</strong>
                <span class="{tag_cls}">{tag}</span>
            </div>
            <div class="card-body">
                <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #E6E1D8;">
                        <td style="padding: 6px 0; width: 25%; color: #6E6B64;">Pasal Pembaruan</td>
                        <td style="padding: 6px 0;"><strong>{ref_b}</strong>: "{cite_b}"</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #6E6B64;">Pasal Acuan Lama</td>
                        <td style="padding: 6px 0;"><strong>{ref_l}</strong>: "{cite_l}"</td>
                    </tr>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TEMA NOTION / WARM CREAM MINIMALIS (CSS)
# ==========================================
st.markdown("""
<style>
    /* Global Typography & Contrast */
    .stApp {
        background-color: #FAF8F5;
        color: #1A1917;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Headings & Paragraphs High Contrast */
    h1, h2, h3, h4, h5, h6 {
        color: #111110 !important;
        font-weight: 700 !important;
    }
    
    p, span, li, label, div[data-testid="stMarkdownContainer"] p {
        color: #1A1917 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F3EFE8 !important;
        border-right: 1px solid #E6E1D8 !important;
    }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
        color: #1A1917 !important;
    }
    
    /* Clean Minimalist Cards */
    .clean-card {
        background-color: #FFFFFF;
        border: 1px solid #DDD8CD;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    
    .card-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #3C3A35 !important;
        margin-bottom: 8px;
    }

    .card-body {
        font-size: 14px;
        line-height: 1.6;
        color: #1A1917 !important;
    }

    /* Minimal Badges / Tags */
    .tag {
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #C8C2B5;
        background-color: #EFECE6;
        color: #2D2C28 !important;
    }
    
    .tag-success {
        border-color: #A3D4B0 !important;
        background-color: #E6F4EA !important;
        color: #0F5C2B !important;
    }

    /* Custom Header Section */
    .app-header {
        border-bottom: 1px solid #DDD8CD;
        padding-bottom: 18px;
        margin-bottom: 24px;
    }
    
    .app-title {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #111110 !important;
        margin: 0;
    }
    
    .app-subtitle {
        font-size: 14px;
        color: #4A4843 !important;
        margin-top: 4px;
    }

    /* Metrics High Contrast */
    div[data-testid="stMetricLabel"] p {
        color: #4A4843 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] div {
        color: #111110 !important;
        font-size: 24px !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricDelta"] div {
        color: #0F5C2B !important;
        font-weight: 600 !important;
    }

    /* Tables High Contrast */
    div[data-testid="stTable"] table {
        color: #1A1917 !important;
        border: 1px solid #DDD8CD !important;
    }
    div[data-testid="stTable"] th {
        background-color: #EFECE6 !important;
        color: #111110 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stTable"] td {
        background-color: #FFFFFF !important;
        color: #1A1917 !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #DDD8CD !important;
        border-radius: 6px !important;
    }
    details summary span {
        color: #111110 !important;
        font-weight: 600 !important;
    }

    /* Captions */
    div[data-testid="stCaptionContainer"] p {
        color: #4A4843 !important;
        font-size: 12px !important;
    }

    /* Primary and Secondary Buttons */
    .stButton>button {
        border-radius: 5px;
        font-weight: 600;
        font-size: 13px;
        padding: 8px 18px;
        transition: all 0.15s ease-in-out;
    }
    .stButton>button[kind="primary"] {
        background-color: #1A1917 !important;
        color: #FFFFFF !important;
        border: 1px solid #1A1917 !important;
    }
    .stButton>button[kind="primary"] p {
        color: #FFFFFF !important;
    }
    .stButton>button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #1A1917 !important;
        border: 1px solid #DDD8CD !important;
    }
    .stButton>button[kind="secondary"] p {
        color: #1A1917 !important;
    }
</style>
""", unsafe_allow_html=True)

langflow_health = _langflow_health()
license_state = get_license_state(st.secrets)

# ==========================================
# SIDEBAR: STATUS & KONTROL SISTEM
# ==========================================
with st.sidebar:
    st.markdown("### SELISIH")
    st.caption("Control Plane Kepatuhan & Rekayasa")
    
    st.markdown("---")
    st.markdown("<div class='card-title'>Integrasi Komponen</div>", unsafe_allow_html=True)
    _hb = langflow_health
    _status = {"ok": "Hidup", "down": "Gagal", "not_configured": "Belum dikonfigurasi"}[_hb["status"]]
    st.markdown(f"• **Langflow:** {_status} ({_hb['msg']})")
    _bob = _mcp_health()
    if _bob["status"] == "ok":
        st.markdown("• **IBM Bob (MCP):** Hidup (server lokal)")
    else:
        st.markdown(f"• **IBM Bob (MCP):** Nonaktif" + (f" — {_bob['msg']}" if _bob.get("msg") else ""))
    
    st.markdown("---")
    st.markdown("<div class='card-title'>Langganan & Lisensi</div>", unsafe_allow_html=True)
    st.markdown(f"**Organisasi:** {license_state['organization']}")
    st.markdown(f"**Paket:** {license_state['plan_label']}")
    st.markdown(f"**Status:** {license_state['status_label']}")
    if license_state["repo_limit"] < 0:
        st.markdown(f"**Repositori Aktif:** {license_state['active_repos']} / tidak dibatasi")
        st.progress(1.0)
    else:
        used = license_state["active_repos"]
        limit = max(license_state["repo_limit"], 1)
        st.markdown(f"**Repositori Aktif:** {used} / {license_state['repo_limit']} repositori")
        st.progress(min(used / limit, 1.0))
    if license_state["can_run"]:
        st.caption(license_state["message"])
    else:
        st.error(license_state["message"])
        
    st.markdown("---")
    st.markdown("<div class='card-title'>Prinsip Keamanan</div>", unsafe_allow_html=True)
    st.checkbox("Kebijakan Abstention Aktif", value=True, disabled=True)
    st.checkbox("Penyimpanan Kode Terisolasi", value=True, disabled=True)
    st.caption("Kode sumber diproses secara lokal di lingkungan klien tanpa transmisi ke repositori eksternal.")

# ==========================================
# HEADER HALAMAN UTAMA
# ==========================================
st.markdown("""
<div class="app-header">
    <div class="app-title">SELISIH</div>
    <div class="app-subtitle">Regulatory Change & Code Impact System — IBM Hackathon IT-Finance</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TABS UTAMA
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "1. Analisis Regulasi (Diff)",
    "2. Pemetaan Dampak Kode",
    "3. Tata Kelola & Tinjauan"
])

# -------------------------------------------------------------------------
# TAB 1: ANALISIS REGULASI (DIFF)
# -------------------------------------------------------------------------
with tab1:
    st.markdown("#### Analisis Perubahan Regulasi")
    st.markdown("Membandingkan klausul regulasi baru terhadap basis pengetahuan regulasi terdahulu pada Astra DB menggunakan alur kerja Langflow.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="clean-card">
            <div class="card-title">Regulasi Acuan (Terdahulu)</div>
            <div class="card-body">
                <strong>POJK Nomor 77/POJK.01/2016</strong><br>
                <em>Pasal 8 ayat (2) & (3)</em><br><br>
                • Batas maksimum plafon pinjaman dana: <strong>Rp 20.000.000</strong><br>
                • Batas maksimum tingkat suku bunga harian: <strong>0,4% per hari</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_b:
        st.markdown("""
        <div class="clean-card">
            <div class="card-title">Regulasi Pembaruan (Terbaru)</div>
            <div class="card-body">
                <strong>POJK Nomor 22 Tahun 2023</strong><br>
                <em>Pasal 12 ayat (1) & (2)</em><br><br>
                • Batas maksimum plafon pinjaman ditingkatkan: <strong>Rp 50.000.000</strong><br>
                • Batas maksimum suku bunga harian diturunkan: <strong>0,1% per hari</strong><br>
                • Tenggat penyesuaian sistem: <strong>30 hari kalender</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if not license_state["can_run"]:
        st.warning("Aksi analisis dinonaktifkan oleh Lisensi Gateway. Perbaiki status/kuota lisensi di konfigurasi.")

    if st.button("Jalankan Analisis Regulasi (Langflow Engine)", type="primary", disabled=not license_state["can_run"]):
        with st.spinner("Mengirim regulasi baru ke Langflow dan memvalidasi sitasi..."):
            try:
                input_path = os.path.join(DATA_DIR, "pojk_baru_22_2023.txt")
                findings = run_analysis(_load_text(input_path))
                if not findings:
                    raise LangflowError("Tidak ada findings yang dapat dinormalkan.")
                st.session_state.diff_analyzed = True
                st.session_state.analysis_source = "live"
                st.session_state.live_findings = findings
                st.success(f"Berhasil menerima {len(findings)} temuan dari Langflow.")
                _save_live_result(findings, input_path)
            except (LangflowError, DocumentLoadError) as err:
                st.session_state.diff_analyzed = False
                st.session_state.analysis_source = "live"
                st.session_state.live_findings = []
                st.error(f"Analisis Live Langflow gagal: {err}")

    if st.session_state.diff_analyzed:
        st.markdown("---")
        st.markdown("##### Hasil Ekstraksi Perubahan")
        source = st.session_state.analysis_source

        findings = st.session_state.live_findings or []
        _render_metrics(findings)
        if findings:
            _render_findings(findings)
        else:
            st.info("Belum ada temuan yang diterima dari Langflow.")
        with st.expander("Inspeksi Struktur Data (data/temuan.json — live)"):
            if os.path.exists(LIVE_RESULT_FILE):
                with open(LIVE_RESULT_FILE, "r", encoding="utf-8") as f:
                    st.json(json.load(f))

# -------------------------------------------------------------------------
# TAB 2: PEMETAAN DAMPAK KODE (IBM BOB)
# -------------------------------------------------------------------------
with tab2:
    st.markdown("#### Pemetaan Dampak Kode & Draf Usulan")
    st.markdown("Scanner deterministik memetakan `kandidat_kode[].evidence` dari kontrak `temuan.json` ke file & baris nyata, lalu artefaknya bisa dikirim ke **IBM Bob (MCP)** melalui server lokal.")

    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        st.text_input("Target Repositori Terdaftar:", value="mock_fintech_repo (FintechCore Banking Service)", disabled=True)
    with col_r2:
        st.write("")
        st.write("")
        scan_btn = st.button("Pindai Dampak (Scanner Deterministik)", type="primary", disabled=not license_state["can_run"])

    if scan_btn:
        with st.spinner("Memindai evidence kandidat kode di repositori..."):
            findings, src = _source_findings()
            st.session_state.impact_records = impact.scan_impact(findings, MOCK_REPO_DIR)
            st.session_state.impact_scanned = True
            st.session_state.dry_run_report = None
            st.session_state.patch_report = None
            st.caption(f"Sumber findings: {src or 'tidak ada'}")

    if st.session_state.impact_scanned:
        records = st.session_state.impact_records
        patchable = [r for r in records if r["status"] == "patchable"]
        c1a, c1b, c1c = st.columns(3)
        c1a.metric("Kandidat Kode", f"{len(records)}")
        c1b.metric("Siap Patch", f"{len(patchable)}")
        c1c.metric("Perlu Perhatian", f"{len(records) - len(patchable)}")

        if not records:
            st.info("Tidak ada `kandidat_kode` pada findings. Hasil live Langflow belum memuat pemetaan kode — integrasi IBM Bob (Fase 3) akan mengisinya.")

        for r in records:
            if r["status"] == "patchable":
                st.markdown(f"""
                <div class="clean-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong>{r['change_id']} — {r['ringkasan'] or 'Tanpa ringkasan'}</strong>
                        <span class="tag tag-success">Siap Patch</span>
                    </div>
                    <div class="card-body">
                        File: <code>{r['path']}</code> · Baris: {', '.join(map(str, r['lines'])) or '-'}<br>
                        {r['alasan'] or ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.code(impact.make_diff(r["old_code"], r["proposed_code"], r["path"]), language="diff")
            else:
                label = {
                    "no_old_code": "tanpa old_code",
                    "already_or_no_match": "tak cocok / mungkin sudah disesuaikan",
                    "missing": "file tidak ditemukan",
                }.get(r["status"], r["status"])
                st.caption(f"{r['change_id'] or '?'} — {r['path'] or '(tanpa path)'}: {label}")

        with st.expander("Data hasil scan (mentah)"):
            st.json(st.session_state.impact_records)

    st.markdown("---")
    st.markdown("##### Artefak untuk IBM Bob (MCP)")
    st.caption(f"MCP server lokal: `{MCP_ADMIN_URL}` · artefak: `artifacts/` · registrasi: `.bob/mcp.json`")

    if st.button("Siapkan & Kirim Analisis ke Bob", type="primary", disabled=not (st.session_state.impact_scanned and license_state["can_run"])):
        with st.spinner("Membangun artefak & handoff ke server MCP lokal..."):
            findings, _ = _source_findings()
            summary = artifacts.build_artifacts(findings, MOCK_REPO_DIR, ARTIFACTS_DIR)
            st.session_state.artifacts_built = True
            st.session_state.artifacts_summary = summary
            try:
                res = requests.post(f"{MCP_ADMIN_URL}/handoff", json={"source": st.session_state.analysis_source}, timeout=5)
                if res.status_code == 200:
                    st.success("Artefak diterima server MCP lokal — buka IBM Bob dan minta tool SELISIH di IDE.")
                else:
                    st.warning(f"Server MCP merespon {res.status_code}; artefak tetap dibuat lokal di artifacts/.")
            except requests.RequestException:
                st.warning("Server Bob/MCP lokal tidak aktif. Artefak tetap dibuat di `artifacts/` (jalankan `python mcp_server.py`).")
            st.info(f"Patch siap: {summary['patchable']} dari {summary['kandidat_kode']} kandidat · file: {', '.join(summary['files'].values())}")

    if st.session_state.artifacts_built and os.path.isdir(ARTIFACTS_DIR):
        diff_file = os.path.join(ARTIFACTS_DIR, "proposed_patch.diff")
        tests_file = os.path.join(ARTIFACTS_DIR, "generated_tests.py")
        report_file = os.path.join(ARTIFACTS_DIR, "impact_report.json")
        if os.path.exists(diff_file):
            st.markdown("###### artifacts/proposed_patch.diff")
            st.code(open(diff_file, encoding="utf-8").read(), language="diff")
        if os.path.exists(tests_file):
            st.markdown("###### artifacts/generated_tests.py")
            st.code(open(tests_file, encoding="utf-8").read(), language="python")
        with st.expander("artifacts/impact_report.json"):
            if os.path.exists(report_file):
                with open(report_file, encoding="utf-8") as f:
                    st.json(json.load(f))

# -------------------------------------------------------------------------
# TAB 3: TATA KELOLA & TINJAUAN MANUSIA
# -------------------------------------------------------------------------
with tab3:
    st.markdown("#### Tata Kelola & Otoritas Keputusan (Human-in-the-Loop)")
    st.markdown("Sesuai standar enterprise perbankan, sistem AI tidak memiliki kewenangan otomatis untuk menerapkan kode ke lingkungan produksi tanpa verifikasi manusia.")

    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        st.markdown("<div class='card-title'>Metadata Jejak Audit (Audit Trail)</div>", unsafe_allow_html=True)
        if st.session_state.impact_scanned:
            ids = ", ".join({r["change_id"] for r in st.session_state.impact_records if r.get("change_id")}) or "—"
        else:
            ids = "Belum dipindai"
        patch_state = "Draft Diterapkan (dengan backup)" if st.session_state.patch_applied else "Menunggu Persetujuan"
        st.table({
            "Atribut": ["ID Analisis", "Regulasi Acuan", "Status Draf", "Otoritas Peninjau", "Prinsip Eksekusi"],
            "Detail": [ids, "OJK No 22/2023", patch_state, "Tech Lead / Compliance Officer", "Dry-Run + Backup (Tanpa Auto-Deploy)"]
        })
        
    with col_g2:
        st.markdown("<div class='card-title'>Tindakan Peninjau</div>", unsafe_allow_html=True)

        if st.button("Pratinjau Patch (Dry-Run)", disabled=not (st.session_state.impact_scanned and license_state["can_run"]), use_container_width=True):
            st.session_state.dry_run_report = impact.apply_patch(st.session_state.impact_records, dry_run=True)

        if st.session_state.dry_run_report:
            dry = st.session_state.dry_run_report
            ready = [d for d in dry if d["status"] == "dry_run_ok"]
            st.caption(f"Dry-run: {len(ready)} draf siap ditulis; {len(dry) - len(ready)} dilewati.")
            for d in dry:
                st.caption(f"• {d['path']}: {d['message']}")

        confirmed = st.checkbox(
            "Saya paham: patch menulis file lokal dan backup otomatis dibuat (.bak.<stamp>).",
            disabled=not (st.session_state.impact_scanned and license_state["can_run"]),
        )

        if st.button(
            "Setujui & Terapkan Patch",
            type="primary",
            disabled=not (confirmed and st.session_state.impact_scanned and license_state["can_run"]),
            use_container_width=True,
        ):
            report = impact.apply_patch(st.session_state.impact_records, dry_run=False)
            st.session_state.patch_report = report
            applied_count = sum(1 for r in report if r["status"] == "applied")
            if applied_count:
                st.session_state.patch_applied = True
                st.success(f"Patch diterapkan ke {applied_count} file. Backup dibuat otomatis.")
            else:
                st.warning("Tidak ada patch yang diterapkan (semua dilewati / sudah sesuai).")

        if st.session_state.patch_report:
            for r in st.session_state.patch_report:
                trail = f" (backup: {os.path.basename(r['backup_path'])})" if r["backup_path"] else ""
                st.caption(f"• {r['path']} — {r['status']}: {r['message']}{trail}")

        if st.session_state.patch_applied:
            st.caption("Status Repositori: Telah Disesuaikan dengan POJK 22/2023 (cek backup sebelum commit).")

        if st.button("Jalankan Pengujian Unit Test Lokal", use_container_width=True):
            with st.spinner("Menjalankan pytest pada repositori mock..."):
                st.session_state.test_output = impact.run_pytest(MOCK_REPO_DIR, "tests")
        
        if st.button("Tolak Usulan & Catat Masukan", use_container_width=True):
            st.session_state.impact_scanned = False
            st.session_state.impact_records = []
            st.session_state.dry_run_report = None
            st.session_state.patch_report = None
            st.info("Usulan patch ditolak. Catatan dikembalikan ke tahap penelaahan hukum.")

    if st.session_state.test_output:
        st.markdown("##### Luaran Eksekusi Unit Test")
        res = st.session_state.test_output
        st.caption(res["cmd"])
        output = (res.get("stdout") or "") if res.get("returncode") == 0 else (res.get("stderr") or "")
        st.code(output, language="text")

# Footer Minimalis
st.markdown("---")
st.caption("SELISIH — Regulatory Change & Code Impact System | IBM Hackathon x Hacktiv8 2026")
