# pipeline complet :
# Mode PDF  : User => Upload PDF => extraction texte => extraction infos => sauvegarde BD => chatbot LLM => Réponse
# Mode Excel: User => Upload Excel => lecture pandas => sauvegarde BD => RAG (détection client + recherche BD) => LLM => Réponse

import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.pdf_reader import extraire_texte
from src.llm import poser_question, poser_question_excel
from src.extractor import extraire_infos_facture
from src.database import init_db, enregistrer_facture, importer_excel_en_db, get_resume_excel
from src.excel_reader import lire_excel

# Initialiser la base de données
init_db()

# ─────────────────────────────────────────────────────────
#  SESSION STATE — PDF (existant, inchangé)
# ─────────────────────────────────────────────────────────
if "texte_facture" not in st.session_state:
    st.session_state.texte_facture = None
if "facture_sauvegardee" not in st.session_state:
    st.session_state.facture_sauvegardee = False
if "message_sauvegarde" not in st.session_state:
    st.session_state.message_sauvegarde = ""
if "fichier_nom" not in st.session_state:
    st.session_state.fichier_nom = None
if "historique" not in st.session_state:
    st.session_state.historique = []
if "infos_facture" not in st.session_state:
    st.session_state.infos_facture = None

# ─────────────────────────────────────────────────────────
#  SESSION STATE — Excel (nouveau)
# ─────────────────────────────────────────────────────────
if "historique_excel" not in st.session_state:
    st.session_state.historique_excel = []

# ✅ FIX : mémoriser quel fichier a déjà été importé + son résultat
if "excel_importe_nom" not in st.session_state:
    st.session_state.excel_importe_nom = None
if "excel_resultat_import" not in st.session_state:
    st.session_state.excel_resultat_import = None

# ─────────────────────────────────────────────────────────
#  TITRE + ONGLETS
# ─────────────────────────────────────────────────────────
st.title("🤖 Assistant SRM — Gestion Intelligente des Factures")

onglet_pdf, onglet_excel = st.tabs(["📄 Analyse de facture PDF", "📊 Base clients Excel"])

# ═════════════════════════════════════════════════════════
#  ONGLET 1 — PDF (code existant, inchangé)
# ═════════════════════════════════════════════════════════
with onglet_pdf:

    st.write("Uploadez votre facture PDF et posez vos questions.")
    fichier = st.file_uploader("Choisir une facture PDF", type="pdf")

    if fichier:
        if fichier.name != st.session_state.fichier_nom:
            st.session_state.fichier_nom = fichier.name
            st.session_state.facture_sauvegardee = False
            st.session_state.historique = []
            st.session_state.infos_facture = None

            with open("facture_temp.pdf", "wb") as f:
                f.write(fichier.read())

            st.session_state.texte_facture = extraire_texte("facture_temp.pdf")

            with st.spinner("📊 Extraction et sauvegarde des données..."):
                infos = extraire_infos_facture(st.session_state.texte_facture)
                if infos:
                    st.session_state.infos_facture = infos
                    saved = enregistrer_facture(infos)
                    if saved:
                        st.session_state.message_sauvegarde = f"💾 Nouvelle facture sauvegardée — Client : {infos.get('nom_client', 'Inconnu')} | Montant : {infos.get('montant_total_ttc')} Dhs"
                    else:
                        st.session_state.message_sauvegarde = "⚠️ Cette facture est déjà enregistrée dans la base de données."
                    st.session_state.facture_sauvegardee = True

        st.success("✅ Facture chargée avec succès !")

        if st.session_state.message_sauvegarde:
            if "Nouvelle" in st.session_state.message_sauvegarde:
                st.info(st.session_state.message_sauvegarde)
            else:
                st.warning(st.session_state.message_sauvegarde)

        if st.session_state.infos_facture:
            infos = st.session_state.infos_facture
            st.markdown("---")
            st.markdown("### 📋 Résumé de votre facture")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👤 Client", infos.get("nom_client") or "—")
                st.metric("🔌 Service", infos.get("type_service") or "—")
            with col2:
                unite = "kWh" if infos.get("type_service") == "electricite" else "m³"
                st.metric("⚡ Consommation", f"{infos.get('consommation') or '—'} {unite}")
                st.metric("📅 Période", f"{infos.get('periode_debut')} → {infos.get('periode_fin')}")
            with col3:
                st.metric("💰 Montant TTC", f"{infos.get('montant_total_ttc')} Dhs")
                st.metric("⏰ Date limite", infos.get("date_limite_paiement") or "—")

        st.markdown("---")
        st.markdown("### 💬 Posez vos questions sur la facture")

        for msg in st.session_state.historique:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        question = st.chat_input("Votre question sur la facture...")

        if question and st.session_state.texte_facture:
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


# ═════════════════════════════════════════════════════════
#  ONGLET 2 — Excel (nouveau)
# ═════════════════════════════════════════════════════════
with onglet_excel:

    # --- Résumé de ce qui est déjà en BD ---
    resume = get_resume_excel()

    if resume["total"] > 0:
        st.success(f"✅ Base active — {resume['total']} factures | {len(resume['clients'])} clients | {len(resume['periodes'])} périodes")

        col1, col2 = st.columns(2)
        with col1:
            with st.expander("👥 Clients disponibles"):
                for client in resume["clients"]:
                    st.write(f"• {client}")
        with col2:
            with st.expander("📅 Périodes couvertes"):
                for periode in resume["periodes"]:
                    st.write(f"• {periode}")
    else:
        st.info("ℹ️ Aucune donnée en base. Importez un fichier Excel pour commencer.")

    # --- Zone import Excel ---
    st.markdown("### 📥 Importer un fichier Excel")
    fichier_excel = st.file_uploader("Choisir un fichier Excel (.xlsx)", type=["xlsx"])

    if fichier_excel:
        # ✅ FIX PRINCIPAL : n'importer que si c'est un nouveau fichier
        # Streamlit re-exécute tout le script à chaque interaction (rerun),
        # ce qui causait un double import à chaque fois.
        if fichier_excel.name != st.session_state.excel_importe_nom:

            chemin_temp = "excel_temp.xlsx"
            with open(chemin_temp, "wb") as f:
                f.write(fichier_excel.read())

            try:
                with st.spinner("📊 Lecture et import en base de données..."):
                    lignes = lire_excel(chemin_temp)
                    resultat = importer_excel_en_db(lignes)

                # Mémoriser le nom du fichier ET le résultat pour l'afficher après rerun
                st.session_state.excel_importe_nom = fichier_excel.name
                st.session_state.excel_resultat_import = resultat

                st.rerun()

            except ValueError as e:
                st.error(f"❌ Erreur de format : {e}")

        # ✅ Afficher le résultat mémorisé (après rerun, le fichier est déjà importé)
        if st.session_state.excel_resultat_import:
            resultat = st.session_state.excel_resultat_import
            if resultat["nouvelles"] > 0 and resultat["doublons"] == 0:
                st.success(f"✅ Import terminé — {resultat['nouvelles']} nouvelles factures ajoutées.")
            elif resultat["nouvelles"] > 0 and resultat["doublons"] > 0:
                st.success(f"✅ Import terminé — {resultat['nouvelles']} nouvelles factures ajoutées, {resultat['doublons']} doublons ignorés.")
            else:
                st.info(f"ℹ️ Ce fichier est déjà en base ({resultat['doublons']} enregistrements existants). Vous pouvez interroger les données ci-dessous.")

    # --- Chatbot RAG multi-clients ---
    st.markdown("---")
    st.markdown("### 💬 Interrogez la base clients")

    if resume["total"] == 0:
        st.warning("⚠️ Importez d'abord un fichier Excel pour utiliser le chatbot.")
    else:
        st.caption("Exemples : 'Quel est le montant de Fatima ?' | 'Quels clients ont des alertes ?' | 'Liste tous les clients'")

        for msg in st.session_state.historique_excel:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        question_excel = st.chat_input("Votre question sur la base clients...")

        if question_excel:
            st.session_state.historique_excel.append({"role": "user", "content": question_excel})
            st.chat_message("user").write(question_excel)

            with st.spinner("⏳ Recherche en cours..."):
                reponse = poser_question_excel(
                    question_excel,
                    st.session_state.historique_excel
                )

            st.session_state.historique_excel.append({"role": "assistant", "content": reponse})
            st.chat_message("assistant").write(reponse)