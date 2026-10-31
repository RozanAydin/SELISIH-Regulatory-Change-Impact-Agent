"""Unit test untuk modul selisih.pipeline (Pipeline Orchestrator)."""

import os
from unittest import mock
import pytest
from selisih.pipeline import resolve_regulation_text, run_full_pipeline


def test_resolve_regulation_text_static_local():
    log = []
    reg_info = {
        "id": "pojk-77-2016",
        "nomor": "77/POJK.01/2016",
        "tahun": "2016",
        "judul": "Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
    }
    with mock.patch("selisih.pipeline.get_cached", return_value=None):
        text, source = resolve_regulation_text(reg_info, log)
        assert len(text) > 0
        assert "Pasal" in text
        assert source == "static_local"
        assert any(entry["step"] in ("cache", "fallback") for entry in log)


def test_resolve_regulation_text_cache_hit(tmp_path):
    from selisih.regulation_cache import save_regulation

    test_db = str(tmp_path / "reg.db")
    with mock.patch("selisih.pipeline.get_cached") as mock_get_cached:
        mock_get_cached.return_value = {
            "id": "POJK-99-2025",
            "full_text": "Teks tersimpan di cache.",
            "pasal_count": 5,
        }
        log = []
        reg_info = {"id": "POJK-99-2025", "nomor": "99", "tahun": "2025", "judul": "Tes"}
        text, source = resolve_regulation_text(reg_info, log)
        assert text == "Teks tersimpan di cache."
        assert source == "sqlite_cache"
        assert any(entry["status"] == "hit" for entry in log)


def test_run_full_pipeline_standard_flow():
    acuan = {
        "id": "pojk-77-2016",
        "nomor": "77/POJK.01/2016",
        "tahun": "2016",
        "judul": "Layanan Pinjam Meminjam Uang",
        "doc_id": "POJK-77-2016",
    }
    ojk = {
        "id": "pojk-22-2023",
        "nomor": "22",
        "tahun": "2023",
        "judul": "Pelindungan Konsumen Sektor Jasa Keuangan",
        "doc_id": "POJK-22-2023",
    }
    res = run_full_pipeline(ojk_info=ojk, acuan_info=acuan, engine="embedded")

    assert "findings" in res
    assert len(res["findings"]) >= 2
    assert "pipeline_log" in res
    assert len(res["pipeline_log"]) >= 4
    assert res["sources"]["acuan"] in ("static_local", "sqlite_cache")
    assert res["sources"]["baru"] in ("static_local", "sqlite_cache")
    assert "Granite" in res["engine"]
