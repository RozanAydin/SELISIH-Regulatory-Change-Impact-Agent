"""Ekspor artefak analisis untuk IBM Bob (Fase 3).

Kontrak `temuan.json` adalah satu-satunya jembatan lintas-batas. Modul ini
mengemas hasil pemindaian ke berkas lokal yang bisa dikonsumsi Bob (MCP/IDE)
tanpa kode perusahaan pernah keluar mesin.
"""

import ast
import json
import os
import time

import selisih.impact as impact


def build_artifacts(findings: dict, repo_dir: str, out_dir: str) -> dict:
    """Buat `impact_report.json`, `proposed_patch.diff`, dan `generated_tests.py`.

    Mengembalikan ringkasan (daftar file yang ditulis + statistik kandidat).
    """
    records = impact.scan_impact(findings, repo_dir)
    patchable = [r for r in records if r["status"] == "patchable"]

    os.makedirs(out_dir, exist_ok=True)
    report = {
        "analysis_meta": findings.get("analysis_meta", {}) or {},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "records": records,
    }

    diff_path = os.path.join(out_dir, "proposed_patch.diff")
    with open(diff_path, "w", encoding="utf-8") as f:
        parts = [impact.make_diff(r["old_code"], r["proposed_code"], r["path"]) for r in patchable]
        f.write("\n".join(parts))

    repo_relpath = os.path.relpath(os.path.abspath(repo_dir), os.path.abspath(out_dir))
    tests_path = os.path.join(out_dir, "generated_tests.py")
    with open(tests_path, "w", encoding="utf-8") as f:
        f.write(_gen_tests(patchable, repo_relpath))

    report_path = os.path.join(out_dir, "impact_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return {
        "out_dir": out_dir,
        "files": {
            "impact_report.json": os.path.basename(report_path),
            "proposed_patch.diff": os.path.basename(diff_path),
            "generated_tests.py": os.path.basename(tests_path),
        },
        "kandidat_kode": len(records),
        "patchable": len(patchable),
        "skipped": len(records) - len(patchable),
    }


def _gen_tests(patchable: list, repo_relpath: str) -> str:
    symbols = {}
    for rec in patchable:
        code = rec["proposed_code"]
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                try:
                    ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue
                literal = code[node.value.col_offset:node.value.end_col_offset].strip()
                symbols[node.targets[0].id] = (rec["change_id"], literal)

    lines = [
        '"""Draf uji regresi yang dihasilkan dari `kandidat_kode` (SELISIH).',
        "Sumber: proposed_code pada temuan. JANGAN dijalankan di produksi tanpa review.",
        '"""',
        "import os",
        "import sys",
        "",
        f"_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), {repo_relpath!r}))",
        "if _REPO not in sys.path:",
        "    sys.path.insert(0, _REPO)",
        "",
    ]
    if not symbols:
        lines.append("# Tidak ada simbol yang dapat diuji dari kandidat_kode.")
        return "\n".join(lines) + "\n"
    names = ", ".join(sorted(symbols))
    lines.append(f"from app.core.config import {names}")
    lines.append("")
    lines.append("")
    lines.append("def test_updated_statutory_limits():")
    for name in sorted(symbols):
        change_id, literal = symbols[name]
        lines.append(f"    assert {name} == {literal}  # {change_id}")
    lines.append("")
    return "\n".join(lines)