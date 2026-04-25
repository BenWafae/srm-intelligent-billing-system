# src/rag/dispatcher.py
import re
import unicodedata
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from normalisation import normaliser_usage
from rag.mode import detecter_mode_reponse, _normaliser_q
from rag.intent import detecter_intent, detecter_intent_client, _appeler_llm
from rag.fetchers_generaux import (
    fetch_liste_clients, fetch_top_consommateurs, fetch_min_consommateurs,
    fetch_min_consommateurs_par_service, fetch_max_consommateurs_par_service,
    fetch_top_montants, fetch_classement_par_mois, fetch_par_agence,fetch_min_montants, 
    fetch_par_usage, fetch_par_service, fetch_alertes,
     fetch_stats_generales, fetch_evolution_mois, 
    fetch_somme_conso_mois,
    fetch_agence_par_client, 
                # ← NOUVEAU
    fetch_somme_montant_mois,             
)
from rag.fetchers_client import (
    fetch_client_max_consommation, fetch_client_min_consommation,
    fetch_client_max_montant, fetch_client_min_montant,
    fetch_client_evolution, fetch_client_moyenne, fetch_client_infos,
    fetch_client_mois_specifique, fetch_client_toutes_factures,
    fetch_client_somme_conso,fetch_client_somme_montant

)


# ════════════════════════════════════════════════════════════
# NORMALISATION LOCALE
# ════════════════════════════════════════════════════════════

def _norm_dispatcher(question: str) -> str:
    q = _normaliser_q(question)
    q = re.sub(r'consom+[a-z]*', 'consomme', q)
    q = re.sub(r'pai+e+[a-z]*', 'paye', q)
    q = re.sub(r'pay[eé]+[a-z]*', 'paye', q)
    q = re.sub(r'e+leve+[a-z]*', 'eleve', q)
    return q


# ════════════════════════════════════════════════════════════
# TOKENS — agence par client
# Couvrent toutes les formulations sans LLM :
#   "agence de chaque client"
#   "agence par client"
#   "quelle agence pour chaque client"
#   "lister les agences par client"
#   "agence de tous les clients"
#   "agence de chaque"
#   "par client agence"
#   "afficher agence de chaque client"
# ════════════════════════════════════════════════════════════

_TOKENS_AGENCE_PAR_CLIENT = [
    # ── formulations directes ──
    "agence de chaque client",
    "agence par client",
    "agence de tous les clients",
    "agence pour chaque client",
    "agence pour tous les clients",
    "agences de chaque client",
    "agences par client",
    "agences de tous les clients",

    # ── avec verbe lister / afficher / montrer / voir / donner ──
    "lister les agences par client",
    "lister agence par client",
    "lister les agences de chaque",
    "afficher agence de chaque",
    "afficher les agences par client",
    "afficher agence pour chaque",
    "montrer agence de chaque",
    "montrer les agences par client",
    "montrer agence pour chaque",
    "montrer moi les agence",           # couvre "montrer moi les agence utulise..."
    "montrer moi agence",
    "voir agence de chaque",
    "voir les agences par client",
    "voir agence pour chaque",
    "donner moi agence",
    "donnez moi agence",
    "donner agence de chaque",
    "donner agence par client",

    # ── avec "utilise / utulise / rattachee" (fautes fréquentes) ──
    "agence utulise",                   # faute de frappe fréquente
    "agence utilise",
    "agence utilisee",
    "agence utilise pour chaque",
    "agence utulise pour chaque",
    "agence rattachee",
    "agence rattache",
    "agence associee",
    "agence associe",

    # ── "quelle agence pour chaque / tous" ──
    "quelle agence pour chaque",
    "quelle agence pour tous",
    "quelle est l agence de chaque",
    "quelle est l agence pour chaque",
    "quel agence pour chaque",
    "quel agence de chaque",

    # ── ordre inversé ou reformulations ──
    "par client agence",
    "agence client par client",
    "agence de chaque",
    "agences pour chaque",
]

# ── TOKENS alertes — count ──
_TOKENS_ALERTE_COUNT = [
    "combien d alerte", "combien d alertes",
    "combien alertes", "combien alerte",
    "nombre d alerte", "nombre d alertes",
    "nombre alertes", "nombre alerte",
    "nbre alerte", "nbre alertes",
    "nb alerte", "nb alertes",
    "nbr alerte", "nbr alertes",
    "quel est le nombre d alerte",
    "quel est le nombre d alertes",
    "donner moi le nombre d alerte",
    "montrer moi le nombre d alerte",
    "montrer moi nbr alerte",
    "afficher le nombre d alerte",
    "total alerte", "total alertes",
    "y a combien d alerte", "ya combien d alerte",
    "il y a combien d alerte",
]
 
# ── TOKENS alertes — list ──
_TOKENS_ALERTE_LIST = [
    "lister les alertes", "liste des alertes",
    "afficher les alertes", "montrer les alertes",
    "voir les alertes", "donner les alertes",
    "montrer moi les alertes", "montrer moi alerte",
    "afficher moi les alertes", "afficher moi alerte",
    "donner moi les alertes", "donner moi alerte",
    "quelles sont les alertes",
    "clients avec alerte", "clients ayant alerte",
    "clients en alerte", "factures avec alerte",
    "factures en alerte", "qui a des alertes",
    "qui a une alerte", "qui sont en alerte",
    "quelles factures ont une alerte",
    "quels clients ont une alerte",
]
 
# ── TOKENS alertes — présence générale (pour déclencher le bloc) ──
_TOKENS_ALERTE_PRESENCES = [
    "alerte", "alertes",
]
 

# ════════════════════════════════════════════════════════════
# TOKENS — consommation élevée / faible
# ════════════════════════════════════════════════════════════

_TOKENS_CONSO_ELEVEE = [
    "consomme le plus",
    "le plus consomme",
    "consomme eleve", "consomme elevee",
    "consomme la plus eleve", "consomme la plus elevee",
    "la plus eleve", "la plus elevee",
    "le plus eleve", "le plus elevee",
    "consomme haute", "consomme haut",
    "consomme max", "consomme maximum",
    "consomme grand", "consomme grande",
    "plus grande consomme", "plus grand consomme",
    "grande consomme", "grand consomme",
    "eleve consomme", "elevee consomme",
    "consomme plus",
    "client le plus consomme",
    "client la plus consomme",
    "a une consomme eleve", "a une consomme elevee",
    "a une consomme max", "a une consomme haute",
    "a une consomme grand", "a une consomme grande",
    "avec la consomme eleve", "avec la consomme elevee",
    "avec la consomme max", "avec la consomme haute",
    "avec la consomme grand", "avec la consomme grande",
    "consomme importante", "consomme fort", "consomme forte",
    "importante consomme", "forte consomme",
    "grand consommateur", "grand consomme",
    "top consomme", "top consommateur",
    "max conso",
    "conso max",
    "client max conso",
    "max consomme",
    "consomme max",
    "maximum conso",
    "conso maximum",
]

_TOKENS_CONSO_FAIBLE = [
    "consomme le moins",
    "le moins consomme",
    "consomme faible", "consomme la plus faible",
    "la plus faible", "le plus faible",
    "consomme basse", "consomme bas",
    "consomme min", "consomme minimum",
    "faible consomme", "basse consomme",
    "petite consomme", "consomme petit", "consomme petite",
    "moins consomme", "consomme moins",
    "consome le moins ","consome le moin"
    "client le moins consomme",
    "client la moins consomme",
    "a une consomme faible", "a une consomme basse",
    "a une consomme min", "a une consomme petite",
    "avec la consomme faible", "avec la consomme basse",
    "avec la consomme min",
    "consomme reduite", "consomme legere",
    "reduite consomme", "legere consomme",
    "petit consommateur", "petit consomme",
    "a une consomme min",
    "a une consomme minimale",
    "a une consomme minimum",
    "min consomme",
    "minimum consomme",
    "minimale consomme",
    "consomme min",
    "consomme minimum",
    "consomme minimale",
    "consomme la min",
    "consomme la minimale",
    "plus petite consomme",
    "petite consomme",
    "avec la min consomme",
    "avec la minimale consomme",
    "avec la minimum consomme",
    "avec le min consomme",

]

# ── Mapping mois local ──
_MAP_MOIS_DISP = {
    "jan": "Janvier",   "janv": "Janvier",    "janvier": "Janvier",
    "fev": "Fevrier",   "fevr": "Fevrier",     "fevrier": "Fevrier",
    "mar": "Mars",      "mars": "Mars",
    "avr": "Avril",     "avril": "Avril",
    "mai": "Mai",
    "jun": "Juin",      "juin": "Juin",
    "jul": "Juillet",   "juil": "Juillet",     "juillet": "Juillet",
    "aou": "Aout",      "aout": "Aout",
    "sep": "Septembre", "sept": "Septembre",   "septembre": "Septembre",
    "oct": "Octobre",   "octobre": "Octobre",
    "nov": "Novembre",  "novembre": "Novembre",
    "dec": "Decembre",  "decembre": "Decembre",
}


def _extraire_mois_disp(q: str):
    tokens_tries = sorted(_MAP_MOIS_DISP.keys(), key=len, reverse=True)
    for token in tokens_tries:
        if re.search(r'\b' + re.escape(token) + r'\b', q):
            return _MAP_MOIS_DISP[token]
    for token in tokens_tries:
        if token in q:
            return _MAP_MOIS_DISP[token]
    return None


# ════════════════════════════════════════════════════════════
# TOKENS — somme de consommation par mois
# ════════════════════════════════════════════════════════════

_TOKENS_SOMME_MOIS = [
    "somme de consomme",
    "somme des consomme",
    "somme de conso",
    "somme conso",
    "total consomme",
    "total de consomme",
    "consomme total",
    "consomme totale",
    "combien a-t-on consomme",
    "combien consomme",
    "consomme en ",
    "conso en ",
]
# ── TOKENS somme montant (sans mois précis) ──
_TOKENS_SOMME_MONTANT = [
    "somme des montant",
    "somme de montant",
    "somme montant",
    "total montant",
    "total des montant",
    "montant total",
    "montant global",
    "montant cumule",
    "combien a-t-on paye",
    "combien ont paye",
]

# ── TOKENS montant élevé (général) ──
_TOKENS_MONTANT_ELEVE = [
    "montant le plus eleve",
    "montant le plus haut",
    "montant le plus grand",
    "montant eleve",
    "montant elevee",
    "montant maximum",
    "montant max",
    "montant maximal",
    "montant maximal",
    "montant la plus eleve",
    "facture la plus chere",
    "facture la plus elevee",
    "plus grand montant",
    "plus haut montant",
    "montant le plus fort",
    "paie le plus",
    "paye le plus",
    "qui paie le plus",
    "qui paye le plus",
    "client le plus cher",
    "client avec le montant",
    "client qui paie le plus",
    "client qui paye le plus",
    "montant fort",
    "montant eleve",
]

# ── TOKENS montant faible (général) ──
_TOKENS_MONTANT_FAIBLE = [
    "montant le plus faible",
    "montant le plus bas",
    "montant le plus petit",
    "montant faible",
    "montant minimum",
    "montant min",
    "montant minimal",
    "montant la plus faible",
    "facture la moins chere",
    "facture la plus faible",
    "plus faible montant",
    "plus bas montant",
    "plus petit montant",
    "montant le moins eleve",
    "montant le moins haut",
    "paie le moins",
    "paye le moins",
    "qui paie le moins",
    "qui paye le moins",
    "client le moins cher",
    "client avec le moins",
    "client qui paie le moins",
    "client qui paye le moins",
    "moins eleve montant",
    "moins cher montant",
]


# ════════════════════════════════════════════════════════════
# FALLBACK TEXT-TO-SQL
# Utilisé uniquement quand aucune règle ni intent LLM
# n'a pu traiter la question.
# Le LLM génère uniquement le SQL → Python exécute → réponse fiable
# ════════════════════════════════════════════════════════════

DB_PATH_FALLBACK = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "srm.db"
)




def repondre_fallback_sql(question: str) -> str:
    print(f"  [FALLBACK SQL] Question : {question}")

    schema = """
Table : factures_excel
Colonnes disponibles :
- nom_client       TEXT    : nom complet du client
- agence           TEXT    : agence SRM du client
- usage            TEXT    : ex 'USAGE DOMESTIQUE', 'USAGE PROFESSIONNEL', 'USAGE AGRICOLE'
- type_service     TEXT    : 'eau' ou 'electricite'
- mois_source      TEXT    : ex 'Octobre 2025', 'Janvier 2026'
- periode_debut    TEXT    : format DD/MM/YYYY
- periode_fin      TEXT    : format DD/MM/YYYY
- consommation     REAL    : valeur numérique de la consommation
- unite            TEXT    : 'm³' pour eau, 'kWh' pour électricité
- montant_ttc      REAL    : montant en dirhams
- date_limite_paiement TEXT : date limite de paiement
- alerte           TEXT    : message d'alerte si présent, sinon NULL
- numero_client    TEXT    : identifiant unique du client (ex: C30EF340/690200) — JAMAIS un nombre simple
- numero_contrat   TEXT    : numéro de contrat (ex: 0005567200/2063200) — JAMAIS un nombre simple
- numero_compteur  TEXT    : numéro de compteur (ex: 8301, 8302...) — nombre simple à 4 chiffres
- adresse          TEXT    : adresse du client
"""

    prompt = f"""Tu es un expert SQL SQLite. Tu dois générer une requête SELECT pour répondre à une question sur des factures SRM (eau et électricité au Maroc).

{schema}

RÈGLES ABSOLUES :
1. Génère UNIQUEMENT une requête SELECT — jamais INSERT, UPDATE, DELETE, DROP
2. Utilise UNIQUEMENT les colonnes listées ci-dessus
3. Pour filtrer par mois, utilise : mois_source LIKE '%Janvier 2026%'
4. Pour filtrer par client, utilise : nom_client LIKE '%nom%'
5. Pour filtrer par service, utilise : LOWER(type_service) = 'eau' ou 'electricite'
6. Utilise ROUND(..., 2) pour les montants
7. Si la question est totalement incompréhensible, réponds exactement : INCOMPREHENSIBLE
8. Utilise toujours GROUP BY nom_client pour éviter les doublons par client
9. Réponds avec UNIQUEMENT le SQL brut, sans explication, sans markdown, sans backticks
10. Si la question mentionne "compteur", "compt", "comp", "n comp", "n compteur" 
   suivi d'un nombre → utilise TOUJOURS numero_compteur, jamais numero_client
11. Pour les numéros (compteur, contrat, client), utilise toujours SELECT DISTINCT
12. Si la question demande un résultat "par mois" ou "pour chaque mois", 
    utilise GROUP BY mois_source avec ORDER BY mois_source
13. Si la question demande "total des factures", retourne COUNT(*) 
    groupé par mois_source, pas un COUNT global


Question : {question}

SQL :"""

    try:
        sql_genere = _appeler_llm(prompt).strip()
  
        print(f"  [FALLBACK SQL] SQL généré : {sql_genere}")
    except Exception as e:
        print(f"  [FALLBACK SQL] Erreur LLM : {e}")
        return "Je n'ai pas pu traiter cette question pour le moment."

    # ── Sécurité : refuser tout ce qui n'est pas SELECT ──
    if sql_genere.upper() == "INCOMPREHENSIBLE":
        return (
            "Je n'ai pas compris votre question.\n"
            "Essayez par exemple :\n"
            "- Combien de clients utilisent l'eau ?\n"
            "- Quel est le montant moyen en janvier 2026 ?\n"
            "- Quels clients sont dans l'agence Agadir Nord ?"
        )

    sql_upper = sql_genere.upper().strip()
    mots_dangereux = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    if not sql_upper.startswith("SELECT") or any(m in sql_upper for m in mots_dangereux):
        print(f"  [FALLBACK SQL] ⚠️ SQL refusé pour sécurité : {sql_genere}")
        return "Je n'ai pas pu traiter cette question. Pouvez-vous la reformuler ?"

    # ── Exécution sécurisée ──
    try:
        conn = sqlite3.connect(DB_PATH_FALLBACK)
        cursor = conn.cursor()
        cursor.execute(sql_genere)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        conn.close()
    except Exception as e:
        print(f"  [FALLBACK SQL] Erreur exécution : {e}")
        return "Je n'ai pas pu exécuter cette recherche. Pouvez-vous reformuler votre question ?"

    if not rows:
        return "Aucun résultat trouvé pour votre question."

    return _formater_resultat_fallback(rows, cols, question)


def _formater_resultat_fallback(rows: list, cols: list, question: str) -> str:
    # ── Cas 1 : une seule valeur (COUNT, SUM, AVG...) ──
    if len(rows) == 1 and len(cols) == 1:
        valeur = rows[0][0]
        if isinstance(valeur, float):
            return f"**{valeur:,.2f}**"
        return f"**{valeur}**"

    # ── Cas 2 : une ligne, plusieurs colonnes ──
    if len(rows) == 1:
        lignes = []
        for i, col in enumerate(cols):
            val = rows[0][i]
            if isinstance(val, float):
                lignes.append(f"- {col} : **{val:,.2f}**")
            else:
                lignes.append(f"- {col} : **{val}**")
        return "\n".join(lignes)

    # ── Cas 3 : plusieurs lignes ──
    lignes = []
    for i, row in enumerate(rows, 1):
        parties = []
        for j, col in enumerate(cols):
            val = row[j]
            if val is None:
                continue
            if isinstance(val, float):
                parties.append(f"{col}: {val:,.2f}")
            else:
                parties.append(f"{col}: {val}")
        lignes.append(f"{i}. " + " | ".join(parties))

    return "\n".join(lignes)


def repondre_question_generale(question: str, historique_texte: str) -> str:
    mode = detecter_mode_reponse(question)
    print(f"  [MODE] {mode}")

    q_norm = _norm_dispatcher(question)

# ════════════════════════════════════════════
    # RÈGLE 0 — Questions courtes prioritaires
    # Gérées avant tout pour éviter hallucinations
    # ════════════════════════════════════════════
    _tokens_count_client = [
        "nbr client", "nb client", "nbre client",
        "nbr clients", "nb clients", "nbre clients",
        "nmb client", "nmb clients",
        "nbr de client", "nb de client",
        "nombre client", "nombre de client",
        "nombre clients", "nombre de clients",
    ]
    if any(t in q_norm for t in _tokens_count_client):
        return fetch_liste_clients(mode="count")

    
    # ════════════════════════════════════════════
    # RÈGLE 1 — AGENCE PAR CLIENT
    # ════════════════════════════════════════════
    if any(t in q_norm for t in _TOKENS_AGENCE_PAR_CLIENT):
        print(f"  [RÈGLE] agence par client → fetch_agence_par_client(mode={mode})")
        return fetch_agence_par_client(mode=mode)

    # ── Détection des sujets ──
    _sujet_facture = any(t in q_norm for t in [
        "facture", "factures", "fact", "enregistrement", "enregistrements", "ligne", "lignes"
    ])
    _sujet_client = any(t in q_norm for t in [
        "client", "clients", "abonne", "abonnes"
    ])
    _sujet_mois = any(t in q_norm for t in [
        "mois", "periode", "periodes"
    ])
    _sujet_agence  = any(t in q_norm for t in ["agence", "agences"])
    _sujet_alerte  = any(t in q_norm for t in ["alerte", "alertes"])
    _sujet_service = any(t in q_norm for t in [
        "type de service", "types de service", "type service",
        "service", "services"
    ])
    _sujet_usage = any(t in q_norm for t in [
        "usage", "usages", "type usage",
        "professionnel", "domestique", "agricole",
        "pro", "dom", "agri"
    ])

    demande_eau = bool(re.search(r'\beau\b', q_norm)) or any(
    m in q_norm for m in ["eauu", "eeau"]
)
    demande_elec   = any(m in q_norm for m in ["elec", "electricit", "electr"])
    demande_faible = any(m in q_norm for m in ["faible", "minimum", "minimale", "plus faible"])
    demande_elevee = any(m in q_norm for m in ["eleve", "plus grand", "maximum", "haut", "top"])

    _tokens_client_eau = [
        "client eau", "clients eau",
        "client utilise eau", "client eau uniquement",
        "client eau seulement",
    ]
    _detect_intention_conso = any(t in q_norm for t in [
        "consomme", "conso", "consommation",
        "max", "plus", "top", "eleve",
        "min", "moins", "faible"
    ])
    if any(t in q_norm for t in _tokens_client_eau) and not demande_elec and not _detect_intention_conso:
        return fetch_par_service(service="eau", mode=mode)

    # ── Détection usage précis ──
    usage_detecte = None
    _mots_usage_contexte = any(t in q_norm for t in [
        "usage", "usages", "type usage",
        "professionnel", "domestique", "agricole",
        "pro", "dom", "agri"
    ])
    if _mots_usage_contexte:
        for mot in q_norm.split():
            result = normaliser_usage(mot)
            if result:
                usage_detecte = result
                break
        if usage_detecte is None:
            mots = q_norm.split()
            for i in range(len(mots) - 1):
                bigramme = mots[i] + " " + mots[i + 1]
                result = normaliser_usage(bigramme)
                if result:
                    usage_detecte = result
                    break

    # ── Cas spécial : usage par client ──
    if (any(t in q_norm for t in ["chaque client", "pour chaque", "par client"]) and
            any(t in q_norm for t in ["usage", "usages", "type", "types"])):
        return fetch_par_usage(usage=None, mode="detail")

    # ── Cas spécial : usage précis + demande clients ──

    _demande_agence_usage = any(t in q_norm for t in [
    "quel agence", "quelle agence", "agence a le plus",
    "agence avec le plus", "agence qui a"
])
    if usage_detecte and _demande_agence_usage:
      return repondre_fallback_sql(question)
    
    
    # ════════════════════════════════════════════════════════
    # COMBINAISON DE FILTRES → fallback SQL
    # ════════════════════════════════════════════════════════
    _a_filtre_agence = any(t in q_norm for t in [
        "agence agadir", "agence inezgane", "agence ait melloul",
        "agence taroudant", "agence tiznit", "agadir nord", "agadir sud",
    ])
    _a_filtre_usage = usage_detecte is not None
    _a_filtre_service = demande_eau or demande_elec
    _a_filtre_mois = _extraire_mois_disp(q_norm) is not None

    _nb_filtres = sum([_a_filtre_agence, _a_filtre_usage, _a_filtre_service, _a_filtre_mois])
    if _nb_filtres >= 2:
        print(f"  [RÈGLE] combinaison {_nb_filtres} filtres → fallback SQL")
        return repondre_fallback_sql(question)

    if usage_detecte and any(t in q_norm for t in ["client", "clients", "qui", "liste", "lister", "combien"]):
        return fetch_par_usage(usage=usage_detecte, mode=mode)

    # ════════════════════════════════════════════
    # RÈGLE 2 — MONTANT élevé / faible   ← INDENTATION CORRECTE ICI
    # ════════════════════════════════════════════
    _detect_montant_eleve = any(t in q_norm for t in _TOKENS_MONTANT_ELEVE)
    _detect_montant_faible = any(t in q_norm for t in _TOKENS_MONTANT_FAIBLE)

    if _detect_montant_eleve:
        mois_detecte = _extraire_mois_disp(q_norm)
        print(f"  [RÈGLE] montant élevé → fetch_top_montants(mois={mois_detecte}, mode={mode})")
        return fetch_top_montants(mois=mois_detecte, mode=mode)

    if _detect_montant_faible:
        mois_detecte = _extraire_mois_disp(q_norm)
        print(f"  [RÈGLE] montant faible → fetch_min_montants(mois={mois_detecte}, mode={mode})")
        return fetch_min_montants(mois=mois_detecte, mode=mode)

    # ════════════════════════════════════════════
    # RÈGLE 3 — CONSOMMATION élevée / faible
    # ════════════════════════════════════════════
    _detect_conso_elevee = any(t in q_norm for t in _TOKENS_CONSO_ELEVEE)
    _detect_conso_faible = any(t in q_norm for t in _TOKENS_CONSO_FAIBLE)

    if _detect_conso_elevee or _detect_conso_faible:
        mois_detecte = _extraire_mois_disp(q_norm)

        _demande_classement = any(t in q_norm for t in [
            "classement", "classe", "classer", "tous", "toutes",
            "liste", "lister", "ordre", "rang", "ranking",
        ])
        _demande_top1 = any(t in q_norm for t in [
            "qui ", "quel ", "client le plus", "client la plus",
            "le client", "la client",
            "client avec", "avec la plus", "avec le plus",
        ])
        mode_effectif = mode
        if _demande_top1 and not _demande_classement:
            mode_effectif = "top1"

        if _detect_conso_elevee and demande_eau and not demande_elec:
            return fetch_max_consommateurs_par_service(service="eau", mois=mois_detecte, mode=mode_effectif)
        if _detect_conso_elevee and demande_elec and not demande_eau:
            return fetch_max_consommateurs_par_service(service="electricite", mois=mois_detecte, mode=mode_effectif)
        if _detect_conso_faible and demande_eau and not demande_elec:
            return fetch_min_consommateurs_par_service(service="eau", mois=mois_detecte, mode=mode_effectif)
        if _detect_conso_faible and demande_elec and not demande_eau:
            return fetch_min_consommateurs_par_service(service="electricite", mois=mois_detecte, mode=mode_effectif)

        if _detect_conso_elevee:
            print(f"  [RÈGLE] consomme élevée → fetch_top_consommateurs(mois={mois_detecte}, mode={mode_effectif})")
            return fetch_top_consommateurs(mois=mois_detecte, mode=mode_effectif)
        if _detect_conso_faible:
            print(f"  [RÈGLE] consomme faible → fetch_min_consommateurs(mois={mois_detecte}, mode={mode_effectif})")
            return fetch_min_consommateurs(mois=mois_detecte, mode=mode_effectif)

    # ════════════════════════════════════════════
    # MODE COUNT
    # ════════════════════════════════════════════
    if mode == "count":
        if _sujet_facture and not _sujet_client:
            return fetch_stats_generales(mode="count", question=question)
        if _sujet_client and not _sujet_facture and not demande_eau and not demande_elec:
            return fetch_liste_clients(mode="count")
        if _sujet_mois and not _sujet_facture and not _sujet_client:
            return fetch_evolution_mois(mode="count")
        if _sujet_agence:
            return fetch_par_agence(agence=None, mode="count")
        if _sujet_alerte:
            return fetch_alertes(mode="count")
        if _sujet_usage and not usage_detecte and not _sujet_client:
            return fetch_par_usage(usage=None, mode="count")
        if _sujet_service and not demande_eau and not demande_elec and not _sujet_client:
            return fetch_par_service(service=None, mode="count")
        if demande_eau and not demande_elec:
            return fetch_par_service(service="eau", mode="count")
        if demande_elec and not demande_eau:
            return fetch_par_service(service="electricite", mode="count")
        if demande_eau and demande_elec:
            return fetch_par_service(service=None, mode="count")

    # ════════════════════════════════════════════
    # MODE LIST
    # ════════════════════════════════════════════
    if mode == "list":
        if _sujet_client and not demande_eau and not demande_elec and not _sujet_service:
            return fetch_liste_clients(mode="list")
        if _sujet_agence and not _sujet_client:
            return fetch_par_agence(agence=None, mode="list")
        if _sujet_alerte:
            return fetch_alertes(mode="list")
        if _sujet_usage and not usage_detecte and not _sujet_client:
            return fetch_par_usage(usage=None, mode="list")
        if _sujet_service and not demande_eau and not demande_elec:
            return fetch_par_service(service=None, mode="list")
        if demande_eau and not demande_elec:
            return fetch_par_service(service="eau", mode="list")
        if demande_elec and not demande_eau:
            return fetch_par_service(service="electricite", mode="list")

    # ════════════════════════════════════════════
    # Pré-détection service / conso
    # ════════════════════════════════════════════
    if demande_faible and demande_eau and not demande_elec:
        return fetch_min_consommateurs_par_service(service="eau", mode=mode)
    if demande_faible and demande_elec and not demande_eau:
        return fetch_min_consommateurs_par_service(service="electricite", mode=mode)
    if demande_elevee and demande_eau and not demande_elec:
        return fetch_max_consommateurs_par_service(service="eau", mode=mode)
    if demande_elevee and demande_elec and not demande_eau:
        return fetch_max_consommateurs_par_service(service="electricite", mode=mode)

    if _sujet_service and not demande_eau and not demande_elec:
        return fetch_par_service(service=None, mode=mode)
    if demande_eau and demande_elec:
        return fetch_par_service(service=None, mode=mode)
    if demande_eau and not demande_elec and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return fetch_par_service(service="eau", mode=mode)
    if demande_elec and not demande_eau and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return fetch_par_service(service="electricite", mode=mode)

    # ════════════════════════════════════════════
    # SOMME CONSO MOIS
    # ════════════════════════════════════════════
    _detect_somme_mois = any(t in q_norm for t in _TOKENS_SOMME_MOIS)
    _detect_intention_classement = any(t in q_norm for t in [
        "max", "plus", "top", "eleve", "elevee", "grand", "haut",
        "min", "moins", "faible", "bas", "petit"
    ])
    if _detect_somme_mois and not _detect_intention_classement:
        mois_detecte = _extraire_mois_disp(q_norm)
        if mois_detecte:
            print(f"  [RÈGLE] somme conso mois → fetch_somme_conso_mois(mois={mois_detecte})")
            return fetch_somme_conso_mois(mois_detecte)

    # ════════════════════════════════════════════
    # SOMME MONTANT MOIS
    # ════════════════════════════════════════════
    _detect_somme_montant = any(t in q_norm for t in _TOKENS_SOMME_MONTANT)
    if _detect_somme_montant:
        mois_detecte = _extraire_mois_disp(q_norm)
        if mois_detecte:
            print(f"  [RÈGLE] somme montant mois → fetch_somme_montant_mois(mois={mois_detecte})")
            return fetch_somme_montant_mois(mois_detecte)
        else:
            print(f"  [RÈGLE] somme montant global → fetch_stats_generales")
            return fetch_stats_generales(mode="count", question="montant total")

    # ════════════════════════════════════════════
    # LLM FALLBACK
    # ════════════════════════════════════════════
    print(f"  [RAG] Détection intent...")
    resultat = detecter_intent(question)
    intent = resultat.get("intent", "QUESTION_LIBRE")
    params = resultat.get("params", {})
    print(f"  [RAG] Intent : {intent} | Params : {params} | Mode : {mode}")

    if intent == "LISTE_CLIENTS":
        return fetch_liste_clients(mode=mode)
    elif intent == "TOP_CONSOMMATEURS":
        return fetch_top_consommateurs(mois=params.get("mois"), mode=mode)
    elif intent == "MIN_CONSOMMATEURS":
        return fetch_min_consommateurs(mois=params.get("mois"), mode=mode)
    elif intent == "TOP_MONTANTS":
        return fetch_top_montants(mois=params.get("mois"), mode=mode)
    elif intent == "MIN_MONTANTS":                                        # ← AJOUT
        return fetch_min_montants(mois=params.get("mois"), mode=mode)    # ← AJOUT
    elif intent == "CLASSEMENT_PAR_MOIS":
        return fetch_classement_par_mois(mode=mode)
    elif intent == "AGENCE_PAR_CLIENT":
        return fetch_agence_par_client(mode=mode)
    elif intent == "PAR_AGENCE":
        return fetch_par_agence(agence=params.get("agence"), mode=mode)
    elif intent == "PAR_USAGE":
        usage_brut = params.get("usage")
        usage_norm = normaliser_usage(usage_brut) if usage_brut else None
        return fetch_par_usage(usage=usage_norm, mode=mode)
    elif intent == "PAR_SERVICE":
        return fetch_par_service(service=params.get("service"), mode=mode)
    elif intent == "ALERTES":
        return fetch_alertes(mode=mode)
    elif intent == "STATS_GENERALES":
        return fetch_stats_generales(mode=mode, question=question)
    elif intent == "EVOLUTION_MOIS":
        return fetch_evolution_mois(mode=mode)
    elif intent == "SOMME_CONSO_MOIS":
        mois = params.get("mois", "")
        if not mois:
            return "Veuillez préciser le mois souhaité."
        return fetch_somme_conso_mois(mois)
    elif intent == "SOMME_MONTANT_MOIS":
        mois = params.get("mois", "")
        if not mois:
            return fetch_stats_generales(mode="count", question="montant total")
        return fetch_somme_montant_mois(mois)
    else:
        print(f"  [FALLBACK] Intent non reconnu → Text-to-SQL")
        return repondre_fallback_sql(question)
def repondre_question_client(question: str, nom_client: str, historique_texte: str) -> str:
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
        champ = params.get("champ")
        return fetch_client_infos(nom_client, champ=champ)
    elif intent == "MOIS_SPECIFIQUE":
        mois  = params.get("mois", "")
        champ = params.get("champ")          # ← récupérer le champ
        return fetch_client_mois_specifique(nom_client, mois, champ=champ)
    elif intent == "SOMME_CONSO_CLIENT":
        return fetch_client_somme_conso(nom_client)
    elif intent == "SOMME_MONTANT_CLIENT":
        return fetch_client_somme_montant(nom_client)
    else:
        return fetch_client_toutes_factures(nom_client)