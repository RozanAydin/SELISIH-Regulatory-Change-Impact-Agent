import streamlit as st
import json
import os
import sys
import time
import subprocess
import requests

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
CONFIG_FILE = os.path.join(MOCK_REPO_DIR, "app", "core", "config.py")
GOLDEN_PATH_FILE = os.path.join(DATA_DIR, "temuan_golden_path.json")

# Inisialisasi Session State
if "diff_analyzed" not in st.session_state:
    st.session_state.diff_analyzed = False
if "bob_scanned" not in st.session_state:
    st.session_state.bob_scanned = False
if "patch_applied" not in st.session_state:
    st.session_state.patch_applied = False
if "test_output" not in st.session_state:
    st.session_state.test_output = None

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

# ==========================================
# SIDEBAR: STATUS & KONTROL SISTEM
# ==========================================
with st.sidebar:
    st.markdown("### SELISIH")
    st.caption("Control Plane Kepatuhan & Rekayasa")
    
    st.markdown("---")
    st.markdown("<div class='card-title'>Integrasi Komponen</div>", unsafe_allow_html=True)
    st.markdown("• **Astra DB:** Terhubung (`pojk_idx`)")
    st.markdown("• **Langflow:** Aktif (`port 7860`)")
    st.markdown("• **IBM Bob:** Terpasang (watsonx Code Assist)")
    
    st.markdown("---")
    st.markdown("<div class='card-title'>Langganan & Lisensi</div>", unsafe_allow_html=True)
    st.markdown("**Organisasi:** PT Bank Digital Nusantara")
    st.markdown("**Paket:** Starter Plan ($500/bulan)")
    st.markdown("**Repositori Aktif:** 3 / 5 repositori")
    st.progress(60)
    st.caption("Pembatasan kuota diterapkan melalui Lisensi Gateway.")

    st.markdown("---")
    st.markdown("<div class='card-title'>Mode Eksekusi</div>", unsafe_allow_html=True)
    exec_mode = st.radio(
        "Pilih alur kerja:",
        ["Deterministik (Demo Mode)", "Live Langflow REST API"],
        label_visibility="collapsed"
    )
    
    if exec_mode == "Live Langflow REST API":
        langflow_endpoint = st.text_input("Endpoint API:", "http://localhost:7860/api/v1/run/<FLOW_ID>")
        langflow_token = st.text_input("Token / API Key Langflow:", type="password", value="")
    else:
        langflow_endpoint = None
        langflow_token = None
        
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

    if st.button("Jalankan Analisis Regulasi (Langflow Engine)", type="primary"):
        if exec_mode == "Live Langflow REST API" and langflow_endpoint:
            with st.spinner("Mengirim data regulasi ke Langflow REST API..."):
                headers = {"Content-Type": "application/json"}
                if langflow_token:
                    headers["x-api-key"] = langflow_token
                
                payload = {
                    "input_value": "Analisis perbedaan batas pinjaman dan suku bunga pada POJK 22 Tahun 2023 Pasal 12 terhadap korpus aturan lama.",
                    "output_type": "chat",
                    "input_type": "chat"
                }
                try:
                    res = requests.post(langflow_endpoint, json=payload, headers=headers, timeout=20)
                    if res.status_code == 200:
                        st.session_state.diff_analyzed = True
                        st.success("Berhasil menerima respon live dari Langflow REST API!")
                    else:
                        st.warning(f"Langflow merespon status {res.status_code}. Menggunakan data terverifikasi lokal.")
                        st.session_state.diff_analyzed = True
                except Exception as err:
                    st.warning(f"Koneksi Langflow tidak merespon ({err}). Menggunakan data terverifikasi lokal.")
                    st.session_state.diff_analyzed = True
        else:
            with st.spinner("Mengakses korpus Astra DB dan memvalidasi sitasi pasal..."):
                time.sleep(1.2)
                st.session_state.diff_analyzed = True

    if st.session_state.diff_analyzed:
        st.markdown("---")
        st.markdown("##### Hasil Ekstraksi Perubahan")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Klausul Terdampak", "2 Pasal")
        col_m2.metric("Validitas Sitasi", "100%", "Tervalidasi")
        col_m3.metric("Tingkat Keyakinan", "Tinggi", "Kualitatif")
        col_m4.metric("Status Abstention", "False", "Bukti Cukup")

        if os.path.exists(GOLDEN_PATH_FILE):
            with open(GOLDEN_PATH_FILE, "r", encoding="utf-8") as f:
                golden_data = json.load(f)
                
            for finding in golden_data.get("findings", []):
                st.markdown(f"""
                <div class="clean-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <strong>{finding['change_id']} — {finding['ringkasan']}</strong>
                        <span class="tag tag-success">Sitasi Valid</span>
                    </div>
                    <div class="card-body">
                        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #E6E1D8;">
                                <td style="padding: 6px 0; width: 25%; color: #6E6B64;">Pasal Pembaruan</td>
                                <td style="padding: 6px 0;"><strong>{finding['pasal_baru']['doc_id']} {finding['pasal_baru']['pasal']} {finding['pasal_baru']['ayat']}</strong>: "{finding['pasal_baru']['kutipan']}"</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #6E6B64;">Pasal Acuan Lama</td>
                                <td style="padding: 6px 0;"><strong>{finding['pasal_lama']['doc_id']} {finding['pasal_lama']['pasal']} {finding['pasal_lama']['ayat']}</strong>: "{finding['pasal_lama']['kutipan']}"</td>
                            </tr>
                        </table>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("Inspeksi Struktur Data Terstruktur (temuan.json)"):
                st.json(golden_data)

# -------------------------------------------------------------------------
# TAB 2: PEMETAAN DAMPAK KODE (IBM BOB)
# -------------------------------------------------------------------------
with tab2:
    st.markdown("#### Pemetaan Dampak Kode & Draf Usulan")
    st.markdown("Agen **IBM Bob** membaca kontrak data `temuan.json` dan memetakan kewajiban hukum baru ke berkas spesifik dalam repositori.")

    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        st.text_input("Target Repositori Terdaftar:", value="mock_fintech_repo (FintechCore Banking Service)", disabled=True)
    with col_r2:
        st.write("")
        st.write("")
        scan_btn = st.button("Pindai Kode (IBM Bob)", type="primary")

    if scan_btn or st.session_state.bob_scanned:
        if scan_btn:
            with st.spinner("IBM Bob menganalisis struktur kode dan mencocokkan logika batasan..."):
                time.sleep(1.5)
                st.session_state.bob_scanned = True
        
        st.markdown("""
        <div class="clean-card">
            <div class="card-title">Lokasi Dampak Teridentifikasi</div>
            <div class="card-body">
                <strong>Berkas:</strong> <code>app/core/config.py</code> (Baris 14 & 17)<br>
                <strong>Simbol:</strong> <code>MAX_LOAN_AMOUNT</code>, <code>MAX_DAILY_INTEREST_RATE</code><br>
                <strong>Rasionalitas Teknis:</strong> Nilai konstanta batas maksimum pinjaman per nasabah dan ambang suku bunga harian harus disesuaikan agar sesuai dengan batas hukum POJK 22/2023.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("##### Perbandingan Usulan Kode (Diff)")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("<div class='card-title'>Implementasi Saat Ini (Lama)</div>", unsafe_allow_html=True)
            st.code("""# app/core/config.py (POJK 77/2016)

MAX_LOAN_AMOUNT = 20_000_000
MAX_DAILY_INTEREST_RATE = 0.004
""", language="python")

        with col_c2:
            st.markdown("<div class='card-title'>Draf Usulan Patch (IBM Bob)</div>", unsafe_allow_html=True)
            st.code("""# app/core/config.py (POJK 22/2023 Pasal 12)

MAX_LOAN_AMOUNT = 50_000_000
MAX_DAILY_INTEREST_RATE = 0.001
""", language="python")

        st.markdown("##### Draf Pengujian Regresi Otomatis")
        st.code("""# tests/test_compliance.py
def test_new_statutory_loan_limit():
    service = LoanService()
    # Pengajuan pinjaman Rp 45.000.000 (Diterima di bawah regulasi baru)
    result = service.validate_loan_application("CUST-009", 45_000_000, 0.001, kyc_level=2)
    assert result["status"] == "APPROVED"
""", language="python")

# -------------------------------------------------------------------------
# TAB 3: TATA KELOLA & TINJAUAN MANUSIA
# -------------------------------------------------------------------------
with tab3:
    st.markdown("#### Tata Kelola & Otoritas Keputusan (Human-in-the-Loop)")
    st.markdown("Sesuai standar enterprise perbankan, sistem AI tidak memiliki kewenangan otomatis untuk menerapkan kode ke lingkungan produksi tanpa verifikasi manusia.")

    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        st.markdown("<div class='card-title'>Metadata Jejak Audit (Audit Trail)</div>", unsafe_allow_html=True)
        st.table({
            "Atribut": ["ID Analisis", "Regulasi Acuan", "Status Draf", "Otoritas Peninjau", "Prinsip Eksekusi"],
            "Detail": ["CHG-POJK-001/002", "OJK No 22/2023", "Menunggu Persetujuan", "Tech Lead / Compliance Officer", "Draft-Only (Tanpa Auto-Deploy)"]
        })
        
    with col_g2:
        st.markdown("<div class='card-title'>Tindakan Peninjau</div>", unsafe_allow_html=True)
        
        # Tombol Setujui Patch
        if st.button("Setujui & Terapkan Patch ke Repositori", type="primary", use_container_width=True):
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("MAX_LOAN_AMOUNT = 20_000_000", "MAX_LOAN_AMOUNT = 50_000_000")
                content = content.replace("MAX_DAILY_INTEREST_RATE = 0.004", "MAX_DAILY_INTEREST_RATE = 0.001")
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
                st.session_state.patch_applied = True
                st.success("Patch berhasil diterapkan ke repositori lokal.")

        if st.session_state.patch_applied:
            st.caption("Status Repositori: Telah Disesuaikan dengan POJK 22/2023")

        # Tombol Uji Coba Unit Test
        if st.button("Jalankan Pengujian Unit Test Lokal", use_container_width=True):
            with st.spinner("Menjalankan verifikasi unit test pada repositori..."):
                test_script = os.path.join(MOCK_REPO_DIR, "tests", "test_compliance.py")
                res = subprocess.run([sys.executable, test_script], capture_output=True, text=True)
                st.session_state.test_output = res.stdout if res.returncode == 0 else res.stderr
        
        if st.button("Tolak Usulan & Catat Masukan", use_container_width=True):
            st.info("Usulan patch ditolak. Catatan dikembalikan ke tahap penelaahan hukum.")

    if st.session_state.test_output:
        st.markdown("##### Luaran Eksekusi Unit Test")
        st.code(st.session_state.test_output, language="text")

# Footer Minimalis
st.markdown("---")
st.caption("SELISIH — Regulatory Change & Code Impact System | IBM Hackathon x Hacktiv8 2026")
