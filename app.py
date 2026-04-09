# pipeline de mon app:
# User => Upload pdf => extraction text => extraction infos importants => sauvegard db => chatbot llm => Response

import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.pdf_reader import extraire_texte
from src.llm import poser_question
from src.extractor import extraire_infos_facture
from src.database import init_db, enregistrer_facture

# Initialiser la base de données
init_db()

# Initialiser session state
if "texte_facture" not in st.session_state:
    st.session_state.texte_facture = None
if "facture_sauvegardee" not in st.session_state:
    st.session_state.facture_sauvegardee = False
if "message_sauvegarde" not in st.session_state:
    st.session_state.message_sauvegarde = ""
if "fichier_nom" not in st.session_state:
    st.session_state.fichier_nom = None
if "historique" not in st.session_state:
    st.session_state.historique = []
if "infos_facture" not in st.session_state:
    st.session_state.infos_facture = None

st.title("🤖 Chatbot SRM — Analyse de Factures")
st.write("Uploadez votre facture PDF et posez vos questions.")

fichier = st.file_uploader("Choisir une facture PDF", type="pdf")

if fichier:
    # Traiter uniquement si c'est un nouveau fichier
    if fichier.name != st.session_state.fichier_nom:
        st.session_state.fichier_nom = fichier.name
        st.session_state.facture_sauvegardee = False
        st.session_state.historique = []
        st.session_state.infos_facture = None

        with open("facture_temp.pdf", "wb") as f:
            f.write(fichier.read())

        st.session_state.texte_facture = extraire_texte("facture_temp.pdf")

        # Extraction et sauvegarde une seule fois
        with st.spinner("📊 Extraction et sauvegarde des données..."):
            infos = extraire_infos_facture(st.session_state.texte_facture)
            if infos:
                st.session_state.infos_facture = infos
                saved = enregistrer_facture(infos)
                if saved:
                    st.session_state.message_sauvegarde = f"💾 Nouvelle facture sauvegardée — Client : {infos.get('nom_client', 'Inconnu')} | Montant : {infos.get('montant_total_ttc')} Dhs"
                else:
                    st.session_state.message_sauvegarde = "⚠️ Cette facture est déjà enregistrée dans la base de données."
                st.session_state.facture_sauvegardee = True

    st.success("✅ Facture chargée avec succès !")

    # Afficher message sauvegarde
    if st.session_state.message_sauvegarde:
        if "Nouvelle" in st.session_state.message_sauvegarde:
            st.info(st.session_state.message_sauvegarde)
        else:
            st.warning(st.session_state.message_sauvegarde)

    # Résumé automatique visuel
    if st.session_state.infos_facture:
        infos = st.session_state.infos_facture
        st.markdown("---")
        st.markdown("### 📋 Résumé de votre facture")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👤 Client", infos.get("nom_client") or "—")
            st.metric("🔌 Service", infos.get("type_service") or "—")
        with col2:
            unite = "kWh" if infos.get("type_service") == "electricite" else "m³"
            st.metric("⚡ Consommation", f"{infos.get('consommation') or '—'} {unite}")
            st.metric("📅 Période", f"{infos.get('periode_debut')} → {infos.get('periode_fin')}")
        with col3:
            st.metric("💰 Montant TTC", f"{infos.get('montant_total_ttc')} Dhs")
            st.metric("⏰ Date limite", infos.get("date_limite_paiement") or "—")

    # Partie question-réponse avec historique
    st.markdown("---")
    st.markdown("### 💬 Posez vos questions sur la facture")

    # Afficher historique conversation
    for msg in st.session_state.historique:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # Input question
    question = st.chat_input("Votre question sur la facture...")

    if question and st.session_state.texte_facture:
        st.session_state.historique.append({"role": "user", "content": question})
        st.chat_message("user").write(question)

        with st.spinner("⏳ Analyse en cours..."):
            reponse = poser_question(
                st.session_state.texte_facture,
                question,
                st.session_state.historique
            )

        st.session_state.historique.append({"role": "assistant", "content": reponse})
        st.chat_message("assistant").write(reponse)