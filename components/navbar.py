import os
import base64
import streamlit as st


def _get_logo_b64():
    """Récupère le logo en base64 depuis le dossier assets"""
    logo_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src", "assets", "srm_logo.png"
    )
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


ROLE_CONFIG = {
    "admin":   {"label": "Administrateur", "color": "#f97316", "icon": "🛡️"},
    "employe": {"label": "Employé SRM",    "color": "#f97316", "icon": "👔"},
    "client":  {"label": "Client SRM",     "color": "#f97316", "icon": "🌐"},
}


def afficher_navbar():
    """Affiche une navbar stylisée avec logo, titre, avatar et déconnexion"""
    
    # ── Chargement CSS externe
    css_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src", "assets", "Css"
    )
    
    css_path = os.path.join(css_dir, "navbar.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

    # ── Données session utilisateur
    user       = st.session_state.get("user", {})
    email      = user.get("email", "utilisateur@srm.ma")
    role       = user.get("role", "employe")
    role_info  = ROLE_CONFIG.get(role, ROLE_CONFIG["employe"])
    role_label = role_info["label"]
    role_icon  = role_info["icon"]

    # ── Logo base64
    logo_b64 = _get_logo_b64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="SRM Logo">'
        if logo_b64
        else '<span class="navbar-logo-fallback">SRM</span>'
    )

    # ── Navbar HTML (partie gauche avec logo + titre)
    st.markdown(f"""
    <div class="navbar">
        <div class="navbar-brand">
            <div class="navbar-logo">{logo_html}</div>
            <div class="navbar-title">
                <span class="navbar-title-main">SRM</span>
                <span class="navbar-title-sub">Société Régionale Multiservices</span>
            </div>
        </div>
    </div>
    <div class="navbar-spacer"></div>
    """, unsafe_allow_html=True)

    # ── Avatar + Popover (positionné avec CSS fixed)
    with st.popover("👤"):
        # ── Affichage des infos utilisateur
        st.markdown(f"""
        <div class="pop-header">
            <div class="pop-avatar">{role_icon}</div>
            <div class="pop-info">
                <span class="pop-email">{email}</span>
                <span class="pop-role">{role_label}</span>
            </div>
        </div>
        <div class="pop-divider"></div>
        """, unsafe_allow_html=True)

        # ── Bouton Déconnexion
        if st.button("Déconnexion", key="navbar_logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()