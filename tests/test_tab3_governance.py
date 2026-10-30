"""
Unit tests untuk Tata Kelola & Tinjauan Manusia (Tab 3 Governance):
- Granular patch selection (allowed_change_ids)
- Endpoint POST /api/impact/apply dengan granular selection
- Endpoint GET /api/impact/compliance-report (Berita Acara Kepatuhan)
"""

import os
import pytest
from fastapi.testclient import TestClient
from api import app, MOCK_REPO_DIR
from selisih import impact


@pytest.fixture(autouse=True)
def restore_baseline():
    """Memastikan repo mock dalam kondisi baseline sebelum dan sesudah setiap test."""
    config_py = os.path.join(MOCK_REPO_DIR, "app", "core", "config.py")
    with open(config_py, "r", encoding="utf-8") as f:
        original_content = f.read()

    yield

    # Pulihkan content asli
    with open(config_py, "w", encoding="utf-8") as f:
        f.write(original_content)

    # Bersihkan file .bak yang mungkin dibuat selama test
    core_dir = os.path.dirname(config_py)
    for fname in os.listdir(core_dir):
        if fname.startswith("config.py.bak."):
            try:
                os.remove(os.path.join(core_dir, fname))
            except OSError:
                pass


def test_granular_apply_patch_unit():
    """Uji unit selisih.impact.apply_patch dengan filter allowed_change_ids."""
    dummy_records = [
        {
            "change_id": "CHG-001",
            "pasal": "Pasal 19",
            "path": os.path.join(MOCK_REPO_DIR, "app", "core", "config.py"),
            "line": 8,
            "old_code": "MAX_LOAN_AMOUNT = 20_000_000\n",
            "proposed_code": "MAX_LOAN_AMOUNT = 10_000_000\n",
            "status": "patchable",
        },
        {
            "change_id": "CHG-002",
            "pasal": "Pasal 20",
            "path": os.path.join(MOCK_REPO_DIR, "app", "core", "config.py"),
            "line": 9,
            "old_code": "MAX_DAILY_INTEREST_RATE = 0.004\n",
            "proposed_code": "MAX_DAILY_INTEREST_RATE = 0.003\n",
            "status": "patchable",
        },
    ]

    # Uji 1: Hanya izinkan CHG-001
    results = impact.apply_patch(dummy_records, dry_run=False, allowed_change_ids=["CHG-001"])
    assert len(results) == 2

    res_001 = next(r for r in results if r["change_id"] == "CHG-001")
    res_002 = next(r for r in results if r["change_id"] == "CHG-002")

    assert res_001["status"] == "applied"
    assert res_002["status"] == "skip"
    assert "ditunda" in res_002["message"].lower()

    # Periksa isi file: MAX_LOAN_AMOUNT berubah, tapi MAX_DAILY_INTEREST_RATE tetap
    config_py = os.path.join(MOCK_REPO_DIR, "app", "core", "config.py")
    with open(config_py, "r", encoding="utf-8") as f:
        content = f.read()

    assert "MAX_LOAN_AMOUNT = 10_000_000" in content
    assert "MAX_DAILY_INTEREST_RATE = 0.004" in content


def test_api_apply_patch_with_selected_change_ids():
    """Uji API POST /api/impact/apply dengan selected_change_ids."""
    client = TestClient(app)

    # Dapatkan scan records terkini
    scan_res = client.get("/api/impact/scan")
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    records = scan_data.get("records", [])

    # Cari change_id yang patchable
    patchable_cids = [r["change_id"] for r in records if r.get("status") == "patchable" and r.get("change_id")]
    if not patchable_cids:
        pytest.skip("Tidak ada record patchable untuk diuji")

    selected = [patchable_cids[0]]  # pilih hanya record pertama

    payload = {
        "confirm": True,
        "reviewer_role": "Compliance Officer",
        "reviewer_note": "Menyetujui batas atas pinjaman, menunda perubahan suku bunga.",
        "selected_change_ids": selected,
    }

    res = client.post(
        "/api/impact/apply",
        json=payload,
        headers={"X-User-Role": "Compliance Officer"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    # Periksa hasil apply
    results = data.get("results", [])
    applied_cids = [r["change_id"] for r in results if r.get("status") == "applied"]
    skipped_cids = [r["change_id"] for r in results if r.get("status") == "skip"]

    # Record terpilih harus diaplikasikan
    for sel_id in selected:
        assert sel_id in applied_cids

    # Jika ada change_id lain, pastikan masuk skip
    other_cids = [cid for cid in patchable_cids if cid not in selected]
    for oth_id in other_cids:
        assert oth_id in skipped_cids


def test_api_compliance_report_generation():
    """Uji endpoint GET /api/impact/compliance-report menghasilkan sertifikasi resmi audit OJK."""
    client = TestClient(app)

    # 1. Terapkan patch terlebih dahulu agar ada riwayat audit
    apply_payload = {
        "confirm": True,
        "reviewer_role": "Compliance Officer",
        "reviewer_note": "Verifikasi mandatori POJK 22/2023 disetujui penuh.",
        "selected_change_ids": ["CHG-001"],
    }
    apply_res = client.post(
        "/api/impact/apply",
        json=apply_payload,
        headers={"X-User-Role": "Compliance Officer"},
    )
    assert apply_res.status_code == 200

    # 2. Ambil compliance report
    res = client.get("/api/impact/compliance-report")
    assert res.status_code == 200
    report = res.json()

    # Periksa struktur berita acara
    assert "report_id" in report
    assert report["report_id"].startswith("CERT-OJK-")
    assert "title" in report
    assert "organization" in report
    assert "target_repository" in report
    assert "regulations" in report
    assert "acuan" in report["regulations"]
    assert "pembaruan" in report["regulations"]

    # Periksa data governance sign-off
    signoff = report["governance_signoff"]
    assert signoff["reviewer_role"] == "Compliance Officer"
    assert "Verifikasi mandatori" in signoff["reviewer_note"]
    assert signoff["status"] == "APPROVED_AND_PATCHED"
    assert signoff["signed_at"] is not None

    # Periksa ringkasan kepatuhan
    summary = report["summary"]
    assert "total_findings" in summary
    assert "code_patches_applied" in summary
    assert "policy_action_items" in summary
    assert isinstance(report["applied_patches"], list)
    assert isinstance(report["policy_actions"], list)
