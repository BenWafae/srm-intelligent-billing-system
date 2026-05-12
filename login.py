import os
import base64
import streamlit as st
from src.database import verifier_login

def _load_css():
    css_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "assets", "Css")
    for filename in ["base.css", "login.css"]:
        path = os.path.join(css_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except FileNotFoundError:
            pass

def _get_logo_html():
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "assets", "srm_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{logo_b64}" class="login-logo-img" alt="SRM Logo">'
    return '<span style="font-size:36px;">🔐</span>'

def afficher_login():
    _load_css()

    st.markdown('''
    <div class="bg-circles">
        <div class="circle-top-right"></div>
        <div class="circle-bottom-left"></div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.6, 1])

    with col2:

        logo_html = _get_logo_html()

        st.markdown(f'''
        <div class="login-card-header">
            <div class="login-icon-circle">
                {logo_html}
            </div>
            <h1 class="login-title">SRM</h1>
            <p class="login-subtitle">Société Régionale Multiservices</p>
            <div class="login-divider"></div>
        </div>
        ''', unsafe_allow_html=True)

        email = st.text_input(
            "✉  Email",
            placeholder="votre.email@example.com",
            key="email"
        )

        password = st.text_input(
            "🔒  Mot de passe",
            type="password",
            placeholder="Entrez votre mot de passe",
            key="password"
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        if st.button("🚀  Se Connecter", use_container_width=True):
            if not email or not password:
                st.warning("⚠️  Veuillez remplir tous les champs.")
            else:
                user = verifier_login(email, password)
                if user:
                    st.success("✅  Connexion réussie !")
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("❌  Email ou mot de passe incorrect.")

        st.markdown('<p class="login-footer">🔒 Vos données sont sécurisées et chiffrées</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(
        page_title="SRM - Connexion",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    afficher_login()