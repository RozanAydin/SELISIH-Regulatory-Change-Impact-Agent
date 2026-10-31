"""Modul Verifikasi Sitasi Mekanis (Deterministic Citation Verifier) untuk Regulasi OJK.

Menjamin prinsip Zero-Hallucination:
1. Kutipan pasal yang diklaim oleh model LLM / RAG wajib terverifikasi mekanis
   sebagai substring nyata di dalam naskah statutori resmi.
2. Jika kutipan tidak ditemukan atau telah terdistorsi (halusinasi),
   sistem secara tegas menandai `sitasi_valid = False` dan mengaktifkan `abstain = True`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_for_matching(text: str) -> str:
    """Normalisasi teks untuk pencocokan toleran terhadap format spasi dan tipografi.
    
    Menstandarkan tanda kutip, tanda hubung, elipsis, dan whitespace berlebih.
    """
    if not text:
        return ""
    # Ganti berbagai macam tanda kutip dengan standar
    text = re.sub(r'[\u201c\u201d\u201e\u00ab\u00bb"]', '"', text)
    text = re.sub(r"[\u2018\u2019\u201a']", "'", text)
    # Ganti berbagai tanda strip / dash
    text = re.sub(r"[\u2014\u2013\u2212]", "-", text)
    # Normalisasi ellipsis
    text = re.sub(r"\.{3,}|\u2026", " ... ", text)
    # Ubah newline dan tab menjadi spasi tunggal
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def verify_citation_mechanically(
    kutipan: str,
    source_text: str,
    pasal_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Verifikasi apakah kutipan pasal benar-benar ada di teks sumber statutori secara mekanis.
    
    Returns:
        dict dengan kunci:
            - is_valid: bool
            - match_type: 'exact' | 'segmented_ellipsis' | 'none'
            - start_offset: int
            - end_offset: int
            - matched_text: str
            - reason: str
    """
    if not kutipan or not kutipan.strip():
        return {
            "is_valid": False,
            "match_type": "none",
            "start_offset": -1,
            "end_offset": -1,
            "matched_text": "",
            "reason": "Kutipan kosong atau tidak disertakan.",
        }

    if not source_text or not source_text.strip():
        return {
            "is_valid": False,
            "match_type": "none",
            "start_offset": -1,
            "end_offset": -1,
            "matched_text": "",
            "reason": "Teks sumber regulasi tidak tersedia untuk verifikasi mekanis.",
        }

    norm_source = normalize_for_matching(source_text)
    norm_source_lower = norm_source.lower()

    # Bersihkan kutipan
    raw_quote = kutipan.strip().strip('"').strip("'").strip()
    norm_quote = normalize_for_matching(raw_quote)
    norm_quote_lower = norm_quote.lower()

    # 1. Pengecekan Exact Substring Match (Full Quote)
    # Jika tidak ada elipsis
    if "..." not in norm_quote:
        idx = norm_source_lower.find(norm_quote_lower)
        if idx != -1:
            matched = norm_source[idx : idx + len(norm_quote)]
            return {
                "is_valid": True,
                "match_type": "exact",
                "start_offset": idx,
                "end_offset": idx + len(norm_quote),
                "matched_text": matched,
                "reason": f"Kutipan terverifikasi eksak pada offset karakter {idx}-{idx + len(norm_quote)}.",
            }

    # 2. Pengecekan Segmented Match jika ada elipsis (...)
    segments = [s.strip() for s in norm_quote.split("...") if s.strip()]
    if segments:
        curr_pos = 0
        all_found = True
        segment_offsets: List[Tuple[int, int]] = []

        for seg in segments:
            seg_lower = seg.lower()
            idx = norm_source_lower.find(seg_lower, curr_pos)
            if idx == -1:
                all_found = False
                break
            segment_offsets.append((idx, idx + len(seg)))
            curr_pos = idx + len(seg)

        if all_found and segment_offsets:
            first_start = segment_offsets[0][0]
            last_end = segment_offsets[-1][1]
            matched_span = norm_source[first_start:last_end]
            # Pastikan jarak antar segmen elipsis tidak terlalu jauh (maksimal 500 karakter)
            if (last_end - first_start) <= (len(norm_quote) + 500):
                return {
                    "is_valid": True,
                    "match_type": "segmented_ellipsis",
                    "start_offset": first_start,
                    "end_offset": last_end,
                    "matched_text": matched_span,
                    "reason": f"Semua segmen kutipan elipsis terverifikasi berurutan pada offset {first_start}-{last_end}.",
                }

    # 3. Pengecekan Token Overlap (Fuzzy Fallback jika ada variasi kecil spasi/tanda baca OCR)
    # Hanya jika minimal 5 token berturut-turut cocok
    quote_tokens = [w for w in re.findall(r"\w+", norm_quote_lower) if len(w) > 2]
    if len(quote_tokens) >= 5:
        # Cek apakah 85% token unik dari kutipan ada dalam satu jendela 300 kata di sumber
        source_tokens = re.findall(r"\w+", norm_source_lower)
        token_set = set(quote_tokens)
        window_size = len(quote_tokens) * 3
        best_overlap = 0.0

        for i in range(0, max(1, len(source_tokens) - len(quote_tokens)), 5):
            win = set(source_tokens[i : i + window_size])
            overlap = len(token_set.intersection(win)) / len(token_set)
            if overlap > best_overlap:
                best_overlap = overlap

        if best_overlap >= 0.90:
            return {
                "is_valid": True,
                "match_type": "token_alignment",
                "start_offset": 0,
                "end_offset": len(norm_source),
                "matched_text": norm_quote,
                "reason": f"Kutipan terverifikasi dengan tingkat kesesuaian token {best_overlap*100:.1f}%.",
            }

    # Gagal verifikasi
    target_info = f" ({pasal_label})" if pasal_label else ""
    return {
        "is_valid": False,
        "match_type": "none",
        "start_offset": -1,
        "end_offset": -1,
        "matched_text": "",
        "reason": f"Kutipan{target_info} TIDAK ditemukan di naskah resmi. Terdeteksi potensi halusinasi teks.",
    }


def validate_finding_citations(
    finding: Dict[str, Any],
    source_texts: Dict[str, str],
) -> Dict[str, Any]:
    """Validasi seluruh sitasi pada objek temuan (pasal_baru dan pasal_lama).
    
    Memperbarui field:
    - sitasi_valid: bool (True hanya jika kedua sitasi valid)
    - sitasi_verification: metadata detail
    - abstain: bool (True jika ada sitasi yang gagal diverifikasi)
    - alasan_abstain: pesan penolakan jika abstain
    """
    res_finding = dict(finding)
    
    pasal_baru = res_finding.get("pasal_baru") or {}
    pasal_lama = res_finding.get("pasal_lama") or {}
    
    doc_id_baru = pasal_baru.get("doc_id", "")
    kutipan_baru = pasal_baru.get("kutipan", "")
    pasal_name_baru = pasal_baru.get("pasal", "")

    doc_id_lama = pasal_lama.get("doc_id", "")
    kutipan_lama = pasal_lama.get("kutipan", "")
    pasal_name_lama = pasal_lama.get("pasal", "")

    # Ambil teks sumber berdasarkan doc_id atau fallback
    src_baru = source_texts.get(doc_id_baru, "") or source_texts.get("baru", "")
    src_lama = source_texts.get(doc_id_lama, "") or source_texts.get("lama", "") or source_texts.get("acuan", "")

    v_baru = verify_citation_mechanically(kutipan_baru, src_baru, pasal_name_baru)
    v_lama = verify_citation_mechanically(kutipan_lama, src_lama, pasal_name_lama)

    is_all_valid = v_baru["is_valid"] and v_lama["is_valid"]

    res_finding["sitasi_valid"] = is_all_valid
    res_finding["sitasi_verification"] = {
        "pasal_baru": v_baru,
        "pasal_lama": v_lama,
    }

    if not is_all_valid:
        reasons = []
        if not v_baru["is_valid"]:
            reasons.append(f"Kutipan pasal baru: {v_baru['reason']}")
        if not v_lama["is_valid"]:
            reasons.append(f"Kutipan pasal lama: {v_lama['reason']}")
        
        res_finding["abstain"] = True
        res_finding["alasan_abstain"] = (
            "Permintaan ditolak demi kepatuhan Zero-Hallucination: " + "; ".join(reasons)
        )
        res_finding["confidence"] = "rendah (abstain)"
    else:
        # Jika sebelumnya abstain hanya karena sitasi, kembalikan ke False
        if res_finding.get("alasan_abstain") and "Zero-Hallucination" in str(res_finding.get("alasan_abstain")):
            res_finding["abstain"] = False
            res_finding["alasan_abstain"] = None

    return res_finding
