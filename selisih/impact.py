"""Scanner dampak kode & engine patch deterministik (Fase 4).

Baseline sebelum integrasi IBM Bob: pemetaan kewajiban hukum ke kode diturunkan
dari `kandidat_kode[].evidence` pada kontrak `temuan.json`. Semua operasi tulis
lewat dry-run/backup sehingga tidak ada perubahan repo yang tak dapat ditinjau.
"""

import difflib
import json
import os
import subprocess
import sys
import time


def load_findings(primary, fallback):
    """Baca findings JSON; prioritas `primary` (e.g. hasil live), fallback ke `fallback`."""
    for path in (primary, fallback):
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path
    return {}, None


def scan_impact(findings: dict, repo_dir: str) -> list:
    """Petakan setiap `kandidat_kode` ke file+baris nyata di `repo_dir`.

    Status per record: ``patchable`` (old_code ditemukan), ``no_old_code``,
    ``already_or_no_match`` (old_code tak ada, kemungkinan sudah disesuaikan),
    ``missing`` (file tak ditemukan).
    """
    records = []
    for finding in findings.get("findings") or []:
        for kc in finding.get("kandidat_kode") or []:
            rel = (kc.get("path") or "").lstrip("/")
            full = os.path.normpath(os.path.join(repo_dir, rel)) if rel else None
            old_code = kc.get("old_code") or ""
            record = {
                "change_id": finding.get("change_id"),
                "ringkasan": finding.get("ringkasan"),
                "path": rel,
                "abs_path": full,
                "evidence": kc.get("evidence") or "",
                "old_code": old_code,
                "proposed_code": kc.get("proposed_code") or "",
                "alasan": kc.get("alasan") or "",
                "lines": [],
                "line": None,
                "status": "missing",
            }
            if full and os.path.isfile(full):
                content = _read(full)
                if not old_code:
                    record["status"] = "no_old_code"
                elif old_code in content:
                    record["status"] = "patchable"
                    record["lines"] = [i + 1 for i, line in enumerate(content.splitlines()) if old_code in line]
                    record["line"] = record["lines"][0] if record["lines"] else None
                else:
                    record["status"] = "already_or_no_match"
                    if record["proposed_code"] and record["proposed_code"] in content:
                        record["lines"] = [i + 1 for i, line in enumerate(content.splitlines()) if record["proposed_code"] in line]
                        record["line"] = record["lines"][0] if record["lines"] else None
            records.append(record)
    return records


def make_diff(old_code: str, proposed_code: str, rel_path: str) -> str:
    """Diff unified old → proposed untuk pratinjau patch."""
    return "".join(
        difflib.unified_diff(
            old_code.splitlines(keepends=True),
            proposed_code.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    )


def apply_patch(records: list, dry_run: bool = True) -> list:
    """Terapkan patch per record dengan backup otomatis ``<file>.bak.<ts>``.

    ``dry_run=True`` hanya mencocokkan old_code (tanpa menulis). Kembalikan
    daftar status per record.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report = []
    for record in records:
        entry = {"path": record["path"], "status": "skip", "backup_path": None, "message": ""}
        if record["status"] != "patchable":
            entry["message"] = f"status: {record['status']}"
            report.append(entry)
            continue
        full = record["abs_path"]
        content = _read(full)
        if record["old_code"] not in content:
            entry["message"] = "old_code tidak ditemukan saat penerapan"
            report.append(entry)
            continue
        new_content = content.replace(record["old_code"], record["proposed_code"])
        if content == new_content:
            entry["message"] = "tidak ada perubahan yang diperlukan"
            report.append(entry)
            continue
        if dry_run:
            entry["status"] = "dry_run_ok"
            entry["message"] = "kecocokan valid, siap ditulis"
            report.append(entry)
            continue
        backup = f"{full}.bak.{stamp}"
        _write(backup, content)
        _write(full, new_content)
        entry["status"] = "applied"
        entry["backup_path"] = backup
        entry["message"] = "ditulis dengan backup"
        report.append(entry)
    return report


def run_pytest(repo_dir: str, test_rel: str = "tests") -> dict:
    """Jalankan `pytest` di dalam `repo_dir`; kembalikan stdout/stderr asli."""
    cmd = [sys.executable, "-m", "pytest", test_rel, "-q"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_dir, timeout=120)
        return {
            "cmd": f"cd {repo_dir} && {' '.join(cmd)}",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as err:
        return {"cmd": " ".join(cmd), "returncode": -1, "stdout": str(err), "stderr": ""}


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def rollback_last_backup(repo_dir: str) -> dict:
    """Mengembalikan berkas dari salinan cadangan (.bak.<timestamp>) terbaru."""
    bak_files = []
    for root, _, files in os.walk(repo_dir):
        for f in files:
            if ".bak." in f:
                full_bak = os.path.join(root, f)
                bak_files.append(full_bak)

    if not bak_files:
        return {
            "status": "no_backups",
            "restored": [],
            "count": 0,
            "message": "Tidak ditemukan berkas cadangan (.bak.<timestamp>).",
        }

    originals = {}
    for b in bak_files:
        orig = b.split(".bak.")[0]
        if orig not in originals:
            originals[orig] = []
        originals[orig].append(b)

    restored = []
    for orig, baks in originals.items():
        newest_bak = sorted(baks, reverse=True)[0]
        try:
            content = _read(newest_bak)
            _write(orig, content)
            try:
                os.remove(newest_bak)
            except OSError:
                pass
            restored.append({
                "target": os.path.relpath(orig, repo_dir).replace("\\", "/"),
                "backup_source": os.path.relpath(newest_bak, repo_dir).replace("\\", "/"),
            })
        except Exception:
            pass

    return {
        "status": "success",
        "restored": restored,
        "count": len(restored),
        "message": f"Berhasil memulihkan {len(restored)} berkas dari salinan cadangan terbaru.",
    }
