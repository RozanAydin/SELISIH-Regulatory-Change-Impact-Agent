"""Pengujian Fase 3: ekspor artefak untuk IBM Bob (tanpa jaringan/Bob)."""

import json
import os
import subprocess
import sys

import selisih.artifacts as artifacts
import selisih.impact as impact

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLDEN = os.path.join(ROOT, "data", "temuan_golden_path.json")
REPO = os.path.join(ROOT, "mock_fintech_repo")


def _golden():
    with open(GOLDEN, "r", encoding="utf-8") as f:
        return json.load(f)


def test_build_artifacts_writes_files(tmp_path):
    summary = artifacts.build_artifacts(_golden(), REPO, str(tmp_path))
    for name in ("impact_report.json", "proposed_patch.diff", "generated_tests.py"):
        assert os.path.isfile(os.path.join(tmp_path, name))
    assert summary["kandidat_kode"] == 2
    assert summary["patchable"] == 2
    assert summary["skipped"] == 0

    diff = (tmp_path / "proposed_patch.diff").read_text(encoding="utf-8")
    assert "--- a/app/core/config.py" in diff
    assert "+++ b/app/core/config.py" in diff
    assert "MAX_LOAN_AMOUNT = 50_000_000" in diff
    assert "MAX_DAILY_INTEREST_RATE = 0.001" in diff

    report = json.loads((tmp_path / "impact_report.json").read_text(encoding="utf-8"))
    assert len(report["records"]) == 2
    assert report["records"][0]["status"] == "patchable"


def test_generated_tests_syntax_and_content(tmp_path):
    summary = artifacts.build_artifacts(_golden(), REPO, str(tmp_path))
    tests = (tmp_path / "generated_tests.py").read_text(encoding="utf-8")
    compile(tests, "generated_tests.py", "exec")
    assert "def test_updated_statutory_limits():"
    assert "assert MAX_LOAN_AMOUNT == 50_000_000  # CHG-POJK-001" in tests
    assert "assert MAX_DAILY_INTEREST_RATE == 0.001  # CHG-POJK-002" in tests


def test_generated_tests_pass_against_patched_repo(tmp_path):
    artifacts.build_artifacts(_golden(), REPO, str(tmp_path))
    target = os.path.join(REPO, "app", "core", "config.py")
    original = open(target, encoding="utf-8").read()
    try:
        applied = impact.apply_patch(impact.scan_impact(_golden(), REPO), dry_run=False)
        assert all(r["status"] == "applied" for r in applied)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp_path / "generated_tests.py"), "-q"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "1 passed" in result.stdout
    finally:
        with open(target, "w", encoding="utf-8") as f:
            f.write(original)
        for backup in os.listdir(os.path.join(REPO, "app", "core")):
            if backup.startswith("config.py.bak."):
                os.remove(os.path.join(REPO, "app", "core", backup))