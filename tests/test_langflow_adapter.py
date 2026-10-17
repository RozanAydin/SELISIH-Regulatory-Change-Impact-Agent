"""Pengujian Fase 0: konfigurasi + normalizer klien Langflow (tanpa jaringan)."""

import json
import unittest.mock as mock

import pytest

import selisih.config as config_mod
from selisih.langflow import (
    LangflowError,
    extract_findings,
    normalize_response,
    run_analysis,
    run_embedded_analysis,
)


def test_config_defaults(monkeypatch):
    for key in ("LANGFLOW_MODE", "LANGFLOW_API_URL", "LANGFLOW_FLOW_ID", "LANGFLOW_API_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    cfg = config_mod.get_langflow_config()
    assert cfg["mode"] == "embedded"
    assert cfg["api_url"] == "http://localhost:7860"
    assert cfg["flow_id"] == ""
    assert cfg["api_token"] == ""



def test_config_from_env(monkeypatch):
    monkeypatch.setattr(config_mod, "st", None)
    monkeypatch.setenv("LANGFLOW_API_URL", "http://host:9999/")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-abc")
    cfg = config_mod.get_langflow_config()
    assert cfg["api_url"] == "http://host:9999"
    assert cfg["flow_id"] == "flow-abc"


def test_normalize_direct_contract():
    raw = {
        "analysis_meta": {"timestamp": "2026-01-01T00:00:00Z"},
        "findings": [
            {
                "change_id": "CHG-X",
                "ringkasan": "ringkasan",
                "pasal_baru": {"doc_id": "POJK-22-2023", "pasal": "Pasal 12"},
                "pasal_lama": {"doc_id": "POJK-77-2016", "pasal": "Pasal 8"},
            }
        ],
    }
    findings = normalize_response(raw)
    assert len(findings) == 1
    assert findings[0]["change_id"] == "CHG-X"
    assert findings[0]["sitasi_valid"] is True
    assert findings[0]["abstain"] is False
    assert findings[0]["confidence"] == "rendah"


def test_normalize_embedded_json():
    raw = {
        "outputs": [
            {
                "outputs": [
                    {
                        "results": {
                            "message": {
                                "text": json.dumps(
                                    {
                                        "findings": [
                                            {
                                                "change_id": "CHG-POJK-001",
                                                "ringkasan": "Plafon pinjaman naik.",
                                                "pasal_baru": {"doc_id": "POJK-22-2023", "pasal": "Pasal 12", "ayat": "(1)"},
                                                "pasal_lama": {"doc_id": "POJK-77-2016", "pasal": "Pasal 8", "ayat": "(2)"},
                                            },
                                            {
                                                "change_id": "CHG-POJK-002",
                                                "ringkasan": "Batas bunga harian turun.",
                                                "pasal_baru": {"doc_id": "POJK-22-2023", "pasal": "Pasal 12", "ayat": "(2)"},
                                                "pasal_lama": {"doc_id": "POJK-77-2016", "pasal": "Pasal 8", "ayat": "(3)"},
                                            },
                                        ]
                                    }
                                )
                            }
                        }
                    }
                ]
            }
        ]
    }
    findings = normalize_response(raw)
    assert len(findings) == 2
    assert findings[0]["change_id"] == "CHG-POJK-001"
    assert findings[1]["abstain"] is False
    assert findings[1]["confidence"] == "rendah"


def test_normalize_single_finding():
    raw = {"change_id": "CHG-Y", "ringkasan": "satu temuan"}
    findings = normalize_response(raw)
    assert len(findings) == 1
    assert findings[0]["kandidat_kode"] == []


def test_normalize_invalid_raises():
    with pytest.raises(LangflowError):
        normalize_response({"outputs": []})


def test_extract_findings_alias():
    raw = {"findings": [{"change_id": "CHG-Z", "ringkasan": "r"}]}
    assert extract_findings(raw)[0]["change_id"] == "CHG-Z"


def test_run_analysis_missing_flow_id():
    with pytest.raises(LangflowError):
        run_analysis("teks", {"mode": "rest", "api_url": "http://lf", "flow_id": "", "api_token": ""})



def test_run_analysis_mocked_success():
    payload = {
        "findings": [
            {
                "change_id": "CHG-1",
                "ringkasan": "x",
                "pasal_baru": {"doc_id": "POJK-22-2023"},
                "pasal_lama": {"doc_id": "POJK-77-2016"},
            }
        ]
    }
    with mock.patch("selisih.langflow.requests.post") as m_post:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = payload
        m_post.return_value = resp

        cfg = {"api_url": "http://lf:7860", "flow_id": "flow-1", "api_token": ""}
        findings = run_analysis("teks regulasi", cfg)

    assert findings[0]["change_id"] == "CHG-1"
    assert m_post.call_args[0][0] == "http://lf:7860/api/v1/run/flow-1"


def test_run_analysis_http_error():
    with mock.patch("selisih.langflow.requests.post") as m_post:
        resp = mock.MagicMock()
        resp.status_code = 500
        resp.text = "internal error"
        m_post.return_value = resp
        with pytest.raises(LangflowError, match="HTTP 500"):
            run_analysis("x", {"api_url": "http://lf", "flow_id": "f", "api_token": ""})


def test_run_analysis_non_json_response():
    with mock.patch("selisih.langflow.requests.post") as m_post:
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("no json")
        resp.text = "<html>"
        m_post.return_value = resp
        with pytest.raises(LangflowError, match="bukan JSON"):
            run_analysis("x", {"api_url": "http://lf", "flow_id": "f", "api_token": ""})


def test_run_embedded_analysis_success():
    sample_text = (
        "POJK Nomor 22 Tahun 2023. Pasal 12 ayat (1) batas maksimum plafon pinjaman Rp 50.000.000. "
        "Pasal 12 ayat (2) batas suku bunga harian diturunkan menjadi 0,1% per hari."
    )
    findings = run_embedded_analysis(sample_text)
    assert len(findings) == 2
    change_ids = [f["change_id"] for f in findings]
    assert "CHG-POJK-001" in change_ids
    assert "CHG-POJK-002" in change_ids
    assert all(f["sitasi_valid"] is True for f in findings)


def test_run_analysis_falls_back_to_embedded_when_no_flow_id(monkeypatch):
    monkeypatch.delenv("LANGFLOW_FLOW_ID", raising=False)
    sample_text = "Pasal 12 batas plafon pinjaman Rp 50.000.000 dan bunga harian 0.1% per hari."
    findings = run_analysis(sample_text)
    assert len(findings) >= 1
    assert any("CHG-POJK" in f["change_id"] for f in findings)


def test_flow_template_file_valid_json():
    import os
    flow_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flows", "selisih_regulatory_flow.json"))
    assert os.path.isfile(flow_file)
    with open(flow_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "name" in data
    assert "nodes" in data["data"]
    assert "edges" in data["data"]
    assert len(data["data"]["nodes"]) >= 3