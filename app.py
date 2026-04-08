import streamlit as st
from src.pdf_reader import extraire_texte  # <-- modification ici
from src.llm import poser_question         # <-- modification ici

st.title("Chatbot SRM — Analyse de Factures")
st.write("Uploadez votre facture PDF et posez vos questions.")

fichier = st.file_uploader("Choisir une facture PDF", type="pdf")

if fichier:
    with open("facture_temp.pdf", "wb") as f:
        f.write(fichier.read())

    texte = extraire_texte("facture_temp.pdf")
    st.success("Facture chargée avec succès !")

    question = st.text_input("Votre question sur la facture :")

    if question:
        with st.spinner("Analyse en cours..."):
            reponse = poser_question(texte, question)
        st.markdown("**Réponse :**")
        st.write(reponse)

     