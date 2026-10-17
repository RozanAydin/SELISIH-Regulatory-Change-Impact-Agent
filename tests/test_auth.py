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


def test_app_unauthenticated_stops_at_login():
    from streamlit.testing.v1 import AppTest

    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
    at = AppTest.from_file(app_path, default_timeout=15).run()
    assert not at.exception
    labels = [btn.label for btn in at.button]
    assert any("Administrator" in label for label in labels)
    assert any("Software Engineer" in label for label in labels)
    assert any("Compliance Officer" in label for label in labels)


def test_app_authenticated_tabs_accessible_for_all_roles():
    from streamlit.testing.v1 import AppTest

    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
    for role_id in ["admin", "engineer", "compliance"]:
        at = AppTest.from_file(app_path, default_timeout=15)
        at.session_state["authenticated"] = True
        at.session_state["user"] = auth.get_personas()[role_id]
        at.run()
        assert not at.exception
        # Pastikan sidebar memuat peran aktif
        role_label = auth.get_personas()[role_id]["role_label"]
        assert any(role_label in str(s.value) for s in at.sidebar.markdown)
        # Pastikan Tab 2 dan Tab 3 terinisialisasi
        assert at.session_state["impact_scanned"] is True
        assert len(at.session_state["impact_records"]) > 0


def test_sidebar_component_integration_shows_status_only():
    from streamlit.testing.v1 import AppTest

    app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
    at = AppTest.from_file(app_path, default_timeout=15)
    at.session_state["authenticated"] = True
    at.session_state["user"] = auth.get_personas()["admin"]
    at.run()
    assert not at.exception

    sidebar_texts = [str(s.value) for s in at.sidebar.markdown]
    langflow_lines = [s for s in sidebar_texts if "Langflow:" in s]
    bob_lines = [s for s in sidebar_texts if "IBM Bob (MCP):" in s]

    assert len(langflow_lines) == 1
    assert len(bob_lines) == 1

    for line in [langflow_lines[0], bob_lines[0]]:
        assert "HTTP" not in line
        assert "Exception" not in line
        assert "Connection" not in line
        assert "traceback" not in line
        assert "Max retries" not in line

