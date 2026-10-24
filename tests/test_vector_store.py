import os
import shutil
import pytest
from selisih import vector_store

TEST_CHROMA_DIR = os.path.join(os.path.dirname(__file__), "test_chroma_db")

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(TEST_CHROMA_DIR):
        try:
            shutil.rmtree(TEST_CHROMA_DIR)
        except Exception:
            pass

def test_fast_legal_embedding():
    emb_fn = vector_store.FastLegalEmbeddingFunction()
    docs = ["Pasal 8 batas pinjaman", "Pasal 12 bunga harian"]
    embeddings = emb_fn(docs)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 128
    assert len(embeddings[1]) == 128

def test_ingest_and_query_reference_pojk():
    # Ingest ke folder tes lokal
    col = vector_store.get_or_create_collection("test_col", persist_directory=TEST_CHROMA_DIR)
    assert col is not None

    count = vector_store.ingest_reference_pojk(
        collection_name="test_col",
        force=True
    )
    assert count > 0

    # Query pinjaman
    matches = vector_store.query_reference_clauses(
        "Batas maksimum pemberian pinjaman dana adalah sebesar Rp20.000.000",
        n_results=1,
        collection_name="test_col"
    )
    assert len(matches) >= 1
    assert matches[0]["pasal"] == "Pasal 8"
    assert "POJK-77-2016" in matches[0]["doc_id"]
