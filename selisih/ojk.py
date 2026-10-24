"""Modul sinkronisasi dan penelusuran regulasi langsung dari JDIH OJK (Otoritas Jasa Keuangan).

Menyediakan fungsi untuk:
1. Memindai pembaruan POJK terbaru (Sektor Fintech, LPBBTI/P2P Lending, Perbankan, Edukasi & Perlindungan Konsumen).
2. Mengekstrak metadata regulasi (Nomor, Tahun, Judul, Tanggal Berlaku, Status Keberlakuan, Riwayat Pencabutan).
3. Mengunduh berkas PDF regulasi resmi OJK ke direktori lokal.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

JDIH_BASE_URL = "https://jdih.ojk.go.id"
JDIH_LIST_URL = f"{JDIH_BASE_URL}/Web/ViewPeraturan/ListDataPeraturan"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Sektor relevan untuk IT-Finance & Fintech
SECTOR_MAP = {
    "10": "Inovasi Teknologi Sektor Keuangan (ITSK) & Kripto",
    "09": "Lembaga Pembiayaan & LPBBTI (P2P Lending)",
    "04": "Pelindungan Konsumen & Market Conduct",
    "01": "Perbankan",
}


def _clean_html_text(raw_html: str) -> str:
    """Membersihkan tag HTML dan mengembalikan teks murni."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _extract_detail_url(raw_html: str) -> Optional[str]:
    """Mengekstrak URL detail regulasi dari tag anchor."""
    if not raw_html:
        return None
    soup = BeautifulSoup(raw_html, "html.parser")
    a_tag = soup.find("a")
    if a_tag and a_tag.get("href"):
        href = a_tag["href"]
        if href.startswith("http"):
            return href
        return f"{JDIH_BASE_URL}{href}"
    return None


def fetch_ojk_regulations(
    sectors: Optional[List[str]] = None,
    jenis_peraturan: str = "06",  # 06 = Peraturan OJK (POJK)
    timeout: float = 12.0,
    limit_per_sector: int = 10,
) -> List[Dict[str, Any]]:
    """Mengambil daftar POJK terbaru langsung dari JDIH OJK API.
    
    Returns:
        Daftar dictionary berisi metadata regulasi OJK yang dinormalisasi.
    """
    if sectors is None:
        sectors = ["10", "09", "04"]

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    results: List[Dict[str, Any]] = []

    for sector in sectors:
        sector_name = SECTOR_MAP.get(sector, f"Sektor {sector}")
        url = f"{JDIH_LIST_URL}?sektor={sector}&jenisPeraturan={jenis_peraturan}&sLanguage=id"
        try:
            with httpx.Client(verify=False, timeout=timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data.get("aaData", [])

                for item in items[:limit_per_sector]:
                    if not item or len(item) < 2:
                        continue
                    title_html = item[0]
                    title = _clean_html_text(title_html)
                    detail_url = _extract_detail_url(title_html)
                    nomor = item[1] if len(item) > 1 else ""
                    sektor_raw = item[2] if len(item) > 2 else sector_name
                    tanggal_berlaku = item[6] if len(item) > 6 else ""
                    status = item[7] if len(item) > 7 else "Berlaku"

                    # Ekstrak tahun dari judul jika ada
                    tahun_match = re.search(r"Tahun\s+(\d{4})", title, re.IGNORECASE) or re.search(r"/(\d{4})", title)
                    tahun = tahun_match.group(1) if tahun_match else ""

                    # ID unik dari URL detail
                    doc_uuid = ""
                    if detail_url:
                        uuid_match = re.search(r"/Detail/([a-f0-9\-]+)/", detail_url)
                        if uuid_match:
                            doc_uuid = uuid_match.group(1)

                    results.append({
                        "id": doc_uuid or f"POJK-{nomor}-{tahun}",
                        "judul": title,
                        "nomor": nomor,
                        "tahun": tahun,
                        "sektor": sektor_raw or sector_name,
                        "sektor_id": sector,
                        "jenis": "Peraturan OJK",
                        "tanggal_berlaku": tanggal_berlaku.strip() if tanggal_berlaku else "-",
                        "status": status.strip() if status else "Berlaku",
                        "detail_url": detail_url,
                        "download_url": None,  # Diisi saat diminta
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception:
            # Fallback gracefully per sector jika koneksi bermasalah
            continue

    # Urutkan berdasarkan tahun descending (jika tahun ada)
    results.sort(key=lambda x: str(x.get("tahun") or "0"), reverse=True)
    return results


def get_regulation_download_url(detail_url: str, timeout: float = 12.0) -> Optional[str]:
    """Mengunjungi halaman detail regulasi untuk menemukan tautan unduh berkas PDF resmi."""
    if not detail_url:
        return None
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        with httpx.Client(verify=False, timeout=timeout) as client:
            resp = client.get(detail_url, headers=headers)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "")
                text = a.get_text(strip=True).lower()
                if "downloaddokumen" in href.lower() or "unduh" in text:
                    if href.startswith("http"):
                        return href
                    return f"{JDIH_BASE_URL}{href}"
    except Exception:
        return None
    return None


def download_regulation_pdf(
    download_url: str,
    output_path: str,
    timeout: float = 30.0,
) -> bool:
    """Mengunduh berkas PDF regulasi dari URL unduhan resmi OJK."""
    if not download_url:
        return False
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with httpx.Client(verify=False, timeout=timeout) as client:
            with client.stream("GET", download_url, headers=headers) as resp:
                if resp.status_code != 200:
                    return False
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=16384):
                        f.write(chunk)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False
