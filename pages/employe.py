import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.pdf_reader import extraire_texte
from src.llm import poser_question, poser_question_excel
from src.extractor import extraire_infos_facture
from src.database import (init_db, enregistrer_facture, importer_excel_en_db,
                           get_resume_excel, get_clients_avec_pdf, get_texte_pdf_client,
                           get_fichiers_excel,get_client_par_numero_contrat)
from src.excel_reader import lire_excel
from src.llm import detecter_client, est_question_generale, normaliser
from components.navbar import afficher_navbar


def afficher_employe():
    afficher_navbar()

    # ← SIDEBAR SUPPRIMÉE ENTIÈREMENT

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
    if "client_contrat_actif" not in st.session_state:
        st.session_state.client_contrat_actif = None

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
                import re
                _PATTERN_CONTRAT = r'\b\d{10}/\d{7}\b'
                match_contrat = re.search(_PATTERN_CONTRAT, question_excel)

                # ── CAS 1 : numéro de contrat saisi ──
                if match_contrat:
                    numero_saisi = match_contrat.group()
                    client_trouve = get_client_par_numero_contrat(numero_saisi)

                    st.session_state.historique_excel.append(
                        {"role": "user", "content": question_excel}
                    )
                    st.chat_message("user").write(question_excel)

                    if client_trouve:
                        st.session_state.client_contrat_actif = client_trouve

                        from src.rag.fetchers_client import fetch_client_mois_specifique
                        from datetime import datetime
                        _MOIS_FR = {
                            "January": "Janvier", "February": "Fevrier",
                            "March": "Mars", "April": "Avril", "May": "Mai",
                            "June": "Juin", "July": "Juillet", "August": "Aout",
                            "September": "Septembre", "October": "Octobre",
                            "November": "Novembre", "December": "Decembre"
                        }
                        mois_actuel = _MOIS_FR[datetime.now().strftime("%B")]
                        conso_mois = fetch_client_mois_specifique(
                            client_trouve["nom_client"], mois_actuel
                        )

                        reponse = f"""✅ Client trouvé pour le contrat **{numero_saisi}** :

- **Nom** : {client_trouve['nom_client']}
- **Agence** : {client_trouve['agence']}
- **Usage** : {client_trouve['usage']}
- **Service** : {client_trouve['type_service']}
- **Adresse** : {client_trouve['adresse']}
- **N° Client** : {client_trouve['numero_client']}
- **N° Compteur** : {client_trouve['numero_compteur']}

📊 **Consommation {mois_actuel} :**
{conso_mois}

💬 Vous pouvez maintenant poser des questions sur ce client."""

                    else:
                        st.session_state.client_contrat_actif = None
                        reponse = f"❌ Aucun client trouvé pour le numéro de contrat **{numero_saisi}**."

                    st.session_state.historique_excel.append(
                        {"role": "assistant", "content": reponse}
                    )
                    st.chat_message("assistant").write(reponse)

                # ── CAS 2 : question sur le client actif ──
                elif st.session_state.client_contrat_actif:
                    client_actif = st.session_state.client_contrat_actif
                    liste_clients = resume["clients"]

                    # Vérifier si question sur autre client ou question générale
                    autre_client, statut = detecter_client(question_excel, liste_clients)

                    st.session_state.historique_excel.append(
                        {"role": "user", "content": question_excel}
                    )
                    st.chat_message("user").write(question_excel)

                    if statut == "exact" and normaliser(autre_client) != normaliser(client_actif["nom_client"]):
                        # Autre client détecté → quitter contexte contrat
                        st.session_state.client_contrat_actif = None
                        with st.spinner("⏳ Recherche en cours..."):
                            reponse = poser_question_excel(
                                question_excel,
                                st.session_state.historique_excel,
                                nom_fichier=nom_fichier_actif
                            )

                    elif est_question_generale(question_excel):
                        # Question générale → quitter contexte contrat
                        st.session_state.client_contrat_actif = None
                        with st.spinner("⏳ Recherche en cours..."):
                            reponse = poser_question_excel(
                                question_excel,
                                st.session_state.historique_excel,
                                nom_fichier=nom_fichier_actif
                            )

                    else:
                        # Question sur le client actif → garder contexte
                        with st.spinner("⏳ Recherche en cours..."):
                            reponse = poser_question_excel(
                                question_excel,
                                st.session_state.historique_excel,
                                nom_fichier=nom_fichier_actif,
                                nom_client_force=client_actif["nom_client"]
                            )

                    st.session_state.historique_excel.append(
                        {"role": "assistant", "content": reponse}
                    )
                    st.chat_message("assistant").write(reponse)

                # ── CAS 3 : question générale normale ──
                else:
                    st.session_state.historique_excel.append(
                        {"role": "user", "content": question_excel}
                    )
                    st.chat_message("user").write(question_excel)

                    with st.spinner("⏳ Recherche en cours..."):
                        reponse = poser_question_excel(
                            question_excel,
                            st.session_state.historique_excel,
                            nom_fichier=nom_fichier_actif
                        )

                    st.session_state.historique_excel.append(
                        {"role": "assistant", "content": reponse}
                    )
                    st.chat_message("assistant").write(reponse)