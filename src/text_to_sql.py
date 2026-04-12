import requests
import sqlite3
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")

SCHEMA_TABLE = """
TABLE factures_excel (
    nom_client TEXT,           -- nom complet du client
    agence TEXT,               -- agence SRM de rattachement du client
    usage TEXT,                -- type d'usage ex: USAGE DOMESTIQUE, FORCE MOTRICE, COMMERCIAL, ADMINISTRATIF
    type_service TEXT,         -- type de service : eau ou electricite
    mois_source TEXT,          -- nom du mois ex: Octobre 2025 — utiliser cette colonne pour les périodes
    consommation REAL,         -- quantité consommée (kWh pour electricite, m³ pour eau)
    unite TEXT,                -- unité de mesure : kWh ou m³
    montant_ttc REAL,          -- montant total en Dirhams
    periode_debut TEXT,        -- date de début de la période ex: 01/10/2025
    periode_fin TEXT,          -- date de fin de la période ex: 31/10/2025
    date_limite_paiement TEXT, -- date limite de paiement de la facture
    adresse TEXT,              -- adresse complète du client
    numero_client TEXT,        -- numéro identifiant unique du client
    numero_contrat TEXT,       -- numéro du contrat
    numero_compteur TEXT       -- numéro du compteur physique
)

RÈGLES IMPORTANTES pour générer le SQL :
- Chaque client a plusieurs lignes (une par mois) — ne pas confondre lignes et clients
- Pour compter les clients uniques : COUNT(DISTINCT nom_client)
- Pour lister les clients uniques : SELECT DISTINCT nom_client
- Pour les périodes : utiliser la colonne mois_source
- Pour les numéros de compteur uniques : SELECT DISTINCT numero_compteur
- Pour toute question sur les usages : SELECT DISTINCT usage pour voir toutes les valeurs
- Pour toute agrégation : utiliser GROUP BY avec la bonne colonne
- Ne jamais utiliser LIMIT 1 — utiliser une sous-requête avec MAX() pour les ex-aequo
"""


def _extraire_colonne_order(sql: str) -> str:
    """
    Extrait le nom de la colonne dans ORDER BY.
    Ex: ORDER BY nb_clients DESC → retourne 'nb_clients'
    """
    match = re.search(r'ORDER BY\s+(\w+)', sql, re.IGNORECASE)
    if match:
        return match.group(1)
    return "1"


def corriger_sql(sql: str) -> str:
    """
    Corrige les problèmes courants dans le SQL généré par Mistral.
    """
    sql_lower = sql.lower()

    # Enlever le point-virgule final — cause des erreurs dans les sous-requêtes
    sql = sql.rstrip().rstrip(';').strip()
    sql_lower = sql.lower()

    if "limit 1" in sql_lower and "order by" in sql_lower:
        colonne_order = _extraire_colonne_order(sql)
        sql_sans_limit = re.sub(r'LIMIT\s+1', '', sql, flags=re.IGNORECASE).strip()
        sql_sans_limit = sql_sans_limit.rstrip(';').strip()

        sous_requete = f"""
SELECT * FROM (
    {sql_sans_limit}
) AS resultats
WHERE resultats.{colonne_order} = (
    SELECT MAX({colonne_order}) FROM (
        {sql_sans_limit}
    )
)
"""
        return sous_requete.strip()

    return sql


def generer_sql(question: str) -> str:
    """
    ÉTAPE 1 — Envoie la question + schéma à Mistral
    Mistral retourne une requête SQL adaptée à la question
    """

    prompt = f"""Tu es un expert SQL. Tu dois générer une requête SQL SQLite pour répondre à la question suivante.

Voici le schéma de la table disponible :
{SCHEMA_TABLE}

Question : {question}

RÈGLES STRICTES :
- Retourne UNIQUEMENT la requête SQL, rien d'autre
- Pas d'explication, pas de texte avant ou après
- Pas de balises markdown, pas de ```sql
- La requête doit être compatible SQLite
- Utilise DISTINCT quand on demande une liste unique
- Utilise COUNT, SUM, AVG, GROUP BY pour les questions analytiques
- Ne jamais supposer les valeurs d'une colonne — laisser SQL les découvrir
- Ne jamais utiliser LIMIT 1

Requête SQL :"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )

    sql_brut = response.json()["response"].strip()
    sql_propre = re.sub(r'```sql|```', '', sql_brut).strip()

    # Corriger automatiquement les problèmes courants
    sql_final = corriger_sql(sql_propre)

    return sql_final


def executer_sql(requete: str) -> tuple[list, list]:
    """
    ÉTAPE 2 — Exécute la requête SQL sur SQLite
    Retourne les colonnes et les résultats
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(requete)
        colonnes = [d[0] for d in cursor.description]
        resultats = cursor.fetchall()
        conn.close()
        return colonnes, resultats

    except Exception as e:
        conn.close()
        raise ValueError(f"Erreur SQL : {e} | Requête : {requete}")


def formuler_reponse(question: str, colonnes: list, resultats: list, historique_texte: str) -> str:
    """
    ÉTAPE 3 — Envoie le résultat SQL à Mistral
    Mistral formule une réponse claire en français
    """

    if not resultats:
        resultat_texte = "Aucun résultat trouvé."
    else:
        lignes = []
        for row in resultats:
            ligne = " | ".join([f"{colonnes[i]}: {row[i]}" for i in range(len(colonnes))])
            lignes.append(ligne)
        resultat_texte = "\n".join(lignes)

    prompt = f"""Tu es un assistant intelligent de la SRM Souss-Massa.

Une requête SQL a été exécutée sur la base de données et voici le résultat exact :

Question : {question}

Résultat exact de la requête SQL :
{resultat_texte}

IMPORTANT :
- Réponds UNIQUEMENT en te basant sur le résultat SQL ci-dessus
- Ce résultat vient directement de la base de données — il est exact
- N'utilise AUCUNE information extérieure ou de conversations précédentes
- Ne contredis jamais ce résultat

Réponds de façon claire et précise en français.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


def repondre_question_generale(question: str, historique_texte: str) -> str:
    """
    Pipeline complet Text-to-SQL :
    Question → SQL généré → corriger SQL → SQL exécuté → Réponse en français
    """

    # Étape 1 — Générer et corriger le SQL
    print(f"  [Text-to-SQL] Génération SQL...")
    requete_sql = generer_sql(question)
    print(f"  [Text-to-SQL] SQL final : {requete_sql}")

    # Étape 2 — Exécuter le SQL
    colonnes, resultats = executer_sql(requete_sql)
    print(f"  [Text-to-SQL] {len(resultats)} lignes retournées.")

    # Étape 3 — Formuler la réponse
    reponse = formuler_reponse(question, colonnes, resultats, historique_texte)

    return reponse


# -------- TEST --------
if __name__ == "__main__":

    print("Test 1 — Liste des clients :")
    print("-" * 50)
    print(repondre_question_generale(
        "Quels clients existent dans la base ?", ""
    ))

    print("\nTest 2 — Tous les usages existants :")
    print("-" * 50)
    print(repondre_question_generale(
        "Quels sont tous les types d'usage dans la base ?", ""
    ))

    print("\nTest 3 — Numéros de compteur :")
    print("-" * 50)
    print(repondre_question_generale(
        "Donne moi tous les numéros de compteur qui existent ?", ""
    ))

    print("\nTest 4 — Clients par type service :")
    print("-" * 50)
    print(repondre_question_generale(
        "Combien de clients utilisent l'eau et combien utilisent l'électricité ?", ""
    ))

    print("\nTest 5 — Question analytique :")
    print("-" * 50)
    print(repondre_question_generale(
        "Quel client a la consommation moyenne la plus élevée ?", ""
    ))

    print("\nTest 6 — Agences ex-aequo :")
    print("-" * 50)
    print(repondre_question_generale(
        "Quelle agence a le plus de clients ?", ""
    ))