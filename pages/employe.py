import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.pdf_reader import extraire_texte
from src.llm import poser_question, poser_question_excel
from src.extractor import extraire_infos_facture
from src.database import (init_db, enregistrer_facture, importer_excel_en_db,
                           get_resume_excel, get_clients_avec_pdf, get_texte_pdf_client,
                           get_fichiers_excel)
from src.excel_reader import lire_excel


def afficher_employe():

    # SIDEBAR
    with st.sidebar:
        st.title("🤖 SRM Assistant")
        st.markdown("---")
        st.markdown(f"👤 Connecté : **{st.session_state.user['email']}**")
        st.markdown(f"🔑 Rôle : **Employé SRM**")
        st.markdown("---")
        if st.button("🚪 Se déconnecter"):
            del st.session_state.user
            st.rerun()

    # SESSION STATE — PDF
    if "texte_facture" not in st.session_state:
        st.session_state.texte_facture = None
    if "historique" not in st.session_state:
        st.session_state.historique = []

    # SESSION STATE — Excel
    if "historique_excel" not in st.session_state:
        st.session_state.historique_excel = []

    # SESSION STATE — Filtre fichier
    if "nom_fichier_selectionne" not in st.session_state:
        st.session_state.nom_fichier_selectionne = ""

    # TITRE + ONGLETS
    st.title("🤖 Assistant SRM — Gestion Intelligente des Factures")
    onglet_pdf, onglet_excel = st.tabs(["📄 Analyse de facture PDF", "📊 Base clients Excel"])

    # ════════════════════════════════════════════
    # ONGLET 1 — PDF
    # ════════════════════════════════════════════
    with onglet_pdf:
        clients_pdf = get_clients_avec_pdf()

        if not clients_pdf:
            st.info("📄 Aucune facture PDF disponible. L'administrateur doit d'abord importer des fichiers PDF.")
        else:
            client_selectionne_pdf = st.selectbox(
                "👤 Sélectionner un client",
                options=clients_pdf,
                key="selectbox_pdf"
            )

            if client_selectionne_pdf != st.session_state.get("client_pdf_actuel"):
                st.session_state.client_pdf_actuel = client_selectionne_pdf
                st.session_state.historique = []
                st.session_state.texte_facture = get_texte_pdf_client(client_selectionne_pdf)

            st.markdown("---")
            st.markdown(f"### 💬 Questions sur la facture de **{client_selectionne_pdf}**")

            for msg in st.session_state.historique:
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    st.chat_message("assistant").write(msg["content"])

            col1, col2 = st.columns([5, 1])
            with col1:
                question = st.text_input(
                    "Votre question sur la facture...",
                    key="question_pdf",
                    label_visibility="collapsed"
                )
            with col2:
                envoyer = st.button("Envoyer", key="btn_pdf")

            if envoyer and question and st.session_state.texte_facture:
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
                st.rerun()

    # ════════════════════════════════════════════
    # ONGLET 2 — Excel
    # ════════════════════════════════════════════
    with onglet_excel:
        resume = get_resume_excel()

        if resume["total"] > 0:
            st.success(f"✅ Base active — {resume['total']} factures | {len(resume['clients'])} clients | {len(resume['periodes'])} périodes")

            # ── Ligne d'informations : clients | périodes | fichier ──
            col1, col2, col3 = st.columns(3)

            with col1:
                with st.expander("👥 Clients disponibles"):
                    for client in resume["clients"]:
                        st.write(f"• {client}")

            with col2:
                with st.expander("📅 Périodes couvertes"):
                    for periode in resume["periodes"]:
                        st.write(f"• {periode}")

            with col3:
                # ── SÉLECTEUR FICHIER ──
                fichiers_disponibles = get_fichiers_excel()

                _OPTION_TOUS = "📂 Tous les fichiers"
                options_fichiers = [_OPTION_TOUS] + fichiers_disponibles

                fichier_choisi = st.selectbox(
                    "🗂️ Fichier Excel",
                    options=options_fichiers,
                    key="selectbox_fichier",
                    help="Sélectionnez un fichier précis pour filtrer les réponses, ou gardez 'Tous les fichiers' pour interroger toute la base."
                )

                # Convertir en nom_fichier utilisable par le dispatcher
                nom_fichier = "" if fichier_choisi == _OPTION_TOUS else fichier_choisi

                # Si le fichier sélectionné change → réinitialiser l'historique
                if nom_fichier != st.session_state.nom_fichier_selectionne:
                    st.session_state.nom_fichier_selectionne = nom_fichier
                    st.session_state.historique_excel = []
                    st.rerun()

                # Afficher un indicateur visuel du périmètre actif
                if nom_fichier:
                    st.caption(f"🎯 Périmètre : **{nom_fichier}**")
                else:
                    st.caption("🌐 Périmètre : **Toute la base**")

        else:
            st.info("ℹ️ Aucune donnée en base. L'administrateur doit d'abord importer un fichier Excel.")

        st.markdown("---")
        st.markdown("### 💬 Interrogez la base clients")

        if resume["total"] == 0:
            st.warning("⚠️ Aucune donnée disponible. Contactez l'administrateur.")
        else:
            # Récupérer le nom_fichier depuis session_state
            nom_fichier_actif = st.session_state.nom_fichier_selectionne

            # Caption contextuelle selon le périmètre actif
            if nom_fichier_actif:
                st.caption(
                    f"🎯 Réponses basées sur **{nom_fichier_actif}** uniquement | "
                    f"Exemples : 'Quel est le montant de Fatima ?' | 'Qui consomme le plus ?'"
                )
            else:
                st.caption(
                    "🌐 Réponses basées sur **toute la base** | "
                    "Exemples : 'Quel est le montant de Fatima ?' | 'Quels clients ont des alertes ?' | 'Liste tous les clients'"
                )

            # Affichage de l'historique
            for msg in st.session_state.historique_excel:
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    st.chat_message("assistant").write(msg["content"])

            # Input question
            question_excel = st.chat_input("Votre question sur la base clients...")

            if question_excel:
                st.session_state.historique_excel.append({"role": "user", "content": question_excel})
                st.chat_message("user").write(question_excel)

                with st.spinner("⏳ Recherche en cours..."):
                    reponse = poser_question_excel(
                        question_excel,
                        st.session_state.historique_excel,
                        nom_fichier=nom_fichier_actif  # ← SEUL AJOUT PAR RAPPORT À L'ORIGINAL
                    )

                st.session_state.historique_excel.append({"role": "assistant", "content": reponse})
                st.chat_message("assistant").write(reponse)