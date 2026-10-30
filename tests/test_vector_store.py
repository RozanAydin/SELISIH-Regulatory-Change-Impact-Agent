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


def test_ingest_regulation_dynamic():
    text = (
        "Pasal 10\n(1) Batas modal disetor minimal Rp 25.000.000.000.\n"
        "\nPasal 11\n(1) Tata kelola manajemen risiko wajib dipatuhi.\n"
    )
    reg_info = {
        "id": "pojk-10-2022",
        "nomor": "10/POJK.05/2022",
        "tahun": "2022",
        "doc_id": "POJK-10-2022",
    }
    col_name = "test_dynamic_col"
    count = vector_store.ingest_regulation_dynamic(
        text=text,
        reg_info=reg_info,
        collection_name=col_name,
        force=True,
    )
    assert count >= 2

    # Query matching clause
    matches = vector_store.query_reference_clauses(
        "modal disetor minimal",
        n_results=1,
        collection_name=col_name,
    )
    assert len(matches) >= 1
    assert "Pasal 10" in matches[0]["full_text"]

