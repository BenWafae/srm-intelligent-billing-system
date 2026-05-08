import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.database import (
    get_nom_client_par_contrat,
    get_mois_client,
    get_derniere_facture_client,
    get_historique_client,
    get_prochain_paiement_client,
)
from src.rag.client_connecte import repondre_client_connecte
from src.rag_client.pdf_facture import generer_pdf_facture


def afficher_client():

    # ══════════════════════════════════════════
    # RESET SESSION SI NOUVEAU UTILISATEUR
    # ══════════════════════════════════════════
    email_actuel = st.session_state.user.get("email")

    if st.session_state.get("_client_email_courant") != email_actuel:
        st.session_state["_client_email_courant"] = email_actuel
        st.session_state["historique_client"] = []
        st.session_state["nom_client_connecte"] = None

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
    if not st.session_state.get("historique_client"):
        st.session_state.historique_client = []

    if not st.session_state.get("nom_client_connecte"):
        numero_contrat = st.session_state.user.get("numero_client")
        st.session_state.nom_client_connecte = get_nom_client_par_contrat(numero_contrat)

    nom_client = st.session_state.nom_client_connecte

    if not nom_client:
        st.error("❌ Aucun client trouvé pour ce compte. Contactez l'administrateur.")
        return

    numero_contrat = st.session_state.user["numero_client"]

    # ══════════════════════════════════════════
    # TITRE
    # ══════════════════════════════════════════
    st.title(f"👤 Bonjour, **{nom_client}**")
    st.markdown("Posez vos questions sur vos factures SRM.")
    st.markdown("---")

    # ══════════════════════════════════════════
    # MINI-DASHBOARD
    # ══════════════════════════════════════════
    derniere = get_derniere_facture_client(numero_contrat)
    prochain = get_prochain_paiement_client(numero_contrat)

    if derniere:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="🧾 Dernière facture",
                value=f"{derniere['montant']:,.0f} Dhs",
                delta=f"{derniere['mois']}"
            )

        with col2:
            if prochain:
                st.metric(
                    label="📅 Prochaine échéance",
                    value=f"⏰ {prochain['date_limite']}",
                    delta=f"dans {prochain['jours']} jours — {prochain['mois']}"
                )
            else:
                st.metric(
                    label="📅 Prochaine échéance",
                    value="✅ Aucune",
                    delta="Toutes les factures sont passées"
                )

        with col3:
            st.metric(
                label="⚡ Conso ce mois",
                value=f"{derniere['consommation']:,.0f} {derniere['unite']}",
                delta=f"{derniere['mois']}"
            )

    # ══════════════════════════════════════════
    # GRAPHIQUE CONSOMMATION
    # ══════════════════════════════════════════
    historique = get_historique_client(numero_contrat)
    if historique:
        with st.expander("📈 Voir mon graphique de consommation", expanded=False):
            df = pd.DataFrame(historique)
            tab1, tab2 = st.tabs(["💰 Montants (Dhs)", "⚡ Consommation"])
            with tab1:
                st.bar_chart(
                    df.set_index("mois")["montant"],
                    use_container_width=True,
                    height=250
                )
            with tab2:
                st.bar_chart(
                    df.set_index("mois")["consommation"],
                    use_container_width=True,
                    height=250
                )

    st.markdown("---")

    # ══════════════════════════════════════════
    # SUGGESTIONS DE QUESTIONS
    # ══════════════════════════════════════════
    if "suggestion_choisie" not in st.session_state:
        st.session_state["suggestion_choisie"] = None

    suggestions = [
        "Mon montant le plus élevé",
        "Suis-je en retard ?",
        "Ma moyenne mensuelle",
        "Mon historique complet",
    ]

    cols = st.columns(len(suggestions))
    for i, (col, sugg) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(sugg, key=f"sugg_{i}", use_container_width=True):
                st.session_state["suggestion_choisie"] = sugg

    if st.session_state["suggestion_choisie"]:
        question_auto = st.session_state["suggestion_choisie"]
        st.session_state["suggestion_choisie"] = None
        st.session_state.historique_client.append({"role": "user", "content": question_auto})
        historique_texte = ""
        for msg in st.session_state.historique_client[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"
        with st.spinner("⏳ Recherche en cours..."):
            reponse = repondre_client_connecte(
                question_auto,
                numero_contrat,
                historique_texte
            )
        st.session_state.historique_client.append({"role": "assistant", "content": reponse})
        st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════════
    # HISTORIQUE CHAT
    # ══════════════════════════════════════════
    for msg in st.session_state.historique_client:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # ══════════════════════════════════════════
    # CHATBOT
    # ══════════════════════════════════════════
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
                numero_contrat,
                historique_texte
            )

        st.session_state.historique_client.append({"role": "assistant", "content": reponse})
        st.chat_message("assistant").write(reponse)

    # ══════════════════════════════════════════
    # TÉLÉCHARGEMENT FACTURE
    # ══════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📥 Télécharger une facture")

    mois_disponibles = get_mois_client(numero_contrat)

    if mois_disponibles:
        mois_choisi = st.selectbox(
            "Choisir un mois",
            options=mois_disponibles,
            key="mois_telechargement"
        )
        if st.button("📄 Générer la facture"):
            pdf = generer_pdf_facture(numero_contrat, mois_choisi)
            if pdf:
                st.download_button(
                    label="💾 Sauvegarder le PDF",
                    data=pdf,
                    file_name=f"facture_{mois_choisi}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Facture introuvable pour ce mois.")
    else:
        st.info("Aucune facture disponible pour votre compte.")