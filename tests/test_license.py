"""Pengujian license gate lokal dashboard."""

from selisih.license import get_license_state


def test_default_license_allows_run(monkeypatch):
    for key in [
        "SELISIH_ORG_NAME",
        "SELISIH_PLAN",
        "SELISIH_LICENSE_STATUS",
        "SELISIH_ACTIVE_REPOS",
        "SELISIH_REPO_LIMIT",
    ]:
        monkeypatch.delenv(key, raising=False)

    state = get_license_state({})

    assert state["organization"] == "PT Bank Digital Nusantara"
    assert state["plan"] == "starter"
    assert state["active_repos"] == 3
    assert state["repo_limit"] == 5
    assert state["can_run"] is True


def test_expired_license_blocks_run(monkeypatch):
    monkeypatch.setenv("SELISIH_LICENSE_STATUS", "expired")

    state = get_license_state({})

    assert state["can_run"] is False
    assert "kedaluwarsa" in state["message"]


def test_repo_quota_blocks_run(monkeypatch):
    monkeypatch.setenv("SELISIH_ACTIVE_REPOS", "6")
    monkeypatch.setenv("SELISIH_REPO_LIMIT", "5")

    state = get_license_state({})

    assert state["quota_ok"] is False
    assert state["can_run"] is False


def test_enterprise_unlimited_quota(monkeypatch):
    monkeypatch.setenv("SELISIH_PLAN", "enterprise")
    monkeypatch.setenv("SELISIH_ACTIVE_REPOS", "100")

    state = get_license_state({})

    assert state["repo_limit"] == -1
    assert state["can_run"] is True
