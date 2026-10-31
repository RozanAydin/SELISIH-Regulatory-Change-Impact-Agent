"""Unit test untuk modul selisih.regulation_cache (SQLite cache)."""

import os
import pytest
from selisih.regulation_cache import (
    init_db,
    save_regulation,
    get_cached,
    mark_ingested,
    list_cached,
)


def test_regulation_cache_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_regulations.db")
    init_db(db_file)

    # 1. Cache Miss
    assert get_cached("POJK-NONEXISTENT", db_path=db_file) is None
    assert list_cached(db_path=db_file) == []

    # 2. Save regulation
    chunks = [
        {"pasal": "Pasal 1", "text": "Ketentuan umum perbankan."},
        {"pasal": "Pasal 2", "text": "Plafon pinjaman maksimal Rp 50.000.000."},
    ]
    save_regulation(
        reg_id="POJK-TEST-2024",
        nomor="41",
        tahun="2024",
        judul="Tata Kelola Digital",
        full_text="Pasal 1 Ketentuan umum.\nPasal 2 Plafon pinjaman...",
        chunks=chunks,
        pdf_path="/path/test.pdf",
        source="jdih_download",
        db_path=db_file,
    )

    # 3. Cache Hit
    cached = get_cached("POJK-TEST-2024", db_path=db_file)
    assert cached is not None
    assert cached["id"] == "POJK-TEST-2024"
    assert cached["nomor"] == "41"
    assert cached["tahun"] == "2024"
    assert cached["pasal_count"] == 2
    assert cached["ingested"] == 0
    assert cached["source"] == "jdih_download"

    # 4. Mark Ingested
    mark_ingested("POJK-TEST-2024", db_path=db_file)
    cached_after = get_cached("POJK-TEST-2024", db_path=db_file)
    assert cached_after["ingested"] == 1

    # 5. List cached
    all_cached = list_cached(db_path=db_file)
    assert len(all_cached) == 1
    assert all_cached[0]["id"] == "POJK-TEST-2024"
