import requests
import sqlite3
import os
import re
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")

# ─────────────────────────────────────────────────────────
# PARTIE 1 — DÉTECTION D'INTENT GÉNÉRAL
# ─────────────────────────────────────────────────────────

INTENTS_DISPONIBLES = """
LISTE_CLIENTS        : liste des clients, qui existe, combien de clients, tous les clients
TOP_CONSOMMATEURS    : qui consomme le plus, consommation la plus élevée, classement consommation
TOP_MONTANTS         : qui paie le plus, montant le plus élevé, facture la plus chère, classement montant
CLASSEMENT_PAR_MOIS  : classer clients par montant ou consommation pour chaque mois, voir classement mois par mois
PAR_AGENCE           : clients d'une agence, quelle agence, combien par agence
PAR_USAGE            : usage domestique, force motrice, commercial, administratif, type d'usage, quels usages existent
PAR_SERVICE          : eau, électricité, type de service, combien utilisent eau vs electricite, lister clients eau ou electricite
ALERTES              : alertes, qui a des alertes, factures avec alerte
STATS_GENERALES      : total, moyenne, somme, montant global, statistiques générales
EVOLUTION_MOIS       : évolution, progression, mois par mois, historique général, tendance
QUESTION_LIBRE       : toute autre question qui ne rentre pas dans les catégories ci-dessus
"""

# ─────────────────────────────────────────────────────────
# PARTIE 1b — DÉTECTION D'INTENT ANALYTIQUE CLIENT
# ─────────────────────────────────────────────────────────

INTENTS_CLIENT = """
MAX_CONSOMMATION  : mois où le client a le plus consommé, consommation maximale, pic de consommation
MIN_CONSOMMATION  : mois où le client a le moins consommé, consommation minimale
MAX_MONTANT       : mois où le client a payé le plus, montant maximum, facture la plus chère
MIN_MONTANT       : mois où le client a payé le moins, montant minimum, facture la moins chère
EVOLUTION_CLIENT  : évolution, progression, tendance, historique du client
MOYENNE_CLIENT    : moyenne, consommation moyenne, montant moyen du client
INFOS_CLIENT      : adresse, numéro client, contrat, compteur, agence, infos générales
MOIS_SPECIFIQUE   : consommation ou montant d'un mois précis, que s'est-il passé en tel mois, facture de tel mois
FACTURES_CLIENT   : toutes les factures, liste des factures, historique complet
"""


def _connexion():
    return sqlite3.connect(DB_PATH)


def detecter_intent(question: str) -> dict:
    """Détecte l'intent pour les questions générales"""

    prompt = f"""Tu es un classificateur de questions. Tu dois identifier l'intent de la question posée.

Voici les intents disponibles :
{INTENTS_DISPONIBLES}

Question : {question}

Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre, sans explication, sans markdown.
Format exact :
{{"intent": "NOM_INTENT", "params": {{}}}}

Si la question mentionne un mois précis, ajoute : {{"mois": "Octobre 2025"}}
Si la question mentionne une agence précise, ajoute : {{"agence": "Agadir Nord"}}
Si la question mentionne un usage précis, ajoute : {{"usage": "USAGE DOMESTIQUE"}}
Si la question mentionne un service précis (eau ou electricite), ajoute : {{"service": "eau"}} ou {{"service": "electricite"}}

JSON :"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    texte = response.json()["response"].strip()
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {"intent": "QUESTION_LIBRE", "params": {}}


def detecter_intent_client(question: str) -> dict:
    """Détecte l'intent analytique pour une question sur un client spécifique"""

    prompt = f"""Tu es un classificateur de questions sur un client.

Voici les intents disponibles :
{INTENTS_CLIENT}

Question : {question}

Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre, sans explication, sans markdown.
Format exact :
{{"intent": "NOM_INTENT", "params": {{}}}}

Si la question mentionne un mois précis (ex: Mars, Octobre 2025, Janvier 2026), ajoute : {{"mois": "Mars"}}

JSON :"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    texte = response.json()["response"].strip()
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intents_valides = [
                "MAX_CONSOMMATION", "MIN_CONSOMMATION",
                "MAX_MONTANT", "MIN_MONTANT",
                "EVOLUTION_CLIENT", "MOYENNE_CLIENT",
                "INFOS_CLIENT", "MOIS_SPECIFIQUE", "FACTURES_CLIENT"
            ]
            if result.get("intent") in intents_valides:
                return result
        except:
            pass
    return {"intent": "FACTURES_CLIENT", "params": {}}


# ─────────────────────────────────────────────────────────
# PARTIE 2 — FETCHERS GÉNÉRAUX (SQL fixe)
# ─────────────────────────────────────────────────────────

def fetch_liste_clients() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, usage, type_service,
               COUNT(*) as nb_mois,
               ROUND(SUM(montant_ttc), 2) as total_ttc
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY nom_client
    """)
    rows = cursor.fetchall()
    conn.close()
    lignes = [f"Nombre total de clients : {len(rows)}\n\nListe des clients :"]
    for r in rows:
        lignes.append(
            f"  - {r[0]} | Agence: {r[1]} | Usage: {r[2]} | "
            f"Service: {r[3]} | {r[4]} mois | Total cumulé: {r[5]} Dhs"
        )
    return "\n".join(lignes)


def fetch_top_consommateurs(mois: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if mois:
        cursor.execute("""
            SELECT nom_client, consommation, unite, mois_source
            FROM factures_excel
            WHERE mois_source LIKE ?
            ORDER BY consommation DESC
        """, (f"%{mois}%",))
        titre = f"Classement consommation — {mois} :"
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total_conso DESC
        """)
        titre = "Classement consommation totale (tous mois) :"
    rows = cursor.fetchall()
    conn.close()
    lignes = [titre]
    for i, r in enumerate(rows, 1):
        lignes.append(f"  {i}. {r[0]} — {r[1]} {r[2]}")
    return "\n".join(lignes)


def fetch_top_montants(mois: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if mois:
        cursor.execute("""
            SELECT nom_client, montant_ttc, mois_source
            FROM factures_excel
            WHERE mois_source LIKE ?
            ORDER BY montant_ttc DESC
        """, (f"%{mois}%",))
        titre = f"Classement montants — {mois} :"
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total DESC
        """)
        titre = "Classement montants totaux (tous mois) :"
    rows = cursor.fetchall()
    conn.close()
    lignes = [titre]
    for i, r in enumerate(rows, 1):
        lignes.append(f"  {i}. {r[0]} — {r[1]} Dhs")
    return "\n".join(lignes)


def fetch_classement_par_mois() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, nom_client, montant_ttc, consommation, unite
        FROM factures_excel
        ORDER BY
            SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2),
            montant_ttc DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    mois_dict = {}
    for r in rows:
        mois = r[0]
        if mois not in mois_dict:
            mois_dict[mois] = []
        mois_dict[mois].append(r)
    lignes = ["Classement des clients par montant pour chaque mois :"]
    for mois, clients in mois_dict.items():
        lignes.append(f"\n  📅 {mois} :")
        for i, r in enumerate(clients, 1):
            lignes.append(f"    {i}. {r[1]} — {r[2]} Dhs | Conso: {r[3]} {r[4]}")
    return "\n".join(lignes)


def fetch_par_agence(agence: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if agence:
        cursor.execute("""
            SELECT nom_client, usage, type_service,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            WHERE agence LIKE ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (f"%{agence}%",))
        rows = cursor.fetchall()
        conn.close()
        lignes = [f"Clients de l'agence '{agence}' ({len(rows)} clients) :"]
        for r in rows:
            lignes.append(
                f"  - {r[0]} | Usage: {r[1]} | Service: {r[2]} | "
                f"{r[3]} mois | Total: {r[4]} Dhs"
            )
    else:
        cursor.execute("""
            SELECT agence, COUNT(DISTINCT nom_client) as nb_clients,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY agence
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        lignes = ["Répartition par agence :"]
        for r in rows:
            lignes.append(f"  - {r[0]} : {r[1]} clients | Total: {r[2]} Dhs")
    return "\n".join(lignes)


def fetch_par_usage(usage: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if usage:
        cursor.execute("""
            SELECT nom_client, agence, type_service,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            WHERE usage LIKE ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (f"%{usage}%",))
        rows = cursor.fetchall()
        conn.close()
        lignes = [f"Clients avec usage '{usage}' ({len(rows)} clients) :"]
        for r in rows:
            lignes.append(
                f"  - {r[0]} | Agence: {r[1]} | Service: {r[2]} | "
                f"{r[3]} mois | Total: {r[4]} Dhs"
            )
    else:
        cursor.execute("""
            SELECT usage, COUNT(DISTINCT nom_client) as nb_clients,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY usage
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        lignes = ["Répartition par usage :"]
        for r in rows:
            lignes.append(f"  - {r[0]} : {r[1]} clients | Total: {r[2]} Dhs")
    return "\n".join(lignes)


def fetch_par_service(service: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if service:
        cursor.execute("""
            SELECT nom_client, agence, usage,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(consommation), 2) as total_conso,
                   unite,
                   ROUND(SUM(montant_ttc), 2) as total_ttc
            FROM factures_excel
            WHERE type_service LIKE ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (f"%{service}%",))
        rows = cursor.fetchall()
        conn.close()
        lignes = [f"Clients utilisant le service '{service}' ({len(rows)} clients) :"]
        for r in rows:
            lignes.append(
                f"  - {r[0]} | Agence: {r[1]} | Usage: {r[2]} | "
                f"Conso totale: {r[4]} {r[5]} | Montant: {r[6]} Dhs"
            )
        lignes.append(f"\nNombre exact : {len(rows)} clients utilisent {service}")
    else:
        cursor.execute("""
            SELECT type_service,
                   COUNT(DISTINCT nom_client) as nb_clients,
                   ROUND(SUM(consommation), 2) as total_conso,
                   ROUND(SUM(montant_ttc), 2) as total_ttc
            FROM factures_excel
            GROUP BY type_service
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        lignes = ["Répartition exacte par type de service :"]
        for r in rows:
            lignes.append(
                f"  - {r[0]} : {r[1]} clients | "
                f"Conso totale: {r[2]} | Montant total: {r[3]} Dhs"
            )
        lignes.append("\nATTENTION : Chaque client utilise UN SEUL service. Ne pas mélanger les catégories.")
    return "\n".join(lignes)


def fetch_alertes() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, mois_source, montant_ttc, alerte
        FROM factures_excel
        WHERE alerte IS NOT NULL AND alerte != '' AND alerte != 'None'
        ORDER BY nom_client, mois_source
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune alerte trouvée dans la base."
    lignes = [f"Factures avec alertes — {len(rows)} trouvées :"]
    for r in rows:
        lignes.append(
            f"  - {r[0]} | {r[1]} | {r[2]} | {r[3]} Dhs | Alerte: {r[4]}"
        )
    return "\n".join(lignes)


def fetch_stats_generales() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(DISTINCT nom_client) as nb_clients,
            COUNT(DISTINCT mois_source) as nb_mois,
            COUNT(*) as nb_factures,
            ROUND(SUM(montant_ttc), 2) as total_ttc,
            ROUND(AVG(montant_ttc), 2) as moyenne_ttc,
            ROUND(MAX(montant_ttc), 2) as max_ttc,
            ROUND(MIN(montant_ttc), 2) as min_ttc
        FROM factures_excel
    """)
    r = cursor.fetchone()
    cursor.execute("""
        SELECT nom_client, ROUND(SUM(montant_ttc), 2) as total
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY total DESC
        LIMIT 1
    """)
    top = cursor.fetchone()
    conn.close()
    return f"""Statistiques générales de la base :
  - Nombre de clients       : {r[0]}
  - Nombre de mois couverts : {r[1]}
  - Nombre de factures      : {r[2]}
  - Montant total TTC       : {r[3]} Dhs
  - Montant moyen / facture : {r[4]} Dhs
  - Montant maximum         : {r[5]} Dhs
  - Montant minimum         : {r[6]} Dhs
  - Client qui paie le plus : {top[0]} ({top[1]} Dhs cumulés)"""


def fetch_evolution_mois() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source,
               COUNT(DISTINCT nom_client) as nb_clients,
               ROUND(SUM(consommation), 2) as total_conso,
               ROUND(SUM(montant_ttc), 2) as total_ttc,
               ROUND(AVG(montant_ttc), 2) as moyenne_ttc
        FROM factures_excel
        GROUP BY mois_source
        ORDER BY SUBSTR(MIN(periode_debut),7,4)||SUBSTR(MIN(periode_debut),4,2)||SUBSTR(MIN(periode_debut),1,2)
    """)
    rows = cursor.fetchall()
    conn.close()
    lignes = ["Évolution mois par mois :"]
    for r in rows:
        lignes.append(
            f"  - {r[0]} : {r[1]} clients | "
            f"Conso totale: {r[2]} | "
            f"Montant total: {r[3]} Dhs | "
            f"Moyenne: {r[4]} Dhs"
        )
    return "\n".join(lignes)


def fetch_question_libre() -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, usage, type_service,
               COUNT(*) as nb_mois,
               ROUND(SUM(consommation), 2) as total_conso,
               unite,
               ROUND(SUM(montant_ttc), 2) as total_ttc,
               ROUND(AVG(montant_ttc), 2) as moy_ttc
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY nom_client
    """)
    clients = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(DISTINCT mois_source), ROUND(SUM(montant_ttc), 2)
        FROM factures_excel
    """)
    globales = cursor.fetchone()
    conn.close()
    lignes = [
        f"Base SRM — {len(clients)} clients | {globales[0]} mois | Total: {globales[1]} Dhs\n",
        "Résumé par client :"
    ]
    for r in clients:
        lignes.append(
            f"  - {r[0]} | {r[1]} | {r[2]} | {r[3]} | "
            f"{r[4]} mois | Conso: {r[5]} {r[6]} | "
            f"Total: {r[7]} Dhs | Moy/mois: {r[8]} Dhs"
        )
    return "\n".join(lignes)


# ─────────────────────────────────────────────────────────
# PARTIE 3 — FETCHERS ANALYTIQUES CLIENT (Python calcule)
# ─────────────────────────────────────────────────────────

def fetch_client_max_consommation(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY consommation DESC
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    max_val = rows[0][1]
    tops = [r for r in rows if r[1] == max_val]
    lignes = [f"Consommation maximale de {nom_client} :"]
    for r in tops:
        lignes.append(f"  - {r[0]} : {r[1]} {r[2]}  ← MAXIMUM")
    lignes.append(f"\nTous les mois classés par consommation décroissante :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]} {r[2]}")
    return "\n".join(lignes)


def fetch_client_min_consommation(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY consommation ASC
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    min_val = rows[0][1]
    mins = [r for r in rows if r[1] == min_val]
    lignes = [f"Consommation minimale de {nom_client} :"]
    for r in mins:
        lignes.append(f"  - {r[0]} : {r[1]} {r[2]}  ← MINIMUM")
    lignes.append(f"\nTous les mois classés par consommation croissante :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]} {r[2]}")
    return "\n".join(lignes)


def fetch_client_max_montant(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY montant_ttc DESC
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    max_val = rows[0][1]
    tops = [r for r in rows if r[1] == max_val]
    lignes = [f"Montant maximum de {nom_client} :"]
    for r in tops:
        lignes.append(f"  - {r[0]} : {r[1]} Dhs  ← MAXIMUM")
    lignes.append(f"\nTous les mois classés par montant décroissant :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]} Dhs")
    return "\n".join(lignes)


def fetch_client_min_montant(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY montant_ttc ASC
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    min_val = rows[0][1]
    mins = [r for r in rows if r[1] == min_val]
    lignes = [f"Montant minimum de {nom_client} :"]
    for r in mins:
        lignes.append(f"  - {r[0]} : {r[1]} Dhs  ← MINIMUM")
    lignes.append(f"\nTous les mois classés par montant croissant :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]} Dhs")
    return "\n".join(lignes)


def fetch_client_evolution(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    lignes = [f"Évolution chronologique de {nom_client} :"]
    for r in rows:
        lignes.append(
            f"  - {r[0]} : Consommation {r[1]} {r[2]} | Montant {r[3]} Dhs"
        )
    return "\n".join(lignes)


def fetch_client_moyenne(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
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
        WHERE nom_client LIKE ?
    """, (f"%{nom_client}%",))
    r = cursor.fetchone()
    conn.close()
    if not r or r[0] is None:
        return f"Aucune donnée trouvée pour {nom_client}."
    return f"""Statistiques de {nom_client} sur {r[7]} mois :
  - Consommation moyenne : {r[0]} {r[1]}
  - Consommation minimum : {r[3]} {r[1]}
  - Consommation maximum : {r[4]} {r[1]}
  - Montant moyen        : {r[2]} Dhs
  - Montant minimum      : {r[5]} Dhs
  - Montant maximum      : {r[6]} Dhs"""


def fetch_client_infos(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, numero_client, numero_contrat, numero_compteur,
               adresse, agence, usage, type_service
        FROM factures_excel
        WHERE nom_client LIKE ?
        LIMIT 1
    """, (f"%{nom_client}%",))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return f"Aucune donnée trouvée pour {nom_client}."
    return f"""Informations du client {r[0]} :
  - N° Client    : {r[1]}
  - N° Contrat   : {r[2]}
  - N° Compteur  : {r[3]}
  - Adresse      : {r[4]}
  - Agence       : {r[5]}
  - Usage        : {r[6]}
  - Type service : {r[7]}"""


def fetch_client_mois_specifique(nom_client: str, mois: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, periode_debut, periode_fin,
               consommation, unite, montant_ttc, date_limite_paiement
        FROM factures_excel
        WHERE nom_client LIKE ? AND mois_source LIKE ?
    """, (f"%{nom_client}%", f"%{mois}%"))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        # Essayer sans l'année si pas trouvé
        conn2 = _connexion()
        cursor2 = conn2.cursor()
        # Extraire juste le nom du mois sans année
        mois_court = mois.split()[0] if mois else mois
        cursor2.execute("""
            SELECT mois_source, periode_debut, periode_fin,
                   consommation, unite, montant_ttc, date_limite_paiement
            FROM factures_excel
            WHERE nom_client LIKE ? AND mois_source LIKE ?
        """, (f"%{nom_client}%", f"%{mois_court}%"))
        rows = cursor2.fetchall()
        conn2.close()
    if not rows:
        return f"Aucune facture trouvée pour {nom_client} en {mois}."
    r = rows[0]
    return (
        f"Facture de {nom_client} — {r[0]} :\n"
        f"  - Période            : {r[1]} → {r[2]}\n"
        f"  - Consommation       : {r[3]} {r[4]}\n"
        f"  - Montant TTC        : {r[5]} Dhs\n"
        f"  - Date limite pmt    : {r[6]}"
    )


def fetch_client_toutes_factures(nom_client: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, periode_debut, periode_fin,
               consommation, unite, montant_ttc, date_limite_paiement
        FROM factures_excel
        WHERE nom_client LIKE ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (f"%{nom_client}%",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."
    lignes = [f"Toutes les factures de {nom_client} ({len(rows)} mois) :"]
    total = 0
    for r in rows:
        lignes.append(
            f"  - {r[0]} | {r[1]}→{r[2]} | "
            f"Conso: {r[3]} {r[4]} | Montant: {r[5]} Dhs | "
            f"Limite pmt: {r[6]}"
        )
        total += r[5]
    lignes.append(f"\nTotal cumulé : {round(total, 2)} Dhs")
    return "\n".join(lignes)


# ─────────────────────────────────────────────────────────
# PARTIE 4 — GÉNÉRATION DE RÉPONSE (prompt strict)
# ─────────────────────────────────────────────────────────

def generer_reponse(question: str, contexte: str, historique_texte: str) -> str:
    prompt = f"""Tu es un assistant de la SRM Souss-Massa.

Voici les données EXACTES extraites de la base de données par Python :
{contexte}

RÈGLES ABSOLUES — tu dois les respecter strictement :
1. Utilise UNIQUEMENT les données ci-dessus — rien d'autre
2. Ne mentionne AUCUN client, chiffre ou information absent de ces données
3. Ne fais AUCUN calcul toi-même — les chiffres fournis sont déjà calculés par Python
4. Ne mélange pas les catégories — si un client est "eau", il n'est pas "electricite"
5. Si une information n'est pas dans les données, dis simplement qu'elle n'est pas disponible
6. Respecte exactement les nombres indiqués — ne les modifie pas

Historique de la conversation :
{historique_texte}

Question : {question}

Réponds de façon claire et précise en français en te basant UNIQUEMENT sur les données fournies.
"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


# ─────────────────────────────────────────────────────────
# PARTIE 5 — FONCTION PRINCIPALE GÉNÉRALE
# ─────────────────────────────────────────────────────────

def repondre_question_generale(question: str, historique_texte: str) -> str:
    """Pipeline RAG par intent pour les questions générales"""
    print(f"  [RAG] Détection intent...")
    resultat = detecter_intent(question)
    intent = resultat.get("intent", "QUESTION_LIBRE")
    params = resultat.get("params", {})
    print(f"  [RAG] Intent détecté : {intent} | Params : {params}")

    if intent == "LISTE_CLIENTS":
        contexte = fetch_liste_clients()
    elif intent == "TOP_CONSOMMATEURS":
        contexte = fetch_top_consommateurs(mois=params.get("mois"))
    elif intent == "TOP_MONTANTS":
        contexte = fetch_top_montants(mois=params.get("mois"))
    elif intent == "CLASSEMENT_PAR_MOIS":
        contexte = fetch_classement_par_mois()
    elif intent == "PAR_AGENCE":
        contexte = fetch_par_agence(agence=params.get("agence"))
    elif intent == "PAR_USAGE":
        contexte = fetch_par_usage(usage=params.get("usage"))
    elif intent == "PAR_SERVICE":
        contexte = fetch_par_service(service=params.get("service"))
    elif intent == "ALERTES":
        contexte = fetch_alertes()
    elif intent == "STATS_GENERALES":
        contexte = fetch_stats_generales()
    elif intent == "EVOLUTION_MOIS":
        contexte = fetch_evolution_mois()
    else:
        contexte = fetch_question_libre()

    print(f"  [RAG] Contexte prêt ({len(contexte)} caractères)")
    return generer_reponse(question, contexte, historique_texte)


# ─────────────────────────────────────────────────────────
# PARTIE 6 — FONCTION ANALYTIQUE CLIENT
# ─────────────────────────────────────────────────────────

def repondre_question_client(question: str, nom_client: str, historique_texte: str) -> str:
    """Pipeline RAG analytique pour les questions sur un client spécifique"""
    print(f"  [RAG CLIENT] Détection intent pour {nom_client}...")
    resultat = detecter_intent_client(question)
    intent = resultat.get("intent", "FACTURES_CLIENT")
    params = resultat.get("params", {})
    print(f"  [RAG CLIENT] Intent : {intent} | Params : {params}")

    if intent == "MAX_CONSOMMATION":
        contexte = fetch_client_max_consommation(nom_client)
    elif intent == "MIN_CONSOMMATION":
        contexte = fetch_client_min_consommation(nom_client)
    elif intent == "MAX_MONTANT":
        contexte = fetch_client_max_montant(nom_client)
    elif intent == "MIN_MONTANT":
        contexte = fetch_client_min_montant(nom_client)
    elif intent == "EVOLUTION_CLIENT":
        contexte = fetch_client_evolution(nom_client)
    elif intent == "MOYENNE_CLIENT":
        contexte = fetch_client_moyenne(nom_client)
    elif intent == "INFOS_CLIENT":
        contexte = fetch_client_infos(nom_client)
    elif intent == "MOIS_SPECIFIQUE":
        mois = params.get("mois", "")
        contexte = fetch_client_mois_specifique(nom_client, mois)
    else:
        contexte = fetch_client_toutes_factures(nom_client)

    print(f"  [RAG CLIENT] Contexte prêt ({len(contexte)} caractères)")
    return generer_reponse(question, contexte, historique_texte)