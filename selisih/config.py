"""Konfigurasi SELISIH: dibaca dari env, file `.env`, atau secrets Streamlit.

Urutan prioritas nilai (tertinggi dulu):
1. `st.secrets` (runtime streamlit, dari `.streamlit/secrets.toml`)
2. Environment variable (termasuk yang dimuat dari file `.env`)

Gunakan modul ini supaya tidak ada secret yang ditulis langsung di kode.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv ada di requirements
    load_dotenv = None

try:
    import streamlit as st
except ImportError:  # pragma: no cover - hanya relevan saat streamlit terpasang
    st = None

DEFAULTS = {
    "LANGFLOW_API_URL": "http://localhost:7860",
    "LANGFLOW_FLOW_ID": "",
    "LANGFLOW_API_TOKEN": "",
}


def _get(name: str) -> str:
    """Versi sederhana untuk pembacaan satu kunci (urutan: secrets non-kosong, lalu env)."""
    env_value = os.getenv(name, DEFAULTS[name])
    if st is not None:
        try:
            if name in st.secrets and st.secrets[name]:
                return str(st.secrets[name])
        except Exception:
            pass
    return env_value


def _env_values() -> dict:
    return {name: os.getenv(name, DEFAULTS[name]) for name in DEFAULTS}


def _resolve(name: str, env_values: dict) -> str:
    if st is not None:
        try:
            if name in st.secrets and st.secrets[name]:
                return str(st.secrets[name])
        except Exception:  # pragma: no cover - runtime tertentu tanpa secrets
            pass
    return env_values[name]


def get_langflow_config() -> dict:
    """Kembalikan konfigurasi Langflow sebagai dict siap pakai.

    Nilai env disnapshot lebih dulu: di mode tanpa runtime streamlit, akses
    ``st.secrets`` bisa menimpa ``os.environ`` untuk semua kunci sekaligus
    (lihat sekret kosong di ``.streamlit/secrets.toml``). Env yang tidak
    tertimpa sekalipun tetap terbaca lewat snapshot.
    """
    env_values = _env_values()
    return {
        "api_url": _resolve("LANGFLOW_API_URL", env_values).rstrip("/"),
        "flow_id": _resolve("LANGFLOW_FLOW_ID", env_values),
        "api_token": _resolve("LANGFLOW_API_TOKEN", env_values),
    }