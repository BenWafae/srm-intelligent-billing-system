import streamlit as st

def afficher_admin():
    st.title("🛠️ Admin — En construction")
    if st.button("🚪 Se déconnecter"):
        del st.session_state.user
        st.rerun()