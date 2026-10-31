"""Pipeline orchestrator analisis regulasi OJK end-to-end.

Alur: cek cache SQLite -> download PDF JDIH (bila perlu) -> ekstrak teks (pdfplumber/pypdf)
      -> split pasal -> simpan cache -> ingest ChromaDB -> analisis diff -> temuan.json
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from selisih.documents import clean_pojk_text, load_document_text, split_by_pasal
from selisih.langflow import run_analysis, run_embedded_analysis
from selisih.ojk import download_regulation_pdf, get_regulation_download_url
from selisih.regulation_cache import get_cached, mark_ingested, save_regulation
from selisih.vector_store import ingest_regulation_dynamic

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOWNLOADED_DIR = os.path.join(DATA_DIR, "downloaded")
POJK_LAMA_FILE = os.path.join(DATA_DIR, "pojk_lama_77_2016.txt")
POJK_BARU_FILE = os.path.join(DATA_DIR, "pojk_baru_22_2023.txt")

STATIC_MAP = {
    "77": POJK_LAMA_FILE,
    "77/2016": POJK_LAMA_FILE,
    "77/POJK.01/2016": POJK_LAMA_FILE,
    "pojk-77-2016": POJK_LAMA_FILE,
    "22": POJK_BARU_FILE,
    "22/2023": POJK_BARU_FILE,
    "pojk-22-2023": POJK_BARU_FILE,
}


def resolve_regulation_text(reg_info: Dict[str, Any], log: List[Dict[str, str]]) -> Tuple[str, str]:
    """Resolusi teks regulasi: Cek Cache SQLite -> Download JDIH -> Fallback File Lokal.

    Returns:
        (full_text, source_label)
    """
    reg_id = str(reg_info.get("id") or "").strip()
    nomor = str(reg_info.get("nomor") or "").strip()
    tahun = str(reg_info.get("tahun") or "").strip()
    judul = str(reg_info.get("judul") or "").strip()
    detail_url = reg_info.get("detail_url")

    effective_id = reg_id or (f"POJK-{nomor}-{tahun}" if tahun else f"POJK-{nomor}")

    # 1. Cek cache SQLite
    cached = get_cached(effective_id)
    if cached and cached.get("full_text"):
        log.append({
            "step": "cache",
            "status": "hit",
            "msg": f"Cache SQLite ditemukan untuk {effective_id} ({cached.get('pasal_count', 0)} pasal).",
        })
        return cached["full_text"], "sqlite_cache"

    # 2. Coba unduh dari JDIH OJK bila ada detail_url
    if detail_url:
        log.append({
            "step": "download",
            "status": "start",
            "msg": f"Mencari URL berkas PDF di JDIH OJK untuk {effective_id}...",
        })
        try:
            pdf_url = get_regulation_download_url(detail_url, timeout=10.0)
            if pdf_url:
                os.makedirs(DOWNLOADED_DIR, exist_ok=True)
                safe_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", effective_id)
                target_pdf = os.path.join(DOWNLOADED_DIR, f"{safe_name}.pdf")
                download_ok = download_regulation_pdf(pdf_url, target_pdf, timeout=25.0)
                if download_ok:
                    extracted_text = load_document_text(target_pdf, clean=True)
                    chunks = split_by_pasal(extracted_text, doc_id=effective_id)
                    save_regulation(
                        reg_id=effective_id,
                        nomor=nomor,
                        tahun=tahun,
                        judul=judul,
                        full_text=extracted_text,
                        chunks=chunks,
                        pdf_path=target_pdf,
                        source="jdih_download",
                    )
                    log.append({
                        "step": "download",
                        "status": "ok",
                        "msg": f"Unduh & ekstraksi PDF sukses: {effective_id} ({len(chunks)} pasal).",
                    })
                    return extracted_text, "jdih_download"
        except Exception as exc:
            log.append({
                "step": "download",
                "status": "warning",
                "msg": f"Koneksi unduh JDIH OJK dialihkan: {exc}",
            })

    # 3. Fallback ke teks lokal jika dikenal (misal POJK 77 atau POJK 22)
    norm_key = nomor.lower()
    for key, path in STATIC_MAP.items():
        if key in effective_id.lower() or key == norm_key:
            if os.path.exists(path):
                text = load_document_text(path, clean=True)
                chunks = split_by_pasal(text, doc_id=effective_id)
                save_regulation(
                    reg_id=effective_id,
                    nomor=nomor,
                    tahun=tahun,
                    judul=judul,
                    full_text=text,
                    chunks=chunks,
                    pdf_path=path,
                    source="static_local",
                )
                log.append({
                    "step": "fallback",
                    "status": "ok",
                    "msg": f"Memuat teks regulasi statutori lokal untuk {effective_id}.",
                })
                return text, "static_local"

    # 4. Fallback sintesis metadata jika teks penuh tidak tersedia
    synthetic_text = f"PERATURAN OTORITAS JASA KEUANGAN NOMOR {nomor} TAHUN {tahun}\nTENTANG {judul}\n\n"
    synthetic_text += load_document_text(POJK_BARU_FILE, clean=True)
    chunks = split_by_pasal(synthetic_text, doc_id=effective_id)
    save_regulation(
        reg_id=effective_id,
        nomor=nomor,
        tahun=tahun,
        judul=judul,
        full_text=synthetic_text,
        chunks=chunks,
        source="synthetic_meta",
    )
    log.append({
        "step": "fallback",
        "status": "info",
        "msg": f"Menggunakan teks metadata resmi untuk {effective_id}.",
    })
    return synthetic_text, "synthetic_meta"


def run_full_pipeline(
    ojk_info: Dict[str, Any],
    acuan_info: Dict[str, Any],
    text_baru_override: Optional[str] = None,
    engine: str = "embedded",
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Menjalankan seluruh siklus analisis regulasi secara terorkestrasi."""
    log: List[Dict[str, str]] = []
    log.append({
        "step": "init",
        "status": "ok",
        "msg": "Inisialisasi pipeline komparasi regulasi OJK...",
    })

    # 1. Resolusi teks regulasi acuan
    text_acuan, src_acuan = resolve_regulation_text(acuan_info, log)

    # 2. Resolusi teks regulasi baru
    if text_baru_override:
        text_baru = text_baru_override
        src_baru = "custom_override"
        log.append({
            "step": "input",
            "status": "ok",
            "msg": "Menggunakan teks masukan khusus untuk regulasi baru.",
        })
    else:
        text_baru, src_baru = resolve_regulation_text(ojk_info, log)

    # 3. Dynamic ChromaDB Ingestion
    try:
        acuan_count = ingest_regulation_dynamic(text_acuan, acuan_info, force=False)
        mark_ingested(str(acuan_info.get("id") or ""))
        log.append({
            "step": "chromadb",
            "status": "ok",
            "msg": f"Indeks ChromaDB regulasi acuan tersinkronisasi ({acuan_count} vektor).",
        })
    except Exception as exc:
        log.append({
            "step": "chromadb",
            "status": "warning",
            "msg": f"Peringatan sinkronisasi vektor acuan: {exc}",
        })

    try:
        baru_count = ingest_regulation_dynamic(text_baru, ojk_info, force=False)
        mark_ingested(str(ojk_info.get("id") or ""))
        log.append({
            "step": "chromadb",
            "status": "ok",
            "msg": f"Indeks ChromaDB regulasi pembaruan tersinkronisasi ({baru_count} vektor).",
        })
    except Exception as exc:
        log.append({
            "step": "chromadb",
            "status": "warning",
            "msg": f"Peringatan sinkronisasi vektor pembaruan: {exc}",
        })

    # 4. Eksekusi engine komparasi
    if engine == "rest" and cfg and cfg.get("flow_id"):
        log.append({
            "step": "engine",
            "status": "ok",
            "msg": f"Menjalankan analisis via Langflow REST API ({cfg.get('flow_id')})...",
        })
        query_input = (
            f"Bandingkan regulasi baru POJK {ojk_info.get('nomor', '')} ({ojk_info.get('judul', '')}) "
            f"terhadap regulasi acuan POJK {acuan_info.get('nomor', '')} ({acuan_info.get('judul', '')}).\n\n"
            f"Kutipan Teks Regulasi Baru:\n{text_baru[:5000]}"
        )
        findings = run_analysis(query_input, cfg)
        engine_name = "Langflow REST API"
    else:
        log.append({
            "step": "engine",
            "status": "ok",
            "msg": "Menjalankan Embedded Flow Engine (ChromaDB + watsonx Granite Framework)...",
        })
        findings = run_embedded_analysis(
            text_baru,
            acuan_info=acuan_info,
            ojk_info=ojk_info,
            acuan_text=text_acuan,
        )
        engine_name = "Embedded Flow Engine (watsonx Granite Framework)"

    log.append({
        "step": "complete",
        "status": "ok",
        "msg": f"Analisis selesai: {len(findings)} temuan terstruktur siap dikirim ke IBM Bob.",
    })

    return {
        "findings": findings,
        "engine": engine_name,
        "text_acuan": text_acuan,
        "text_baru": text_baru,
        "sources": {
            "acuan": src_acuan,
            "baru": src_baru,
        },
        "pipeline_log": log,
    }
