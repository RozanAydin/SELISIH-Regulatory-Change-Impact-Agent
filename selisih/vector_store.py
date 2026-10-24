"""Modul Vector Store Lokal (ChromaDB) untuk Regulasi Finansial OJK.

Menyediakan penyimpanan vektor lokal dan penelusuran semantik klausul acuan (POJK 77/2016)
tanpa ketergantungan pada database cloud eksternal (Astra DB), 100% offline dan tahan banting.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional
import numpy as np

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from selisih.documents import clean_pojk_text, load_document_text, split_by_pasal

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
POJK_LAMA_FILE = os.path.join(DATA_DIR, "pojk_lama_77_2016.txt")


class FastLegalEmbeddingFunction(EmbeddingFunction):
    """Fungsi embedding n-gram deterministik lokal 128 dimensi.
    
    100% offline, instan tanpa perlu mengunduh bobot model puluhan megabyte dari internet.
    """

    def __init__(self):
        super().__init__()

    def name(self) -> str:
        return "fast_legal_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for doc in input:
            vec = np.zeros(128, dtype=np.float32)
            words = doc.lower().split()
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % 128
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            embeddings.append(vec.tolist())
        return embeddings


_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_vector_client(persist_directory: str = CHROMA_DIR) -> chromadb.PersistentClient:
    """Mengembalikan persistent Chroma client lokal."""
    global _client
    if _client is None:
        os.makedirs(persist_directory, exist_ok=True)
        _client = chromadb.PersistentClient(path=persist_directory)
    return _client


def get_or_create_collection(
    collection_name: str = "pojk_acuan_idx",
    persist_directory: str = CHROMA_DIR,
):
    """Mengambil atau membuat koleksi regulasi acuan di ChromaDB."""
    global _collection
    client = get_vector_client(persist_directory)
    emb_fn = FastLegalEmbeddingFunction()
    _collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=emb_fn,
        metadata={"description": "Koleksi Pasal Regulasi Acuan OJK (POJK 77/2016)"},
    )
    return _collection


def ingest_reference_pojk(
    file_path: str = POJK_LAMA_FILE,
    doc_id: str = "POJK-77-2016",
    collection_name: str = "pojk_acuan_idx",
    force: bool = False,
) -> int:
    """Memotong dokumen POJK lama per pasal dan memasukkannya ke ChromaDB."""
    col = get_or_create_collection(collection_name)
    existing_count = col.count()
    if existing_count > 0 and not force:
        return existing_count

    if not os.path.exists(file_path):
        return 0

    text = load_document_text(file_path)
    chunks = split_by_pasal(text, doc_id=doc_id)

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        pasal_name = chunk["pasal"]
        chunk_text = chunk["text"]

        # 1. Simpan level Pasal utuh
        chunk_id = f"{doc_id}-{pasal_name}".replace(" ", "_")
        ids.append(chunk_id)
        documents.append(chunk_text)
        metadatas.append({
            "doc_id": chunk.get("doc_id", doc_id),
            "pasal": pasal_name,
            "ayat": "(1)",
            "level": "pasal",
        })

        # 2. Simpan level Ayat terurai untuk sitasi presisi
        ayat_blocks = re.findall(r"(?m)^\s*\((\d+)\)\s*(.+?)(?=(?:^\s*\(\d+\)|\Z))", chunk_text, re.DOTALL)
        for ayat_num, ayat_content in ayat_blocks:
            ayat_id = f"{doc_id}-{pasal_name}-Ayat_{ayat_num}".replace(" ", "_")
            ids.append(ayat_id)
            documents.append(f"{pasal_name} Ayat ({ayat_num}) {ayat_content.strip()}")
            metadatas.append({
                "doc_id": chunk.get("doc_id", doc_id),
                "pasal": pasal_name,
                "ayat": f"({ayat_num})",
                "level": "ayat",
            })

    if ids:
        col.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return col.count()


def query_reference_clauses(
    query_text: str,
    n_results: int = 3,
    collection_name: str = "pojk_acuan_idx",
) -> List[Dict[str, Any]]:
    """Mencari pasal acuan yang paling relevan dengan klausul regulasi baru."""
    col = get_or_create_collection(collection_name)
    if col.count() == 0:
        ingest_reference_pojk(collection_name=collection_name)

    results = col.query(query_texts=[query_text], n_results=n_results)

    matches: List[Dict[str, Any]] = []
    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            ayat = meta.get("ayat", "(1)")
            clean_kutipan = doc.replace(meta.get("pasal", ""), "").replace(f"Ayat {ayat}", "").strip()
            # Bersihkan jika ada awalan ayat
            clean_kutipan = re.sub(r"^\(\d+\)\s*", "", clean_kutipan)

            matches.append({
                "doc_id": meta.get("doc_id", "POJK-77-2016"),
                "pasal": meta.get("pasal", "Pasal 8"),
                "ayat": ayat,
                "kutipan": clean_kutipan[:220],
                "full_text": doc,
                "distance": float(dist) if dist is not None else 0.0,
            })
    return matches
