"""MCP server lokal SELISIH + pintu admin HTTP untuk dashboard (Fase 3).

Dua pintu menuju proses yang sama:
- **stdio (JSON-RPC 2.0)** — dipakai IBM Bob (MCP client) di IDE.
- **HTTP admin (localhost)** — dipakai dashboard: `GET /health`, `POST /handoff`.

Seluruh akses terbatas (allowlist) ke `mock_fintech_repo/` + `artifacts/`.
Kode perusahaan tidak pernah keluar mesin; hanya kontrak `temuan.json`
(regulasi publik) yang menyeberang domain.
"""

import json
import os
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, HTTPServer

from selisih import artifacts, impact

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MOCK_REPO_DIR = os.path.join(BASE_DIR, "mock_fintech_repo")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
GOLDEN_PATH_FILE = os.path.join(DATA_DIR, "temuan_golden_path.json")
LIVE_RESULT_FILE = os.path.join(DATA_DIR, "temuan.json")

TOOLS = [
    {
        "name": "get_temuan",
        "description": "Isi kontrak temuan.json saat ini (live) atau fallback golden path.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_artifacts",
        "description": "Daftar berkas yang tersedia di artifacts/ (hasil handoff).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_artifact",
        "description": "Baca berkas dalam artifacts/ (minta: name).",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "preview_patch",
        "description": "Dry-run patch dari kandidat_kode (tanpa menulis file).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "apply_patch",
        "description": "Tulis patch dengan backup otomatis. Wajib confirm=true (minta: confirm).",
        "inputSchema": {
            "type": "object",
            "properties": {"confirm": {"type": "boolean"}},
            "required": ["confirm"],
        },
    },
    {
        "name": "run_repo_tests",
        "description": "Jalankan pytest pada mock_fintech_repo dan kembalikan output asli.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

LAST_SOURCE = None


def _resp(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _load_findings(primary=None):
    global LAST_SOURCE
    data, path = impact.load_findings(primary, GOLDEN_PATH_FILE)
    LAST_SOURCE = path
    return data


def _records():
    return impact.scan_impact(_load_findings(), MOCK_REPO_DIR)


def _fmt_report(report):
    lines = [f"- {r['path']} — {r['status']}: {r['message']}" for r in report]
    return "\n".join(lines) if lines else "(tidak ada draf patch)"


def _dispatch(name, args):
    if name == "get_temuan":
        data = _load_findings()
        if not data.get("findings"):
            return "Belum ada temuan. Jalankan analisis (mode Live) dulu, atau gunakan golden path."
        return json.dumps(data, ensure_ascii=False, indent=2)
    if name == "list_artifacts":
        if not os.path.isdir(ARTIFACTS_DIR):
            return "(artifacts/ belum ada)"
        return "\n".join(f"- {n}" for n in sorted(os.listdir(ARTIFACTS_DIR))) or "(kosong)"
    if name == "read_artifact":
        return _read_artifact(args.get("name", ""))
    if name == "preview_patch":
        return _fmt_report(impact.apply_patch(_records(), dry_run=True))
    if name == "apply_patch":
        if not args.get("confirm"):
            return "[ditolak] set confirm=true setelah peninjauan manusian."
        applied = impact.apply_patch(_records(), dry_run=False)
        for r in applied:
            if r["backup_path"]:
                r["backup_path"] = os.path.basename(r["backup_path"])
        return _fmt_report(applied)
    if name == "run_repo_tests":
        res = impact.run_pytest(MOCK_REPO_DIR, "tests")
        return f"$ {res['cmd']}\nreturncode={res['returncode']}\n{'stdout:'}\n{res['stdout']}\n{'stderr:'}\n{res['stderr']}"
    raise ValueError(f"tool tak dikenal: {name}")


def _read_artifact(name):
    base = os.path.abspath(ARTIFACTS_DIR)
    target = os.path.abspath(os.path.join(base, name))
    if target != base and not target.startswith(base + os.sep):
        return f"[ditolak] nama di luar artifacts/: {name}"
    if not os.path.isfile(target):
        return f"[tidak ditemukan] {name}"
    with open(target, "r", encoding="utf-8") as f:
        return f.read()


def handle_message(line: str):
    """Proses satu pesan JSON-RPC MCP; kembalikan string respons (atau None)."""
    msg = json.loads(line)
    rid = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {}) or {}
    if method == "initialize":
        return _resp(rid, {
            "protocolVersion": params.get("protocolVersion") or "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "selisih-mcp", "version": "0.1.0"},
        })
    if method.startswith("notifications/"):
        return None
    if method == "ping":
        return _resp(rid, {})
    if method == "tools/list":
        return _resp(rid, {"tools": TOOLS})
    if method == "tools/call":
        try:
            text = _dispatch(params.get("name", ""), params.get("arguments") or {})
            return _resp(rid, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as exc:  # noqa: BLE001 - jembatan MCP, tetap kirim isError
            return _resp(rid, {"content": [{"type": "text", "text": f"error: {exc}"}], "isError": True})
    return _error(rid, -32601, f"Method not found: {method}")


class _AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # pragma: no cover - diam di logger
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        if self.path != "/health":
            self._json(404, {"error": "not found"})
            return
        data = _load_findings()
        source = os.path.basename(LAST_SOURCE) if LAST_SOURCE else None
        self._json(200, {
            "status": "ok",
            "server": "selisih-mcp",
            "tools": [t["name"] for t in TOOLS],
            "findings_source": source,
            "has_findings": bool(data.get("findings")),
            "artifacts": sorted(os.listdir(ARTIFACTS_DIR)) if os.path.isdir(ARTIFACTS_DIR) else [],
        })

    def do_POST(self):
        if self.path != "/handoff":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) or b"{}"
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            self._json(400, {"error": f"JSON invalid: {exc}"})
            return
        primary = LIVE_RESULT_FILE if payload.get("source") == "live" else None
        findings = _load_findings(primary)
        summary = artifacts.build_artifacts(findings, MOCK_REPO_DIR, ARTIFACTS_DIR)
        summary["source"] = ("live" if LAST_SOURCE == LIVE_RESULT_FILE
                             else "golden" if LAST_SOURCE == GOLDEN_PATH_FILE else "none")
        summary["handoff_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log_path = os.path.join(ARTIFACTS_DIR, "last_handoff.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self._json(200, summary)


def start_admin_http(host: str = "127.0.0.1", port: int = 8765) -> HTTPServer:
    server = HTTPServer((host, port), _AdminHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main_stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            out = handle_message(line)
        except json.JSONDecodeError:
            continue
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    port = int(os.environ.get("MCP_ADMIN_PORT", "8765"))
    server = start_admin_http(port=port)
    main_stdio()
    # stdin ditutup (mis. diuji headless / Bob terputus): pertahankan HTTP admin tetap hidup.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()