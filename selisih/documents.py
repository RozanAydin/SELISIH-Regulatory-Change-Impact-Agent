"""Loader dokumen regulasi untuk TXT/PDF POJK.

Modul ini hanya menyiapkan teks lokal. Ingest ke Astra/Langflow tetap dikerjakan
terpisah pada Fase 1.
"""

from __future__ import annotations

import os
import re


class DocumentLoadError(RuntimeError):
    """Galat saat membaca atau menormalisasi dokumen regulasi."""


def load_document_text(path: str, *, clean: bool = True) -> str:
    """Baca dokumen regulasi `.txt` atau `.pdf` sebagai teks UTF-8 bersih."""
    if not os.path.exists(path):
        raise DocumentLoadError(f"Dokumen tidak ditemukan: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, encoding="utf-8") as f:
            text = f.read()
    elif ext == ".pdf":
        text = extract_pdf_text_pdfplumber(path)
    else:
        raise DocumentLoadError(f"Format dokumen belum didukung: {ext or '(tanpa ekstensi)'}")

    text = clean_pojk_text(text) if clean else text
    if not text.strip():
        raise DocumentLoadError(f"Dokumen kosong atau gagal diekstrak: {path}")
    return text


def extract_pdf_text_pdfplumber(path: str) -> str:
    """Ekstrak teks PDF memakai `pdfplumber` (dengan fallback otomatis ke `pypdf`)."""
    try:
        import pdfplumber

        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                pages.append(text)
        extracted = "\n\n".join(pages).strip()
        if extracted:
            return extracted
        # Bila string kosong (misal pdfplumber tidak mendeteksi teks), coba fallback
        return extract_pdf_text(path)
    except ImportError:
        return extract_pdf_text(path)
    except Exception:
        # Fallback aman ke pypdf bila pdfplumber gagal membaca format tertentu
        return extract_pdf_text(path)


def extract_pdf_text(path: str) -> str:
    """Ekstrak teks PDF berbasis teks memakai `pypdf` (bukan OCR)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentLoadError("Dependency `pypdf` belum terpasang. Jalankan `pip install -r requirements.txt`.") from exc

    try:
        reader = PdfReader(path)
    except Exception as exc:  # pragma: no cover - bergantung parser PDF
        raise DocumentLoadError(f"PDF gagal dibuka: {exc}") from exc

    pages = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - bergantung PDF spesifik
            raise DocumentLoadError(f"PDF gagal diekstrak pada halaman {index}: {exc}") from exc
    return "\n\n".join(pages)


def clean_pojk_text(text: str) -> str:
    """Normalisasi noise umum hasil ekstraksi PDF POJK tanpa mengubah substansi."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n\s*-\s*\d+\s*-\s*\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_by_pasal(text: str, *, doc_id: str = "") -> list[dict]:
    """Potong teks regulasi menjadi chunk per `Pasal` untuk calon ingest Astra/ChromaDB."""
    cleaned = clean_pojk_text(text)
    matches = list(re.finditer(r"(?mi)^\s*(Pasal\s+\d+[A-Za-z]?)\s*$", cleaned))
    chunks = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        body = cleaned[start:end].strip()
        if body:
            pasal_str = match.group(1).title() if match.group(1).isupper() else match.group(1)
            chunks.append({"doc_id": doc_id, "pasal": pasal_str, "text": body})
    return chunks


def infer_doc_id(path: str) -> str:
    """Buat doc_id sederhana dari nama file regulasi."""
    name = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()
