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
                            if st.button("✓ Valider", key=f"ok_{conv_id}"):
                                modifier_titre_conversation(conv_id, nouveau_titre)
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        with col_annuler:
                            if st.button("✗ Annuler", key=f"annuler_{conv_id}"):
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # Afficher le titre et le menu 3 points
                    col1, col2 = st.sidebar.columns([10, 1])
                    
                    with col1:
                        # Bouton titre pour charger la conversation
                        if st.button(titre[:40], key=f"load_{conv_id}", use_container_width=True):
                            # Fermer le menu ouvert
                            st.session_state["menu_open_for"] = None
                            messages = get_messages_conversation(conv_id)
                            st.session_state["historique_client"] = messages
                            st.session_state["conversation_id_actuelle"] = conv_id
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    with col2:
                        # Bouton 3 points
                        if st.button("⋯", key=f"menu_btn_{conv_id}"):
                            # Toggle du menu
                            if st.session_state.get("menu_open_for") == conv_id:
                                st.session_state["menu_open_for"] = None
                            else:
                                st.session_state["menu_open_for"] = conv_id
                            st.rerun()
                    
                    # Afficher le menu contextuel si ouvert
                    if st.session_state.get("menu_open_for") == conv_id:
                        # Créer un conteneur pour le menu
                        menu_container = st.sidebar.container()
                        with menu_container:
                            # CSS pour le menu
                            st.markdown("""
                            <style>
                            .menu-contextuel {
                                background: white;
                                border: 1px solid rgba(139, 92, 246, 0.2);
                                border-radius: 12px;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                margin-left: 40px;
                                margin-bottom: 10px;
                                overflow: hidden;
                            }
                            .menu-contextuel button {
                                width: 100% !important;
                                text-align: left !important;
                                padding: 10px 15px !important;
                                background: transparent !important;
                                border: none !important;
                                cursor: pointer !important;
                                font-size: 13px !important;
                                font-weight: 500 !important;
                                color: #333 !important;
                                border-radius: 0 !important;
                            }
                            .menu-contextuel button:hover {
                                background: #f5f3ff !important;
                            }
                            .menu-contextuel .delete-option {
                                color: #ef4444 !important;
                            }
                            .menu-contextuel .delete-option:hover {
                                background: #fef2f2 !important;
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            st.markdown('<div class="menu-contextuel">', unsafe_allow_html=True)
                            
                            # Option Renommer
                            if st.button("✎ Renommer", key=f"rename_option_{conv_id}", use_container_width=True):
                                st.session_state["titre_en_edition"] = conv_id
                                st.session_state["menu_open_for"] = None
                                st.rerun()
                            
                            # Option Supprimer
                            if st.button("🗑 Supprimer", key=f"delete_option_{conv_id}", use_container_width=True):
                                supprimer_conversation(conv_id)
                                if st.session_state.get("conversation_id_actuelle") == conv_id:
                                    st.session_state["historique_client"] = []
                                    st.session_state["conversation_id_actuelle"] = None
                                st.session_state["menu_open_for"] = None
                                st.rerun()
                            
                            st.markdown('</div>', unsafe_allow_html=True)
    
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