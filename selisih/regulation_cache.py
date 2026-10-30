"""Cache lokal regulasi OJK berbasis SQLite.

Menyimpan metadata dan teks hasil ekstraksi agar tidak perlu
mengunduh ulang PDF yang sama berkali-kali.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "regulations.db")


def init_db(db_path: str = DB_PATH) -> None:
    """Inisialisasi tabel cache jika belum ada."""
    abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with sqlite3.connect(abs_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS regulations (
                id          TEXT PRIMARY KEY,
                nomor       TEXT,
                tahun       TEXT,
                judul       TEXT,
                pdf_path    TEXT,
                full_text   TEXT NOT NULL,
                pasal_count INTEGER DEFAULT 0,
                ingested    INTEGER DEFAULT 0,
                source      TEXT,
                cached_at   TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS pasal_chunks (
                chunk_id      TEXT PRIMARY KEY,
                regulation_id TEXT NOT NULL,
                pasal         TEXT,
                text          TEXT,
                FOREIGN KEY(regulation_id) REFERENCES regulations(id)
            )
            """
        )
        con.commit()


def get_cached(reg_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Ambil regulasi dari cache. None jika belum ada."""
    abs_path = os.path.abspath(db_path)
    init_db(abs_path)
    with sqlite3.connect(abs_path) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM regulations WHERE id = ?", (reg_id,)
        ).fetchone()
        return dict(row) if row else None


def save_regulation(
    reg_id: str,
    nomor: str,
    tahun: str,
    judul: str,
    full_text: str,
    chunks: List[Dict[str, Any]],
    pdf_path: str = "",
    source: str = "jdih_download",
    db_path: str = DB_PATH,
) -> None:
    """Simpan teks dan metadata regulasi ke SQLite."""
    abs_path = os.path.abspath(db_path)
    init_db(abs_path)
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(abs_path) as con:
        con.execute(
            """
            INSERT OR REPLACE INTO regulations
                (id, nomor, tahun, judul, pdf_path, full_text, pasal_count, source, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (reg_id, nomor, tahun, judul, pdf_path, full_text, len(chunks), source, now),
        )
        for chunk in chunks:
            pasal = chunk.get("pasal", "")
            chunk_id = f"{reg_id}-{pasal}".replace(" ", "_")
            con.execute(
                """
                INSERT OR REPLACE INTO pasal_chunks (chunk_id, regulation_id, pasal, text)
                VALUES (?, ?, ?, ?)
                """,
                (chunk_id, reg_id, pasal, chunk.get("text", "")),
            )
        con.commit()


def mark_ingested(reg_id: str, db_path: str = DB_PATH) -> None:
    """Tandai regulasi sudah di-ingest ke ChromaDB."""
    abs_path = os.path.abspath(db_path)
    init_db(abs_path)
    with sqlite3.connect(abs_path) as con:
        con.execute("UPDATE regulations SET ingested = 1 WHERE id = ?", (reg_id,))
        con.commit()


def list_cached(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Daftar semua regulasi yang tersimpan di cache."""
    abs_path = os.path.abspath(db_path)
    init_db(abs_path)
    with sqlite3.connect(abs_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT id, nomor, tahun, judul, pasal_count, ingested, source, cached_at FROM regulations"
        ).fetchall()
        return [dict(r) for r in rows]
