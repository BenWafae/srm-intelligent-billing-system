import streamlit as st

def afficher_client():
    st.title("👤 Espace Client — En construction")
    if st.button("🚪 Se déconnecter"):
        del st.session_state.user
        st.rerun()