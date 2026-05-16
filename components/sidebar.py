import streamlit as st
import os
from datetime import datetime
from src.database import (
    get_conversations_client,
    get_messages_conversation,
    modifier_titre_conversation,
    supprimer_conversation,
)

def group_conversations_by_date(conversations):
    """Groupe les conversations par catégories de dates"""
    today = datetime.now().date()
    groups = {}
    
    for conv in conversations:
        try:
            date_str = conv["date_creation"][:19]
            conv_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
            days_diff = (today - conv_date).days
            
            if days_diff == 0:
                group = "Aujourd'hui"
            elif days_diff == 1:
                group = "Hier"
            elif days_diff <= 7:
                group = "Cette semaine"
            elif days_diff <= 30:
                group = "Ce mois"
            else:
                group = conv_date.strftime("%B %Y")
            
            if group not in groups:
                groups[group] = []
            groups[group].append(conv)
        except Exception:
            if "Plus ancien" not in groups:
                groups["Plus ancien"] = []
            groups["Plus ancien"].append(conv)
    
    return groups


def _inject_css():
    """Injecte tout le CSS du design premium avec gestion des boutons."""
    css_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "assets", "Css", "sidebar.css"
    )
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown(
        """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    .block-container { padding-top: 0rem !important; }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important; margin-top: 0 !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.98) !important;
        width: 300px !important; min-width: 300px !important;
        border-right: 1px solid rgba(203,213,225,0.5) !important;
        box-shadow: 4px 0 20px rgba(0,0,0,0.02) !important;
    }

    [data-testid="stSidebarContent"] {
        background: transparent !important; padding: 0 !important;
        display: flex; flex-direction: column;
        height: 100vh !important;
        overflow: hidden !important;
    }

    /* ── Header fixe avec logo réel SRM et anneau pulsant ── */
    .sidebar-header {
        padding: 28px 24px 20px 24px !important;
        border-bottom: 1px solid rgba(203,213,225,0.5);
        margin-bottom: 0px;
        flex-shrink: 0;
        background: rgba(255,255,255,0.98);
        z-index: 10;
    }
    .sidebar-logo-wrapper { display:flex; align-items:center; gap:14px; }
    
    /* Conteneur du logo avec le même effet d'anneau que l'avatar */
    .sidebar-logo-container {
        position: relative;
        width: 44px;
        height: 44px;
        flex-shrink: 0;
    }
    
    /* Anneau pulsant autour du logo (exactement comme l'avatar) */
    .logo-ring {
        position: absolute;
        inset: -3px;
        border-radius: 14px;
        border: 2px solid transparent;
        background: linear-gradient(135deg, #8b5cf6, #f97316) border-box;
        -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
        mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: destination-out;
        mask-composite: exclude;
        animation: pulse-ring 2.5s ease-in-out infinite;
        pointer-events: none;
        z-index: 2;
    }
    
    @keyframes pulse-ring {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.08); }
    }
    
    .sidebar-logo-icon {
        width: 100%;
        height: 100%;
        background: white !important;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 20px rgba(102,126,234,.25);
        transition: transform .3s ease, box-shadow .3s ease;
        position: relative;
        padding: 6px;
        z-index: 1;
        /* Bordure gradient permanente */
        border: 2px solid transparent;
        background: linear-gradient(white, white) padding-box,
                    linear-gradient(135deg, #8b5cf6 0%, #f97316 50%, #8b5cf6 100%) border-box;
        background-clip: padding-box, border-box;
    }
    
    .sidebar-logo-icon:hover {
        transform: scale(1.02);
        box-shadow: 0 12px 28px rgba(249,115,22,.3);
        background: linear-gradient(white, white) padding-box,
                    linear-gradient(135deg, #f97316 0%, #8b5cf6 50%, #f97316 100%) border-box;
        background-clip: padding-box, border-box;
    }
    
    /* Style de l'image du logo */
    .sidebar-logo-img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        border-radius: 10px;
    }
    
    .sidebar-logo-text h1 {
        font-size:20px; font-weight:800;
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        margin:0;
    }
    .sidebar-logo-text p {
        font-size:10px; color:#94a3b8; margin:4px 0 0 0;
        font-weight:600; text-transform:uppercase;
    }

    /* Style du bouton Nouvelle conversation avec + stylisé */
    [data-testid="stSidebar"] .stButton > button {
        width:calc(100% - 32px) !important;
        background:linear-gradient(135deg,#667eea 0%,#f97316 100%) !important;
        border:none !important;
        border-radius:12px !important;
        padding:12px 16px !important;
        color:white !important;
        font-size:14px !important;
        font-weight:600 !important;
        margin:4px 16px 16px 16px !important;
        transition:all .3s ease !important;
        box-shadow:0 4px 12px rgba(102,126,234,.25) !important;
        flex-shrink: 0;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        cursor: pointer !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 20px rgba(249,115,22,.4) !important;
        background:linear-gradient(135deg,#764ba2 0%,#f97316 100%) !important;
    }
    
    /* Style pour le symbole + dans le bouton */
    [data-testid="stSidebar"] .stButton > button::before {
        content: "+";
        font-size: 20px;
        font-weight: 700;
        margin-right: 4px;
        line-height: 1;
    }

    /* ── Section titles ── */
    .sidebar-section-title {
        font-size:11px !important; font-weight:700 !important;
        color:#64748b !important; padding:12px 24px 4px 24px !important;
        text-transform:uppercase; letter-spacing:.08em;
        margin: 0;
    }

    /* ── Zone scrollable UNIQUEMENT pour les conversations ── */
    .conversations-scrollable {
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        min-height: 0;
        padding: 0;
        margin: 0;
    }
    .conversations-scrollable::-webkit-scrollbar { width: 4px; }
    .conversations-scrollable::-webkit-scrollbar-track { background: transparent; }
    .conversations-scrollable::-webkit-scrollbar-thumb {
        background: #cbd5e1; border-radius: 10px;
    }
    .conversations-scrollable::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }

    /* Style pour la ligne de conversation avec les boutons */
    .conv-wrapper {
        margin: 0;
        padding: 0;
        border-radius: 0;
        transition: all .2s ease;
    }
    .conv-wrapper:hover {
        background: linear-gradient(135deg, rgba(102,126,234,.08) 0%, rgba(118,75,162,.08) 100%);
    }
    .conv-wrapper-active {
        background: linear-gradient(135deg, rgba(102,126,234,.12) 0%, rgba(118,75,162,.12) 100%);
        border-left: 3px solid #f97316;
    }
    .conv-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 12px;
        gap: 8px;
    }
    .conv-titre {
        flex: 1;
        font-size: 14px;
        font-weight: 500;
        color: #1e293b;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .conv-wrapper-active .conv-titre {
        color: #f97316;
        font-weight: 700;
    }
    .conv-actions {
        display: flex;
        gap: 4px;
        opacity: 0;
        transition: opacity .2s ease;
    }
    .conv-wrapper:hover .conv-actions {
        opacity: 1;
    }
    .conv-btn {
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 4px 6px;
        cursor: pointer;
        font-size: 14px;
        transition: all .2s ease;
        color: #94a3b8;
    }
    .conv-btn:hover {
        background: rgba(102,126,234,.1);
        color: #f97316;
        transform: scale(1.05);
    }
    .conv-btn-delete:hover {
        background: rgba(239,68,68,.1);
        color: #ef4444;
    }

    /* ── Mode édition en ligne ── */
    .rename-inline {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: 1;
    }
    .rename-input-inline {
        flex: 1;
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        padding: 4px 8px;
        font-size: 13px;
        font-family: 'Inter', sans-serif;
    }
    .rename-input-inline:focus { 
        outline: none; 
        border-color: #f97316;
    }
    .rename-icon {
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 4px 8px;
        cursor: pointer;
        font-size: 14px;
        transition: all .2s ease;
        color: #94a3b8;
    }
    .rename-icon:hover {
        background: rgba(102,126,234,.1);
        color: #f97316;
        transform: scale(1.05);
    }

    /* ── Footer fixe avec avatar et anneau pulsant ── */
    .sidebar-footer {
        flex-shrink: 0;
        margin-top: auto;
        padding: 16px 20px 20px 20px;
        border-top: 1px solid #e2e8f0;
        background: rgba(255,255,255,.95);
        z-index: 10;
    }
    .sidebar-user {
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        padding: 8px 0;
        border-radius: 12px;
        transition: all .2s ease;
    }
    .sidebar-user:hover {
        background: linear-gradient(135deg, rgba(102,126,234,.06) 0%, rgba(118,75,162,.06) 100%);
        padding-left: 8px;
    }
    
    /* Conteneur de l'avatar footer avec anneau pulsant */
    .sidebar-user-avatar-container {
        position: relative;
        width: 40px;
        height: 40px;
        flex-shrink: 0;
    }
    
    /* Anneau pulsant autour de l'avatar footer (exactement comme l'avatar principal) */
    .avatar-footer-ring {
        position: absolute;
        inset: -3px;
        border-radius: 12px;
        border: 2px solid transparent;
        background: linear-gradient(135deg, #8b5cf6, #f97316) border-box;
        -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
        mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: destination-out;
        mask-composite: exclude;
        animation: pulse-ring 2.5s ease-in-out infinite;
        pointer-events: none;
        z-index: 2;
    }
    
    .sidebar-user-avatar {
        width: 100%;
        height: 100%;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #f97316 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(102,126,234,.25);
        position: relative;
        z-index: 1;
        transition: transform .3s ease;
    }
    
    .sidebar-user:hover .sidebar-user-avatar {
        transform: scale(1.05);
    }
    
    .sidebar-user-avatar span {
        font-size: 14px;
        font-weight: 700;
        color: white;
    }
    
    .sidebar-user-info {
        flex: 1;
        min-width: 0;
    }
    .sidebar-user-name {
        font-size: 13px;
        font-weight: 700;
        color: #1e293b;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .sidebar-user-role {
        font-size: 9px;
        font-weight: 700;
        color: #f97316;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── État vide ── */
    .empty-conv-state { padding:48px 24px; text-align:center; }
    .empty-conv-state svg { color:#cbd5e1; margin-bottom:16px; }
    .empty-conv-state p { font-size:14px; color:#64748b; margin:8px 0; }
    .empty-conv-state p:first-of-type { font-weight:700; color:#1e293b; }

    /* Cache les éléments Streamlit natifs */
    [data-testid="stSidebarNav"], .st-emotion-cache-1dp5vir { display:none !important; }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    section[data-testid="stSidebarCollapsedControl"] { display:none !important; }

    /* Cache les espaces Streamlit entre éléments sidebar */
    [data-testid="stSidebar"] .element-container {
        margin-top:0 !important; margin-bottom:0 !important;
        padding-top:0 !important; padding-bottom:0 !important;
    }
    [data-testid="stSidebar"] .stButton { margin:0 !important; padding:0 !important; }
    
    /* Style personnalisé pour les colonnes dans la sidebar */
    [data-testid="stSidebar"] .stColumns {
        gap: 4px !important;
    }
    [data-testid="stSidebar"] .stColumn {
        padding: 0 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def afficher_sidebar_client(numero_contrat: str, nom_client: str):
    """
    Sidebar premium avec persistance conversationnelle complète.
    Utilise des st.button pour toutes les interactions (fonctionnel à 100%).
    
    Retourne "new_chat" si l'utilisateur clique sur Nouvelle conversation,
    None sinon.
    """
    _inject_css()

    # ── Chemin du logo réel SRM ──
    logo_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "assets", "srm_logo.png"
    )
    
    # Vérifier si le logo existe, sinon utiliser l'icône par défaut
    if os.path.exists(logo_path):
        # Lire l'image et la convertir en base64 pour l'afficher directement
        import base64
        with open(logo_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{img_data}" class="sidebar-logo-img" alt="SRM Logo">'
    else:
        # Fallback: icône SVG par défaut
        logo_html = """
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            <path d="M12 2v20"/>
        </svg>
        """

    # ── Header fixe avec logo réel SRM et anneau pulsant ──────────────────────────────
    st.sidebar.markdown(
        f"""
    <div class="sidebar-header">
        <div class="sidebar-logo-wrapper">
            <div class="sidebar-logo-container">
                <div class="logo-ring"></div>
                <div class="sidebar-logo-icon">
                    {logo_html}
                </div>
            </div>
            <div class="sidebar-logo-text">
                <h1>SRM</h1>
                <p>Société Régionale Multiservices</p>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Bouton Nouvelle conversation avec + stylisé ────────────────────────
    new_chat_clicked = st.sidebar.button("Nouvelle conversation", key="btn_new_chat", use_container_width=True)
    
    if new_chat_clicked:
        st.session_state["historique_client"] = []
        st.session_state["conversation_id_actuelle"] = None
        st.session_state["titre_en_edition"] = None
        return "new_chat"

    # ── Charger les conversations (zone scrollable) ────────────────────────────
    conversations = get_conversations_client(numero_contrat)

    if not conversations:
        st.sidebar.markdown(
            """
        <div class="empty-conv-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                <path d="M8 10h.01M12 10h.01M16 10h.01"/>
            </svg>
            <p>Aucune conversation</p>
            <p style="font-size:12px;">Démarrez une nouvelle discussion ✨</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        # Début de la zone scrollable
        st.sidebar.markdown('<div class="conversations-scrollable">', unsafe_allow_html=True)

        grouped = group_conversations_by_date(conversations)

        for group_name, convs in grouped.items():
            st.sidebar.markdown(
                f'<div class="sidebar-section-title">{group_name}</div>',
                unsafe_allow_html=True,
            )

            for conv in convs:
                conv_id = conv["id"]
                titre = conv["titre"]
                est_active = st.session_state.get("conversation_id_actuelle") == conv_id

                # ── Mode renommage en ligne ──────────────────────────
                if st.session_state.get("titre_en_edition") == conv_id:
                    # Affichage du conteneur principal
                    st.sidebar.markdown(
                        f'<div class="conv-wrapper {active_class if est_active else ""}"><div class="conv-content">',
                        unsafe_allow_html=True
                    )
                    
                    # Champ de texte inline
                    nouveau_titre = st.sidebar.text_input(
                        "Nouveau titre",
                        value=titre,
                        key=f"input_rename_{conv_id}",
                        label_visibility="collapsed",
                        placeholder="Nouveau titre..."
                    )
                    
                    # Conteneur inline pour les boutons icônes
                    col_ok, col_cancel = st.sidebar.columns([1, 1])
                    with col_ok:
                        if st.button("✓", key=f"confirm_rename_{conv_id}", help="Valider"):
                            if nouveau_titre.strip():
                                modifier_titre_conversation(conv_id, nouveau_titre.strip())
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    with col_cancel:
                        if st.button("✗", key=f"cancel_rename_{conv_id}", help="Annuler"):
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    st.sidebar.markdown('</div></div>', unsafe_allow_html=True)
                
                else:
                    # ── Ligne de conversation avec style moderne ──
                    active_class = "conv-wrapper-active" if est_active else ""
                    
                    # Affichage HTML pour le conteneur stylisé
                    st.sidebar.markdown(
                        f'<div class="conv-wrapper {active_class}"><div class="conv-content"><span class="conv-titre">{titre[:45]}</span><div class="conv-actions">',
                        unsafe_allow_html=True
                    )
                    
                    # Boutons d'action (load, rename, delete) en colonnes sans espace
                    col_load, col_rename, col_delete = st.sidebar.columns([1, 1, 1])
                    
                    with col_load:
                        if st.button("💬", key=f"load_{conv_id}", help="Ouvrir cette conversation"):
                            messages = get_messages_conversation(conv_id)
                            st.session_state["historique_client"] = messages
                            st.session_state["conversation_id_actuelle"] = conv_id
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    with col_rename:
                        if st.button("✎", key=f"rename_{conv_id}", help="Renommer"):
                            st.session_state["titre_en_edition"] = conv_id
                            st.rerun()
                    
                    with col_delete:
                        if st.button("🗑", key=f"delete_{conv_id}", help="Supprimer"):
                            supprimer_conversation(conv_id)
                            if st.session_state.get("conversation_id_actuelle") == conv_id:
                                st.session_state["historique_client"] = []
                                st.session_state["conversation_id_actuelle"] = None
                            st.rerun()
                    
                    # Fermeture du HTML
                    st.sidebar.markdown('</div></div></div>', unsafe_allow_html=True)

        # Fin de la zone scrollable
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # ── Footer utilisateur avec avatar et anneau pulsant (assorti au logo) ──
    initiales = (
        "".join([w[0].upper() for w in nom_client.split()[:2]]) if nom_client else "C"
    )

    st.sidebar.markdown(
        f"""
    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="sidebar-user-avatar-container">
                <div class="avatar-footer-ring"></div>
                <div class="sidebar-user-avatar">
                    <span>{initiales}</span>
                </div>
            </div>
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">{nom_client}</div>
                <div class="sidebar-user-role">Espace Client</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    return None