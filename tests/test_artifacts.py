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


def test_ensure_mcp_config_creates_files(tmp_path):
    server_script = os.path.join(ROOT, "mcp_server.py")
    res = artifacts.ensure_mcp_config(str(tmp_path), server_script)

    assert os.path.isfile(res["bob"])
    assert os.path.isfile(res["instruction"])

    bob_data = json.loads((tmp_path / ".bob" / "mcp.json").read_text(encoding="utf-8"))
    assert "selisih-local" in bob_data["mcpServers"]
    assert bob_data["mcpServers"]["selisih-local"]["args"][0].endswith("mcp_server.py")


def test_launch_ide_priority_bob(tmp_path, monkeypatch):
    launched_cmd = []

    def fake_popen(cmd, **kwargs):
        launched_cmd.append(cmd)
        return None

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setenv("BOB_PATH", "C:/MockPath/bob.exe")

    res = artifacts.launch_ide(str(tmp_path))
    assert res["status"] == "launched"
    assert res["app"] == "IBM Bob"
    assert len(launched_cmd) == 1
    assert launched_cmd[0][0] == "C:/MockPath/bob.exe"
    assert launched_cmd[0][1] == str(tmp_path)


def test_launch_ide_not_installed(tmp_path, monkeypatch):
    monkeypatch.delenv("BOB_PATH", raising=False)
    monkeypatch.setattr(artifacts.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(os.path, "isfile", lambda p: False)

    res = artifacts.launch_ide(str(tmp_path))
    assert res["status"] == "not_installed"
    assert res["app"] == "IBM Bob"
    assert "Aplikasi IBM Bob belum ditemukan" in res["message"]


def test_check_bob_status(monkeypatch):
    monkeypatch.setattr(artifacts, "find_bob_executable", lambda: "C:/MockPath/bobide.cmd")
    monkeypatch.setattr(os.path, "isdir", lambda p: True)
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    status = artifacts.check_bob_status()
    assert status["installed"] is True
    assert status["session_active"] is True
    assert status["status_label"] == "Aktif & Terhubung"


def test_run_bob_shell_agent(tmp_path):
    findings = _golden()
    result = artifacts.run_bob_shell_agent(REPO, findings)
    assert result["status"] == "success"
    assert "IBM Bob Shell" in result["engine"]
    assert len(result["reasoning_steps"]) >= 3
    assert result["patchable_count"] == 2