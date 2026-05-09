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
    get_statut_paiements_client,
)
from src.rag.intent import _appeler_llm
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
        if "msg_accueil" in st.session_state:
            del st.session_state["msg_accueil"]

    # ══════════════════════════════════════════
    # CSS PERSONNALISÉ
    # ══════════════════════════════════════════
    st.markdown("""
    <style>
    /* ── Boutons rapides ── */
    div[data-testid="column"] .stButton > button {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e2e8f0;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 0.5rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 500;
        transition: all 0.2s ease;
        width: 100%;
    }
    div[data-testid="column"] .stButton > button:hover {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
        border-color: #6366f1;
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    }

    /* ── Boutons LLM ── */
    .llm-section .stButton > button {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%) !important;
        border-color: #818cf8 !important;
    }

    /* ── Card style pour section analyse ── */
    .analyse-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid #4338ca;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        margin: 0.5rem 0 1rem 0;
    }
    .analyse-card h4 {
        color: #a5b4fc;
        font-size: 0.95rem;
        margin: 0 0 0.3rem 0;
    }
    .analyse-card p {
        color: #64748b;
        font-size: 0.78rem;
        margin: 0;
    }

    /* ── Séparateur stylé ── */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #334155, transparent);
        margin: 1.5rem 0;
    }

    /* ── Label section rapide ── */
    .section-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)

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
    # CHARGER LES DONNÉES EN PREMIER
    # ══════════════════════════════════════════
    derniere = get_derniere_facture_client(numero_contrat)
    prochain = get_prochain_paiement_client(numero_contrat)
    statuts  = get_statut_paiements_client(numero_contrat)
    nb_retard = sum(1 for f in statuts if f["en_retard"])
    prenom   = nom_client.split()[0]

    # ══════════════════════════════════════════
    # TITRE
    # ══════════════════════════════════════════
    st.title(f"👤 Bonjour, **{nom_client}**")
    st.markdown("Posez vos questions sur vos factures SRM.")
    st.markdown("---")

    # ══════════════════════════════════════════
    # MESSAGE PERSONNALISÉ
    # ══════════════════════════════════════════
    if derniere:
        if nb_retard > 0:
            phrase_3 = f"⚠️ {nb_retard} facture(s) non réglée(s) — pensez à contacter votre agence SRM pour régulariser votre situation."
        else:
            phrase_3 = "✅ Votre compte est à jour, continuez comme ça !"

        if prochain:
            if prochain["jours"] <= 5:
                phrase_2 = f"Attention, votre échéance approche : vous avez jusqu'au **{prochain['date_limite']}** pour régler la facture de {prochain['mois']} (dans {prochain['jours']} jours seulement)."
            elif prochain["jours"] <= 15:
                phrase_2 = f"Votre prochaine échéance est le **{prochain['date_limite']}** pour la facture de {prochain['mois']} — il vous reste {prochain['jours']} jours."
            else:
                phrase_2 = f"Vous avez encore {prochain['jours']} jours pour régler votre facture de {prochain['mois']} (échéance le {prochain['date_limite']})."
        else:
            phrase_2 = "Aucune échéance à venir pour le moment."

        msg_accueil = (
            f"Bonjour {prenom} ! Votre dernière facture porte sur **{derniere['mois']}** "
            f"pour un montant de **{derniere['montant']:,.0f} Dhs** "
            f"({derniere['consommation']:,.0f} {derniere['unite']} consommés). "
            f"{phrase_2} {phrase_3}"
        )

        if nb_retard > 0:
            st.warning(msg_accueil)
        else:
            st.success(msg_accueil)

        st.markdown("---")

    # ══════════════════════════════════════════
    # MINI-DASHBOARD
    # ══════════════════════════════════════════
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
                    delta=f"dans {prochain['jours']} jours — facture de {prochain['mois']}"
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
    # INIT SUGGESTION
    # ══════════════════════════════════════════
    if "suggestion_choisie" not in st.session_state:
        st.session_state["suggestion_choisie"] = None

    # ══════════════════════════════════════════
    # SECTION 1 — QUESTIONS RAPIDES
    # ══════════════════════════════════════════
    st.markdown('<div class="section-label">⚡ Questions rapides</div>', unsafe_allow_html=True)

    suggestions = [
        ("🏆", "Mon montant le plus élevé"),
        ("⏰", "Suis-je en retard ?"),
        ("📊", "Ma moyenne mensuelle"),
        ("📋", "Mon historique complet"),
    ]

    cols = st.columns(len(suggestions))
    for i, (col, (emoji, texte)) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(f"{emoji} {texte}", key=f"sugg_{i}", use_container_width=True):
                st.session_state["suggestion_choisie"] = texte

    # ══════════════════════════════════════════
    # SECTION 2 — ANALYSE INTELLIGENTE (LLM)
    # ══════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="analyse-card">
        <h4>🤖 Analyse intelligente</h4>
        <p>⏳ Ces analyses utilisent l'IA — la réponse peut prendre quelques secondes</p>
    </div>
    """, unsafe_allow_html=True)

    col_llm1, col_llm2 = st.columns(2)
    with col_llm1:
        if st.button(
            "📈 Pourquoi ma facture a augmenté ?",
            key="btn_llm_hausse",
            use_container_width=True,
            help="Analyse comparative avec le mois précédent"
        ):
            st.session_state["suggestion_choisie"] = "Pourquoi ma facture a augmenté par rapport au mois dernier ?"
    with col_llm2:
        if st.button(
            "💡 Comment réduire ma consommation ?",
            key="btn_llm_conseil",
            use_container_width=True,
            help="Conseils personnalisés selon votre profil"
        ):
            st.session_state["suggestion_choisie"] = "Comment réduire ma consommation ?"

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

        with st.spinner("⏳ Analyse en cours..."):
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