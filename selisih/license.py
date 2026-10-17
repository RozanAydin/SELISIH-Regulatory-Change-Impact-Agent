"""Lisensi lokal sederhana untuk gating fitur dashboard.

Ini bukan billing server eksternal. Modul ini membuat status lisensi benar-benar
dipakai oleh UI: aksi analisis/patch dinonaktifkan bila lisensi tidak aktif atau
kuota repositori terlampaui.
"""

from __future__ import annotations

import os


PLAN_LIMITS = {
    "starter": 5,
    "professional": 25,
    "enterprise": -1,
}

PLAN_LABELS = {
    "starter": "Starter Plan",
    "professional": "Professional Plan",
    "enterprise": "Enterprise Plan",
}

STATUS_LABELS = {
    "active": "Aktif",
    "trial": "Trial",
    "expired": "Kedaluwarsa",
    "suspended": "Ditangguhkan",
}


def get_license_state(secrets=None) -> dict:
    """Ambil status lisensi dari env/secrets dengan default aman untuk demo lokal."""
    env = {key: os.environ.get(key) for key in _keys()}
    secrets = secrets or {}

    def value(key: str, default: str = "") -> str:
        raw = _get_secret(secrets, key)
        if raw not in (None, ""):
            return str(raw)
        raw = env.get(key)
        return str(raw) if raw not in (None, "") else default

    plan = value("SELISIH_PLAN", "starter").strip().lower()
    if plan not in PLAN_LIMITS:
        plan = "starter"

    repo_limit = _to_int(value("SELISIH_REPO_LIMIT", str(PLAN_LIMITS[plan])), PLAN_LIMITS[plan])
    active_repos = max(0, _to_int(value("SELISIH_ACTIVE_REPOS", "3"), 3))
    status = value("SELISIH_LICENSE_STATUS", "active").strip().lower()
    if status not in STATUS_LABELS:
        status = "active"

    quota_ok = repo_limit < 0 or active_repos <= repo_limit
    status_ok = status in {"active", "trial"}
    can_run = status_ok and quota_ok

    return {
        "organization": value("SELISIH_ORG_NAME", "PT Bank Digital Nusantara"),
        "plan": plan,
        "plan_label": PLAN_LABELS[plan],
        "status": status,
        "status_label": STATUS_LABELS[status],
        "repo_limit": repo_limit,
        "active_repos": active_repos,
        "quota_ok": quota_ok,
        "can_run": can_run,
        "message": _message(status, quota_ok, active_repos, repo_limit),
    }


def _keys() -> tuple[str, ...]:
    return (
        "SELISIH_ORG_NAME",
        "SELISIH_PLAN",
        "SELISIH_LICENSE_STATUS",
        "SELISIH_ACTIVE_REPOS",
        "SELISIH_REPO_LIMIT",
    )


def _get_secret(secrets, key: str):
    try:
        return secrets.get(key)
    except Exception:
        return None


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _message(status: str, quota_ok: bool, active_repos: int, repo_limit: int) -> str:
    if status not in {"active", "trial"}:
        return f"Lisensi {STATUS_LABELS[status].lower()}. Aksi analisis dinonaktifkan."
    if not quota_ok:
        return f"Kuota repositori terlampaui: {active_repos}/{repo_limit}."
    if repo_limit < 0:
        return "Lisensi valid. Kuota repositori tidak dibatasi."
    return f"Lisensi valid. Kuota repositori {active_repos}/{repo_limit}."
