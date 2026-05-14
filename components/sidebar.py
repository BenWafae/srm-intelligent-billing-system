# components/sidebar.py
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


def afficher_sidebar_client(numero_contrat, nom_client):
    """
    Affiche une sidebar moderne inspirée de DeepSeek/ChatGPT
    """
    
    # Charger le CSS de la sidebar
    css_path = os.path.join(os.path.dirname(__file__), "..", "src", "assets", "Css", "sidebar.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Header avec logo SRM
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <div class="sidebar-logo-wrapper">
            <div class="sidebar-logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <div class="sidebar-logo-text">
                <h1>SRM Intelligence</h1>
                <p>Espace Client</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Bouton Nouvelle conversation
    st.sidebar.markdown('<div class="new-chat-btn-container">', unsafe_allow_html=True)
    if st.sidebar.button(
        "✨ Nouvelle conversation",
        key="new_chat_btn",
        use_container_width=True,
    ):
        return "new_chat"
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # Charger les conversations
    conversations = get_conversations_client(numero_contrat)
    
    if not conversations:
        st.sidebar.markdown("""
        <div class="empty-conv-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <p>Aucune conversation</p>
            <p style="font-size: 11px;">Cliquez sur "Nouvelle conversation"</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Grouper par date
        grouped = group_conversations_by_date(conversations)
        
        for group_name, convs in grouped.items():
            st.sidebar.markdown(f'<div class="sidebar-section-title">{group_name}</div>', unsafe_allow_html=True)
            
            for conv in convs:
                conv_id = conv["id"]
                titre = conv["titre"]
                date_raw = conv["date_creation"]
                
                try:
                    dt = datetime.strptime(date_raw[:19], "%Y-%m-%d %H:%M:%S")
                    date_affichee = dt.strftime("%d/%m")
                except Exception:
                    date_affichee = date_raw[:10] if date_raw else ""
                
                est_active = st.session_state.get("conversation_id_actuelle") == conv_id
                classe_active = "conv-item-active" if est_active else ""
                
                # Mode édition
                if st.session_state.get("titre_en_edition") == conv_id:
                    with st.sidebar.container():
                        st.markdown('<div class="rename-container">', unsafe_allow_html=True)
                        nouveau_titre = st.text_input(
                            "",
                            value=titre,
                            key=f"edit_titre_{conv_id}",
                            label_visibility="collapsed",
                            placeholder="Nouveau titre..."
                        )
                        col_ok, col_annuler = st.columns(2)
                        with col_ok:
                            if st.button("✓", key=f"ok_{conv_id}"):
                                modifier_titre_conversation(conv_id, nouveau_titre)
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        with col_annuler:
                            if st.button("✗", key=f"annuler_{conv_id}"):
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # Affichage normal avec boutons d'action
                    col1, col2, col3 = st.sidebar.columns([5, 1, 1])
                    
                    with col1:
                        if st.button(titre[:35], key=f"load_{conv_id}", use_container_width=True):
                            messages = get_messages_conversation(conv_id)
                            st.session_state["historique_client"] = messages
                            st.session_state["conversation_id_actuelle"] = conv_id
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    with col2:
                        if st.button("✎", key=f"rename_{conv_id}", help="Renommer"):
                            st.session_state["titre_en_edition"] = conv_id
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑", key=f"del_{conv_id}", help="Supprimer"):
                            supprimer_conversation(conv_id)
                            if st.session_state.get("conversation_id_actuelle") == conv_id:
                                st.session_state["historique_client"] = []
                                st.session_state["conversation_id_actuelle"] = None
                            st.rerun()
    
    # Footer avec utilisateur
    prenom = nom_client.split()[0] if nom_client else "Client"
    st.sidebar.markdown(f"""
    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="sidebar-user-avatar">
                <span>{prenom[0].upper()}</span>
            </div>
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">{nom_client}</div>
                <div class="sidebar-user-role">Client SRM</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return None