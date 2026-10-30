"""Scanner dampak kode & engine patch deterministik (Fase 4).

Baseline sebelum integrasi IBM Bob: pemetaan kewajiban hukum ke kode diturunkan
dari `kandidat_kode[].evidence` pada kontrak `temuan.json`. Semua operasi tulis
lewat dry-run/backup sehingga tidak ada perubahan repo yang tak dapat ditinjau.
"""

import difflib
import json
import os
import re
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


def scan_repo_for_compliance_targets(
    repo_dir: str,
    target_values: list[str] = None,
    keywords: list[str] = None,
) -> list[dict]:
    """Menelusuri direktori repositori klien untuk mendeteksi variabel/konstanta kepatuhan."""
    matches = []
    if not repo_dir or not os.path.isdir(repo_dir):
        return matches

    ignore_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "artifacts", ".bob"}
    target_vals = set(target_values or [])
    kw_patterns = [k.lower() for k in (keywords or [])]

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        for f in files:
            if not f.endswith(".py") or ".bak." in f:
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()
            except Exception:
                continue

            for idx, line in enumerate(lines):
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue

                val_match = any(v in line_str for v in target_vals if v)
                kw_match = any(k in line_str.lower() for k in kw_patterns) if kw_patterns else False

                if val_match or (kw_match and ("=" in line_str)):
                    matches.append({
                        "path": rel_path,
                        "abs_path": full_path,
                        "line": idx + 1,
                        "code": line_str,
                        "matched_value": next((v for v in target_vals if v and v in line_str), None),
                    })
    return matches


def scan_impact(findings: dict, repo_dir: str) -> list:
    """Petakan setiap temuan regulasi ke file+baris nyata di `repo_dir`.

    Status per record:
    - ``patchable``: old_code ditemukan pada berkas kode repositori.
    - ``no_old_code``: berkas ditemukan namun nilai lama tidak ditentukan.
    - ``already_or_no_match``: kode kemungkinan sudah disesuaikan sebelumnya.
    - ``missing``: berkas target awal tidak ditemukan.
    - ``policy_guidance``: klausul prosedural/organisasional (tata kelola).

    Setiap record juga memiliki field ``category``:
    - ``code_patchable``: dapat diterapkan patch kode secara langsung.
    - ``policy_action_required``: butuh tindakan manual tim kepatuhan/manajemen.
    """
    records = []
    finding_list = findings.get("findings") or []

    for finding in finding_list:
        kandidat_list = finding.get("kandidat_kode") or []
        change_id = finding.get("change_id")
        ringkasan = finding.get("ringkasan")

        if not kandidat_list:
            pasal_lama = finding.get("pasal_lama", {})
            pasal_baru = finding.get("pasal_baru", {})
            kutipan_lama = pasal_lama.get("kutipan", "")
            kutipan_baru = pasal_baru.get("kutipan", "")

            nums_lama = re.findall(r"\b\d+(?:[.,_]\d+)*%?\b", kutipan_lama)
            finding_text = f"{ringkasan} {kutipan_lama} {kutipan_baru}".lower()
            active_keywords = [
                k for k in ["limit", "max", "min", "rate", "bunga", "pinjaman", "modal", "plafon", "denda", "fee", "suku bunga"]
                if k in finding_text
            ]

            dynamic_matches = []
            if nums_lama or active_keywords:
                dynamic_matches = scan_repo_for_compliance_targets(repo_dir, target_values=nums_lama, keywords=active_keywords)
            if dynamic_matches:
                for match in dynamic_matches[:2]:
                    records.append({
                        "change_id": change_id,
                        "ringkasan": ringkasan,
                        "category": "code_patchable",
                        "path": match["path"],
                        "abs_path": match["abs_path"],
                        "evidence": match["code"],
                        "old_code": match["code"],
                        "proposed_code": match["code"],
                        "alasan": f"Terdeteksi variabel kepatuhan {match['code']} yang relevan dengan {change_id}.",
                        "lines": [match["line"]],
                        "line": match["line"],
                        "status": "patchable",
                    })
            else:
                records.append({
                    "change_id": change_id,
                    "ringkasan": ringkasan,
                    "category": "policy_action_required",
                    "path": None,
                    "abs_path": None,
                    "evidence": kutipan_baru[:200] if kutipan_baru else ringkasan,
                    "old_code": "",
                    "proposed_code": "",
                    "alasan": f"Kewajiban prosedural/tata kelola regulasi: {ringkasan}. Memerlukan penyesuaian SOP atau arsitektur sistem.",
                    "lines": [],
                    "line": None,
                    "status": "policy_guidance",
                })
            continue

        for kc in kandidat_list:
            rel = (kc.get("path") or "").lstrip("/")
            full = os.path.normpath(os.path.join(repo_dir, rel)) if rel else None
            old_code = kc.get("old_code") or ""
            proposed_code = kc.get("proposed_code") or ""

            record = {
                "change_id": change_id,
                "ringkasan": ringkasan,
                "category": "code_patchable",
                "path": rel,
                "abs_path": full,
                "evidence": kc.get("evidence") or "",
                "old_code": old_code,
                "proposed_code": proposed_code,
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
                    if proposed_code and proposed_code in content:
                        record["lines"] = [i + 1 for i, line in enumerate(content.splitlines()) if proposed_code in line]
                        record["line"] = record["lines"][0] if record["lines"] else None
            else:
                if old_code:
                    dynamic_matches = scan_repo_for_compliance_targets(repo_dir, target_values=[old_code])
                    if dynamic_matches:
                        first = dynamic_matches[0]
                        record["path"] = first["path"]
                        record["abs_path"] = first["abs_path"]
                        record["status"] = "patchable"
                        record["lines"] = [first["line"]]
                        record["line"] = first["line"]
                        record["alasan"] += f" (Otomatis dipetakan oleh Bob Shell ke berkas {first['path']})"

            records.append(record)

    return records


def make_diff(old_code: str, proposed_code: str, rel_path: str, full_file_content: str | None = None) -> str:
    """Diff unified old → proposed untuk pratinjau patch, dengan dukungan konteks baris."""
    if full_file_content and old_code and old_code in full_file_content:
        new_content = full_file_content.replace(old_code, proposed_code)
        diff_lines = list(
            difflib.unified_diff(
                full_file_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                n=3,
                lineterm="",
            )
        )
        if diff_lines:
            return "".join(diff_lines)

    return "".join(
        difflib.unified_diff(
            old_code.splitlines(keepends=True),
            proposed_code.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    )


def apply_patch(records: list, dry_run: bool = True, allowed_change_ids: list[str] = None) -> list:
    """Terapkan patch per record dengan backup otomatis ``<file>.bak.<ts>``.

    ``dry_run=True`` hanya mencocokkan old_code (tanpa menulis). Kembalikan
    daftar status per record. Jika ``allowed_change_ids`` ditentukan, hanya record
    dengan change_id tersebut yang akan diproses.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report = []
    allowed_set = set(allowed_change_ids) if allowed_change_ids is not None else None

    for record in records:
        cid = record.get("change_id")
        entry = {
            "path": record["path"],
            "change_id": cid,
            "status": "skip",
            "backup_path": None,
            "message": "",
        }

        if allowed_set is not None and cid and cid not in allowed_set:
            entry["message"] = "ditunda/dilewati oleh peninjau (tidak dipilih)"
            report.append(entry)
            continue

        if record["status"] != "patchable":
            entry["message"] = f"status: {record['status']}"
            report.append(entry)
            continue
        full = record.get("abs_path") or record.get("path")
        if not full or not os.path.isfile(full):
            entry["message"] = "berkas tidak ditemukan pada disk"
            report.append(entry)
            continue
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
