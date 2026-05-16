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
        height: 100vh !important;  /* Hauteur totale de l'écran */
        overflow: hidden !important;  /* Empêche le scroll global */
    }

    /* ── Header fixe ── */
    .sidebar-header {
        padding: 28px 24px 20px 24px !important;
        border-bottom: 1px solid rgba(203,213,225,0.5);
        margin-bottom: 0px;
        flex-shrink: 0;  /* Empêche le rétrécissement */
        background: rgba(255,255,255,0.98);
        z-index: 10;
    }
    .sidebar-logo-wrapper { display:flex; align-items:center; gap:14px; }
    .sidebar-logo-icon {
        width:44px; height:44px;
        background: linear-gradient(135deg,#667eea 0%,#764ba2 100%);
        border-radius:14px; display:flex; align-items:center;
        justify-content:center; box-shadow:0 8px 20px rgba(102,126,234,.25);
        transition:transform .3s ease;
    }
    .sidebar-logo-icon:hover { transform:scale(1.02); }
    .sidebar-logo-icon svg { width:24px; height:24px; color:white; }
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

    /* Style du bouton Streamlit */
    [data-testid="stSidebar"] .stButton > button {
        width:calc(100% - 32px) !important;
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%) !important;
        border:none !important;
        border-radius:12px !important;
        padding:12px 16px !important;
        color:white !important;
        font-size:14px !important;
        font-weight:600 !important;
        margin:4px 16px 16px 16px !important;
        transition:all .3s ease !important;
        box-shadow: none !important;
        flex-shrink: 0;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 8px 20px rgba(102,126,234,.3) !important;
    }

    /* ── Section titles ── */
    .sidebar-section-title {
        font-size:11px !important; font-weight:700 !important;
        color:#64748b !important; padding:16px 24px 8px 24px !important;
        text-transform:uppercase; letter-spacing:.08em;
        margin: 0;
    }

    /* ── Zone scrollable UNIQUEMENT pour les conversations ── */
    .conversations-scrollable {
        flex: 1;  /* Prend tout l'espace restant */
        overflow-y: auto;  /* Scroll uniquement ici */
        overflow-x: hidden;
        min-height: 0;  /* Important pour le flexbox */
        padding: 0 8px;
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
        margin: 4px 0;
        border-radius: 10px;
        transition: all .2s ease;
    }
    .conv-wrapper:hover {
        background: linear-gradient(135deg, rgba(102,126,234,.08) 0%, rgba(118,75,162,.08) 100%);
        transform: translateX(4px);
    }
    .conv-wrapper-active {
        background: linear-gradient(135deg, rgba(102,126,234,.12) 0%, rgba(118,75,162,.12) 100%);
        border-left: 3px solid #667eea;
    }
    .conv-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
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
        color: #667eea;
        font-weight: 700;
    }
    .conv-actions {
        display: flex;
        gap: 6px;
        opacity: 0;
        transition: opacity .2s ease;
    }
    .conv-wrapper:hover .conv-actions {
        opacity: 1;
    }
    .conv-btn {
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px 8px;
        cursor: pointer;
        font-size: 14px;
        transition: all .2s ease;
        color: #94a3b8;
    }
    .conv-btn:hover {
        background: rgba(102,126,234,.1);
        color: #667eea;
        transform: scale(1.05);
    }
    .conv-btn-delete:hover {
        background: rgba(239,68,68,.1);
        color: #ef4444;
    }

    /* ── Mode édition ── */
    .rename-container {
        padding:12px;
        background:linear-gradient(135deg,rgba(102,126,234,.05) 0%,rgba(118,75,162,.05) 100%);
        border-radius:12px; margin:8px 4px;
    }
    .rename-input {
        width:100%; background:white; border:2px solid #e2e8f0;
        border-radius:10px; padding:10px 12px; font-size:13px;
        font-family:'Inter',sans-serif; margin-bottom:10px;
    }
    .rename-input:focus { outline:none; border-color:#667eea; }
    .rename-actions { display:flex; gap:10px; }
    .rename-confirm, .rename-cancel {
        flex:1; padding:8px; border-radius:8px; border:none;
        font-size:12px; font-weight:600; cursor:pointer; transition:all .2s ease;
    }
    .rename-confirm {
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white;
    }
    .rename-cancel { background:#f1f5f9; color:#64748b; }
    .rename-confirm:hover, .rename-cancel:hover { transform:translateY(-1px); }

    /* ── Footer fixe ── */
    .sidebar-footer {
        flex-shrink: 0;  /* Empêche le rétrécissement */
        margin-top: auto;
        padding: 16px 20px 20px 20px;
        border-top: 1px solid #e2e8f0;
        background: rgba(255,255,255,.95);
        z-index: 10;
    }
    .sidebar-user {
        display:flex; align-items:center; gap:12px; cursor:pointer;
        padding:8px 0; border-radius:12px; transition:all .2s ease;
    }
    .sidebar-user:hover {
        background:linear-gradient(135deg,rgba(102,126,234,.06) 0%,rgba(118,75,162,.06) 100%);
        padding-left:8px;
    }
    .sidebar-user-avatar {
        width:40px; height:40px; border-radius:12px;
        background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
        display:flex; align-items:center; justify-content:center;
        flex-shrink:0; box-shadow:0 4px 12px rgba(102,126,234,.25);
    }
    .sidebar-user-avatar span { font-size:14px; font-weight:700; color:white; }
    .sidebar-user-name { font-size:13px; font-weight:700; color:#1e293b; }
    .sidebar-user-role { font-size:9px; font-weight:700; color:#667eea; text-transform:uppercase; }

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

    # ── Header fixe ──────────────────────────────────────────────
    st.sidebar.markdown(
        """
    <div class="sidebar-header">
        <div class="sidebar-logo-wrapper">
            <div class="sidebar-logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    <path d="M12 2v20"/>
                </svg>
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

    # ── Bouton Nouvelle conversation (fixe) ────────────────────────
    new_chat_clicked = st.sidebar.button("✨ Nouvelle conversation", key="btn_new_chat", use_container_width=True)
    
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

                # ── Mode renommage ──────────────────────────
                if st.session_state.get("titre_en_edition") == conv_id:
                    st.sidebar.markdown('<div class="rename-container">', unsafe_allow_html=True)
                    
                    nouveau_titre = st.sidebar.text_input(
                        "Nouveau titre",
                        value=titre,
                        key=f"input_rename_{conv_id}",
                        label_visibility="collapsed",
                        placeholder="Nouveau titre..."
                    )
                    
                    col_ok, col_cancel = st.sidebar.columns(2)
                    with col_ok:
                        if st.button("✓ Valider", key=f"confirm_rename_{conv_id}", use_container_width=True):
                            if nouveau_titre.strip():
                                modifier_titre_conversation(conv_id, nouveau_titre.strip())
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    with col_cancel:
                        if st.button("✗ Annuler", key=f"cancel_rename_{conv_id}", use_container_width=True):
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    st.sidebar.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    # ── Ligne de conversation avec style moderne ──
                    active_class = "conv-wrapper-active" if est_active else ""
                    
                    # Affichage HTML pour le conteneur stylisé
                    st.sidebar.markdown(
                        f'<div class="conv-wrapper {active_class}"><div class="conv-content"><span class="conv-titre">{titre[:45]}</span><div class="conv-actions">',
                        unsafe_allow_html=True
                    )
                    
                    # Boutons d'action (load, rename, delete) en colonnes
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

    # ── Footer utilisateur (fixe) ───────────────────────────────────
    initiales = (
        "".join([w[0].upper() for w in nom_client.split()[:2]]) if nom_client else "C"
    )

    st.sidebar.markdown(
        f"""
    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="sidebar-user-avatar"><span>{initiales}</span></div>
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