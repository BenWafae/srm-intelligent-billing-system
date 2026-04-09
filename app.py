# pipline de mon app:
# Usert=>Upload pdf => exttraction text=> extraction ds infos importants=>sauvgard db=> chatbot llm=>Response




import streamlit as st
# sys & os pour gerer ls chemuns des fichiers
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
# pdfreader lire le fihcierr et extraire son contenue 
from src.pdf_reader import extraire_texte
# llm chatbot llm dans notre cas c ollama
from src.llm import poser_question
# extractor trouve les infos importante dans le pdf
from src.extractor import extraire_infos_facture
# databaase souvegard dans db
from src.database import init_db, enregistrer_facture

# Initialiser la base de données
init_db()

# sst.session-state jai lajouter caar streamlite recharge la page a toute action donc session state pour  memorise ls donnees
# Initialiser session state
if "texte_facture" not in st.session_state:
    st.session_state.texte_facture = None
if "facture_sauvegardee" not in st.session_state:
    st.session_state.facture_sauvegardee = False
if "message_sauvegarde" not in st.session_state:
    st.session_state.message_sauvegarde = ""
if "fichier_nom" not in st.session_state:
    st.session_state.fichier_nom = None

st.title("🤖 Chatbot SRM — Analyse de Factures")
st.write("Uploadez votre facture PDF et posez vos questions.")

fichier = st.file_uploader("Choisir une facture PDF", type="pdf")

if fichier:
    # Traiter uniquement si c'est un nouveau fichier
    if fichier.name != st.session_state.fichier_nom:
        st.session_state.fichier_nom = fichier.name
        st.session_state.facture_sauvegardee = False

        with open("facture_temp.pdf", "wb") as f:
            f.write(fichier.read())

        st.session_state.texte_facture = extraire_texte("facture_temp.pdf")

        # Extraction et sauvegarde une seule fois
        with st.spinner("📊 Extraction et sauvegarde des données..."):
            infos = extraire_infos_facture(st.session_state.texte_facture)
            if infos:
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

    # Partie question-réponse
    st.markdown("---")
    st.markdown("### 💬 Posez vos questions sur la facture")
    question = st.text_input("Votre question :")

    if question and st.session_state.texte_facture:
        with st.spinner("⏳ Analyse en cours..."):
            reponse = poser_question(st.session_state.texte_facture, question)
        st.markdown("**Réponse :**")
        st.write(reponse)
     