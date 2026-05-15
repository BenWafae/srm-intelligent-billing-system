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

def afficher_sidebar_client(numero_contrat, nom_client):
    """
    Affiche une sidebar ultra-premium avec logique Streamlit intacte
    """
    
    # Charger le CSS
    css_path = os.path.join(os.path.dirname(__file__), "..", "src", "assets", "Css", "sidebar.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # CSS supplémentaire pour supprimer les espaces entre les conversations et aligner à gauche
    st.markdown("""
    <style>
    /* Supprimer tous les backgrounds et bordures des colonnes dans la sidebar */
    [data-testid="stSidebar"] .stHorizontalBlock,
    [data-testid="stSidebar"] [data-testid="column"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        gap: 0 !important;
    }
    
    /* Supprimer les paddings par défaut des colonnes */
    [data-testid="stSidebar"] [data-testid="column"] {
        padding: 0 !important;
    }
    
    /* S'assurer que les boutons n'ont pas de bordures */
    [data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    [data-testid="stSidebar"] .stButton button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    
    /* Ajuster l'espacement entre les colonnes */
    .stHorizontalBlock {
        gap: 0px !important;
    }
    
    /* NOUVEAU : Supprimer les espaces entre les conversations */
    .element-container:has(.stButton) {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* NOUVEAU : Aligner les titres des sections à gauche */
    .sidebar-section-title {
        text-align: left !important;
        padding-left: 0 !important;
    }
    
    /* NOUVEAU : Aligner les boutons de conversation à gauche */
    div[data-testid="column"]:first-child button {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    
    /* Réduire l'espace entre les lignes de conversation */
    .stHorizontalBlock {
        margin-bottom: -10px !important;
    }
    
    /* Supprimer l'espace supplémentaire dans la zone scrollable */
    .conversations-scrollable {
        margin-top: -10px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header avec logo
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <div class="sidebar-logo-wrapper">
            <div class="sidebar-logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    <path d="M12 2v20"/>
                </svg>
            </div>
            <div class="sidebar-logo-text">
                <h1>SRM Intelligence</h1>
                <p>Platform Premium</p>
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
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                <path d="M8 10h.01M12 10h.01M16 10h.01"/>
            </svg>
            <p>Aucune conversation</p>
            <p style="font-size: 12px;">Démarrez une nouvelle discussion ✨</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # OUVERTURE DU CONTENEUR SCROLLABLE
        st.sidebar.markdown('<div class="conversations-scrollable">', unsafe_allow_html=True)
        
        # Grouper par date
        grouped = group_conversations_by_date(conversations)
        
        for group_name, convs in grouped.items():
            st.sidebar.markdown(
    f'<div class="sidebar-section-title" style="padding: 10px 0 2px 4px; margin: 0;">{group_name}</div>',
    unsafe_allow_html=True
)
            
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
                            if st.button("✓ Valider", key=f"ok_{conv_id}", use_container_width=True):
                                modifier_titre_conversation(conv_id, nouveau_titre)
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        with col_annuler:
                            if st.button("✗ Annuler", key=f"annuler_{conv_id}", use_container_width=True):
                                st.session_state["titre_en_edition"] = None
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # Utilisation des colonnes Streamlit (logique originale qui fonctionne)
                    col1, col2 = st.sidebar.columns([10, 1])
                    
                    with col1:
                        # Style pour le bouton titre - MODIFIÉ: aligné à gauche
                        st.markdown(f"""
                        <style>
                        div[data-testid="column"]:first-child button {{
                            text-align: left !important;
                            justify-content: flex-start !important;
                            background: transparent !important;
                            border: none !important;
                            padding: 8px 0 !important;
                            margin: 0 !important;
                            font-weight: {"700" if est_active else "500"} !important;
                            color: {"#667eea" if est_active else "#1e293b"} !important;
                            width: 100% !important;
                            cursor: pointer !important;
                            border-radius: 8px !important;
                            transition: all 0.2s ease !important;
                            white-space: nowrap !important;
                            overflow: hidden !important;
                            text-overflow: ellipsis !important;
                            display: block !important;
                        }}
                        div[data-testid="column"]:first-child button:hover {{
                            background: rgba(102, 126, 234, 0.08) !important;
                            padding-left: 8px !important;
                        }}
                        /* Supprimer l'espace entre les colonnes */
                        div[data-testid="column"] {{
                            margin: 0 !important;
                            padding: 0 !important;
                        }}
                        </style>
                        """, unsafe_allow_html=True)
                        
                        # Bouton titre pour charger la conversation
                        if st.button(titre[:40], key=f"load_{conv_id}", use_container_width=True):
                            # Fermer le menu ouvert
                            st.session_state["menu_open_for"] = None
                            # Charger les messages
                            messages = get_messages_conversation(conv_id)
                            st.session_state["historique_client"] = messages
                            st.session_state["conversation_id_actuelle"] = conv_id
                            st.session_state["titre_en_edition"] = None
                            st.rerun()
                    
                    with col2:
                        # Style pour le bouton 3 points
                        st.markdown(f"""
                        <style>
                        div[data-testid="column"]:last-child {{
                            display: flex !important;
                            justify-content: flex-end !important;
                            background: transparent !important;
                            border: none !important;
                            margin: 0 !important;
                            padding: 0 !important;
                        }}
                        div[data-testid="column"]:last-child button {{
                            background: transparent !important;
                            border: none !important;
                            color: #94a3b8 !important;
                            font-size: 18px !important;
                            font-weight: 600 !important;
                            cursor: pointer !important;
                            padding: 6px 0 !important;
                            border-radius: 8px !important;
                            transition: all 0.2s ease !important;
                            width: auto !important;
                            min-width: 30px !important;
                            margin: 0 !important;
                        }}
                        div[data-testid="column"]:last-child button:hover {{
                            background: rgba(102, 126, 234, 0.1) !important;
                            color: #667eea !important;
                        }}
                        </style>
                        """, unsafe_allow_html=True)
                        
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
                            # CSS pour le menu premium
                            st.markdown("""
                            <style>
                            .menu-contextuel-premium {
                                background: white;
                                border: 1px solid #e2e8f0;
                                border-radius: 14px;
                                box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.15);
                                margin-left: 40px;
                                margin-bottom: 4px;
                                margin-top: 2px;
                                overflow: hidden;
                                animation: dropdownSlide 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                            }
                            .menu-contextuel-premium button {
                                width: 100% !important;
                                text-align: left !important;
                                padding: 10px 16px !important;
                                background: transparent !important;
                                border: none !important;
                                cursor: pointer !important;
                                font-size: 13px !important;
                                font-weight: 500 !important;
                                color: #1e293b !important;
                                border-radius: 0 !important;
                                transition: all 0.2s ease !important;
                            }
                            .menu-contextuel-premium button:hover {
                                background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%) !important;
                                padding-left: 20px !important;
                            }
                            .menu-contextuel-premium .delete-option {
                                color: #ef4444 !important;
                            }
                            .menu-contextuel-premium .delete-option:hover {
                                background: rgba(239, 68, 68, 0.08) !important;
                            }
                            @keyframes dropdownSlide {
                                from {
                                    opacity: 0;
                                    transform: translateY(-10px);
                                }
                                to {
                                    opacity: 1;
                                    transform: translateY(0);
                                }
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            st.markdown('<div class="menu-contextuel-premium">', unsafe_allow_html=True)
                            
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
        
        # FERMETURE DU CONTENEUR SCROLLABLE
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # Footer avec utilisateur
    prenom = nom_client.split()[0] if nom_client else "Client"
    initiales = ''.join([word[0].upper() for word in nom_client.split()[:2]]) if nom_client else "C"
    
    st.sidebar.markdown(f"""
    <div class="sidebar-footer">
        <div class="sidebar-user">
            <div class="sidebar-user-avatar">
                <span>{initiales}</span>
            </div>
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">{nom_client}</div>
                <div class="sidebar-user-role">Client Premium</div>
            </div>
            <button class="user-menu-btn" id="userMenuBtn">⚙️</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return None