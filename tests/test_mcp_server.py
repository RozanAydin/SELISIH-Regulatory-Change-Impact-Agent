"""Pengujian Fase 3: protokol JSON-RPC MCP server lokal (tanpa Bob/jaringan)."""

import json
import os

import mcp_server

MCPS = {"jsonrpc": "2.0"}


def _msg(method, params=None, _id=1):
    msg = dict(MCPS, id=_id, method=method)
    if params is not None:
        msg["params"] = params
    return msg


def _call(handle, method, params=None, _id=1):
    out = handle(json.dumps(_msg(method, params, _id=_id)))
    return out if isinstance(out, dict) else json.loads(out)


def test_initialize_protocol():
    out = _call(mcp_server.handle_message, "initialize", {
        "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "x", "version": "1"}
    })
    assert out["result"]["protocolVersion"] == "2024-11-05"
    assert out["result"]["capabilities"]["tools"] == {}


def test_initialized_notification_returns_none():
    assert mcp_server.handle_message(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})) is None


def test_tools_list_exposes_expected_tools():
    out = _call(mcp_server.handle_message, "tools/list")
    names = [t["name"] for t in out["result"]["tools"]]
    assert "get_temuan" in names
    assert {"preview_patch", "apply_patch", "read_artifact", "run_repo_tests", "list_artifacts"} <= set(names)


def test_unknown_method_returns_error():
    out = _call(mcp_server.handle_message, "bogus/method")
    assert out["error"]["code"] == -32601


def test_get_temuan_falls_back_to_golden():
    out = _call(mcp_server.handle_message, "tools/call", {"name": "get_temuan", "arguments": {}})
    text = out["result"]["content"][0]["text"]
    assert "findings" in text or "CHG-POJK" in text


def test_read_artifact_path_traversal_blocked():
    out = _call(mcp_server.handle_message, "tools/call", {"name": "read_artifact", "arguments": {"name": "../../app.py"}})
    text = out["result"]["content"][0]["text"]
    assert "ditolak" in text


def test_apply_patch_requires_confirm_and_applies(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    cfg = repo / "app" / "core"
    cfg.mkdir(parents=True)
    (cfg / "config.py").write_text("MAX_LOAN_AMOUNT = 20_000_000\n", encoding="utf-8")
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({
        "analysis_meta": {},
        "findings": [{
            "change_id": "C1",
            "ringkasan": "naik plafon",
            "kandidat_kode": [{
                "path": "app/core/config.py",
                "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
            }],
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "MOCK_REPO_DIR", str(repo))
    monkeypatch.setattr(mcp_server, "GOLDEN_PATH_FILE", str(findings))
    monkeypatch.setattr(mcp_server, "ARTIFACTS_DIR", str(tmp_path / "artifacts"))

    denied = _call(mcp_server.handle_message, "tools/call", {"name": "apply_patch", "arguments": {}}, _id=1)
    assert "ditolak" in denied["result"]["content"][0]["text"]
    assert "MAX_LOAN_AMOUNT = 20_000_000" in (cfg / "config.py").read_text(encoding="utf-8")

    applied = _call(mcp_server.handle_message, "tools/call",
                    {"name": "apply_patch", "arguments": {"confirm": True}}, _id=2)
    text = applied["result"]["content"][0]["text"]
    assert "applied" in text
    assert "MAX_LOAN_AMOUNT = 50_000_000" in (cfg / "config.py").read_text(encoding="utf-8")
    backups = [n for n in os.listdir(cfg) if n.startswith("config.py.bak.")]
    assert backups, "backup harus dibuat"


def test_preview_patch_dry_run_does_not_write(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    cfg = repo / "app" / "core"
    cfg.mkdir(parents=True)
    (cfg / "config.py").write_text("MAX_LOAN_AMOUNT = 20_000_000\n", encoding="utf-8")
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({
        "findings": [{
            "change_id": "C1",
            "kandidat_kode": [{
                "path": "app/core/config.py",
                "old_code": "MAX_LOAN_AMOUNT = 20_000_000",
                "proposed_code": "MAX_LOAN_AMOUNT = 50_000_000",
            }],
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "MOCK_REPO_DIR", str(repo))
    monkeypatch.setattr(mcp_server, "GOLDEN_PATH_FILE", str(findings))
    monkeypatch.setattr(mcp_server, "ARTIFACTS_DIR", str(tmp_path / "artifacts"))

    out = _call(mcp_server.handle_message, "tools/call", {"name": "preview_patch", "arguments": {}})
    text = out["result"]["content"][0]["text"]
    assert "dry_run_ok" in text
    assert "MAX_LOAN_AMOUNT = 20_000_000" in (cfg / "config.py").read_text(encoding="utf-8")