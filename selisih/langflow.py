"""Klien & normalizer respons Langflow untuk kontrak data `temuan.json`.

Fase 0: jembatan REST antara `app.py` dan flow Langflow. Output flow (berapa pun
bentuk aslinya di dalam JSON tree, atau JSON yang menyatu dalam string text)
dinormalisasi menjadi list `findings[]` sesuai skema `data/temuan_schema.json`.
"""

import json

import requests

from .config import get_langflow_config


class LangflowError(RuntimeError):
    """Galat saat memanggil Langflow atau memparse outputnya."""


def run_analysis(input_text: str, cfg: dict | None = None) -> list[dict]:
    """Kirim teks regulasi baru ke Langflow, kembalikan list `findings`.

    `cfg` opsional (dict hasil `get_langflow_config()`). Jika tidak diberikan,
    konfigurasi dibaca dari env / secrets.
    """
    cfg = cfg or get_langflow_config()
    if not cfg.get("flow_id"):
        raise LangflowError(
            "LANGFLOW_FLOW_ID belum dikonfigurasi (periksa .env / .streamlit/secrets.toml)."
        )

    url = f"{cfg['api_url']}/api/v1/run/{cfg['flow_id']}"
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_token"):
        headers["x-api-key"] = cfg["api_token"]

    payload = {
        "input_value": input_text,
        "output_type": "chat",
        "input_type": "chat",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise LangflowError(f"Koneksi ke Langflow gagal: {exc}") from exc

    if resp.status_code != 200:
        raise LangflowError(
            f"Langflow merespon HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise LangflowError(f"Respons Langflow bukan JSON: {resp.text[:300]}") from exc

    return normalize_response(data)


def normalize_response(raw: dict) -> list[dict]:
    """Normalisasi respons Langflow mentah menjadi list `findings`.

    Menerima salah satu bentuk berikut secara toleran:
    - dict kontrak penuh `{"findings": [...]}`
    - dict tunggal yang menyerupai finding
    - JSON findings yang terkubur di dalam string text hasil LLM
    Menimbulkan `LangflowError` bila tidak ada findings valid sama sekali.
    """
    findings = list(_scan(raw))
    normalized = [f for f in (_normalize_finding(f) for f in findings) if f.get("change_id") or f.get("ringkasan")]
    if not normalized:
        raise LangflowError("Output Langflow tidak mengandung findings yang valid.")
    return normalized


def extract_findings(raw) -> list[dict]:
    """Alias `normalize_response` untuk konteks yang ingin menamainya 'ekstraksi'."""
    return normalize_response(raw)


def _looks_like_finding(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    return "ringkasan" in obj or ("change_id" in obj and "pasal_baru" in obj)


def _scan(obj):
    """Cari semua dict finding di dalam tree, termasuk yang terkubur di string JSON."""
    if isinstance(obj, dict):
        findings = obj.get("findings")
        if isinstance(findings, list):
            for f in findings:
                if isinstance(f, dict):
                    yield f
        elif _looks_like_finding(obj):
            yield obj
        for value in obj.values():
            if findings is not None and value is findings:
                continue
            yield from _scan(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _scan(item)
    elif isinstance(obj, str) and obj.lstrip().startswith("{"):
        try:
            parsed = json.loads(obj)
        except ValueError:
            pass
        else:
            yield from _scan(parsed)


def _normalize_finding(f: dict) -> dict:
    """Pastikan field kontrak penting ada (dengan nilai default bila kosong)."""
    out = dict(f)
    out.setdefault("change_id", "")
    out.setdefault("ringkasan", "")
    out.setdefault("jenis_perubahan", "diubah")
    out.setdefault("pasal_baru", {})
    out.setdefault("pasal_lama", {})
    out.setdefault(
        "sitasi_valid", bool(out.get("pasal_baru")) and bool(out.get("pasal_lama"))
    )
    out.setdefault("confidence", "rendah")
    out.setdefault("abstain", False)
    out.setdefault("alasan_abstain", None)
    out.setdefault("kandidat_kode", [])
    return out