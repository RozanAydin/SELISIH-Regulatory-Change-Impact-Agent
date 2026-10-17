"""Autentikasi Peran & RBAC untuk Tata Kelola SELISIH.

Menyediakan akun berbasis peran fungsional (Administrator, Software Engineer, Compliance Officer)
dan pencatatan identitas peninjau pada audit trail tanpa ketergantungan database eksternal.
Tampilan bersih dan profesional tanpa elemen emoji.
"""

from typing import Any, Dict, Optional

# Daftar Peran Fungsional Sistem
PERSONAS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "id": "admin",
        "username": "admin",
        "password": "admin123",
        "name": "Administrator",
        "title": "System & Compliance Administrator",
        "role": "admin",
        "role_label": "Administrator",
        "description": "Akses menyeluruh ke analisis regulasi, pemetaan dampak kode, dan otorisasi patch.",
        "permissions": {
            "can_run_analysis": True,
            "can_view_impact": True,
            "can_send_bob": True,
            "can_apply_patch": True,
            "can_run_tests": True,
        },
    },
    "engineer": {
        "id": "engineer",
        "username": "engineer",
        "password": "engineer123",
        "name": "Software Engineer",
        "title": "Lead Software Engineer",
        "role": "engineer",
        "role_label": "Software Engineer",
        "description": "Meninjau dampak perubahan kode pada repositori, menjalankan dry-run, dan menerapkan patch.",
        "permissions": {
            "can_run_analysis": True,
            "can_view_impact": True,
            "can_send_bob": True,
            "can_apply_patch": True,
            "can_run_tests": True,
        },
    },
    "compliance": {
        "id": "compliance",
        "username": "compliance",
        "password": "compliance123",
        "name": "Compliance Officer",
        "title": "Regulatory Compliance Reviewer",
        "role": "compliance",
        "role_label": "Compliance Officer",
        "description": "Menganalisis klausul regulasi baru OJK, menelaah perubahan, dan memverifikasi kepatuhan.",
        "permissions": {
            "can_run_analysis": True,
            "can_view_impact": True,
            "can_send_bob": True,
            "can_apply_patch": True,
            "can_run_tests": True,
        },
    },
}


def get_personas() -> Dict[str, Dict[str, Any]]:
    """Kembalikan kamus seluruh peran yang tersedia."""
    return PERSONAS


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifikasi kredensial pengguna berdasarkan peran.
    
    Mengembalikan data peran jika valid, atau None jika tidak cocok.
    """
    clean_user = (username or "").strip().lower()
    for persona in PERSONAS.values():
        if persona["username"].lower() == clean_user:
            if persona["password"] == password:
                return persona
    return None


def get_current_user(session_state: Any = None) -> Optional[Dict[str, Any]]:
    """Ambil data peran aktif dari session_state."""
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except ImportError:
            return None

    if getattr(session_state, "authenticated", False) or (isinstance(session_state, dict) and session_state.get("authenticated")):
        if hasattr(session_state, "get"):
            return session_state.get("user")
        return getattr(session_state, "user", None)
    return None


def login(user_data: Dict[str, Any], session_state: Any = None) -> Dict[str, Any]:
    """Tandai sesi pengguna sebagai terautentikasi."""
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except ImportError:
            pass

    if session_state is not None:
        if hasattr(session_state, "__setitem__"):
            session_state["authenticated"] = True
            session_state["user"] = user_data
        else:
            setattr(session_state, "authenticated", True)
            setattr(session_state, "user", user_data)
    return user_data


def quick_login(persona_id: str, session_state: Any = None) -> Optional[Dict[str, Any]]:
    """Login langsung berdasarkan peran ID untuk evaluasi cepat."""
    alias_map = {"legal": "compliance", "auditor": "admin"}
    target_id = alias_map.get(persona_id, persona_id)
    persona = PERSONAS.get(target_id)
    if persona:
        return login(persona, session_state)
    return None


def logout(session_state: Any = None) -> None:
    """Hapus sesi login aktif."""
    if session_state is None:
        try:
            import streamlit as st
            session_state = st.session_state
        except ImportError:
            pass

    if session_state is not None:
        if hasattr(session_state, "__setitem__"):
            session_state["authenticated"] = False
            session_state["user"] = None
        else:
            setattr(session_state, "authenticated", False)
            setattr(session_state, "user", None)


def can_apply_patch(user: Optional[Dict[str, Any]]) -> bool:
    """Periksa apakah pengguna memiliki hak menerapkan patch ke basis kode."""
    if not user:
        return False
    perms = user.get("permissions", {})
    return bool(perms.get("can_apply_patch", True))


def can_run_analysis(user: Optional[Dict[str, Any]]) -> bool:
    """Periksa apakah pengguna memiliki hak menjalankan diff regulasi."""
    if not user:
        return False
    perms = user.get("permissions", {})
    return bool(perms.get("can_run_analysis", True))
