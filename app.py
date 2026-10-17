import sys

# Segarkan cache modul selisih agar proses Streamlit selalu memuat versi terbaru dari disk
for _mod in list(sys.modules.keys()):
    if _mod.startswith("selisih"):
        del sys.modules[_mod]

import streamlit as st
import json
import os
import requests
from selisih import artifacts, auth, impact
from selisih.config import get_langflow_config
from selisih.documents import DocumentLoadError, load_document_text
from selisih.langflow import run_analysis, run_embedded_analysis, LangflowError
from selisih.license import get_license_state

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="SELISIH — Regulatory Change & Code Impact System",
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
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "patch_reviewer" not in st.session_state:
    st.session_state.patch_reviewer = None
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
if "ide_launch_result" not in st.session_state:
    st.session_state.ide_launch_result = None
if "bob_agent_result" not in st.session_state:
    st.session_state.bob_agent_result = None



def _source_findings():
    if st.session_state.analysis_source == "live" and st.session_state.live_findings:
        return {"analysis_meta": {}, "findings": st.session_state.live_findings}, "session live"
    return impact.load_findings(LIVE_RESULT_FILE, GOLDEN_PATH_FILE)


def _load_text(path):
    return load_document_text(path)


def _save_live_result(findings, input_path, engine="Langflow (Embedded Execution)"):
    import hashlib
    from datetime import datetime, timezone

    digest = hashlib.sha256()
    with open(input_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    payload = {
        "analysis_meta": {
            "engine": engine,
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
    if not cfg.get("flow_id"):
        return {"status": "embedded", "msg": "Mode Embedded aktif"}
    try:
        res = requests.get(f"{cfg['api_url']}/health", timeout=2)
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
    
    p, span, li, label, div[data-testid="stMarkdownContainer"]:not(button *):not(.stButton *) p {
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

    /* Primary and Secondary Buttons - High Contrast Enterprise Theme */
    .stButton>button {
        border-radius: 5px;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px 18px;
        transition: all 0.15s ease-in-out;
    }
    
    /* Primary Button: Solid dark background with pure white text */
    .stButton>button[kind="primary"],
    .stButton>button[data-testid*="primary"],
    button[data-testid="baseButton-primary"],
    button[data-testid="stBaseButton-primary"] {
        background-color: #1A1917 !important;
        color: #FFFFFF !important;
        border: 1px solid #1A1917 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
    
    /* Primary Button Text Elements - High Specificity */
    .stButton>button[kind="primary"] p,
    .stButton>button[kind="primary"] span,
    .stButton>button[kind="primary"] div,
    .stButton>button[kind="primary"] div[data-testid="stMarkdownContainer"] p,
    .stButton>button[data-testid*="primary"] p,
    .stButton>button[data-testid*="primary"] span,
    .stButton>button[data-testid*="primary"] div,
    .stButton>button[data-testid*="primary"] div[data-testid="stMarkdownContainer"] p,
    button[data-testid="baseButton-primary"] p,
    button[data-testid="baseButton-primary"] span,
    button[data-testid="baseButton-primary"] div,
    button[data-testid="baseButton-primary"] div[data-testid="stMarkdownContainer"] p,
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-primary"] span,
    button[data-testid="stBaseButton-primary"] div,
    button[data-testid="stBaseButton-primary"] div[data-testid="stMarkdownContainer"] p,
    .stButton>button[kind="primary"] *,
    .stButton>button[data-testid*="primary"] *,
    button[data-testid="baseButton-primary"] *,
    button[data-testid="stBaseButton-primary"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }
    .stButton>button[kind="primary"]:hover,
    .stButton>button[data-testid*="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #2D2C28 !important;
        border-color: #2D2C28 !important;
        color: #FFFFFF !important;
    }
    .stButton>button[kind="primary"]:hover *,
    .stButton>button[data-testid*="primary"]:hover *,
    button[data-testid="baseButton-primary"]:hover *,
    button[data-testid="stBaseButton-primary"]:hover * {
        color: #FFFFFF !important;
    }

    /* Secondary Button: Clean white background with high contrast dark text */
    .stButton>button[kind="secondary"],
    .stButton>button[data-testid*="secondary"],
    button[data-testid="baseButton-secondary"],
    button[data-testid="stBaseButton-secondary"] {
        background-color: #FFFFFF !important;
        color: #1A1917 !important;
        border: 1px solid #C8C2B5 !important;
    }
    .stButton>button[kind="secondary"] *,
    .stButton>button[data-testid*="secondary"] *,
    button[data-testid="baseButton-secondary"] *,
    button[data-testid="stBaseButton-secondary"] * {
        color: #1A1917 !important;
        font-weight: 600 !important;
    }
    .stButton>button[kind="secondary"]:hover,
    .stButton>button[data-testid*="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #F8F7F4 !important;
        border-color: #1A1917 !important;
        color: #111110 !important;
    }
    .stButton>button[kind="secondary"]:hover *,
    .stButton>button[data-testid*="secondary"]:hover *,
    button[data-testid="baseButton-secondary"]:hover *,
    button[data-testid="stBaseButton-secondary"]:hover * {
        color: #111110 !important;
    }

    /* Disabled State */
    .stButton>button:disabled,
    button[data-testid*="primary"]:disabled,
    button[data-testid*="secondary"]:disabled {
        background-color: #EFECE6 !important;
        border-color: #DDD8CD !important;
        color: #8C887B !important;
        cursor: not-allowed !important;
        opacity: 0.7 !important;
    }
    .stButton>button:disabled *,
    button[data-testid*="primary"]:disabled *,
    button[data-testid="baseButton-secondary"]:disabled * {
        color: #8C887B !important;
    }
</style>
""", unsafe_allow_html=True)

def _render_login_screen():
    st.markdown("""
    <div class="app-header" style="text-align: center; margin-top: 24px; padding-bottom: 24px;">
        <div class="app-title" style="font-size: 32px;">SELISIH</div>
        <div class="app-subtitle" style="font-size: 15px; margin-top: 6px;">
            Regulatory Change & Code Impact System — Control Plane Kepatuhan & Rekayasa
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="max-width: 820px; margin: 0 auto 24px auto; text-align: center;">
        <p style="color: #4A4843; font-size: 14px; line-height: 1.6;">
            Sistem tata kelola kepatuhan regulasi finansial dengan prinsip <strong>Responsible AI</strong> dan 
            <strong>Segregation of Duties</strong>. Silakan pilih peran pengguna untuk akses cepat atau masukkan kredensial internal.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_demo, col_form = st.columns([3, 2], gap="large")

    with col_demo:
        st.markdown("<div class='card-title'>Akses Cepat per Peran</div>", unsafe_allow_html=True)
        st.caption("Pilih peran untuk masuk ke sistem sesuai fungsi tanggung jawab:")

        personas = auth.get_personas()

        # Peran 1: Administrator
        p_admin = personas.get("admin") or personas.get("auditor") or {
            "name": "Administrator",
            "title": "System & Compliance Administrator",
            "role_label": "Administrator",
            "description": "Akses menyeluruh ke analisis regulasi, pemetaan dampak kode, dan otorisasi patch."
        }
        st.markdown(f"""
        <div class="clean-card" style="margin-bottom: 12px; padding: 14px 18px;">
            <div>
                <strong>{p_admin.get('name', 'Administrator')}</strong><br/>
                <span style="font-size: 12px; color: #6E6B64;">{p_admin.get('title', '')} · <span class="tag tag-success">{p_admin.get('role_label', 'Administrator')}</span></span>
            </div>
            <p style="font-size: 13px; margin-top: 8px; margin-bottom: 0; color: #3C3A35;">
                {p_admin.get('description', '')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Masuk sebagai Administrator", key="btn_quick_admin", type="primary", use_container_width=True):
            auth.quick_login("admin", st.session_state)
            st.rerun()

        # Peran 2: Software Engineer
        p_eng = personas.get("engineer") or {
            "name": "Software Engineer",
            "title": "Lead Software Engineer",
            "role_label": "Software Engineer",
            "description": "Meninjau dampak perubahan kode pada repositori, menjalankan dry-run, dan menerapkan patch."
        }
        st.markdown(f"""
        <div class="clean-card" style="margin-bottom: 12px; padding: 14px 18px;">
            <div>
                <strong>{p_eng.get('name', 'Software Engineer')}</strong><br/>
                <span style="font-size: 12px; color: #6E6B64;">{p_eng.get('title', '')} · <span class="tag">{p_eng.get('role_label', 'Software Engineer')}</span></span>
            </div>
            <p style="font-size: 13px; margin-top: 8px; margin-bottom: 0; color: #3C3A35;">
                {p_eng.get('description', '')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Masuk sebagai Software Engineer", key="btn_quick_eng", use_container_width=True):
            auth.quick_login("engineer", st.session_state)
            st.rerun()

        # Peran 3: Compliance Officer
        p_comp = personas.get("compliance") or personas.get("legal") or {
            "name": "Compliance Officer",
            "title": "Regulatory Compliance Reviewer",
            "role_label": "Compliance Officer",
            "description": "Menganalisis klausul regulasi baru OJK, menelaah perubahan, dan memverifikasi kepatuhan."
        }
        st.markdown(f"""
        <div class="clean-card" style="margin-bottom: 12px; padding: 14px 18px;">
            <div>
                <strong>{p_comp.get('name', 'Compliance Officer')}</strong><br/>
                <span style="font-size: 12px; color: #6E6B64;">{p_comp.get('title', '')} · <span class="tag" style="background-color: #E8EEF5; color: #2B579A; border-color: #A4B8D1;">{p_comp.get('role_label', 'Compliance Officer')}</span></span>
            </div>
            <p style="font-size: 13px; margin-top: 8px; margin-bottom: 0; color: #3C3A35;">
                {p_comp.get('description', '')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Masuk sebagai Compliance Officer", key="btn_quick_comp", use_container_width=True):
            auth.quick_login("compliance", st.session_state)
            st.rerun()

    with col_form:
        st.markdown("<div class='card-title'>Kredensial Organisasi</div>", unsafe_allow_html=True)
        st.caption("Masuk menggunakan akun korporat internal:")
        with st.form("form_login"):
            username_input = st.text_input("Nama Pengguna (Username)", placeholder="admin / engineer / compliance")
            password_input = st.text_input("Kata Sandi (Password)", type="password", value="admin123")
            submit_login = st.form_submit_button("Masuk ke Dashboard", use_container_width=True)
            if submit_login:
                user = auth.authenticate(username_input, password_input)
                if user:
                    auth.login(user, st.session_state)
                    st.rerun()
                else:
                    st.error("Kredensial tidak valid. Silakan gunakan tombol peran cepat atau periksa username.")
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        st.caption("Organisasi Terdaftar: **PT Bank Digital Nusantara**")
        st.caption("Standar Kepatuhan: OJK POJK 77/2016 & POJK 22/2023")


langflow_health = _langflow_health()
license_state = get_license_state(st.secrets)

if not getattr(st.session_state, "authenticated", False):
    _render_login_screen()
    st.stop()

current_user = auth.get_current_user(st.session_state) or {}

# ==========================================
# SIDEBAR: STATUS & KONTROL SISTEM
# ==========================================
with st.sidebar:
    st.markdown(f"### {current_user.get('name', 'User')}")
    st.caption(f"{current_user.get('title', '')}")
    st.markdown(f"<span class='tag' style='font-weight: 600;'>{current_user.get('role_label', '')}</span>", unsafe_allow_html=True)
    if st.button("Keluar / Ganti Akun", key="btn_logout_sidebar", use_container_width=True):
        auth.logout(st.session_state)
        st.rerun()

    st.markdown("---")
    st.markdown("### SELISIH")
    st.caption("Control Plane Kepatuhan & Rekayasa")
    
    st.markdown("---")
    st.markdown("<div class='card-title'>Integrasi Komponen</div>", unsafe_allow_html=True)
    _hb = langflow_health
    _status_langflow = {
        "ok": "Terhubung",
        "embedded": "Terhubung",
        "down": "Terputus",
        "not_configured": "Belum dikonfigurasi",
    }.get(_hb.get("status"), "Terputus")
    st.markdown(f"• **Langflow:** {_status_langflow}")

    _bob = _mcp_health()
    _status_bob = "Terhubung" if _bob.get("status") == "ok" else "Terputus"
    st.markdown(f"• **IBM Bob (MCP):** {_status_bob}")

    
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
st.markdown(f"""
<div class="app-header">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <div class="app-title">SELISIH</div>
            <div class="app-subtitle">Regulatory Change & Code Impact System — IBM Hackathon IT-Finance</div>
        </div>
        <div style="text-align: right;">
            <span style="font-size: 13px; font-weight: 600; color: #111110;">{current_user.get('name', '')}</span><br/>
            <span class="tag" style="margin-top: 4px;">{current_user.get('role_label', '')}</span>
        </div>
    </div>
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
        with st.spinner("Menjalankan analisis regulasi via Embedded Langflow Engine..."):
            try:
                input_path = os.path.join(DATA_DIR, "pojk_baru_22_2023.txt")
                cfg = get_langflow_config()
                if cfg.get("flow_id") and cfg.get("mode") == "rest":
                    findings = run_analysis(_load_text(input_path), cfg)
                    engine_desc = "Langflow (live REST)"
                else:
                    findings = run_embedded_analysis(_load_text(input_path))
                    engine_desc = "Langflow (Embedded Execution)"


                if not findings:
                    raise LangflowError("Tidak ada findings yang dapat dinormalkan.")
                st.session_state.diff_analyzed = True
                st.session_state.analysis_source = "live"
                st.session_state.live_findings = findings
                st.success(f"Berhasil menganalisis {len(findings)} temuan regulasi ({engine_desc}).")
                _save_live_result(findings, input_path, engine=engine_desc)
            except (LangflowError, DocumentLoadError) as err:
                st.session_state.diff_analyzed = False
                st.session_state.analysis_source = "live"
                st.session_state.live_findings = []
                st.error(f"Analisis Langflow gagal: {err}")

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

    # Otomatis muat pemetaan dampak awal agar Tab 2 dan Tab 3 langsung siap diakses
    if not st.session_state.impact_scanned:
        findings, src = _source_findings()
        if findings and findings.get("findings"):
            st.session_state.impact_records = impact.scan_impact(findings, MOCK_REPO_DIR)
            st.session_state.impact_scanned = True

    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        st.text_input("Target Repositori Terdaftar:", value="mock_fintech_repo (FintechCore Banking Service)", disabled=True)
    with col_r2:
        st.write("")
        st.write("")
        scan_btn = st.button("Pindai Ulang Dampak", type="primary", disabled=not license_state["can_run"])

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
    st.markdown("##### Integrasi IBM Bob (Bob Shell & Desktop)")
    st.caption(f"Repositori Target: `{MOCK_REPO_DIR}` · MCP: `{MCP_ADMIN_URL}` · Artefak: `artifacts/`")

    bob_status = artifacts.check_bob_status()
    tag_color = "success" if bob_status["session_active"] else ("warning" if bob_status["installed"] else "info")
    st.markdown(f"""
    <div class="clean-card" style="margin-bottom: 14px; padding: 12px 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>Status Lingkungan IBM Bob:</strong> {bob_status['status_label']}
                <br><span style="font-size: 12px; color: #6E6B64;">Path Binary: <code>{bob_status['path'] or 'Belum terdeteksi di direktori standar'}</code></span>
            </div>
            <span class="tag tag-{tag_color}">Bob V2 Ready</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        run_agent_btn = st.button(
            "Jalankan Agen IBM Bob di Dashboard",
            type="primary",
            disabled=not (st.session_state.impact_scanned and license_state["can_run"]),
            use_container_width=True,
            help="Eksekusi Bob Shell di latar belakang dan tampilkan hasil penalaran agen langsung di web.",
        )
    with col_btn2:
        launch_bob_btn = st.button(
            "Buka di IBM Bob Desktop",
            disabled=not (st.session_state.impact_scanned and license_state["can_run"]),
            use_container_width=True,
            help="Luncurkan aplikasi desktop IBM Bob dengan repositori target dan konfigurasi MCP yang sudah terpasang.",
        )

    if run_agent_btn:
        with st.spinner("Memasang konfigurasi MCP, membangun artefak, dan menjalankan agen IBM Bob (Bob Shell)..."):
            server_script = os.path.join(BASE_DIR, "mcp_server.py")
            # 1. Pastikan server MCP lokal aktif
            artifacts.ensure_mcp_server_running(server_script)

            # 2. Pasang konfigurasi MCP (.bob/mcp.json) di repositori target
            mcp_paths = artifacts.ensure_mcp_config(MOCK_REPO_DIR, server_script)

            # 3. Bangun artefak
            findings, _ = _source_findings()
            summary = artifacts.build_artifacts(findings, MOCK_REPO_DIR, ARTIFACTS_DIR)
            st.session_state.artifacts_built = True
            st.session_state.artifacts_summary = summary

            # 4. Kirim sinyal handoff ke server MCP lokal
            handoff_ok = False
            try:
                res = requests.post(f"{MCP_ADMIN_URL}/handoff", json={"source": st.session_state.analysis_source}, timeout=1.5)
                if res.status_code == 200:
                    handoff_ok = True
            except requests.RequestException:
                handoff_ok = False

            # 5. Jalankan orkestrasi agen Bob Shell di latar belakang
            agent_res = artifacts.run_bob_shell_agent(MOCK_REPO_DIR, findings, ARTIFACTS_DIR)
            st.session_state.bob_agent_result = agent_res

            st.success("Analisis agen IBM Bob selesai dieksekusi via Bob Shell.")
            if handoff_ok:
                st.caption("Server MCP lokal aktif menerima handoff. Asisten Bob siap menggunakan tool SELISIH.")
            else:
                st.caption(f"Konfigurasi MCP tersimpan di {mcp_paths['bob']}.")
            st.info(f"Patch siap: {summary['patchable']} dari {summary['kandidat_kode']} kandidat · file: {', '.join(summary['files'].values())}")

    if launch_bob_btn:
        with st.spinner("Menyiapkan MCP dan meluncurkan IBM Bob Desktop..."):
            server_script = os.path.join(BASE_DIR, "mcp_server.py")
            artifacts.ensure_mcp_server_running(server_script)
            mcp_paths = artifacts.ensure_mcp_config(MOCK_REPO_DIR, server_script)
            findings, _ = _source_findings()
            summary = artifacts.build_artifacts(findings, MOCK_REPO_DIR, ARTIFACTS_DIR)
            st.session_state.artifacts_built = True
            st.session_state.artifacts_summary = summary

            launch_res = artifacts.launch_ide(MOCK_REPO_DIR)
            st.session_state.ide_launch_result = launch_res
            if launch_res.get("status") == "launched":
                st.success(launch_res.get("message"))
            else:
                st.info(launch_res.get("message"))

    if st.session_state.bob_agent_result:
        ag = st.session_state.bob_agent_result
        st.markdown(f"""
        <div class="clean-card" style="margin-top: 14px; margin-bottom: 14px; border-left: 4px solid #0F5C2B;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 15px;">Penalaran Agen IBM Bob ({ag.get('engine', 'Bob Shell')})</strong>
                <span class="tag tag-success">Model: {ag.get('model', 'watsonx / Granite')}</span>
            </div>
            <div class="card-body" style="font-size: 13px; line-height: 1.6;">
                <strong>Instruksi Agen:</strong> <em>{ag.get('prompt', '')}</em>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("###### Tahapan Otonom Agen IBM Bob:")
        for step in ag.get("reasoning_steps", []):
            st.markdown(f"""
            <div style="padding: 10px 14px; margin-bottom: 6px; background-color: #F8F7F4; border-left: 3px solid #1A1917; border-radius: 4px;">
                <strong>Langkah {step['step']}: {step['title']}</strong><br/>
                <span style="font-size: 13px; color: #4A4843;">{step['detail']}</span>
            </div>
            """, unsafe_allow_html=True)

    if st.session_state.ide_launch_result:
        res = st.session_state.ide_launch_result
        st.markdown(f"""
        <div class="clean-card" style="margin-top: 10px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong>Status IBM Bob Desktop</strong>
                <span class="tag tag-{'success' if res.get('status') == 'launched' else 'warning'}">{res.get('app', 'IBM Bob')}</span>
            </div>
            <div class="card-body">
                Target: <code>{res.get('target', MOCK_REPO_DIR)}</code><br>
                {res.get('message', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)


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

    # Pastikan data dampak terinisialisasi bila pengguna langsung membuka Tab 3
    if not st.session_state.impact_scanned:
        findings, src = _source_findings()
        if findings and findings.get("findings"):
            st.session_state.impact_records = impact.scan_impact(findings, MOCK_REPO_DIR)
            st.session_state.impact_scanned = True

    reviewer_name = current_user.get("name", "Reviewer Kepatuhan")
    reviewer_role = current_user.get("role_label", "Reviewer")
    reviewer_title = current_user.get("title", "")
    reviewer_badge = f"{reviewer_name} ({reviewer_role})"

    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        st.markdown("<div class='card-title'>Metadata Jejak Audit (Audit Trail)</div>", unsafe_allow_html=True)
        if st.session_state.impact_scanned:
            ids = ", ".join({r["change_id"] for r in st.session_state.impact_records if r.get("change_id")}) or "—"
        else:
            ids = "Belum dipindai"
        patch_state = "Draft Diterapkan (dengan backup)" if st.session_state.patch_applied else "Menunggu Persetujuan"
        st.table({
            "Atribut": ["ID Analisis", "Regulasi Acuan", "Status Draf", "Peninjau Aktif", "Wewenang Eksekusi", "Prinsip Tata Kelola"],
            "Detail": [ids, "OJK No 22/2023", patch_state, reviewer_badge, "Otorisasi Disetujui", "Dry-Run + Backup (Tanpa Auto-Deploy)"]
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
                st.session_state.patch_reviewer = f"{reviewer_name} ({reviewer_title})"
                st.success(f"Patch diterapkan ke {applied_count} file oleh {reviewer_name}. Backup dibuat otomatis.")
            else:
                st.warning("Tidak ada patch yang diterapkan (semua dilewati / sudah sesuai).")

        if st.session_state.patch_report:
            for r in st.session_state.patch_report:
                trail = f" (backup: {os.path.basename(r['backup_path'])})" if r["backup_path"] else ""
                st.caption(f"• {r['path']} — {r['status']}: {r['message']}{trail}")

        if st.session_state.patch_applied:
            rev_label = f" oleh {st.session_state.patch_reviewer}" if st.session_state.patch_reviewer else ""
            st.caption(f"Status Repositori: Telah Disesuaikan dengan POJK 22/2023{rev_label} (cek backup sebelum commit).")

        if st.button("Jalankan Pengujian Unit Test Lokal", use_container_width=True):
            with st.spinner("Menjalankan pytest pada repositori mock..."):
                st.session_state.test_output = impact.run_pytest(MOCK_REPO_DIR, "tests")
        
        if st.button("Tolak Usulan & Catat Masukan", use_container_width=True):
            st.session_state.impact_scanned = False
            st.session_state.impact_records = []
            st.session_state.dry_run_report = None
            st.session_state.patch_report = None
            st.info(f"Usulan patch ditolak oleh {reviewer_name}. Catatan dikembalikan ke tahap penelaahan hukum.")

    if st.session_state.test_output:
        st.markdown("##### Luaran Eksekusi Unit Test")
        res = st.session_state.test_output
        st.caption(res["cmd"])
        output = (res.get("stdout") or "") if res.get("returncode") == 0 else (res.get("stderr") or "")
        st.code(output, language="text")

# Footer Minimalis
st.markdown("---")
st.caption("SELISIH — Regulatory Change & Code Impact System | IBM Hackathon x Hacktiv8 2026")
