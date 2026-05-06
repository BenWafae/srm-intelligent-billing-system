import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.database import (
    init_db, importer_excel_en_db, get_resume_excel,
    reset_base_excel, supprimer_factures_client,
    enregistrer_facture, get_clients_avec_pdf,
    creer_user, verifier_doublons
)
from src.excel_reader import lire_excel
from src.pdf_reader import extraire_texte
from src.extractor import extraire_infos_facture
from src.database import get_contrats_disponibles
from src.database import  get_all_users, supprimer_user


def afficher_admin():

    # SIDEBAR
    with st.sidebar:
        st.title("⚙️ SRM Admin")
        st.markdown("---")
        st.markdown(f"👤 Connecté : **{st.session_state.user['email']}**")
        st.markdown(f"🔑 Rôle : **Administrateur**")
        st.markdown("---")
        if st.button("🚪 Se déconnecter"):
            del st.session_state.user
            st.rerun()

    st.title("⚙️ Interface Administrateur SRM")

    onglet_excel, onglet_pdf, onglet_users = st.tabs([
        "📊 Import Excel",
        "📄 Import PDF",
        "👥 Gestion Utilisateurs"
    ])

# ════════════════════════════════════════════
    # ONGLET 1 — IMPORT EXCEL
    # ════════════════════════════════════════════
    with onglet_excel:
        st.markdown("### 📥 Importer un fichier Excel")

        resume = get_resume_excel()
        if resume["total"] > 0:
            st.success(f"✅ Base active — {resume['total']} factures | {len(resume['clients'])} clients | {len(resume['periodes'])} périodes")
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("👥 Clients dans la base"):
                    for client in resume["clients"]:
                        st.write(f"• {client}")
            with col2:
                with st.expander("📅 Périodes couvertes"):
                    for periode in resume["periodes"]:
                        st.write(f"• {periode}")
        else:
            st.info("ℹ️ Base vide — importez un fichier Excel.")

        st.markdown("---")

        fichier_excel = st.file_uploader(
            "Choisir un fichier Excel (.xlsx)",
            type=["xlsx"],
            key="upload_excel_admin"
        )

        if fichier_excel:
            nom_fichier = fichier_excel.name
            chemin_temp = "excel_temp.xlsx"
            with open(chemin_temp, "wb") as f:
                f.write(fichier_excel.read())

            try:
                lignes = lire_excel(chemin_temp)
                apercu = verifier_doublons(lignes)

                if apercu["existantes"] == apercu["total"]:
                    st.warning("⚠️ Ce fichier est déjà entièrement en base. Aucun import effectué.")

                elif apercu["existantes"] > 0:
                    st.info(
                        f"📋 {apercu['nouvelles']} nouvelles lignes | "
                        f"{apercu['existantes']} déjà en base (ignorées)"
                    )
                    if st.button("✅ Importer les nouvelles lignes", key="btn_import_excel"):
                        with st.spinner("Import en cours..."):
                            resultat = importer_excel_en_db(lignes, mode="skip", nom_fichier=nom_fichier)
                        st.success(f"✅ {resultat['nouvelles']} factures ajoutées.")
                        st.rerun()

                else:
                    st.info(f"📋 {apercu['total']} nouvelles lignes à importer.")
                    if st.button("✅ Confirmer l'import", key="btn_import_excel"):
                        with st.spinner("Import en cours..."):
                            resultat = importer_excel_en_db(lignes, mode="skip", nom_fichier=nom_fichier)
                        st.success(f"✅ {resultat['nouvelles']} factures ajoutées.")
                        st.rerun()

            except Exception as e:
                st.error(f"❌ Erreur : {e}")

        st.markdown("---")
        st.markdown("### 🗑️ Gestion de la base")

        col1, col2 = st.columns(2)
        with col1:
            client_suppr = st.selectbox(
                "Supprimer un client",
                options=[""] + resume["clients"],
                key="client_suppr"
            )
            if st.button("🗑️ Supprimer ce client", key="btn_suppr_client"):
                if client_suppr:
                    n = supprimer_factures_client(client_suppr)
                    st.success(f"✅ {n} factures supprimées pour {client_suppr}")
                    st.rerun()

        with col2:
            st.warning("⚠️ Supprimer toute la base Excel")
            if st.button("🔴 Reset complet", key="btn_reset"):
                n = reset_base_excel()
                st.success(f"✅ {n} factures supprimées")
                st.rerun()
    # ════════════════════════════════════════════
    # ONGLET 2 — IMPORT PDF
    # ════════════════════════════════════════════
    with onglet_pdf:
        st.markdown("### 📥 Importer des factures PDF")

        clients_pdf = get_clients_avec_pdf()
        if clients_pdf:
            st.success(f"✅ {len(clients_pdf)} clients avec PDF importé")
            with st.expander("📄 Clients avec PDF"):
                for c in clients_pdf:
                    st.write(f"• {c}")
        else:
            st.info("ℹ️ Aucun PDF importé pour le moment.")

        st.markdown("---")

        fichiers_pdf = st.file_uploader(
            "Choisir un ou plusieurs PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="upload_pdf_admin"
        )

        if fichiers_pdf:
            if st.button("✅ Importer les PDFs", key="btn_import_pdf"):
                progress = st.progress(0)
                total = len(fichiers_pdf)
                succes, doublons, erreurs = 0, 0, 0

                for i, fichier in enumerate(fichiers_pdf):
                    chemin_temp = f"pdf_temp_{i}.pdf"
                    with open(chemin_temp, "wb") as f:
                        f.write(fichier.read())

                    try:
                        texte = extraire_texte(chemin_temp)
                        infos = extraire_infos_facture(texte)

                        if infos:
                            infos["texte_extrait"] = texte
                            saved = enregistrer_facture(infos)
                            if saved:
                                succes += 1
                            else:
                                doublons += 1
                        else:
                            erreurs += 1
                    except Exception as e:
                        erreurs += 1

                    progress.progress((i + 1) / total)
                    os.remove(chemin_temp)

                st.success(
                    f"✅ Import terminé — "
                    f"{succes} ajoutés | "
                    f"{doublons} doublons | "
                    f"{erreurs} erreurs"
                )
                st.rerun()

    # ════════════════════════════════════════════
    # ONGLET 3 — GESTION UTILISATEURS
    # ════════════════════════════════════════════
    with onglet_users:
        st.markdown("### 👥 Créer un compte utilisateur")

        role_nouveau = st.selectbox(
            "Rôle",
            ["employe", "client"],
            key="role_nouveau"
        )

        email_nouveau = st.text_input("Email", key="email_nouveau")
        password_nouveau = st.text_input("Mot de passe", type="password", key="password_nouveau")

        numero_contrat_nouveau = None
        if role_nouveau == "client":
            contrats = get_contrats_disponibles()
            with st.expander("📋 Contrats disponibles"):
                for c in contrats:
                    st.write(f"• {c['nom_client']} → {c['numero_contrat']}")

            numero_contrat_nouveau = st.text_input(
                "Numéro de contrat du client",
                key="numero_contrat_nouveau",
                placeholder="ex: 0005567200/2063200"
            )

        if st.button("✅ Créer le compte", key="btn_creer_user"):
            if email_nouveau and password_nouveau:
                if role_nouveau == "client" and not numero_contrat_nouveau:
                    st.warning("⚠️ Le numéro de contrat est obligatoire pour un client.")
                else:
                    ok = creer_user(
                        email=email_nouveau,
                        password=password_nouveau,
                        role=role_nouveau,
                        numero_client=numero_contrat_nouveau or None
                    )
                    if ok:
                        st.success(f"✅ Compte **{email_nouveau}** créé — rôle : **{role_nouveau}**")
                    else:
                        st.error("❌ Cet email existe déjà.")
            else:
                st.warning("⚠️ Remplissez email et mot de passe.")

        st.markdown("---")
        st.markdown("### 📋 Utilisateurs existants")

        col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
        with col1:
            st.markdown("**Email**")
        with col2:
            st.markdown("**Rôle**")
        with col3:
            st.markdown("**N° Contrat**")
        with col4:
            st.markdown("**Action**")

        st.markdown("---")

        users = get_all_users()
        if not users:
            st.info("Aucun utilisateur créé.")
        else:
            for u in users:
                col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
                with col1:
                    st.write(f"📧 {u['email']}")
                with col2:
                    role_emoji = "⚙️" if u['role'] == "admin" else "👔" if u['role'] == "employe" else "👤"
                    st.write(f"{role_emoji} {u['role']}")
                with col3:
                    st.write(f"📄 {u['numero_client'] or '—'}")
                with col4:
                    if st.button("🗑️", key=f"del_user_{u['id']}"):
                        supprimer_user(u['id'])
                        st.rerun()