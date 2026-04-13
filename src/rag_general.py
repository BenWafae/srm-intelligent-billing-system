import requests
import sqlite3
import os
import re
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")

# ─────────────────────────────────────────────────────────
# ARCHITECTURE : RÉPONSE DIRECTE PYTHON (sans LLM pour les données)
#
# PRINCIPE CLÉ :
#   Les fetchers Python calculent ET formatent la réponse finale.
#   Le LLM (Mistral) n'est utilisé QUE pour :
#     1. Détecter l'intent (classification)
#     2. Les questions libres (QUESTION_LIBRE) où on n'a pas de fetcher dédié
#
#   Pour toutes les questions structurées, Python répond directement.
#   Cela élimine 100% des hallucinations sur les données.
# ─────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────
# PARTIE 1 — DÉTECTION D'INTENT (LLM utilisé uniquement ici)
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


def _appeler_llm(prompt: str) -> str:
    """Appel LLM Mistral — UNIQUEMENT pour classification d'intent et questions libres"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"].strip()


def detecter_intent(question: str) -> dict:
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

    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {"intent": "QUESTION_LIBRE", "params": {}}


def detecter_intent_client(question: str) -> dict:
    prompt = f"""Tu es un classificateur de questions sur un client.

Voici les intents disponibles :
{INTENTS_CLIENT}

Question : {question}

Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre, sans explication, sans markdown.
Format exact :
{{"intent": "NOM_INTENT", "params": {{}}}}

Si la question mentionne un mois précis (ex: Mars, Octobre 2025, Janvier 2026), ajoute : {{"mois": "Mars"}}

JSON :"""

    texte = _appeler_llm(prompt)
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
# PARTIE 2 — FETCHERS GÉNÉRAUX
# Chaque fetcher retourne une réponse FINALE prête à afficher.
# Aucun LLM ne touche à ces données.
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
    lignes = [f"Il y a **{len(rows)} clients** dans la base :\n"]
    for i, r in enumerate(rows, 1):
        lignes.append(
            f"{i}. **{r[0]}** — {r[1]} | {r[2]} | {r[3]} | "
            f"{r[4]} mois | Total cumulé : {r[5]:,.2f} Dhs"
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
        titre = f"Classement par consommation — **{mois}** :\n"
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total_conso DESC
        """)
        titre = "Classement par consommation totale (tous mois) :\n"
    rows = cursor.fetchall()
    conn.close()
    lignes = [titre]
    for i, r in enumerate(rows, 1):
        lignes.append(f"{i}. **{r[0]}** — {r[1]:,} {r[2]}")
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
        titre = f"Classement par montant — **{mois}** :\n"
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total DESC
        """)
        titre = "Classement par montant total (tous mois) :\n"
    rows = cursor.fetchall()
    conn.close()
    lignes = [titre]
    for i, r in enumerate(rows, 1):
        lignes.append(f"{i}. **{r[0]}** — {r[1]:,.2f} Dhs")
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

    lignes = ["Classement des clients par montant pour chaque mois :\n"]
    for mois, clients in mois_dict.items():
        lignes.append(f"📅 **{mois}** :")
        for i, r in enumerate(clients, 1):
            lignes.append(f"  {i}. {r[1]} — {r[2]:,.2f} Dhs | Conso : {r[3]:,} {r[4]}")
        lignes.append("")
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
        lignes = [f"**{len(rows)} clients** dans l'agence « {agence} » :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Usage : {r[1]} | Service : {r[2]} | "
                f"{r[3]} mois | Total : {r[4]:,.2f} Dhs"
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
        lignes = ["Répartition des clients par agence :\n"]
        for r in rows:
            lignes.append(f"- **{r[0]}** : {r[1]} clients | Total : {r[2]:,.2f} Dhs")
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
        lignes = [f"**{len(rows)} clients** avec usage « {usage} » :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Agence : {r[1]} | Service : {r[2]} | "
                f"{r[3]} mois | Total : {r[4]:,.2f} Dhs"
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
        lignes = ["Répartition par type d'usage :\n"]
        for r in rows:
            lignes.append(f"- **{r[0]}** : {r[1]} clients | Total : {r[2]:,.2f} Dhs")
    return "\n".join(lignes)


def fetch_par_service(service: str = None) -> str:
    """
    Fetcher robuste pour les questions sur le type de service (eau / electricite).
    Retourne une réponse directe Python — AUCUN LLM ne touche ces données.
    """
    conn = _connexion()
    cursor = conn.cursor()

    if service:
        # Normaliser : accepter "électricité", "electricite", "elec", "eau", "water"...
        service_norm = service.lower().strip()
        if any(k in service_norm for k in ["elec", "électr"]):
            service_filtre = "electricite"
            service_label = "Électricité"
        elif any(k in service_norm for k in ["eau", "water"]):
            service_filtre = "eau"
            service_label = "Eau"
        else:
            service_filtre = service_norm
            service_label = service

        cursor.execute("""
            SELECT nom_client, agence, usage,
                   ROUND(SUM(consommation), 2) as total_conso,
                   unite,
                   ROUND(SUM(montant_ttc), 2) as total_ttc,
                   COUNT(*) as nb_mois
            FROM factures_excel
            WHERE LOWER(type_service) = ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (service_filtre,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"Aucun client trouvé pour le service « {service_label} »."

        lignes = [f"Il y a **{len(rows)} clients** qui utilisent le service **{service_label}** :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Agence : {r[1]} | Usage : {r[2]} | "
                f"Conso totale : {r[3]:,} {r[4]} | Montant total : {r[5]:,.2f} Dhs"
            )
        return "\n".join(lignes)

    else:
        # Vue comparative eau vs electricite — chiffres exacts
        cursor.execute("""
            SELECT LOWER(type_service) as service,
                   COUNT(DISTINCT nom_client) as nb_clients,
                   GROUP_CONCAT(DISTINCT nom_client) as noms,
                   ROUND(SUM(consommation), 2) as total_conso,
                   ROUND(SUM(montant_ttc), 2) as total_ttc
            FROM factures_excel
            GROUP BY LOWER(type_service)
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        lignes = ["Répartition exacte par type de service :\n"]
        total_clients = sum(r[1] for r in rows)
        lignes.append(f"Total : **{total_clients} clients** répartis comme suit :\n")

        for r in rows:
            service_label = "Électricité" if r[0] == "electricite" else "Eau" if r[0] == "eau" else r[0]
            noms_liste = r[2].split(",") if r[2] else []
            lignes.append(f"💧⚡ **{service_label}** : **{r[1]} clients**")
            for nom in noms_liste:
                lignes.append(f"   • {nom.strip()}")
            lignes.append(f"   Consommation totale : {r[3]:,} | Montant total : {r[4]:,.2f} Dhs\n")

        lignes.append("⚠️ Chaque client utilise UN SEUL service. Les totaux ci-dessus sont indépendants.")
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
        return "✅ Aucune alerte trouvée dans la base de données."
    lignes = [f"⚠️ **{len(rows)} factures** avec alerte :\n"]
    for r in rows:
        lignes.append(
            f"- **{r[0]}** | {r[1]} | {r[2]} | {r[3]:,.2f} Dhs | Alerte : {r[4]}"
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

    # Stats par service
    cursor.execute("""
        SELECT LOWER(type_service), COUNT(DISTINCT nom_client)
        FROM factures_excel
        GROUP BY LOWER(type_service)
    """)
    services = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    nb_eau = services.get("eau", 0)
    nb_elec = services.get("electricite", 0)

    return f"""📊 **Statistiques générales de la base SRM :**

- Nombre de clients       : **{r[0]}** ({nb_eau} eau · {nb_elec} électricité)
- Nombre de mois couverts : **{r[1]}**
- Nombre de factures      : **{r[2]}**
- Montant total TTC       : **{r[3]:,.2f} Dhs**
- Montant moyen / facture : **{r[4]:,.2f} Dhs**
- Montant maximum         : **{r[5]:,.2f} Dhs**
- Montant minimum         : **{r[6]:,.2f} Dhs**
- Client avec le plus de dépenses : **{top[0]}** ({top[1]:,.2f} Dhs cumulés)"""


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
    lignes = ["📈 **Évolution mois par mois :**\n"]
    for r in rows:
        lignes.append(
            f"- **{r[0]}** : {r[1]} clients | "
            f"Conso totale : {r[2]:,} | "
            f"Montant total : {r[3]:,.2f} Dhs | "
            f"Moyenne : {r[4]:,.2f} Dhs"
        )
    return "\n".join(lignes)


def fetch_question_libre(question: str, historique_texte: str) -> str:
    """
    Seul cas où le LLM est utilisé pour RÉPONDRE.
    On lui fournit un résumé complet mais on lui interdit de modifier les chiffres.
    """
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

    contexte_lignes = [
        f"Base SRM : {len(clients)} clients | {globales[0]} mois | Total : {globales[1]:,.2f} Dhs\n",
        "Résumé par client :"
    ]
    for r in clients:
        contexte_lignes.append(
            f"  - {r[0]} | {r[1]} | Usage: {r[2]} | Service: {r[3]} | "
            f"{r[4]} mois | Conso: {r[5]} {r[6]} | "
            f"Total: {r[7]} Dhs | Moy/mois: {r[8]} Dhs"
        )
    contexte = "\n".join(contexte_lignes)

    prompt = f"""Tu es un assistant de la SRM Souss-Massa.

Données EXACTES extraites de la base :
{contexte}

RÈGLES STRICTES :
1. Utilise UNIQUEMENT les données ci-dessus
2. Ne modifie AUCUN chiffre
3. Si l'info n'est pas dans les données, dis-le clairement

Historique :
{historique_texte}

Question : {question}

Réponds clairement en français, en te basant UNIQUEMENT sur les données fournies."""

    return _appeler_llm(prompt)


# ─────────────────────────────────────────────────────────
# PARTIE 3 — FETCHERS ANALYTIQUES CLIENT
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    max_val = rows[0][1]
    tops = [r for r in rows if r[1] == max_val]
    lignes = [f"📈 Consommation maximale de **{nom_client}** :\n"]
    for r in tops:
        lignes.append(f"🏆 **{r[0]}** : {r[1]:,} {r[2]}  ← MAXIMUM")
    lignes.append("\nTous les mois (ordre décroissant) :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]:,} {r[2]}")
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    min_val = rows[0][1]
    mins = [r for r in rows if r[1] == min_val]
    lignes = [f"📉 Consommation minimale de **{nom_client}** :\n"]
    for r in mins:
        lignes.append(f"🔻 **{r[0]}** : {r[1]:,} {r[2]}  ← MINIMUM")
    lignes.append("\nTous les mois (ordre croissant) :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]:,} {r[2]}")
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    max_val = rows[0][1]
    tops = [r for r in rows if r[1] == max_val]
    lignes = [f"💰 Montant maximum de **{nom_client}** :\n"]
    for r in tops:
        lignes.append(f"🏆 **{r[0]}** : {r[1]:,.2f} Dhs  ← MAXIMUM")
    lignes.append("\nTous les mois (ordre décroissant) :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]:,.2f} Dhs")
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    min_val = rows[0][1]
    mins = [r for r in rows if r[1] == min_val]
    lignes = [f"💸 Montant minimum de **{nom_client}** :\n"]
    for r in mins:
        lignes.append(f"🔻 **{r[0]}** : {r[1]:,.2f} Dhs  ← MINIMUM")
    lignes.append("\nTous les mois (ordre croissant) :")
    for r in rows:
        lignes.append(f"  - {r[0]} : {r[1]:,.2f} Dhs")
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    lignes = [f"📈 Évolution chronologique de **{nom_client}** :\n"]
    for r in rows:
        lignes.append(
            f"  - **{r[0]}** : Consommation {r[1]:,} {r[2]} | Montant {r[3]:,.2f} Dhs"
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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    return f"""📊 Statistiques de **{nom_client}** sur {r[7]} mois :

- Consommation moyenne : **{r[0]:,} {r[1]}**
- Consommation minimum : {r[3]:,} {r[1]}
- Consommation maximum : {r[4]:,} {r[1]}
- Montant moyen        : **{r[2]:,.2f} Dhs**
- Montant minimum      : {r[5]:,.2f} Dhs
- Montant maximum      : {r[6]:,.2f} Dhs"""


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
        return f"Aucune donnée trouvée pour « {nom_client} »."
    return f"""📋 Informations du client **{r[0]}** :

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
        mois_court = mois.split()[0] if mois else mois
        conn2 = _connexion()
        cursor2 = conn2.cursor()
        cursor2.execute("""
            SELECT mois_source, periode_debut, periode_fin,
                   consommation, unite, montant_ttc, date_limite_paiement
            FROM factures_excel
            WHERE nom_client LIKE ? AND mois_source LIKE ?
        """, (f"%{nom_client}%", f"%{mois_court}%"))
        rows = cursor2.fetchall()
        conn2.close()

    if not rows:
        return f"Aucune facture trouvée pour **{nom_client}** en {mois}."
    r = rows[0]
    return f"""🧾 Facture de **{nom_client}** — {r[0]} :

- Période            : {r[1]} → {r[2]}
- Consommation       : **{r[3]:,} {r[4]}**
- Montant TTC        : **{r[5]:,.2f} Dhs**
- Date limite pmt    : {r[6]}"""


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


# ─────────────────────────────────────────────────────────
# PARTIE 4 — FONCTIONS PRINCIPALES
# ─────────────────────────────────────────────────────────

def repondre_question_generale(question: str, historique_texte: str) -> str:
    """
    Pipeline RAG par intent pour les questions générales.
    Le LLM est utilisé UNIQUEMENT pour classifier l'intent.
    La réponse finale vient directement des fetchers Python.
    """
    print(f"  [RAG] Détection intent...")
    resultat = detecter_intent(question)
    intent = resultat.get("intent", "QUESTION_LIBRE")
    params = resultat.get("params", {})
    print(f"  [RAG] Intent : {intent} | Params : {params}")

    if intent == "LISTE_CLIENTS":
        return fetch_liste_clients()

    elif intent == "TOP_CONSOMMATEURS":
        return fetch_top_consommateurs(mois=params.get("mois"))

    elif intent == "TOP_MONTANTS":
        return fetch_top_montants(mois=params.get("mois"))

    elif intent == "CLASSEMENT_PAR_MOIS":
        return fetch_classement_par_mois()

    elif intent == "PAR_AGENCE":
        return fetch_par_agence(agence=params.get("agence"))

    elif intent == "PAR_USAGE":
        return fetch_par_usage(usage=params.get("usage"))

    elif intent == "PAR_SERVICE":
        return fetch_par_service(service=params.get("service"))

    elif intent == "ALERTES":
        return fetch_alertes()

    elif intent == "STATS_GENERALES":
        return fetch_stats_generales()

    elif intent == "EVOLUTION_MOIS":
        return fetch_evolution_mois()

    else:
        # QUESTION_LIBRE : seul cas où le LLM génère la réponse
        return fetch_question_libre(question, historique_texte)


def repondre_question_client(question: str, nom_client: str, historique_texte: str) -> str:
    """
    Pipeline RAG analytique pour les questions sur un client spécifique.
    Le LLM est utilisé UNIQUEMENT pour classifier l'intent.
    La réponse finale vient directement des fetchers Python.
    """
    print(f"  [RAG CLIENT] Détection intent pour {nom_client}...")
    resultat = detecter_intent_client(question)
    intent = resultat.get("intent", "FACTURES_CLIENT")
    params = resultat.get("params", {})
    print(f"  [RAG CLIENT] Intent : {intent} | Params : {params}")

    if intent == "MAX_CONSOMMATION":
        return fetch_client_max_consommation(nom_client)

    elif intent == "MIN_CONSOMMATION":
        return fetch_client_min_consommation(nom_client)

    elif intent == "MAX_MONTANT":
        return fetch_client_max_montant(nom_client)

    elif intent == "MIN_MONTANT":
        return fetch_client_min_montant(nom_client)

    elif intent == "EVOLUTION_CLIENT":
        return fetch_client_evolution(nom_client)

    elif intent == "MOYENNE_CLIENT":
        return fetch_client_moyenne(nom_client)

    elif intent == "INFOS_CLIENT":
        return fetch_client_infos(nom_client)

    elif intent == "MOIS_SPECIFIQUE":
        mois = params.get("mois", "")
        return fetch_client_mois_specifique(nom_client, mois)

    else:
        return fetch_client_toutes_factures(nom_client)