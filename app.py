import streamlit as st
import sys
import os
st.set_page_config(page_title="SRM Assistant", layout="wide")

sys.path.insert(0, os.path.dirname(__file__))

from src.database import init_db
from login import afficher_login
from pages.employe import afficher_employe
from pages.admin import afficher_admin
from pages.client import afficher_client

# Initialisation de la base
init_db()

# ── Routeur principal ──
if "user" not in st.session_state:
    afficher_login()
else:
    role = st.session_state.user["role"]

    if role == "admin":
        afficher_admin()
    elif role == "employe":
        afficher_employe()
    elif role == "client":
        afficher_client()
    else:
        st.error("❌ Rôle non reconnu.")
        if st.button("Se déconnecter"):
            del st.session_state.user
            st.rerun()