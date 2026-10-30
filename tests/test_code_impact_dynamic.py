"""Unit test komprehensif untuk pemindai dampak kode dinamis & integrasi artefak Bob (Fase 11)."""

import json
import os
import pytest
from fastapi.testclient import TestClient

import selisih.impact as impact
import selisih.artifacts as artifacts
from api import app

client = TestClient(app)


@pytest.fixture
def temp_fintech_repo(tmp_path):
    """Membuat struktur repositori fintech simulasi."""
    repo = tmp_path / "fintech_app"
    repo.mkdir()
    core = repo / "core"
    core.mkdir()
    services = repo / "services"
    services.mkdir()

    # Berkas konfigurasi batas
    config_file = core / "settings.py"
    config_file.write_text(
        "# Konfigurasi Batas Operasional Fintech\n"
        "APP_NAME = 'NusantaraCore'\n"
        "DEBUG = False\n"
        "MAX_LOAN_AMOUNT = 20_000_000\n"
        "MAX_DAILY_INTEREST_RATE = 0.004\n"
        "SYSTEM_CURRENCY = 'IDR'\n",
        encoding="utf-8",
    )

    # Berkas service logika pinjaman
    service_file = services / "lending.py"
    service_file.write_text(
        "from core.settings import MAX_LOAN_AMOUNT\n\n"
        "def check_loan(amount: float) -> bool:\n"
        "    return amount <= MAX_LOAN_AMOUNT\n",
        encoding="utf-8",
    )

    return repo


def test_scan_repo_for_compliance_targets(temp_fintech_repo):
    """Memastikan scanner dinamis mendeteksi variabel moneter dan bunga di repo tanpa asumsi path statis."""
    matches = impact.scan_repo_for_compliance_targets(
        str(temp_fintech_repo),
        target_values=["20_000_000", "0.004"],
        keywords=["loan", "rate", "max"],
    )
    assert len(matches) >= 2
    paths = {m["path"] for m in matches}
    assert "core/settings.py" in paths

    found_loan = any("MAX_LOAN_AMOUNT = 20_000_000" in m["code"] for m in matches)
    found_rate = any("MAX_DAILY_INTEREST_RATE = 0.004" in m["code"] for m in matches)
    assert found_loan is True
    assert found_rate is True


def test_scan_impact_dynamic_classification(temp_fintech_repo):
    """Memverifikasi pemisahan temuan menjadi code_patchable dan policy_action_required."""
    findings_payload = {
        "findings": [
            {
                "change_id": "CHG-001",
                "ringkasan": "Peningkatan batas pinjaman per POJK 22/2023",
                "pasal_lama": {"kutipan": "Batas pinjaman tidak melebihi Rp 20_000_000"},
                "pasal_baru": {"kutipan": "Batas pinjaman dinaikkan menjadi Rp 50_000_000"},
            },
            {
                "change_id": "CHG-002",
                "ringkasan": "Kewajiban pembentukan Unit Edukasi dan Perlindungan Konsumen",
                "pasal_lama": {"kutipan": "Penyelenggara menyediakan layanan konsumen"},
                "pasal_baru": {"kutipan": "Penyelenggara wajib membentuk unit khusus perlindungan konsumen"},
            },
        ]
    }

    records = impact.scan_impact(findings_payload, str(temp_fintech_repo))
    assert len(records) >= 2

    patchable = [r for r in records if r["category"] == "code_patchable"]
    policy = [r for r in records if r["category"] == "policy_action_required"]

    assert len(patchable) >= 1
    assert patchable[0]["status"] == "patchable"
    assert "core/settings.py" in patchable[0]["path"]

    assert len(policy) >= 1
    assert policy[0]["status"] == "policy_guidance"


def test_make_diff_with_context_lines():
    """Memastikan diff unified menghasilkan baris konteks ketika konten berkas lengkap tersedia."""
    full_content = (
        "# Header\n"
        "APP = 1\n"
        "ENV = 'prod'\n"
        "MAX_LOAN_AMOUNT = 20_000_000\n"
        "OTHER = 2\n"
        "FOOTER = 3\n"
    )
    diff = impact.make_diff(
        old_code="MAX_LOAN_AMOUNT = 20_000_000",
        proposed_code="MAX_LOAN_AMOUNT = 50_000_000",
        rel_path="core/settings.py",
        full_file_content=full_content,
    )
    assert "--- a/core/settings.py" in diff
    assert "+++ b/core/settings.py" in diff
    assert "-MAX_LOAN_AMOUNT = 20_000_000" in diff
    assert "+MAX_LOAN_AMOUNT = 50_000_000" in diff
    # Context lines should be included
    assert " ENV = 'prod'" in diff
    assert " OTHER = 2" in diff


def test_build_artifacts_with_context_diff(temp_fintech_repo, tmp_path):
    """Memastikan paket artefak menghasilkan diff berkonteks dan berkas uji kepatuhan."""
    out_dir = tmp_path / "artifacts_out"
    findings = {
        "findings": [
            {
                "change_id": "CHG-TEST-1",
                "ringkasan": "Plafon pinjaman",
                "kandidat_kode": [
                    {
                        "path": "core/settings.py",
                        "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                        "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
                        "alasan": "Penyelarasan limit batas",
                    }
                ],
            }
        ]
    }
    summary = artifacts.build_artifacts(findings, str(temp_fintech_repo), str(out_dir))
    assert summary["patchable"] == 1

    diff_content = (out_dir / "proposed_patch.diff").read_text(encoding="utf-8")
    assert "-MAX_LOAN_AMOUNT = 20_000_000" in diff_content
    assert "+MAX_LOAN_AMOUNT = 50_000_000" in diff_content
    assert "DEBUG = False" in diff_content  # baris konteks terbukti termuat!


def test_api_bob_launch_desktop_endpoint():
    """Memastikan endpoint peluncur desktop IBM Bob merespons dengan struktur status."""
    res = client.post("/api/bob/launch-desktop")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "app" in data
    assert data["app"] == "IBM Bob"
