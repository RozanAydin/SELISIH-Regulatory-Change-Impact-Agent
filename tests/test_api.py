import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "license" in data
    assert "langflow" in data

def test_api_analysis_findings():
    res = client.get("/api/analysis/findings")
    assert res.status_code == 200
    data = res.json()
    assert "findings" in data
    assert "metrics" in data
    assert len(data["findings"]) > 0

def test_api_impact_scan():
    res = client.get("/api/impact/scan")
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert data["records_count"] >= 2

def test_api_impact_dry_run():
    res = client.get("/api/impact/dry-run")
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert "results" in data
    assert "records_count" in data

def test_api_audit_logs():
    res = client.get("/api/audit/logs")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert len(data["logs"]) >= 1

def test_api_ojk_analyze():
    req = {
        "id": "test-pojk-22",
        "judul": "Pelindungan Konsumen Sektor Jasa Keuangan",
        "nomor": "22",
        "tahun": "2023",
        "detail_url": "https://jdih.ojk.go.id/test",
    }
    res = client.post("/api/ojk/analyze", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["findings_count"] >= 1

def test_api_impact_rollback():
    res = client.post("/api/impact/rollback")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "count" in data
    assert "message" in data
    assert "restored" in data


def test_api_license_profiles_and_switching():
    # 1. Ambil daftar profil
    res = client.get("/api/license/profiles")
    assert res.status_code == 200
    data = res.json()
    assert len(data["profiles"]) == 3
    org_names = [p["organization"] for p in data["profiles"]]
    assert "PT Bank Digital Nusantara" in org_names
    assert "PT Dana Mandiri Fintech" in org_names
    assert "PT Pinjaman Kilat Indonesia" in org_names

    # 2. Ganti profil ke Starter (Pinjaman Kilat) yang kuota penuh
    res2 = client.post("/api/license/select", json={"company_id": "pinjaman_kilat"})
    assert res2.status_code == 200
    assert res2.json()["company"]["plan"] == "starter"
    assert res2.json()["company"]["can_run"] is False

    # 3. Upaya menambahkan repo baru saat kuota penuh (5/5) harus ditolak
    res3 = client.post("/api/license/add-repo", json={"company_id": "pinjaman_kilat", "name": "new-svc", "path": "test"})
    assert res3.status_code == 400

    # 4. Kembalikan ke Bank Digital Nusantara (Enterprise)
    res4 = client.post("/api/license/select", json={"company_id": "bank_digital"})
    assert res4.status_code == 200
    assert res4.json()["company"]["can_run"] is True


def test_api_rbac_guard():
    # Role tidak sah ditolak dengan 403
    bad_res = client.post(
        "/api/impact/apply",
        json={"reviewer_role": "Hacker", "confirm": False},
        headers={"X-User-Role": "UnauthorizedRole"},
    )
    assert bad_res.status_code == 403
    assert "Akses ditolak" in bad_res.json()["detail"]

    # Role yang diizinkan (Compliance Officer / Admin / Engineer) diizinkan
    good_res = client.post(
        "/api/impact/apply",
        json={"reviewer_role": "Compliance Officer", "confirm": False},
        headers={"X-User-Role": "Compliance Officer"},
    )
    assert good_res.status_code == 200



