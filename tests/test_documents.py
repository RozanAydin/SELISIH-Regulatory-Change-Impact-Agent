"""Pengujian loader dokumen regulasi TXT/PDF (tanpa integrasi Astra/Langflow)."""

import os

import pytest

from selisih.documents import (
    DocumentLoadError,
    clean_pojk_text,
    extract_pdf_text_pdfplumber,
    infer_doc_id,
    load_document_text,
    split_by_pasal,
)


# PDF contoh di luar repo (opsional): atur via env atau path relatif demo paket.
RAW_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "NPL", "SELISIH_demo_paket", "RCIA", "data", "raw",
    )
)
_CANDIDATE_PDFS = [
    os.environ.get("SELISIH_SAMPLE_PDF", ""),
    os.path.join(os.path.dirname(__file__), "..", "data", "POJK_08_2023_APU_PPT_PPPSPM.pdf"),
    os.path.join(RAW_DIR, "POJK_08_2023_APU_PPT_PPPSPM.pdf"),
]
SAMPLE_PDF = next((p for p in _CANDIDATE_PDFS if p and os.path.exists(p)), "")


def test_load_txt_and_clean(tmp_path):
    doc = tmp_path / "regulasi.txt"
    doc.write_text("Judul\n\n\n- 1 -\n\nPasal 1\n  Isi   pasal.\n", encoding="utf-8")

    text = load_document_text(str(doc))

    assert "- 1 -" not in text
    assert "Pasal 1" in text
    assert "Isi pasal." in text


def test_clean_pojk_text_removes_page_number_noise():
    text = clean_pojk_text("A\n\n   - 12 -   \n\nB\t C\n\n\nD")

    assert text == "A\nB C\n\nD"


def test_split_by_pasal():
    chunks = split_by_pasal(
        "Pembukaan\n\nPasal 1\nIsi satu.\n\nPasal 2\n(1) Isi dua.\n",
        doc_id="POJK-TEST",
    )

    assert [c["pasal"] for c in chunks] == ["Pasal 1", "Pasal 2"]
    assert chunks[0]["doc_id"] == "POJK-TEST"
    assert "Isi satu" in chunks[0]["text"]
    assert "Isi dua" in chunks[1]["text"]


def test_infer_doc_id_from_filename():
    assert infer_doc_id("/x/POJK_08_2023_APU_PPT_PPPSPM.pdf") == "POJK-08-2023-APU-PPT-PPPSPM"


def test_unsupported_extension(tmp_path):
    doc = tmp_path / "regulasi.docx"
    doc.write_text("x", encoding="utf-8")

    with pytest.raises(DocumentLoadError, match="Format dokumen"):
        load_document_text(str(doc))


def test_extract_real_pojk_pdf_if_available():
    if not os.path.exists(SAMPLE_PDF):
        pytest.skip("PDF contoh eksternal tidak tersedia di mesin ini")
    try:
        import pypdf  # noqa: F401
    except ImportError:
        pytest.skip("pypdf belum terpasang")

    text = load_document_text(SAMPLE_PDF)
    chunks = split_by_pasal(text, doc_id=infer_doc_id(SAMPLE_PDF))

    assert "NOMOR 8 TAHUN 2023" in text
    assert "Pasal 1" in text
    assert len(chunks) >= 80


def test_split_by_pasal_case_insensitive():
    chunks = split_by_pasal(
        "Menimbang...\n\nPASAL 12\nIsi pasal dua belas.\n\nPasal 13A\nKetentuan tambahan.\n",
        doc_id="POJK-TEST-UPPER",
    )
    assert len(chunks) == 2
    assert chunks[0]["pasal"] == "Pasal 12"
    assert chunks[1]["pasal"] == "Pasal 13A"


def test_extract_pdf_text_pdfplumber_fallback_on_error(tmp_path):
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy corrupted")

    with pytest.raises(DocumentLoadError):
        extract_pdf_text_pdfplumber(str(dummy_pdf))

