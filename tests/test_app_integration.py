"""Pengujian integrasi antarmuka Streamlit (AppTest).

Memvalidasi alur autentikasi peran, navigasi tab, eksekusi Bob Shell
langsung dari dashboard, dan peluncuran IBM Bob Desktop.
"""

import os
import subprocess
from streamlit.testing.v1 import AppTest

APP_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def test_login_screen_renders():
    """Memastikan layar login muncul tanpa error dan memuat 4 tombol autentikasi."""
    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.run()
    assert len(at.exception) == 0
    # 3 tombol peran cepat + 1 tombol submit form
    assert len(at.button) >= 4


def test_login_and_inspect_dashboard():
    """Memastikan alur login berhasil dan memuat kontrol dashboard."""
    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.run()
    # Login via tombol peran pertama (Administrator)
    at.button[0].click().run()
    assert len(at.exception) == 0
    assert at.session_state.authenticated is True

    # Tombol utama IBM Bob harus tersedia di antarmuka
    button_labels = [b.label for b in at.button]
    assert "Jalankan Agen IBM Bob di Dashboard" in button_labels
    assert "Buka di IBM Bob Desktop" in button_labels


def test_run_bob_agent_in_dashboard():
    """Memvalidasi eksekusi agen IBM Bob di dashboard (Bob Shell mode)."""
    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.run()
    at.button[0].click().run()

    # Temukan dan klik tombol 'Jalankan Agen IBM Bob di Dashboard'
    agent_btn = next(b for b in at.button if b.label == "Jalankan Agen IBM Bob di Dashboard")
    agent_btn.click().run()

    assert len(at.exception) == 0
    assert at.session_state.bob_agent_result is not None
    res = at.session_state.bob_agent_result
    assert res["status"] == "success"
    assert "IBM Bob Shell" in res["engine"]
    assert len(res["reasoning_steps"]) >= 3


def test_launch_bob_desktop_action(monkeypatch):
    """Memvalidasi aksi tombol peluncuran IBM Bob Desktop."""
    launched_cmds = []

    def fake_popen(cmd, **kwargs):
        launched_cmds.append(cmd)
        return None

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    at = AppTest.from_file(APP_FILE, default_timeout=15)
    at.run()
    at.button[0].click().run()

    desktop_btn = next(b for b in at.button if b.label == "Buka di IBM Bob Desktop")
    desktop_btn.click().run()

    assert len(at.exception) == 0
    assert at.session_state.ide_launch_result is not None
    assert at.session_state.ide_launch_result["app"] == "IBM Bob"
