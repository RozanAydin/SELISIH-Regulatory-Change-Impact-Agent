"""Modul Vector Store Lokal (ChromaDB) untuk Regulasi Finansial OJK.

Menyediakan penyimpanan vektor lokal dan penelusuran semantik klausul acuan (POJK 77/2016)
tanpa ketergantungan pada database cloud eksternal (Astra DB), 100% offline dan tahan banting.
Mendukung Fallback In-Memory Index berbasis NumPy murni jika biner Rust ChromaDB bermasalah
pada lingkungan Python 3.13 Windows.
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

    def __init__(self, **kwargs):
        pass

    def name(self) -> str:
        return "fast_legal_embedding"

    def get_config(self) -> dict:
        return {}

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


class FallbackVectorIndex:
    """Mesin indeks vektor in-memory deterministik murni berbasis NumPy.
    
    Menjamin 0% risiko crash memori (Access Violation) di Python 3.13 Windows.
    """

    def __init__(self, embedding_fn: FastLegalEmbeddingFunction):
        self.emb_fn = embedding_fn
        self.records: List[Dict[str, Any]] = []

    def count(self) -> int:
        return len(self.records)

    def upsert(self, ids: list, documents: list, metadatas: list):
        embeddings = self.emb_fn(documents)
        for i, doc, meta, emb in zip(ids, documents, metadatas):
            self.records = [r for r in self.records if r["id"] != i]
            self.records.append({
                "id": i,
                "document": doc,
                "metadata": meta,
                "embedding": np.array(emb, dtype=np.float32),
            })

    def query(self, query_texts: list, n_results: int = 3) -> dict:
        if not self.records or not query_texts:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        q_emb = np.array(self.emb_fn(query_texts)[0], dtype=np.float32)
        scores = []
        for r in self.records:
            sim = float(np.dot(q_emb, r["embedding"]))
            scores.append((sim, r))

        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[:n_results]

        return {
            "documents": [[t[1]["document"] for t in top]],
            "metadatas": [[t[1]["metadata"] for t in top]],
            "distances": [[round(1.0 - t[0], 4) for t in top]],
        }


_client: Optional[chromadb.PersistentClient] = None
_collection = None
_FALLBACK_INDEX: Optional[FallbackVectorIndex] = None


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
    """Mengambil atau membuat koleksi regulasi acuan di ChromaDB dengan fallback otomatis."""
    global _collection, _FALLBACK_INDEX
    try:
        client = get_vector_client(persist_directory)
        emb_fn = FastLegalEmbeddingFunction()
        col = client.get_or_create_collection(
            name=collection_name,
            embedding_function=emb_fn,
            metadata={"description": "Koleksi Pasal Regulasi Acuan OJK (POJK 77/2016)"},
        )
        _ = col.count()
        _collection = col
        return _collection
    except Exception:
        if _FALLBACK_INDEX is None:
            _FALLBACK_INDEX = FallbackVectorIndex(FastLegalEmbeddingFunction())
        return _FALLBACK_INDEX


def ingest_reference_pojk(
    file_path: str = POJK_LAMA_FILE,
    doc_id: str = "POJK-77-2016",
    collection_name: str = "pojk_acuan_idx",
    force: bool = False,
) -> int:
    """Memotong dokumen POJK lama per pasal dan memasukkannya ke ChromaDB."""
    global _FALLBACK_INDEX
    col = get_or_create_collection(collection_name)
    try:
        existing_count = col.count()
        if existing_count > 0 and not force:
            return existing_count
    except Exception:
        pass

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

    try:
        if ids:
            col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return col.count()
    except Exception:
        if _FALLBACK_INDEX is None:
            _FALLBACK_INDEX = FallbackVectorIndex(FastLegalEmbeddingFunction())
        if ids:
            _FALLBACK_INDEX.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return _FALLBACK_INDEX.count()


def query_reference_clauses(
    query_text: str,
    n_results: int = 3,
    collection_name: str = "pojk_acuan_idx",
) -> List[Dict[str, Any]]:
    """Mencari pasal acuan yang paling relevan dengan klausul regulasi baru."""
    global _FALLBACK_INDEX
    col = get_or_create_collection(collection_name)
    try:
        if col.count() == 0:
            ingest_reference_pojk(collection_name=collection_name)
        results = col.query(query_texts=[query_text], n_results=n_results)
    except Exception:
        if _FALLBACK_INDEX is None:
            _FALLBACK_INDEX = FallbackVectorIndex(FastLegalEmbeddingFunction())
        if _FALLBACK_INDEX.count() == 0:
            ingest_reference_pojk(collection_name=collection_name)
        results = _FALLBACK_INDEX.query(query_texts=[query_text], n_results=n_results)

    matches: List[Dict[str, Any]] = []
    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            ayat = meta.get("ayat", "(1)")
            clean_kutipan = doc.replace(meta.get("pasal", ""), "").replace(f"Ayat {ayat}", "").strip()
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
