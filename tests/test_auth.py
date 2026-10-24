"""Pengujian modul autentikasi peran dan akses sistem selisih.auth."""

import os
import pytest
from selisih import auth


def test_personas_structure():
    personas = auth.get_personas()
    assert "admin" in personas
    assert "engineer" in personas
    assert "compliance" in personas

    for pid, p in personas.items():
        assert p["id"] == pid
        assert p["name"]
        assert p["title"]
        assert p["role"]
        assert "permissions" in p
        assert isinstance(p["permissions"], dict)


def test_authenticate_success():
    user = auth.authenticate("admin", "admin123")
    assert user is not None
    assert user["id"] == "admin"
    assert user["role"] == "admin"


def test_authenticate_case_insensitive():
    user = auth.authenticate(" Engineer ", "engineer123")
    assert user is not None
    assert user["id"] == "engineer"


def test_authenticate_failure():
    assert auth.authenticate("admin", "wrongpass") is None
    assert auth.authenticate("unknown_user", "password123") is None
    assert auth.authenticate("", "") is None


def test_quick_login_and_logout():
    mock_session = {}
    user = auth.quick_login("engineer", session_state=mock_session)
    assert user is not None
    assert mock_session["authenticated"] is True
    assert mock_session["user"]["id"] == "engineer"

    current = auth.get_current_user(session_state=mock_session)
    assert current == user

    auth.logout(session_state=mock_session)
    assert mock_session["authenticated"] is False
    assert mock_session["user"] is None
    assert auth.get_current_user(session_state=mock_session) is None


def test_quick_login_unknown():
    mock_session = {}
    assert auth.quick_login("non_existent", session_state=mock_session) is None
    assert not mock_session.get("authenticated")


def test_permissions_patch():
    admin = auth.get_personas()["admin"]
    engineer = auth.get_personas()["engineer"]
    compliance = auth.get_personas()["compliance"]

    assert auth.can_apply_patch(admin) is True
    assert auth.can_apply_patch(engineer) is True
    assert auth.can_apply_patch(compliance) is True
    assert auth.can_apply_patch(None) is False


def test_permissions_analysis():
    admin = auth.get_personas()["admin"]
    compliance = auth.get_personas()["compliance"]

    assert auth.can_run_analysis(admin) is True
    assert auth.can_run_analysis(compliance) is True
    assert auth.can_run_analysis(None) is False


