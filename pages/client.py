import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.database import get_nom_client_par_contrat
from src.rag.client_connecte import repondre_client_connecte


def afficher_client():

    # SIDEBAR
    with st.sidebar:
        st.title("👤 Espace Client")
        st.markdown("---")
        st.markdown(f"📧 Connecté : **{st.session_state.user['email']}**")
        st.markdown("---")
        if st.button("🚪 Se déconnecter"):
            del st.session_state.user
            st.rerun()

    # SESSION STATE
    if "historique_client" not in st.session_state:
        st.session_state.historique_client = []
    if "nom_client_connecte" not in st.session_state:
        numero_contrat = st.session_state.user.get("numero_client")
        st.session_state.nom_client_connecte = get_nom_client_par_contrat(numero_contrat)

    nom_client = st.session_state.nom_client_connecte

    # CLIENT INTROUVABLE
    if not nom_client:
        st.error("❌ Aucun client trouvé pour ce compte. Contactez l'administrateur.")
        return

    # TITRE
    st.title(f"👤 Bonjour, **{nom_client}**")
    st.markdown("Posez vos questions sur vos factures SRM.")
    st.markdown("---")

    # HISTORIQUE
    for msg in st.session_state.historique_client:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # CHATBOT
    question = st.chat_input("Votre question sur vos factures...")

    if question:
        st.session_state.historique_client.append({"role": "user", "content": question})
        st.chat_message("user").write(question)

        historique_texte = ""
        for msg in st.session_state.historique_client[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"

        with st.spinner("⏳ Recherche en cours..."):

            reponse = repondre_client_connecte(
                question,
                # numero client est garde uniquemnt pour laffichage de nom client et pas pour les requetes
                st.session_state.user["numero_client"],  # numero_contrat
                historique_texte
            )

        st.session_state.historique_client.append({"role": "assistant", "content": reponse})
        st.chat_message("assistant").write(reponse)