import streamlit as st
import sys
import os
import re
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.database import (
    get_nom_client_par_contrat,
    get_mois_client,
    get_derniere_facture_client,
    get_historique_client,
    get_prochain_paiement_client,
    get_statut_paiements_client,
)
from src.rag.intent import _appeler_llm
from src.rag.client_connecte import repondre_client_connecte
from src.rag_client.pdf_facture import generer_pdf_facture
from components.navbar import afficher_navbar


def format_message(text):
    """Convertit les **texte** en <strong>texte</strong> pour le HTML"""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def afficher_client():
    # ══════════════════════════════════════════
    # AFFICHER LE NAVBAR PERSONNALISE
    # ══════════════════════════════════════════
    afficher_navbar()
    
    # 2. Charger le CSS client juste apres la navbar
    css_path = os.path.join(os.path.dirname(__file__), "..", "src", "assets", "Css", "client.css")
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # RESET SESSION SI NOUVEAU UTILISATEUR
    # ══════════════════════════════════════════
    email_actuel = st.session_state.user.get("email")

    if st.session_state.get("_client_email_courant") != email_actuel:
        st.session_state["_client_email_courant"] = email_actuel
        st.session_state["historique_client"] = []
        st.session_state["nom_client_connecte"] = None
        if "msg_accueil" in st.session_state:
            del st.session_state["msg_accueil"]

    # SESSION STATE
    if not st.session_state.get("historique_client"):
        st.session_state.historique_client = []

    if not st.session_state.get("nom_client_connecte"):
        numero_contrat = st.session_state.user.get("numero_client")
        st.session_state.nom_client_connecte = get_nom_client_par_contrat(numero_contrat)

    nom_client = st.session_state.nom_client_connecte

    if not nom_client:
        st.error("Aucun client trouve pour ce compte. Contactez l'administrateur.")
        return

    numero_contrat = st.session_state.user["numero_client"]

    # ══════════════════════════════════════════
    # CHARGER LES DONNEES EN PREMIER
    # ══════════════════════════════════════════
    derniere = get_derniere_facture_client(numero_contrat)
    prochain = get_prochain_paiement_client(numero_contrat)
    statuts  = get_statut_paiements_client(numero_contrat)
    nb_retard = sum(1 for f in statuts if f["en_retard"])
    prenom   = nom_client.split()[0]

    # ══════════════════════════════════════════
    # HEADER HERO PREMIUM
    # ══════════════════════════════════════════
    st.markdown(f'''
    <div class="client-hero">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <div class="hero-avatar">
                <span class="avatar-letter">{prenom[0].upper()}</span>
                <div class="avatar-ring"></div>
            </div>
            <div class="hero-text">
                <span class="hero-badge">Espace Client</span>
                <h1 class="hero-title">Bonjour, {prenom}</h1>
                <p class="hero-subtitle">Bienvenue sur votre espace SRM</p>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # MESSAGE PERSONNALISE (BANNIERE STATUS)
    # ══════════════════════════════════════════
    if derniere:
        if nb_retard > 0:
            phrase_3 = f"{nb_retard} facture(s) non reglee(s) - pensez a contacter votre agence SRM."
            status_class = "status-warning"
            status_icon = '''<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'''
        else:
            phrase_3 = "Votre compte est a jour !"
            status_class = "status-success"
            status_icon = '''<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'''

        if prochain:
            phrase_2 = f"Echeance: <strong>{prochain['date_limite']}</strong> ({prochain['jours']} jours)"
        else:
            phrase_2 = "Aucune echeance a venir"

        st.markdown(f'''
        <div class="status-banner {status_class}">
            <div class="status-header">
                {status_icon}
                <span class="status-title">{phrase_3}</span>
            </div>
            <div class="status-details">
                <span class="status-item">{phrase_2}</span>
                <span class="status-divider">|</span>
                <span class="status-item">Derniere facture: <strong>{derniere['montant']:,.0f} Dhs</strong></span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # MINI-DASHBOARD (METRICS CARDS)
    # ══════════════════════════════════════════
    if derniere:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-icon metric-icon-violet">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
                </div>
                <div class="metric-content">
                    <span class="metric-label">Derniere facture</span>
                    <span class="metric-value">{derniere['montant']:,.0f} Dhs</span>
                    <span class="metric-delta">{derniere['mois']}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        with col2:
            if prochain:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-icon metric-icon-orange">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    </div>
                    <div class="metric-content">
                        <span class="metric-label">Prochaine echeance</span>
                        <span class="metric-value">{prochain['date_limite']}</span>
                        <span class="metric-delta">dans {prochain['jours']} jours</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown('''
                <div class="metric-card">
                    <div class="metric-icon metric-icon-orange">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    </div>
                    <div class="metric-content">
                        <span class="metric-label">Prochaine echeance</span>
                        <span class="metric-value">Aucune</span>
                        <span class="metric-delta">Tout est paye</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

        with col3:
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-icon metric-icon-gradient">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                </div>
                <div class="metric-content">
                    <span class="metric-label">Consommation</span>
                    <span class="metric-value">{derniere['consommation']:,.0f} {derniere['unite']}</span>
                    <span class="metric-delta">{derniere['mois']}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION CHATBOT - HEADER COMPACT
    # ══════════════════════════════════════════
    st.markdown(f'''
    <div class="chat-section-header">
        <div class="chat-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        </div>
        <span class="chat-section-title">Discussion</span>
    </div>
    ''', unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # INIT SUGGESTION
    # ══════════════════════════════════════════
    if "suggestion_choisie" not in st.session_state:
        st.session_state["suggestion_choisie"] = None

    # ══════════════════════════════════════════
    # QUESTIONS RAPIDES
    # ══════════════════════════════════════════
    suggestions = [
        "Mon montant le plus eleve",
        "Suis-je en retard ?",
        "Ma moyenne mensuelle",
        "Mon historique",
    ]

    cols = st.columns(len(suggestions))
    for i, (col, texte) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(texte, key=f"sugg_{i}", use_container_width=True):
                st.session_state["suggestion_choisie"] = texte

    # ══════════════════════════════════════════
    # ANALYSE INTELLIGENTE
    # ══════════════════════════════════════════
    col_llm1, col_llm2 = st.columns(2)
    with col_llm1:
        if st.button("Pourquoi ma facture a augmente ?", key="btn_llm_hausse", use_container_width=True):
            st.session_state["suggestion_choisie"] = "Pourquoi ma facture a augmente par rapport au mois dernier ?"
    with col_llm2:
        if st.button("Comment reduire ma consommation ?", key="btn_llm_conseil", use_container_width=True):
            st.session_state["suggestion_choisie"] = "Comment reduire ma consommation ?"

    # ══════════════════════════════════════════
    # TRAITEMENT SUGGESTION CHOISIE
    # ══════════════════════════════════════════
    if st.session_state["suggestion_choisie"]:
        question_auto = st.session_state["suggestion_choisie"]
        st.session_state["suggestion_choisie"] = None
        st.session_state.historique_client.append({"role": "user", "content": question_auto})

        historique_texte = ""
        for msg in st.session_state.historique_client[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"

        with st.spinner("Analyse en cours..."):
            reponse = repondre_client_connecte(
                question_auto,
                numero_contrat,
                historique_texte
            )
        st.session_state.historique_client.append({"role": "assistant", "content": reponse})
        st.rerun()

    # ══════════════════════════════════════════
    # HISTORIQUE CHAT - CUSTOM BUBBLES
    # ══════════════════════════════════════════
    if st.session_state.historique_client:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in st.session_state.historique_client:
            content_html = format_message(msg["content"])
            if msg["role"] == "user":
                st.markdown(f'''
                <div class="msg-row msg-row-user">
                    <div class="msg-bubble msg-user">
                        <p>{content_html}</p>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="msg-row msg-row-assistant">
                    <div class="msg-bubble msg-assistant">
                        <p>{content_html}</p>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # CHATBOT INPUT
    # ══════════════════════════════════════════
    question = st.chat_input("Votre question sur vos factures...")

    if question:
        st.session_state.historique_client.append({"role": "user", "content": question})

        historique_texte = ""
        for msg in st.session_state.historique_client[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"

        with st.spinner("Recherche en cours..."):
            reponse = repondre_client_connecte(
                question,
                numero_contrat,
                historique_texte
            )

        st.session_state.historique_client.append({"role": "assistant", "content": reponse})
        st.rerun()

    # ══════════════════════════════════════════
    # TELECHARGEMENT FACTURE
    # ══════════════════════════════════════════
    st.markdown('''
    <div class="download-section">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
        <span>Telecharger une facture</span>
    </div>
    ''', unsafe_allow_html=True)

    mois_disponibles = get_mois_client(numero_contrat)

    if mois_disponibles:
        mois_choisi = st.selectbox(
            "Choisir un mois",
            options=mois_disponibles,
            key="mois_telechargement"
        )
        if st.button("Generer la facture", key="btn_generate_pdf"):
            pdf = generer_pdf_facture(numero_contrat, mois_choisi)
            if pdf:
                st.download_button(
                    label="Sauvegarder le PDF",
                    data=pdf,
                    file_name=f"facture_{mois_choisi}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Facture introuvable pour ce mois.")
    else:
        st.info("Aucune facture disponible pour votre compte.")