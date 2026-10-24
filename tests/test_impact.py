"""Pengujian Fase 4: scanner dampak & engine patch deterministik (tanpa jaringan)."""

import json
import os

import selisih.impact as impact


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    cfg = repo / "app" / "core"
    cfg.mkdir(parents=True)
    (cfg / "config.py").write_text(
        "APP_NAME = 'x'\nMAX_LOAN_AMOUNT = 20_000_000\nMAX_DAILY_INTEREST_RATE = 0.004\n",
        encoding="utf-8",
    )
    return repo


def test_load_findings_primary_wins(tmp_path):
    primary = tmp_path / "a.json"
    fallback = tmp_path / "b.json"
    primary.write_text(json.dumps({"findings": ["X"]}), encoding="utf-8")
    fallback.write_text(json.dumps({"findings": ["Y"]}), encoding="utf-8")
    data, path = impact.load_findings(str(primary), str(fallback))
    assert data["findings"] == ["X"]
    assert path == str(primary)


def test_scan_impact_patchable(tmp_path):
    repo = _make_repo(tmp_path)
    findings = {
        "findings": [
            {
                "change_id": "CHG-1",
                "ringkasan": "naikkan plafon",
                "kandidat_kode": [
                    {
                        "path": "app/core/config.py",
                        "evidence": "MAX_LOAN_AMOUNT = 20_000_000",
                        "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                        "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
                    }
                ],
            }
        ]
    }
    records = impact.scan_impact(findings, str(repo))
    assert len(records) == 1
    assert records[0]["status"] == "patchable"
    assert records[0]["lines"] == [2]


def test_scan_impact_missing_file_and_no_match(tmp_path):
    repo = _make_repo(tmp_path)
    findings = {
        "findings": [
            {"change_id": "CHG-2", "kandidat_kode": [{"path": "app/x.py", "old_code": "a"}]},
            {"change_id": "CHG-3", "kandidat_kode": [{"path": "app/core/config.py", "old_code": "ALREADY_NEW"}]},
        ]
    }
    records = impact.scan_impact(findings, str(repo))
    statuses = {r["change_id"]: r["status"] for r in records}
    assert statuses["CHG-2"] == "missing"
    assert statuses["CHG-3"] == "already_or_no_match"


def test_apply_patch_dry_run_then_apply(tmp_path):
    repo = _make_repo(tmp_path)
    records = impact.scan_impact(
        {
            "findings": [
                {
                    "change_id": "CHG-1",
                    "kandidat_kode": [
                        {
                            "path": "app/core/config.py",
                            "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                            "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
                        }
                    ],
                }
            ]
        },
        str(repo),
    )
    target = repo / "app" / "core" / "config.py"

    dry = impact.apply_patch(records, dry_run=True)
    assert dry[0]["status"] == "dry_run_ok"
    assert "20_000_000" in target.read_text(encoding="utf-8")

    applied = impact.apply_patch(records, dry_run=False)
    assert applied[0]["status"] == "applied"
    assert applied[0]["backup_path"] and os.path.exists(applied[0]["backup_path"])
    content = target.read_text(encoding="utf-8")
    assert "MAX_LOAN_AMOUNT = 50_000_000" in content
    assert "MAX_LOAN_AMOUNT = 20_000_000" not in content
    backup_content = open(applied[0]["backup_path"], encoding="utf-8").read()
    assert "MAX_LOAN_AMOUNT = 20_000_000" in backup_content


def test_make_diff_contains_markers(tmp_path):
    diff = impact.make_diff("old\n", "new\n", "app/core/config.py")
    assert "--- a/app/core/config.py" in diff
    assert "+++ b/app/core/config.py" in diff


def test_run_pytest_reports_result(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "test_ok.py").write_text("def test_pass():\n    assert True\n", encoding="utf-8")
    result = impact.run_pytest(str(repo), "test_ok.py")
    assert result["returncode"] == 0
    assert "1 passed" in result["stdout"]


def test_rollback_last_backup(tmp_path):
    repo = _make_repo(tmp_path)
    target = repo / "app" / "core" / "config.py"
    original_text = target.read_text(encoding="utf-8")

    records = impact.scan_impact(
        {
            "findings": [
                {
                    "change_id": "CHG-1",
                    "kandidat_kode": [
                        {
                            "path": "app/core/config.py",
                            "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                            "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
                        }
                    ],
                }
            ]
        },
        str(repo),
    )
    # Apply patch
    impact.apply_patch(records, dry_run=False)
    assert "MAX_LOAN_AMOUNT = 50_000_000" in target.read_text(encoding="utf-8")

    # Rollback
    res = impact.rollback_last_backup(str(repo))
    assert res["status"] == "success"
    assert res["count"] == 1
    assert target.read_text(encoding="utf-8") == original_text

    # Rollback again when no more backups
    res2 = impact.rollback_last_backup(str(repo))
    assert res2["status"] == "no_backups"
    assert res2["count"] == 0
