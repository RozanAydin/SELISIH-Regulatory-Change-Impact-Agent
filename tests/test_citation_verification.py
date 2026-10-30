"""Unit test untuk verifikasi sitasi mekanis (selisih/citation.py)."""

import pytest
from selisih.citation import (
    normalize_for_matching,
    verify_citation_mechanically,
    validate_finding_citations,
)

SAMPLE_POJK_SOURCE = """
PERATURAN OTORITAS JASA KEUANGAN
NOMOR 22 TAHUN 2023
TENTANG PELINDUNGAN KONSUMEN DAN MASYARAKAT DI SEKTOR JASA KEUANGAN

Pasal 12
(1) Batas maksimum pemberian pinjaman dana oleh Penyelenggara kepada setiap Penerima Pinjaman ditingkatkan menjadi paling banyak sebesar Rp50.000.000,00 (lima puluh juta rupiah).
(2) Dalam rangka pelindungan konsumen, batas maksimum suku bunga harian diturunkan menjadi paling tinggi sebesar 0,1% (nol koma satu persen) per hari kalender.
"""

SAMPLE_POJK_LAMA = """
PERATURAN OTORITAS JASA KEUANGAN
NOMOR 77/POJK.01/2016

Pasal 8
(2) Batas maksimum total pemberian pinjaman dana kepada setiap Penerima Pinjaman sebagaimana dimaksud pada ayat (1) adalah sebesar Rp20.000.000,00 (dua puluh juta rupiah).
(3) Penyelenggara wajib memastikan tingkat suku bunga harian yang dikenakan kepada Penerima Pinjaman tidak melebihi 0,4% (nol koma empat persen) per hari kalender.
"""


def test_normalize_for_matching():
    text = '\u201cBatas   maksimum\u2014pinjaman\u201d...adalah   Rp50.000.000\n\n'
    norm = normalize_for_matching(text)
    assert norm == '"Batas maksimum-pinjaman" ... adalah Rp50.000.000'


def test_verify_citation_exact_match():
    quote = "Batas maksimum pemberian pinjaman dana oleh Penyelenggara kepada setiap Penerima Pinjaman ditingkatkan"
    res = verify_citation_mechanically(quote, SAMPLE_POJK_SOURCE)
    assert res["is_valid"] is True
    assert res["match_type"] == "exact"
    assert res["start_offset"] > 0
    assert "terverifikasi eksak" in res["reason"]


def test_verify_citation_ellipsis_match():
    quote = "Batas maksimum pemberian pinjaman dana ... ditingkatkan menjadi paling banyak sebesar Rp50.000.000,00"
    res = verify_citation_mechanically(quote, SAMPLE_POJK_SOURCE)
    assert res["is_valid"] is True
    assert res["match_type"] == "segmented_ellipsis"
    assert res["start_offset"] > 0


def test_verify_citation_hallucinated_fails():
    # Quote with fabricated words
    fake_quote = "Batas maksimum pemberian pinjaman dana ditingkatkan menjadi Rp100.000.000 secara sepihak"
    res = verify_citation_mechanically(fake_quote, SAMPLE_POJK_SOURCE)
    assert res["is_valid"] is False
    assert res["match_type"] == "none"
    assert "TIDAK ditemukan" in res["reason"]


def test_verify_citation_empty():
    assert verify_citation_mechanically("", SAMPLE_POJK_SOURCE)["is_valid"] is False
    assert verify_citation_mechanically("tes", "")["is_valid"] is False


def test_validate_finding_citations_success():
    finding = {
        "change_id": "CHG-001",
        "pasal_baru": {
            "doc_id": "POJK-22-2023",
            "pasal": "Pasal 12",
            "ayat": "(1)",
            "kutipan": "Batas maksimum pemberian pinjaman dana ... ditingkatkan menjadi paling banyak sebesar Rp50.000.000,00",
        },
        "pasal_lama": {
            "doc_id": "POJK-77-2016",
            "pasal": "Pasal 8",
            "ayat": "(2)",
            "kutipan": "Batas maksimum total pemberian pinjaman dana ... adalah sebesar Rp20.000.000,00",
        },
        "abstain": False,
    }
    sources = {
        "POJK-22-2023": SAMPLE_POJK_SOURCE,
        "POJK-77-2016": SAMPLE_POJK_LAMA,
    }
    validated = validate_finding_citations(finding, sources)
    assert validated["sitasi_valid"] is True
    assert validated["abstain"] is False
    assert validated["sitasi_verification"]["pasal_baru"]["is_valid"] is True
    assert validated["sitasi_verification"]["pasal_lama"]["is_valid"] is True


def test_validate_finding_citations_triggers_abstain_on_hallucination():
    finding = {
        "change_id": "CHG-FAKE",
        "pasal_baru": {
            "doc_id": "POJK-22-2023",
            "pasal": "Pasal 99",
            "ayat": "(1)",
            "kutipan": "Pasal halusinasi yang tidak ada sama sekali di naskah regulasi OJK.",
        },
        "pasal_lama": {
            "doc_id": "POJK-77-2016",
            "pasal": "Pasal 8",
            "ayat": "(2)",
            "kutipan": "Batas maksimum total pemberian pinjaman dana ... adalah sebesar Rp20.000.000,00",
        },
        "abstain": False,
    }
    sources = {
        "POJK-22-2023": SAMPLE_POJK_SOURCE,
        "POJK-77-2016": SAMPLE_POJK_LAMA,
    }
    validated = validate_finding_citations(finding, sources)
    assert validated["sitasi_valid"] is False
    assert validated["abstain"] is True
    assert "Zero-Hallucination" in validated["alasan_abstain"]
