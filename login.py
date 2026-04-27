import streamlit as st
from src.database import verifier_login

def afficher_login():
    st.title("🔐 SRM — Connexion")
    st.markdown("---")

    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    btn = st.button("Se connecter")

    if btn:
        if not email or not password:
            st.warning("Veuillez remplir tous les champs.")
            return

        user = verifier_login(email, password)

        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Email ou mot de passe incorrect.")