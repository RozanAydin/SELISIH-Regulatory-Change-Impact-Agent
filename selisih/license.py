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


COMPANY_PROFILES = {
    "bank_digital": {
        "id": "bank_digital",
        "organization": "PT Bank Digital Nusantara",
        "plan": "enterprise",
        "plan_label": "Enterprise Plan",
        "status": "active",
        "status_label": "Aktif",
        "repo_limit": -1,
        "active_repos": 3,
        "quota_ok": True,
        "can_run": True,
        "message": "Lisensi valid. Kuota repositori tidak dibatasi.",
        "repositories": [
            {"id": "repo-core", "name": "mock_fintech_repo (Core Banking)", "path": "mock_fintech_repo", "is_active": True},
            {"id": "repo-loan", "name": "loan-service (Microservice Pinjaman)", "path": "mock_fintech_repo", "is_active": False},
            {"id": "repo-pay", "name": "payment-gateway (Layanan Pembayaran)", "path": "mock_fintech_repo", "is_active": False},
        ],
    },
    "dana_mandiri": {
        "id": "dana_mandiri",
        "organization": "PT Dana Mandiri Fintech",
        "plan": "professional",
        "plan_label": "Professional Plan",
        "status": "active",
        "status_label": "Aktif",
        "repo_limit": 25,
        "active_repos": 18,
        "quota_ok": True,
        "can_run": True,
        "message": "Lisensi valid. Kuota repositori 18/25.",
        "repositories": [
            {"id": "repo-core", "name": "mock_fintech_repo (Core P2P Engine)", "path": "mock_fintech_repo", "is_active": True},
            {"id": "repo-kyc", "name": "kyc-verification-service", "path": "mock_fintech_repo", "is_active": False},
        ],
    },
    "pinjaman_kilat": {
        "id": "pinjaman_kilat",
        "organization": "PT Pinjaman Kilat Indonesia",
        "plan": "starter",
        "plan_label": "Starter Plan",
        "status": "suspended",
        "status_label": "Kuota Penuh (5/5)",
        "repo_limit": 5,
        "active_repos": 5,
        "quota_ok": False,
        "can_run": False,
        "message": "Kuota repositori paket Starter telah terlampaui (5/5). Aksi penerapan patch dinonaktifkan.",
        "repositories": [
            {"id": "repo-1", "name": "mock_fintech_repo (Main App)", "path": "mock_fintech_repo", "is_active": True},
            {"id": "repo-2", "name": "auth-service", "path": "mock_fintech_repo", "is_active": False},
            {"id": "repo-3", "name": "notification-service", "path": "mock_fintech_repo", "is_active": False},
            {"id": "repo-4", "name": "billing-service", "path": "mock_fintech_repo", "is_active": False},
            {"id": "repo-5", "name": "reporting-service", "path": "mock_fintech_repo", "is_active": False},
        ],
    },
}

_CURRENT_COMPANY_ID = "bank_digital"


def get_company_profiles() -> list[dict]:
    """Mengembalikan seluruh daftar profil entitas perusahaan yang terdaftar."""
    return list(COMPANY_PROFILES.values())


def set_active_company(company_id: str) -> dict:
    """Mengubah entitas perusahaan aktif untuk sesi sistem."""
    global _CURRENT_COMPANY_ID
    if company_id in COMPANY_PROFILES:
        _CURRENT_COMPANY_ID = company_id
    return get_license_state(company_id=_CURRENT_COMPANY_ID)


def add_repository_to_company(company_id: str, name: str, path: str) -> dict:
    """Mendaftarkan repositori baru ke entitas perusahaan dengan validasi kuota."""
    global _CURRENT_COMPANY_ID
    cid = company_id or _CURRENT_COMPANY_ID
    if cid not in COMPANY_PROFILES:
        cid = _CURRENT_COMPANY_ID
    comp = COMPANY_PROFILES[cid]

    # Validasi kuota paket
    if comp["repo_limit"] != -1 and comp["active_repos"] >= comp["repo_limit"]:
        return {
            "success": False,
            "error": f"Batas kuota paket {comp['plan_label']} ({comp['active_repos']}/{comp['repo_limit']}) telah tercapai. Tingkatkan paket langganan untuk menambah repositori.",
            "company": comp,
        }

    new_repo = {
        "id": f"repo-{len(comp['repositories']) + 1}",
        "name": name,
        "path": path,
        "is_active": False,
    }
    comp["repositories"].append(new_repo)
    comp["active_repos"] = len(comp["repositories"])
    comp["quota_ok"] = comp["repo_limit"] < 0 or comp["active_repos"] <= comp["repo_limit"]
    comp["can_run"] = comp["status"] in {"active", "trial"} and comp["quota_ok"]
    comp["message"] = _message(comp["status"], comp["quota_ok"], comp["active_repos"], comp["repo_limit"])

    return {
        "success": True,
        "repo": new_repo,
        "company": comp,
    }


def get_license_state(secrets=None, company_id: str | None = None) -> dict:
    """Ambil status lisensi dari profil perusahaan atau env/secrets."""
    global _CURRENT_COMPANY_ID

    # Jika company_id eksplisit diberikan, gunakan profil tersebut
    if company_id and company_id in COMPANY_PROFILES:
        return dict(COMPANY_PROFILES[company_id])

    # Jika dipanggil dalam konteks test dengan secrets dikirim eksplisit
    if secrets is not None:
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
            "id": "custom",
            "organization": value("SELISIH_ORG_NAME", "PT Bank Digital Nusantara"),
            "plan": plan,
            "plan_label": PLAN_LABELS.get(plan, plan.title()),
            "status": status,
            "status_label": STATUS_LABELS.get(status, status.title()),
            "repo_limit": repo_limit,
            "active_repos": active_repos,
            "quota_ok": quota_ok,
            "can_run": can_run,
            "message": _message(status, quota_ok, active_repos, repo_limit),
            "repositories": [
                {"id": "repo-core", "name": "mock_fintech_repo", "path": "mock_fintech_repo", "is_active": True}
            ],
        }

    # Default ke profil perusahaan aktif saat ini
    cid = _CURRENT_COMPANY_ID
    if cid in COMPANY_PROFILES:
        return dict(COMPANY_PROFILES[cid])

    return dict(COMPANY_PROFILES["bank_digital"])


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
