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

st.title("🤖 Chatbot SRM — Analyse de Factures")
st.write("Uploadez votre facture PDF et posez vos questions.")

fichier = st.file_uploader("Choisir une facture PDF", type="pdf")

if fichier:
    with open("facture_temp.pdf", "wb") as f:
        f.write(fichier.read())

    texte = extraire_texte("facture_temp.pdf")
    st.success("✅ Facture chargée avec succès !")

    # Extraction et sauvegarde automatique
    with st.spinner("📊 Extraction et sauvegarde des données..."):
        infos = extraire_infos_facture(texte)
        if infos:
            enregistrer_facture(infos)
            st.info(f"💾 Données sauvegardées — Client : {infos.get('nom_client', 'Inconnu')} | Montant : {infos.get('montant_total_ttc')} Dhs")

    # Partie question-réponse
    st.markdown("---")
    st.markdown("### 💬 Posez vos questions sur la facture")
    question = st.text_input("Votre question :")

    if question:
        with st.spinner("⏳ Analyse en cours..."):
            reponse = poser_question(texte, question)
        st.markdown("**Réponse :**")
        st.write(reponse)

     