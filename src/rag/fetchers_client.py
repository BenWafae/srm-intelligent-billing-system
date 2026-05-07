# src/rag/fetchers_client.py
import sqlite3
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from normalisation import normaliser_mois

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "srm.db")


def _connexion():
    return sqlite3.connect(DB_PATH)


def _filtre_fichier(nom_fichier: str) -> tuple[str, list]:
    """
    Retourne la clause SQL et les paramètres associés au filtre nom_fichier.
    Si nom_fichier est vide → pas de filtre (comportement original).
    Usage : clause, params = _filtre_fichier(nom_fichier)
            WHERE nom_client LIKE ? {clause}
            params = [f"%{nom_client}%"] + params
    """
    if nom_fichier:
        return "AND nom_fichier = ?", [nom_fichier]
    return "", []


# ════════════════════════════════════════════════════════════


def fetch_client_max_consommation(nom_client: str, limit: int = 1, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY consommation DESC
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."

    if limit == 1:
        max_val = rows[0][1]
        tops = [r for r in rows if r[1] == max_val]
        lignes = [f"📈 Consommation maximale de **{nom_client}** :\n"]
        for r in tops:
            lignes.append(f"🏆 **{r[0]}** : {r[1]:,} {r[2]}  ← MAXIMUM")
        return "\n".join(lignes)

    # limit > 1 → top N mois
    top_rows = rows[:limit]
    lignes = [f"📈 Top {limit} mois — **{nom_client}** :\n"]
    for i, r in enumerate(top_rows, 1):
        marker = "🏆" if i == 1 else f"  {i}."
        lignes.append(f"{marker} **{r[0]}** : {r[1]:,} {r[2]}")
    return "\n".join(lignes)


def fetch_client_min_consommation(nom_client: str, limit: int = 1, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY consommation ASC
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."

    if limit == 1:
        min_val = rows[0][1]
        mins = [r for r in rows if r[1] == min_val]
        lignes = [f"📉 Consommation minimale de **{nom_client}** :\n"]
        for r in mins:
            lignes.append(f"🔻 **{r[0]}** : {r[1]:,} {r[2]}  ← MINIMUM")
        return "\n".join(lignes)

    # limit > 1 → top N mois
    top_rows = rows[:limit]
    lignes = [f"📉 Top {limit} mois les moins consommés — **{nom_client}** :\n"]
    for i, r in enumerate(top_rows, 1):
        marker = "🔻" if i == 1 else f"  {i}."
        lignes.append(f"{marker} **{r[0]}** : {r[1]:,} {r[2]}")
    return "\n".join(lignes)


def fetch_client_max_montant(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY montant_ttc DESC
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    max_val = rows[0][1]
    tops = [r for r in rows if r[1] == max_val]
    lignes = [f"💰 Montant maximum de **{nom_client}** :\n"]
    for r in tops:
        lignes.append(f"🏆 **{r[0]}** : {r[1]:,.2f} Dhs  ← MAXIMUM")
    return "\n".join(lignes)


def fetch_client_min_montant(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY montant_ttc ASC
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    min_val = rows[0][1]
    mins = [r for r in rows if r[1] == min_val]
    lignes = [f"💸 Montant minimum de **{nom_client}** :\n"]
    for r in mins:
        lignes.append(f"🔻 **{r[0]}** : {r[1]:,.2f} Dhs  ← MINIMUM")
    return "\n".join(lignes)


def fetch_client_evolution(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    lignes = [f"📈 Évolution chronologique de **{nom_client}** :\n"]
    for r in rows:
        lignes.append(
            f"  - **{r[0]}** : Consommation {r[1]:,} {r[2]} | Montant {r[3]:,.2f} Dhs"
        )
    return "\n".join(lignes)


def fetch_client_moyenne(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            ROUND(AVG(consommation), 2) as moy_conso,
            unite,
            ROUND(AVG(montant_ttc), 2) as moy_montant,
            ROUND(MIN(consommation), 2) as min_conso,
            ROUND(MAX(consommation), 2) as max_conso,
            ROUND(MIN(montant_ttc), 2) as min_montant,
            ROUND(MAX(montant_ttc), 2) as max_montant,
            COUNT(*) as nb_mois
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
    """, [f"%{nom_client}%"] + fparams)
    r = cursor.fetchone()
    conn.close()
    if not r or r[0] is None:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    return f"""📊 Statistiques de **{nom_client}** sur {r[7]} mois :

- Consommation moyenne : **{r[0]:,} {r[1]}**
- Consommation minimum : {r[3]:,} {r[1]}
- Consommation maximum : {r[4]:,} {r[1]}
- Montant moyen        : **{r[2]:,.2f} Dhs**
- Montant minimum      : {r[5]:,.2f} Dhs
- Montant maximum      : {r[6]:,.2f} Dhs"""


def fetch_client_infos(nom_client: str, champ: str = None, nom_fichier: str = "") -> str:
    """
    Si champ est précisé → réponse ciblée (usage, adresse, agence, service, contrat, compteur)
    Si champ est None    → fiche complète
    Note : le filtre nom_fichier ne change pas les infos statiques du client
    (agence, adresse...) mais garantit la cohérence si un client apparaît
    dans plusieurs fichiers avec des données différentes.
    """
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT nom_client, numero_client, numero_contrat, numero_compteur,
               adresse, agence, usage, type_service
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        LIMIT 1
    """, [f"%{nom_client}%"] + fparams)
    r = cursor.fetchone()
    conn.close()
    if not r:
        return f"Aucune donnée trouvée pour « {nom_client} »."

    if champ == "usage":
        return f"Usage de **{r[0]}** : **{r[6]}**"
    if champ == "adresse":
        return f"Adresse de **{r[0]}** : **{r[4]}**"
    if champ == "agence":
        return f"Agence de **{r[0]}** : **{r[5]}**"
    if champ == "service":
        return f"Type de service de **{r[0]}** : **{r[7]}**"
    if champ == "contrat":
        return f"N° Contrat de **{r[0]}** : **{r[2]}**"
    if champ == "compteur":
        return f"N° Compteur de **{r[0]}** : **{r[3]}**"
    if champ == "numero_client":
        return f"N° Client de **{r[0]}** : **{r[1]}**"

    return f"""📋 Informations du client **{r[0]}** :

- N° Client    : {r[1]}
- N° Contrat   : {r[2]}
- N° Compteur  : {r[3]}
- Adresse      : {r[4]}
- Agence       : {r[5]}
- Usage        : {r[6]}
- Type service : {r[7]}"""


def fetch_client_mois_specifique(nom_client: str, mois: str, champ: str = None, nom_fichier: str = "") -> str:
    mois_normalise = normaliser_mois(mois)
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, periode_debut, periode_fin,
               consommation, unite, montant_ttc, date_limite_paiement
        FROM factures_excel
        WHERE nom_client LIKE ? AND mois_source LIKE ? {clause}
    """, [f"%{nom_client}%", f"%{mois_normalise}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune facture trouvée pour **{nom_client}** en {mois_normalise}."
    r = rows[0]

    if champ == "consommation":
        return (
            f"⚡💧 Consommation de **{nom_client}** en **{r[0]}** :\n"
            f"→ **{r[3]:,} {r[4]}**"
        )
    if champ == "montant":
        return (
            f"💰 Montant de **{nom_client}** en **{r[0]}** :\n"
            f"→ **{r[5]:,.2f} Dhs**"
        )
    if champ == "date_limite":
        return (
            f"📅 Date limite de paiement — **{nom_client}** ({r[0]}) :\n"
            f"→ **{r[6]}**"
        )

    return f"""🧾 Facture de **{nom_client}** — {r[0]} :

- Période            : {r[1]} → {r[2]}
- Consommation       : **{r[3]:,} {r[4]}**
- Montant TTC        : **{r[5]:,.2f} Dhs**
- Date limite pmt    : {r[6]}"""


def fetch_client_somme_conso(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            ROUND(SUM(consommation), 2) as total_conso,
            unite,
            ROUND(SUM(montant_ttc), 2) as total_ttc,
            COUNT(*) as nb_mois
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
    """, [f"%{nom_client}%"] + fparams)
    r = cursor.fetchone()
    conn.close()
    if not r or r[0] is None:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    return (
        f"Consommation totale de **{nom_client}** sur {r[3]} mois :\n\n"
        f"- Consommation totale  : **{r[0]:,} {r[1]}**\n"
        f"- Montant total cumulé : **{r[2]:,.2f} Dhs**"
    )


def fetch_client_toutes_factures(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, periode_debut, periode_fin,
               consommation, unite, montant_ttc, date_limite_paiement
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, [f"%{nom_client}%"] + fparams)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour « {nom_client} »."
    lignes = [f"🧾 Toutes les factures de **{nom_client}** ({len(rows)} mois) :\n"]
    total = 0
    for r in rows:
        lignes.append(
            f"  - **{r[0]}** | {r[1]}→{r[2]} | "
            f"Conso : {r[3]:,} {r[4]} | Montant : {r[5]:,.2f} Dhs | "
            f"Limite pmt : {r[6]}"
        )
        total += r[5]
    lignes.append(f"\n💰 **Total cumulé : {round(total, 2):,.2f} Dhs**")
    return "\n".join(lignes)


def fetch_client_somme_montant(nom_client: str, nom_fichier: str = "") -> str:
    clause, fparams = _filtre_fichier(nom_fichier)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            ROUND(SUM(montant_ttc), 2) as total,
            COUNT(*) as nb_mois,
            ROUND(AVG(montant_ttc), 2) as moyenne,
            ROUND(MIN(montant_ttc), 2) as minimum,
            ROUND(MAX(montant_ttc), 2) as maximum
        FROM factures_excel
        WHERE nom_client LIKE ? {clause}
    """, [f"%{nom_client}%"] + fparams)
    r = cursor.fetchone()
    conn.close()
    if not r or r[0] is None:
        return f"Aucune donnée trouvée pour {nom_client}."
    return (
        f"💰 **Total montants — {nom_client}** :\n\n"
        f"- Montant total cumulé : **{r[0]:,.2f} Dhs**\n"
        f"- Nombre de mois      : {r[1]}\n"
        f"- Montant moyen       : {r[2]:,.2f} Dhs\n"
        f"- Montant minimum     : {r[3]:,.2f} Dhs\n"
        f"- Montant maximum     : {r[4]:,.2f} Dhs"
    )