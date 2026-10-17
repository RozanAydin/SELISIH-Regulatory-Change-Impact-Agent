"""Paket inti SELISIH: konfigurasi, dokumen, Langflow, impact, artefak."""

from .config import get_langflow_config
from .documents import DocumentLoadError, clean_pojk_text, load_document_text, split_by_pasal
from .langflow import LangflowError, extract_findings, normalize_response, run_analysis
from .license import get_license_state

__all__ = [
    "get_langflow_config",
    "DocumentLoadError",
    "clean_pojk_text",
    "load_document_text",
    "split_by_pasal",
    "LangflowError",
    "extract_findings",
    "normalize_response",
    "run_analysis",
    "get_license_state",
]

__version__ = "0.1.0"
