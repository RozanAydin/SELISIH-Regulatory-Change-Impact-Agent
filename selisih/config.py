"""Konfigurasi SELISIH: dibaca dari environment variables atau file `.env`."""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    load_dotenv = None

# st disediakan sebagai None demi kompatibilitas pengujian tanpa runtime Streamlit
st = None

DEFAULTS = {
    "LANGFLOW_MODE": "embedded",
    "LANGFLOW_API_URL": "http://localhost:7860",
    "LANGFLOW_FLOW_ID": "",
    "LANGFLOW_API_TOKEN": "",
}


def _get(name: str) -> str:
    """Pembacaan nilai konfigurasi dari environment variable."""
    return os.getenv(name, DEFAULTS.get(name, ""))


def get_langflow_config() -> dict:
    """Kembalikan konfigurasi Langflow sebagai dict siap pakai."""
    return {
        "mode": os.getenv("LANGFLOW_MODE", DEFAULTS["LANGFLOW_MODE"]),
        "api_url": os.getenv("LANGFLOW_API_URL", DEFAULTS["LANGFLOW_API_URL"]).rstrip("/"),
        "flow_id": os.getenv("LANGFLOW_FLOW_ID", DEFAULTS["LANGFLOW_FLOW_ID"]),
        "api_token": os.getenv("LANGFLOW_API_TOKEN", DEFAULTS["LANGFLOW_API_TOKEN"]),
    }
