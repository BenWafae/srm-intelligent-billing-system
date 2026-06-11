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
    fetch_top_montants, fetch_classement_par_mois, fetch_par_agence, fetch_min_montants,
    fetch_par_usage, fetch_par_service, fetch_alertes,
    fetch_stats_generales, fetch_evolution_mois,
    fetch_somme_conso_mois,
    fetch_agence_par_client,
    fetch_somme_montant_mois,
    fetch_top_mois_conso,
)
from rag.fetchers_client import (
    fetch_client_max_consommation, fetch_client_min_consommation,
    fetch_client_max_montant, fetch_client_min_montant,
    fetch_client_evolution, fetch_client_moyenne, fetch_client_infos,
    fetch_client_mois_specifique, fetch_client_toutes_factures,
    fetch_client_somme_conso, fetch_client_somme_montant
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
# ════════════════════════════════════════════════════════════

_TOKENS_AGENCE_PAR_CLIENT = [
    "agence de chaque client", "agence par client", "agence de tous les clients",
    "agence pour chaque client", "agence pour tous les clients",
    "agences de chaque client", "agences par client", "agences de tous les clients",
    "lister les agences par client", "lister agence par client",
    "lister les agences de chaque", "afficher agence de chaque",
    "afficher les agences par client", "afficher agence pour chaque",
    "montrer agence de chaque", "montrer les agences par client",
    "montrer agence pour chaque", "montrer moi les agence", "montrer moi agence",
    "voir agence de chaque", "voir les agences par client", "voir agence pour chaque",
    "donner moi agence", "donnez moi agence", "donner agence de chaque",
    "donner agence par client", "agence utulise", "agence utilise",
    "agence utilisee", "agence utilise pour chaque", "agence utulise pour chaque",
    "agence rattachee", "agence rattache", "agence associee", "agence associe",
    "quelle agence pour chaque", "quelle agence pour tous",
    "quelle est l agence de chaque", "quelle est l agence pour chaque",
    "quel agence pour chaque", "quel agence de chaque",
    "par client agence", "agence client par client", "agence de chaque",
    "agences pour chaque",
]

# ── TOKENS alertes ──
_TOKENS_ALERTE_COUNT = [
    "combien d alerte", "combien d alertes", "combien alertes", "combien alerte",
    "nombre d alerte", "nombre d alertes", "nombre alertes", "nombre alerte",
    "nbre alerte", "nbre alertes", "nb alerte", "nb alertes",
    "nbr alerte", "nbr alertes",
    "quel est le nombre d alerte", "quel est le nombre d alertes",
    "donner moi le nombre d alerte", "montrer moi le nombre d alerte",
    "montrer moi nbr alerte", "afficher le nombre d alerte",
    "total alerte", "total alertes",
    "y a combien d alerte", "ya combien d alerte", "il y a combien d alerte",
]

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
    "quelles factures ont une alerte", "quels clients ont une alerte",
]

_TOKENS_ALERTE_PRESENCES = ["alerte", "alertes"]


# ════════════════════════════════════════════════════════════
# TOKENS — consommation élevée / faible
# ════════════════════════════════════════════════════════════

_TOKENS_CONSO_ELEVEE = [
    "consomme le plus", "le plus consomme",
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
    "consomme plus", "client le plus consomme", "client la plus consomme",
    "a une consomme eleve", "a une consomme elevee",
    "a une consomme max", "a une consomme haute",
    "a une consomme grand", "a une consomme grande",
    "avec la consomme eleve", "avec la consomme elevee",
    "avec la consomme max", "avec la consomme haute",
    "avec la consomme grand", "avec la consomme grande",
    "consomme importante", "consomme fort", "consomme forte",
    "importante consomme", "forte consomme",
    "grand consommateur", "grand consomme",
    "top consomme", "top consommateur", "top consomateur"
    "max conso", "conso max", "client max conso",
    "max consomme", "consomme max", "maximum conso", "conso maximum",
    "consomme beaucoup", "consomateur beaucoup",
    "grand consomateur", "gros consomateur",
    "grosse consomation", "grande consomation",
    "consomme bcp", "conso bcp", "consome bcp",
    "grande consommateur", "grande consomateur",
    "quel est le grande", "quel est le grand",
    "ayant conso eleve", "ayant conso elevee",
    "ayant consomation eleve", "ayant consomation elevee",
    "ayant consommation eleve", "ayant consommation elevee",
]
 


_TOKENS_CONSO_FAIBLE = [
    "consomme le moins", "le moins consomme",
    "consomme faible", "consomme la plus faible",
    "la plus faible", "le plus faible",
    "consomme basse", "consomme bas",
    "consomme min", "consomme minimum",
    "faible consomme", "basse consomme",
    "petite consomme", "consomme petit", "consomme petite",
    "moins consomme", "consomme moins",
    "consome le moins", "consome le moin",
    "client le moins consomme", "client la moins consomme",
    "a une consomme faible", "a une consomme basse",
    "a une consomme min", "a une consomme petite",
    "avec la consomme faible", "avec la consomme basse",
    "avec la consomme min",
    "consomme reduite", "consomme legere",
    "reduite consomme", "legere consomme",
    "petit consommateur", "petit consomme",
    "a une consomme minimale", "a une consomme minimum",
    "min consomme", "minimum consomme", "minimale consomme",
    "consomme minimum", "consomme minimale",
    "consomme la min", "consomme la minimale",
    "plus petite consomme", "petite consomme",
    "avec la min consomme", "avec la minimale consomme",
    "avec la minimum consomme", "avec le min consomme",
    "ayant conso faible", "ayant consomation faible",
    "ayant consommation faible",
    "le moins faible", "moins faible",
    "ayant le moins", "ayant conso le moins"
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


def _extraire_n_limit(q: str):
    _LETTRES = {
        "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
        "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
        "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
    }
    for mot, val in _LETTRES.items():
        if re.search(r'\b' + mot + r'\b', q):
            return val

    patterns = [
        r'\btop\s+(\d+)\b',
        r'\bles\s+(\d+)\b',
        r'\b(\d+)\s+(?:premier|premiere|premiers|premieres|dernier|derniers|derniere|dernieres)',
        r'\b(\d+)\s+(?:client|clients|consomm)',
        r'\bdonner?\s+(?:moi\s+)?(?:les\s+)?(\d+)\b',
        r'\bafficher?\s+(?:les\s+)?(\d+)\b',
        r'\bmontrer?\s+(?:les\s+)?(\d+)\b',
        r'\b(\d+)\s+(?:top|premier|meilleur|grand|gros|eleve|consomm)',
    ]
    for pattern in patterns:
        m = re.search(pattern, q)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 100:
                return n

    _mots_action = ["top", "premier", "premiers", "dernier", "derniers",
                    "meilleur", "meilleurs", "plus", "moins"]
    if any(m in q for m in _mots_action):
        m = re.search(r'\b(\d+)\b', q)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 100:
                return n

    return None


# ════════════════════════════════════════════════════════════
# TOKENS — somme consommation / montant
# ════════════════════════════════════════════════════════════

_TOKENS_SOMME_MOIS = [
    "somme de consomme", "somme des consomme", "somme de conso", "somme conso",
    "total consomme", "total de consomme", "consomme total", "consomme totale",
    "combien a-t-on consomme", "combien consomme",
    "consomme en ", "conso en ", "consomation total", "consomtion total",
    "consommation total", "total consommation", "total consomation",
    "total de consommation", "total de consomation", "consomtion en ",
    "somme de consommation", "somme consommation", "somme consomation",
    "somme de consomation", "somme des consomation",
    "total consomation", "total de consomation",
    "consomation total", "consomation totale",
    "consomation en ", "consomation dans ",
    "consomation du mois", "consomation pour ",
    "consomme dans ", "consomme de ",
    "conso dans ", "consommation en ", "consommation dans ",
    "combien a-t-on consomme", "combien ont consomme",
    "combien on a consomme", "combien de consomation",
    "combien de consommation", "quelle est la consomation",
    "quel est la consomation", "quelle consomation", "quel consomation",
    "quelle est la consommation", "quel est la consommation",
    "somme de consome", "total consome", "consome en ", "consome dans ",
    "consome total", "consomation global", "consomation generale",
    "consommation global", "consommation generale", "consomtion total",
]


_TOKENS_SOMME_MONTANT = [
    "somme des montant", "somme de montant", "somme montant",
    "total montant", "total des montant", "montant total",
    "montant global", "montant cumule",
    "combien a-t-on paye", "combien ont paye",
    "mantant total", "mantant en ", "total mantant", "somme mantant",
]


_TOKENS_MONTANT_ELEVE = [
    "montant le plus eleve", "montant le plus haut", "montant le plus grand",
    "montant eleve", "montant elevee", "montant maximum", "montant max",
    "montant maximal", "montant la plus eleve",
    "facture la plus chere", "facture la plus elevee",
    "plus grand montant", "plus haut montant", "montant le plus fort",
    "paie le plus", "paye le plus", "qui paie le plus", "qui paye le plus",
    "client le plus cher", "client avec le montant",
    "client qui paie le plus", "client qui paye le plus",
    "montant fort",
]


_TOKENS_MONTANT_FAIBLE = [
    "montant le plus faible", "montant le plus bas", "montant le plus petit",
    "montant faible", "montant minimum", "montant min", "montant minimal",
    "montant la plus faible", "facture la moins chere", "facture la plus faible",
    "plus faible montant", "plus bas montant", "plus petit montant",
    "montant le moins eleve", "montant le moins haut",
    "paie le moins", "paye le moins", "qui paie le moins", "qui paye le moins",
    "client le moins cher", "client avec le moins",
    "client qui paie le moins", "client qui paye le moins",
    "moins eleve montant", "moins cher montant",
]


_CONCEPTS_CONNUS = {
    "consommation", "consomme", "conso", "consomation", "consome",
    "consomtion", "consomateur", "consommateur", "kwh", "m3",
    "montant", "mantant", "monton", "montan", "mntant", "ttc",
    "paye", "paie", "depense", "prix", "cout", "facture", "factures",
    "client", "clients", "abonne", "abonnes", "nom",
    "numero client", "numero contrat", "numero compteur",
    "contrat", "compteur",
    "adresse", "agence", "agences",
    "service", "type service", "eau", "electricite", "elec", "electr",
    "usage", "usages", "domestique", "professionnel", "agricole",
    "dom", "pro", "agri",
    "mois", "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
    "jan", "fev", "mar", "avr", "jun", "jul", "sep", "oct", "nov", "dec",
    "janv", "fevr", "juil", "aou", "sept",
    "periode", "date", "limite", "paiement", "echeance",
    "alerte", "alertes",
    "liste", "lister", "afficher", "montrer", "donner", "voir",
    "combien", "quel", "quelle", "quels", "quelles", "qui",
    "somme", "total", "moyenne", "moyen", "max", "min",
    "evolution", "classement", "statistique", "stat",
    "plus", "moins", "eleve", "faible", "grand", "petit",
    "top", "haut", "bas", "fort", "fort",
}

_CONCEPTS_INEXISTANTS = {
    "telephone", "tel", "phone", "mobile", "gsm", "portable",
    "email", "mail", "courriel", "lemail", "lemail",
    "cin", "carte", "identite", "passeport", "cni",
    "age", "naissance", "date naissance", "sexe", "genre",
    "ville", "pays", "region", "code postal", "code postale",
    "quartier", "commune", "province", "wilaya",
    "salaire", "revenu", "solde", "dette", "credit", "rib", "iban",
    "virement", "cheque", "banque",
    "statut", "status", "categorie", "classe", "type client",
    "actif", "inactif", "suspendu", "bloque",
    "photo", "image", "note", "commentaire", "observation",
    "numero agence", "code agence", "id agence",
    "profession", "metier", "emploi", "entreprise client",
    "nationalite", "langue", "tele", "telep", "telepone", "telephon", "telphone",
    "mob", "portable", "gsm",
    "code postalle",
}


def _separer_articles(q: str) -> str:
    q = re.sub(r'\bl([aeio][a-z]+)', r'\1', q)
    q = re.sub(r'\bd([aeio][a-z]+)', r'\1', q)
    q = re.sub(r'\bdu([a-z]+)', r'\1', q)
    return q


def valider_concept_question(question: str) -> str | None:
    q = _normaliser_q(question)
    q = _separer_articles(q)
    mots = q.split()

    for mot in mots:
        if mot in _CONCEPTS_INEXISTANTS and mot not in _CONCEPTS_CONNUS:
            return (
                f"⚠️ L'information **« {mot} »** n'est pas disponible "
                f"dans notre système.\n\n"
                f"Les informations disponibles sont :\n"
                f"- Consommation, Montant, Agence, Usage\n"
                f"- N° Client, N° Contrat, N° Compteur\n"
                f"- Adresse, Type de service, Alertes, Mois"
            )

    for i in range(len(mots) - 1):
        bigramme = mots[i] + " " + mots[i + 1]
        if bigramme in _CONCEPTS_INEXISTANTS:
            return (
                f"⚠️ L'information **« {bigramme} »** n'est pas disponible "
                f"dans notre système.\n\n"
                f"Les informations disponibles sont :\n"
                f"- Consommation, Montant, Agence, Usage\n"
                f"- N° Client, N° Contrat, N° Compteur\n"
                f"- Adresse, Type de service, Alertes, Mois"
            )

    return None


# ════════════════════════════════════════════════════════════
# VALIDATION SCHÉMA SQL
# ════════════════════════════════════════════════════════════

_COLONNES_REELLES = {
    "nom_client", "agence", "usage", "type_service",
    "mois_source", "periode_debut", "periode_fin",
    "consommation", "unite", "montant_ttc",
    "date_limite_paiement", "alerte",
    "numero_client", "numero_contrat", "numero_compteur",
    "adresse", "id", "date_enregistrement",
    "nom_fichier",  # ← ajouté pour le filtre fichier
}

_MOTS_CLES_SQL = {
    "select", "from", "where", "group", "order", "by",
    "limit", "having", "join", "as", "and", "or", "not",
    "in", "like", "between", "sum", "count", "avg", "min",
    "max", "round", "distinct", "lower", "upper", "substr",
    "desc", "asc", "null", "is", "case", "when", "then",
    "else", "end", "inner", "left", "on", "factures_excel",
    "eau", "electricite", "true", "false",
}


def valider_colonnes_sql(sql: str) -> bool:
    sql_lower = sql.lower()
    alias_definis = set(re.findall(r'\bas\s+([a-z_]+)', sql_lower))
    sql_sans_alias = re.sub(r'\bas\s+[a-z_]+', '', sql_lower)
    sql_sans_alias = re.sub(r"'[^']*'", '', sql_sans_alias)
    sql_sans_alias = re.sub(r'"[^"]*"', '', sql_sans_alias)

    texte_critique = ""
    where_match = re.search(
        r'\bwhere\b(.+?)(?:\bgroup\b|\border\b|\blimit\b|$)',
        sql_sans_alias, re.DOTALL
    )
    order_match = re.search(
        r'\border\s+by\b(.+?)(?:\blimit\b|$)',
        sql_sans_alias, re.DOTALL
    )
    if where_match:
        texte_critique += " " + where_match.group(1)
    if order_match:
        texte_critique += " " + order_match.group(1)
    if not texte_critique:
        return True

    mots = re.findall(r'\b([a-z_]+)\b', texte_critique)
    colonnes_inconnues = [
        m for m in mots
        if m not in _COLONNES_REELLES
        and m not in _MOTS_CLES_SQL
        and m not in alias_definis
        and len(m) >= 3
        and not m.isdigit()
    ]
    if colonnes_inconnues:
        print(f"  [VALIDATION SQL] ⚠️ Colonnes inexistantes : {colonnes_inconnues}")
        return False
    return True


# ════════════════════════════════════════════════════════════
# INJECTION SÉCURISÉE DU FILTRE NOM_FICHIER DANS UN SQL
# ════════════════════════════════════════════════════════════

def _injecter_filtre_fichier(sql: str, nom_fichier: str) -> str:
    """
    Injecte WHERE nom_fichier = '...' dans un SQL généré par le LLM.
    Fonctionne que le SQL ait déjà un WHERE ou non.
    Approche post-génération : plus fiable que de demander au LLM de le faire.
    """
    if not nom_fichier:
        return sql

    # Échapper les apostrophes dans le nom de fichier (sécurité basique)
    nom_safe = nom_fichier.replace("'", "''")
    filtre = f"nom_fichier = '{nom_safe}'"

    # Cas 1 : SQL a déjà un WHERE → ajouter en tête du WHERE
    if re.search(r'\bWHERE\b', sql, re.IGNORECASE):
        sql = re.sub(
            r'\bWHERE\b',
            f"WHERE {filtre} AND",
            sql, count=1, flags=re.IGNORECASE
        )
    # Cas 2 : pas de WHERE → injecter avant GROUP BY / ORDER BY / LIMIT / fin
    else:
        insertion = f" WHERE {filtre}"
        for keyword in [r'\bGROUP\s+BY\b', r'\bORDER\s+BY\b', r'\bLIMIT\b']:
            m = re.search(keyword, sql, re.IGNORECASE)
            if m:
                pos = m.start()
                sql = sql[:pos] + insertion + " " + sql[pos:]
                return sql
        # Aucun mot-clé trouvé → ajouter en fin
        sql = sql + insertion

    return sql


# ════════════════════════════════════════════════════════════
# FALLBACK TEXT-TO-SQL
# ════════════════════════════════════════════════════════════

DB_PATH_FALLBACK = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "srm.db"
)


def repondre_fallback_sql(question: str, nom_fichier: str = "") -> str:
    print(f"  [FALLBACK SQL] Question : {question} | Fichier : {nom_fichier or 'tous'}")

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
- numero_client    TEXT    : identifiant unique du client (ex: C30EF340/690200)
- numero_contrat   TEXT    : numéro de contrat (ex: 0005567200/2063200)
- numero_compteur  TEXT    : numéro de compteur (ex: 8301, 8302...)
- adresse          TEXT    : adresse du client
- nom_fichier      TEXT    : nom du fichier Excel source
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
14. Si la question demande une LISTE de clients avec des filtres (agence, usage, service...),
    retourne UNIQUEMENT : nom_client, agence, usage, type_service
    avec SELECT DISTINCT et GROUP BY nom_client — jamais de colonnes mois/montant/conso
15. Pour filtrer agence et usage, utilise TOUJOURS LIKE avec % :
    LOWER(agence) LIKE '%agadir%' — jamais agence = 'agadir'
    LOWER(usage) LIKE '%domestique%'
    LOWER(usage) LIKE '%agricole%'
    LOWER(usage) LIKE '%professionnel%'
16. INTENTION CONSOMMATION vs MONTANT — ne jamais confondre :
    - "consomme", "consomation", "consomateur" → ORDER BY consommation
    - "paie", "paye", "montant", "depense" → ORDER BY montant_ttc
17. CLASSEMENT :
    - "le plus", "max", "eleve", "grand", "beaucoup", "bzaf" → ORDER BY DESC
    - "le moins", "min", "faible", "petit", "peu" → ORDER BY ASC
    - LIMIT 1 si UN seul client, LIMIT 5 si "les plus..." sans précision
18. AGRÉGATION OBLIGATOIRE : SUM(consommation) groupé par nom_client
19. COLONNES À RETOURNER selon l'intention — jamais SELECT *
20. FAUTES D'ORTHOGRAPHE : "bcp", "bzaf", "grand", "gros" → sens MAX/DESC
21. NOM PROPRE dans la question → WHERE nom_client LIKE '%prenom%'
22. COMPARAISON SERVICES : GROUP BY type_service si "eau et electricite"
23. PÉRIODES : mois_source LIKE '%Janvier%' pour un mois précis
24. RÉSULTAT VIDE : préférer requête large plutôt que filtre trop strict
25. Ne jamais ajouter de filtre sur nom_fichier — ce filtre sera ajouté automatiquement

EXEMPLES :
Q: "qui consomme le plus"
SQL: SELECT nom_client, ROUND(SUM(consommation),2) as total_conso, unite FROM factures_excel GROUP BY nom_client ORDER BY total_conso DESC LIMIT 1

Q: "grand consomateur"
SQL: SELECT nom_client, ROUND(SUM(consommation),2) as total_conso, unite FROM factures_excel GROUP BY nom_client ORDER BY total_conso DESC LIMIT 5

Q: "qui paie le plus"
SQL: SELECT nom_client, ROUND(SUM(montant_ttc),2) as total_ttc FROM factures_excel GROUP BY nom_client ORDER BY total_ttc DESC LIMIT 1

Q: "clients agence agadir usage domestique"
SQL: SELECT DISTINCT nom_client, agence, usage, type_service FROM factures_excel WHERE LOWER(agence) LIKE '%agadir%' AND LOWER(usage) LIKE '%domestique%' GROUP BY nom_client

Q: "total montant janvier"
SQL: SELECT ROUND(SUM(montant_ttc),2) as total, COUNT(DISTINCT nom_client) as nb_clients FROM factures_excel WHERE mois_source LIKE '%Janvier%'

Q: "evolution par mois"
SQL: SELECT mois_source, COUNT(DISTINCT nom_client) as nb_clients, ROUND(SUM(montant_ttc),2) as total_ttc FROM factures_excel GROUP BY mois_source ORDER BY mois_source

Q: "numero compteur de Fatima"
SQL: SELECT DISTINCT nom_client, numero_compteur FROM factures_excel WHERE nom_client LIKE '%Fatima%'

Question : {question}

SQL :"""

    try:
        sql_genere = _appeler_llm(prompt).strip()
        print(f"  [FALLBACK SQL] SQL généré : {sql_genere}")
    except Exception as e:
        print(f"  [FALLBACK SQL] Erreur LLM : {e}")
        return "Je n'ai pas pu traiter cette question pour le moment."

    # ── Sécurité 1 : INCOMPREHENSIBLE ──
    if sql_genere.upper() == "INCOMPREHENSIBLE":
        return (
            "Je n'ai pas compris votre question.\n"
            "Essayez par exemple :\n"
            "- Combien de clients utilisent l'eau ?\n"
            "- Quel est le montant moyen en janvier 2026 ?\n"
            "- Quels clients sont dans l'agence Agadir Nord ?"
        )

    # ── Sécurité 2 : whitelist SELECT ──
    sql_upper = sql_genere.upper().strip()
    mots_dangereux = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    if not sql_upper.startswith("SELECT") or any(m in sql_upper for m in mots_dangereux):
        print(f"  [FALLBACK SQL] ⚠️ SQL refusé pour sécurité : {sql_genere}")
        return "Je n'ai pas pu traiter cette question. Pouvez-vous la reformuler ?"

    # ── Sécurité 3 : validation colonnes schéma ──
    if not valider_colonnes_sql(sql_genere):
        print(f"  [FALLBACK SQL] ⚠️ SQL refusé — colonnes hors schéma : {sql_genere}")
        return "Je n'ai pas pu traiter cette question. Pouvez-vous la reformuler ?"

    # ── Injection du filtre nom_fichier APRÈS validation ──
    if nom_fichier:
        sql_genere = _injecter_filtre_fichier(sql_genere, nom_fichier)
        print(f"  [FALLBACK SQL] SQL après filtre fichier : {sql_genere}")

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
    if len(rows) == 1 and len(cols) == 1:
        valeur = rows[0][0]
        if isinstance(valeur, float):
            return f"**{valeur:,.2f}**"
        return f"**{valeur}**"

    if len(rows) == 1:
        lignes = []
        for i, col in enumerate(cols):
            val = rows[0][i]
            if isinstance(val, float):
                lignes.append(f"- {col} : **{val:,.2f}**")
            else:
                lignes.append(f"- {col} : **{val}**")
        return "\n".join(lignes)

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


# ════════════════════════════════════════════════════════════
# QUESTION GÉNÉRALE
# ════════════════════════════════════════════════════════════

def repondre_question_generale(question: str, historique_texte: str, nom_fichier: str = "") -> str:

    # ── PORTAIL 1 : validation concept universel ──
    msg_concept = valider_concept_question(question)
    if msg_concept:
        return msg_concept

    # ── PORTAIL 2 : questions ambiguës ──
    from rag.intent import detecter_question_ambigue
    msg = detecter_question_ambigue(question)
    if msg:
        return msg

    mode = detecter_mode_reponse(question)
    print(f"  [MODE] {mode} | [FICHIER] {nom_fichier or 'tous'}")

    q_norm = _norm_dispatcher(question)

    if len(question.strip().split()) <= 1:
        return (
            "Je n'ai pas bien compris votre question. "
            "Pourriez-vous la préciser ?\n\n"
            "Par exemple :\n"
            "- *Quel est le montant total en janvier ?*\n"
            "- *Qui consomme le plus ?*\n"
            "- *Liste des clients*"
        )

    # ── Helper local : passer nom_fichier à tous les fetch ──
    # On définit des wrappers partiels pour ne pas répéter nom_fichier partout
    def _fetch(fn, **kwargs):
        """Appelle fn en injectant nom_fichier si elle l'accepte."""
        try:
            return fn(**kwargs, nom_fichier=nom_fichier)
        except TypeError:
            return fn(**kwargs)

    # ════════════════════════════════════════════
    # RÈGLE 1 — AGENCE PAR CLIENT
    # ════════════════════════════════════════════
    if any(t in q_norm for t in _TOKENS_AGENCE_PAR_CLIENT):
        print(f"  [RÈGLE] agence par client → fetch_agence_par_client(mode={mode})")
        return _fetch(fetch_agence_par_client, mode=mode)

    # ════════════════════════════════════════════
    # RÈGLE 1b — EVOLUTION MOIS
    # ════════════════════════════════════════════
    _TOKENS_EVOLUTION_MOIS = [
        "evolution mois", "evolution par mois",
        "mois par mois", "progression mois",
        "historique general", "historique global",
        "tendance mois", "par mois",
        "chaque mois", "tous les mois",
    ]
    if any(t in q_norm for t in _TOKENS_EVOLUTION_MOIS):
        print(f"  [RÈGLE] évolution mois → fetch_evolution_mois(mode={mode})")
        return _fetch(fetch_evolution_mois, mode=mode)

    # ── Détection des sujets ──
    _sujet_facture = any(t in q_norm for t in [
        "facture", "factures", "fact", "enregistrement", "enregistrements", "ligne", "lignes"
    ])
    _sujet_client = any(t in q_norm for t in [
        "client", "clients", "abonne", "abonnes"
    ])
    _sujet_mois = any(t in q_norm for t in ["mois", "periode", "periodes"])
    _sujet_agence = any(t in q_norm for t in ["agence", "agences"])
    _sujet_alerte = any(t in q_norm for t in ["alerte", "alertes"])
    _sujet_service = any(t in q_norm for t in [
        "type de service", "types de service", "type service", "service", "services"
    ])
    _sujet_usage = any(t in q_norm for t in [
        "usage", "usages", "type usage",
        "professionnel", "domestique", "agricole", "pro", "dom", "agri"
    ])

    demande_eau = bool(re.search(r'\beau\b', q_norm)) or any(
        m in q_norm for m in ["eauu", "eeau"]
    )
    demande_elec = any(m in q_norm for m in ["elec", "electricit", "electr"])
    demande_faible = any(m in q_norm for m in ["faible", "minimum", "minimale", "plus faible"])
    demande_elevee = any(m in q_norm for m in ["eleve", "plus grand", "maximum", "haut", "top"])

    _tokens_client_eau = [
        "client eau", "clients eau",
        "client utilise eau", "client eau uniquement", "client eau seulement",
    ]
    _detect_intention_conso = any(t in q_norm for t in [
        "consomme", "conso", "consommation", "max", "plus", "top", "eleve", "min", "moins", "faible"
    ])
    if any(t in q_norm for t in _tokens_client_eau) and not demande_elec and not _detect_intention_conso:
        return _fetch(fetch_par_service, service="eau", mode=mode)

    # ── Détection usage précis ──
    usage_detecte = None
    _mots_usage_contexte = any(t in q_norm for t in [
        "usage", "usages", "type usage",
        "professionnel", "domestique", "agricole", "pro", "dom", "agri"
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

    if (any(t in q_norm for t in ["chaque client", "pour chaque", "par client"]) and
            any(t in q_norm for t in ["usage", "usages", "type", "types"])):
        return _fetch(fetch_par_usage, usage=None, mode="detail")

    _demande_agence_usage = any(t in q_norm for t in [
        "quel agence", "quelle agence", "agence a le plus",
        "agence avec le plus", "agence qui a"
    ])
    if usage_detecte and _demande_agence_usage:
        return repondre_fallback_sql(question, nom_fichier)

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
        return repondre_fallback_sql(question, nom_fichier)

    if usage_detecte and any(t in q_norm for t in ["client", "clients", "qui", "liste", "lister", "combien"]):
        return _fetch(fetch_par_usage, usage=usage_detecte, mode=mode)

    # ════════════════════════════════════════════
    # RÈGLE — CLIENT + AGENCE PRÉCISE
    # ════════════════════════════════════════════
    _a_filtre_agence_precise = any(t in q_norm for t in [
        "agence agadir", "agence tiznit", "agence inezgane",
        "agence taroudant", "agence ait melloul",
        "agence agadir nord", "agence agadir sud",
        "lagence agadir", "lagence tiznit", "lagence inezgane",
        "lagence taroudant", "lagence ait melloul",
        "lagence agadir nord", "lagence agadir sud",
        "utulise agence agadir", "utulise agence tiznit",
        "utulise agence inezgane", "utulise agence taroudant",
        "utulise agence ait melloul",
    ])

    if _sujet_client and _a_filtre_agence_precise:
        _agences_map = {
            "agadir nord": "Agadir Nord",
            "agadir sud": "Agadir Sud",
            "ait melloul": "Ait Melloul",
            "melloul": "Ait Melloul",
            "inezgane": "Inezgane",
            "taroudant": "Taroudant",
            "tiznit": "Tiznit",
            "agadir": "Agadir",
        }
        agence_trouvee = None
        for token, nom in sorted(_agences_map.items(), key=lambda x: len(x[0]), reverse=True):
            if token in q_norm:
                agence_trouvee = nom
                break
        print(f"  [RÈGLE] client + agence → fetch_par_agence(agence={agence_trouvee}, mode={mode})")
        return _fetch(fetch_par_agence, agence=agence_trouvee, mode=mode)
    # ════════════════════════════════════════════
    # RÈGLE TOP MOIS CONSO — avant RÈGLE 2.5
    # ════════════════════════════════════════════
    _TOKENS_TOP_MOIS_DISP = [
        "les mois les plus consomme", "les mois les moins consomme",
        "mois les plus consomme", "mois les moins consomme",
        "top mois consomme", "mois avec le plus de consomme",
        "mois avec le moins de consomme", "mois les plus eleve",
        "mois les plus faible", "les mois plus consomme",
        "les mois moins consomme", "mois qui a le plus consomme",
        "mois qui a le moins consomme",
        "les mois les plus consomme", "les mois les moins consomme",
        "donner moi les mois", "montrer moi les mois",
    ]
    if any(t in q_norm for t in _TOKENS_TOP_MOIS_DISP):
        _est_min_mois = any(t in q_norm for t in [
            "moins", "faible", "min", "minimum", "petit", "bas"
        ])
        n_limit_mois = _extraire_n_limit(q_norm)
        ordre_mois = "asc" if _est_min_mois else "desc"
        limit_mois = n_limit_mois if n_limit_mois else 5
        print(f"  [RÈGLE] top mois conso → fetch_top_mois_conso(ordre={ordre_mois}, limit={limit_mois})")
        return _fetch(fetch_top_mois_conso, ordre=ordre_mois, limit=limit_mois)

    # ════════════════════════════════════════════
    # RÈGLE 2 — MONTANT élevé / faible
    # ════════════════════════════════════════════
    _detect_montant_eleve = (
        any(t in q_norm for t in _TOKENS_MONTANT_ELEVE) and
        not any(t in q_norm for t in ["consomme", "conso", "consomation", "consommation", "kwh", "m3"])
    )
    _detect_montant_faible = (
        any(t in q_norm for t in _TOKENS_MONTANT_FAIBLE) and
        not any(t in q_norm for t in ["consomme", "conso", "consomation", "consommation", "kwh", "m3"])
    )

    if _detect_montant_eleve:
        mois_detecte = _extraire_mois_disp(q_norm)
        n_limit = _extraire_n_limit(q_norm)
        print(f"  [RÈGLE] montant élevé → fetch_top_montants(mois={mois_detecte}, mode={mode}, limit={n_limit})")
        return _fetch(fetch_top_montants, mois=mois_detecte, mode=mode, limit=n_limit)

    if _detect_montant_faible:
        mois_detecte = _extraire_mois_disp(q_norm)
        n_limit = _extraire_n_limit(q_norm)
        print(f"  [RÈGLE] montant faible → fetch_min_montants(mois={mois_detecte}, mode={mode}, limit={n_limit})")
        return _fetch(fetch_min_montants, mois=mois_detecte, mode=mode, limit=n_limit)

    # ════════════════════════════════════════════
    # RÈGLE 2.5 — TOP N détection précoce
    # ════════════════════════════════════════════
    _match_top_n = re.search(r'\btop\s+(\d+)\b', q_norm)
    if _match_top_n:
        n_top = int(_match_top_n.group(1))
        if 1 <= n_top <= 100:
            _est_montant = any(t in q_norm for t in [
                "montant", "mantant", "paye", "paie", "depense", "ttc", "cher"
            ])
            _est_conso = any(t in q_norm for t in [
                "consomm", "consomateur", "consommateur", "conso",
                "consomation", "consomateurs", "consommateurs", "kwh", "m3"
            ])
            mois_detecte = _extraire_mois_disp(q_norm)
            if _est_montant and not _est_conso:
                print(f"  [RÈGLE top-N] montant → fetch_top_montants(limit={n_top})")
                return _fetch(fetch_top_montants, mois=mois_detecte, mode="detail", limit=n_top)
            else:
                print(f"  [RÈGLE top-N] conso → fetch_top_consommateurs(limit={n_top})")
                return _fetch(fetch_top_consommateurs, mois=mois_detecte, mode="detail", limit=n_top)

    # ════════════════════════════════════════════
    # RÈGLE 3 — CONSOMMATION élevée / faible
    # ════════════════════════════════════════════
    _detect_conso_elevee = (
        any(t in q_norm for t in _TOKENS_CONSO_ELEVEE) and
        not any(t in q_norm for t in ["montant", "paie", "paye", "depense", "mantant", "ttc"])
    )
    _detect_conso_faible = (
        any(t in q_norm for t in _TOKENS_CONSO_FAIBLE) and
        not any(t in q_norm for t in ["montant", "paie", "paye", "depense", "mantant", "ttc"])
    )

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
        n_limit = _extraire_n_limit(q_norm)

        if n_limit:
            mode_effectif = "detail"
        elif _demande_top1 and not _demande_classement:
            mode_effectif = "top1"
        else:
            mode_effectif = mode

        if _detect_conso_elevee and demande_eau and not demande_elec:
            return _fetch(fetch_max_consommateurs_par_service, service="eau", mois=mois_detecte, mode=mode_effectif, limit=n_limit)
        if _detect_conso_elevee and demande_elec and not demande_eau:
            return _fetch(fetch_max_consommateurs_par_service, service="electricite", mois=mois_detecte, mode=mode_effectif, limit=n_limit)
        if _detect_conso_faible and demande_eau and not demande_elec:
            return _fetch(fetch_min_consommateurs_par_service, service="eau", mois=mois_detecte, mode=mode_effectif, limit=n_limit)
        if _detect_conso_faible and demande_elec and not demande_eau:
            return _fetch(fetch_min_consommateurs_par_service, service="electricite", mois=mois_detecte, mode=mode_effectif, limit=n_limit)

        if _detect_conso_elevee:
            print(f"  [RÈGLE] conso élevée → fetch_top_consommateurs(mois={mois_detecte}, mode={mode_effectif}, limit={n_limit})")
            return _fetch(fetch_top_consommateurs, mois=mois_detecte, mode=mode_effectif, limit=n_limit)
        if _detect_conso_faible:
            print(f"  [RÈGLE] conso faible → fetch_min_consommateurs(mois={mois_detecte}, mode={mode_effectif}, limit={n_limit})")
            return _fetch(fetch_min_consommateurs, mois=mois_detecte, mode=mode_effectif, limit=n_limit)

    # ════════════════════════════════════════════
    # MODE COUNT
    # ════════════════════════════════════════════
    if mode == "count":
        if _sujet_facture and not _sujet_client:
            return _fetch(fetch_stats_generales, mode="count", question=question)
        if _sujet_client and not _sujet_facture and not demande_eau and not demande_elec:
            return _fetch(fetch_liste_clients, mode="count")
        if _sujet_mois and not _sujet_facture and not _sujet_client:
            return _fetch(fetch_evolution_mois, mode="count")
        if _sujet_agence:
            return _fetch(fetch_par_agence, agence=None, mode="count")
        if _sujet_alerte:
            return _fetch(fetch_alertes, mode="count")
        if _sujet_usage and not usage_detecte and not _sujet_client:
            return _fetch(fetch_par_usage, usage=None, mode="count")
        if _sujet_service and not demande_eau and not demande_elec and not _sujet_client:
            return _fetch(fetch_par_service, service=None, mode="count")
        if demande_eau and not demande_elec:
            return _fetch(fetch_par_service, service="eau", mode="count")
        if demande_elec and not demande_eau:
            return _fetch(fetch_par_service, service="electricite", mode="count")
        if demande_eau and demande_elec:
            return _fetch(fetch_par_service, service=None, mode="count")

    # ════════════════════════════════════════════
    # MODE LIST
    # ════════════════════════════════════════════
    if mode == "list":
        if _sujet_client and not demande_eau and not demande_elec \
                and not _sujet_service and not _sujet_agence:
            return _fetch(fetch_liste_clients, mode="list")
        if _sujet_agence:
            return _fetch(fetch_par_agence, agence=None, mode="list")
        if _sujet_alerte:
            return _fetch(fetch_alertes, mode="list")
        if _sujet_usage and not usage_detecte and not _sujet_client:
            return _fetch(fetch_par_usage, usage=None, mode="list")
        if _sujet_service and not demande_eau and not demande_elec:
            return _fetch(fetch_par_service, service=None, mode="list")
        if demande_eau and not demande_elec:
            return _fetch(fetch_par_service, service="eau", mode="list")
        if demande_elec and not demande_eau:
            return _fetch(fetch_par_service, service="electricite", mode="list")

    # ════════════════════════════════════════════
    # Pré-détection service / conso
    # ════════════════════════════════════════════
    if demande_faible and demande_eau and not demande_elec:
        return _fetch(fetch_min_consommateurs_par_service, service="eau", mode=mode)
    if demande_faible and demande_elec and not demande_eau:
        return _fetch(fetch_min_consommateurs_par_service, service="electricite", mode=mode)
    if demande_elevee and demande_eau and not demande_elec:
        return _fetch(fetch_max_consommateurs_par_service, service="eau", mode=mode)
    if demande_elevee and demande_elec and not demande_eau:
        return _fetch(fetch_max_consommateurs_par_service, service="electricite", mode=mode)

    if _sujet_service and not demande_eau and not demande_elec:
        return _fetch(fetch_par_service, service=None, mode=mode)
    if demande_eau and demande_elec:
        return _fetch(fetch_par_service, service=None, mode=mode)
    if demande_eau and not demande_elec and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return _fetch(fetch_par_service, service="eau", mode=mode)
    if demande_elec and not demande_eau and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return _fetch(fetch_par_service, service="electricite", mode=mode)

   # ════════════════════════════════════════════
    # SOMME CONSO MOIS
    # ════════════════════════════════════════════
    _detect_somme_mois = any(t in q_norm for t in _TOKENS_SOMME_MOIS)

    _pattern_somme_conso_mois = (
        any(t in q_norm for t in ["somme", "total", "combien"]) and
        any(t in q_norm for t in [
            "consomme", "conso", "consomation", "consommation", "consome", "consomtion"
        ]) and
        _extraire_mois_disp(q_norm) is not None
    )

    _detect_intention_classement = any(t in q_norm for t in [
        "max", "plus", "top", "eleve", "elevee", "grand", "haut",
        "min", "moins", "faible", "bas", "petit"
    ])

    # Détection nom client dans la question (pour ne pas bloquer "somme conso de Sanaa")
    _MOTS_CLES_DISPATCHER = {
        "somme", "total", "montant", "consomme", "conso", "consommation",
        "consomation", "consome", "mantant", "monton", "paye", "paie",
        "depense", "client", "clients", "liste", "lister", "afficher",
        "montrer", "donner", "voir", "quel", "quelle", "quels", "quelles",
        "qui", "combien", "pour", "dans", "avec", "par", "les", "des",
        "une", "eau", "elec", "electricite", "agence", "usage", "alerte",
        "alertes", "service", "facture", "factures", "mois", "evolution",
        "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre",
        "jan", "fev", "avr", "jun", "jul", "sep", "oct", "nov", "dec",
        "janv", "fevr", "juil", "aou", "sept",
        "de", "du", "la", "le", "en", "sur", "et", "ou", "est", "son",
        "tout", "tous", "toutes", "chaque", "global", "generale", "ttc",
        "dhs", "kwh", "m3", "max", "min", "plus", "moins", "eleve",
        "faible", "haut", "bas", "top", "grand", "petit", "fort",
        "moyenne", "moyen", "stat", "statistique", "classement",
        "moi", "me", "mon", "ma", "mes",
    }
    _mots_inconnus_disp = [
        m for m in q_norm.split()
        if len(m) >= 3 and m not in _MOTS_CLES_DISPATCHER
    ]
    _a_nom_dans_question = (
        any(len(m) >= 4 and m[0].isupper() for m in question.split())
        or len(_mots_inconnus_disp) >= 1
    )

    if (_detect_somme_mois or _pattern_somme_conso_mois) and not _detect_intention_classement and _extraire_n_limit(q_norm) is None:
        mois_detecte = _extraire_mois_disp(q_norm)
        if mois_detecte:
            # Mois présent → somme générale du mois (comportement inchangé)
            print(f"  [RÈGLE] somme conso mois → fetch_somme_conso_mois(mois={mois_detecte})")
            return _fetch(fetch_somme_conso_mois, mois=mois_detecte)
        elif _a_nom_dans_question:
            # Pas de mois mais nom client détecté → laisser passer vers LLM/fallback
            print(f"  [RÈGLE] somme conso sans mois + nom client détecté → fallback")
            pass  # continue vers la suite du dispatcher

    # ════════════════════════════════════════════
    # SOMME MONTANT MOIS
    # ════════════════════════════════════════════
    _pattern_somme_montant_mois = (
        any(t in q_norm for t in ["somme", "total", "combien"]) and
        any(t in q_norm for t in [
            "montant", "mantant", "monton", "montan", "paie", "paye", "depense", "ttc"
        ]) and
        _extraire_mois_disp(q_norm) is not None
    )

    _detect_somme_montant = any(t in q_norm for t in _TOKENS_SOMME_MONTANT)

    if _detect_somme_montant or _pattern_somme_montant_mois:
        mois_detecte = _extraire_mois_disp(q_norm)
        if mois_detecte:
            # Mois présent → somme générale du mois (comportement inchangé)
            print(f"  [RÈGLE] somme montant mois → fetch_somme_montant_mois(mois={mois_detecte})")
            return _fetch(fetch_somme_montant_mois, mois=mois_detecte)
        elif _a_nom_dans_question:
            # Pas de mois mais nom client détecté → laisser passer vers LLM/fallback
            print(f"  [RÈGLE] somme montant sans mois + nom client détecté → fallback")
            pass  # continue vers la suite du dispatcher
        else:
            # Ni mois ni nom → stats générales (comportement inchangé)
            print(f"  [RÈGLE] somme montant global → fetch_stats_generales")
            return _fetch(fetch_stats_generales, mode="count", question="montant total")

    # ════════════════════════════════════════════
    # LLM FALLBACK
    # ════════════════════════════════════════════
    print(f"  [RAG] Détection intent...")
    resultat = detecter_intent(question)
    intent = resultat.get("intent", "QUESTION_LIBRE")
    params = resultat.get("params", {})
    print(f"  [RAG] Intent : {intent} | Params : {params} | Mode : {mode}")

    if intent == "LISTE_CLIENTS":
        return _fetch(fetch_liste_clients, mode=mode)
    elif intent == "TOP_CONSOMMATEURS":
        n_limit = _extraire_n_limit(q_norm)
        return _fetch(fetch_top_consommateurs, mois=params.get("mois"), mode=mode, limit=n_limit)
    elif intent == "MIN_CONSOMMATEURS":
        n_limit = _extraire_n_limit(q_norm)
        return _fetch(fetch_min_consommateurs, mois=params.get("mois"), mode=mode, limit=n_limit)
    elif intent == "TOP_MONTANTS":
        n_limit = _extraire_n_limit(q_norm)
        return _fetch(fetch_top_montants, mois=params.get("mois"), mode=mode, limit=n_limit)
    elif intent == "MIN_MONTANTS":
        n_limit = _extraire_n_limit(q_norm)
        return _fetch(fetch_min_montants, mois=params.get("mois"), mode=mode, limit=n_limit)
    elif intent == "CLASSEMENT_PAR_MOIS":
        return _fetch(fetch_classement_par_mois, mode=mode)
    elif intent == "AGENCE_PAR_CLIENT":
        return _fetch(fetch_agence_par_client, mode=mode)
    elif intent == "PAR_AGENCE":
        return _fetch(fetch_par_agence, agence=params.get("agence"), mode=mode)
    elif intent == "PAR_USAGE":
        usage_brut = params.get("usage")
        usage_norm = normaliser_usage(usage_brut) if usage_brut else None
        return _fetch(fetch_par_usage, usage=usage_norm, mode=mode)
    elif intent == "PAR_SERVICE":
        return _fetch(fetch_par_service, service=params.get("service"), mode=mode)
    elif intent == "ALERTES":
        return _fetch(fetch_alertes, mode=mode)
    elif intent == "STATS_GENERALES":
        return _fetch(fetch_stats_generales, mode=mode, question=question)
    elif intent == "EVOLUTION_MOIS":
        return _fetch(fetch_evolution_mois, mode=mode)
    elif intent == "TOP_MOIS_CONSO":                          
        ordre = params.get("ordre", "desc")
        limit = params.get("limit", 5)
        return _fetch(fetch_top_mois_conso, ordre=ordre, limit=limit)
    elif intent == "SOMME_CONSO_MOIS":
        mois = params.get("mois", "")
        if not mois:
            return "Veuillez préciser le mois souhaité."
        return _fetch(fetch_somme_conso_mois, mois)
    elif intent == "SOMME_MONTANT_MOIS":
        mois = params.get("mois", "")
        if not mois:
            return _fetch(fetch_stats_generales, mode="count", question="montant total")
        return _fetch(fetch_somme_montant_mois, mois)
    else:
        print(f"  [FALLBACK] Intent non reconnu → Text-to-SQL")
        return repondre_fallback_sql(question, nom_fichier)


# ════════════════════════════════════════════════════════════
# QUESTION CLIENT
# ════════════════════════════════════════════════════════════

def repondre_question_client(question: str, nom_client: str, historique_texte: str, nom_fichier: str = "") -> str:

    # ── PORTAIL 1 : validation concept universel ──
    msg_concept = valider_concept_question(question)
    if msg_concept:
        return msg_concept

    # ── PORTAIL 2 : questions ambiguës ──
    from rag.intent import detecter_question_ambigue
    msg_ambigue = detecter_question_ambigue(question)
    if msg_ambigue:
        return msg_ambigue

    from rag.mode import _normaliser_q
    q = _normaliser_q(question)
    mots = [m for m in q.split() if len(m) > 1]

    if len(mots) == 1:
        mot = mots[0]

        if mot in ["somme", "total"]:
            return (
                f"Vous demandez un total pour **{nom_client}**, "
                f"mais **total de quoi ?**\n\n"
                f"Précisez par exemple :\n"
                f"- *Somme de consommation de {nom_client}*\n"
                f"- *Total montant de {nom_client}*"
            )

        if mot in ["montant", "mantant", "monton"]:
            return (
                f"Vous parlez du montant de **{nom_client}**, "
                f"mais **quel mois ou quel type ?**\n\n"
                f"Précisez par exemple :\n"
                f"- *Montant de {nom_client} en janvier*\n"
                f"- *Montant total de {nom_client}*\n"
                f"- *Mois où {nom_client} a payé le plus*"
            )

        if mot in ["consomme", "conso", "consommation", "consomation", "consome"]:
            return (
                f"Vous parlez de la consommation de **{nom_client}**, "
                f"mais **quel mois ou quel type ?**\n\n"
                f"Précisez par exemple :\n"
                f"- *Consommation de {nom_client} en janvier*\n"
                f"- *Total consommé par {nom_client}*\n"
                f"- *Mois où {nom_client} a le plus consommé*"
            )

    # ── Helper local pour propager nom_fichier ──
    def _fetch_client(fn, **kwargs):
        try:
            return fn(**kwargs, nom_fichier=nom_fichier)
        except TypeError:
            return fn(**kwargs)

    print(f"  [RAG CLIENT] Détection intent pour {nom_client} | Fichier : {nom_fichier or 'tous'}")
    resultat = detecter_intent_client(question)
    intent = resultat.get("intent", "FACTURES_CLIENT")
    params = resultat.get("params", {})
    print(f"  [RAG CLIENT] Intent : {intent} | Params : {params}")

    if intent == "MAX_CONSOMMATION":
        limit = params.get("limit", 1)
        return _fetch_client(fetch_client_max_consommation, nom_client=nom_client, limit=limit)
    elif intent == "MIN_CONSOMMATION":
        limit = params.get("limit", 1) 
        return _fetch_client(fetch_client_min_consommation, nom_client=nom_client,  limit=limit)
    elif intent == "MAX_MONTANT":
        return _fetch_client(fetch_client_max_montant, nom_client=nom_client)
    elif intent == "MIN_MONTANT":
        return _fetch_client(fetch_client_min_montant, nom_client=nom_client)
    elif intent == "EVOLUTION_CLIENT":
        return _fetch_client(fetch_client_evolution, nom_client=nom_client)
    elif intent == "MOYENNE_CLIENT":
        return _fetch_client(fetch_client_moyenne, nom_client=nom_client)
    elif intent == "INFOS_CLIENT":
        champ = params.get("champ")

        CHAMPS_INEXISTANTS = {
            "telephone", "tel", "phone", "mobile", "gsm",
            "email", "mail", "courriel",
            "age", "date naissance", "naissance",
            "photo", "image", "solde", "dette", "credit",
            "note", "commentaire", "code postal",
            "ville", "region", "pays", "rib", "iban",
            "cin", "carte", "identite", "categorie",
            "numero agence", "n agence", "num agence",
            "code agence", "id agence", "code postale","coefficient",
        }

        q_norm_check = _normaliser_q(question)
        champ_inexistant = None
        for c in CHAMPS_INEXISTANTS:
            if re.search(r'\b' + re.escape(c) + r'\b', q_norm_check):
                champ_inexistant = c
                break

        if champ_inexistant:
            return (
                f"⚠️ L'information **« {champ_inexistant} »** "
                f"n'est pas disponible dans notre système "
                f"pour **{nom_client}**.\n\n"
                f"Les informations disponibles sont :\n"
                f"- N° Client, N° Contrat, N° Compteur\n"
                f"- Adresse, Agence, Usage, Type de service"
            )

        return _fetch_client(fetch_client_infos, nom_client=nom_client, champ=champ)
    elif intent == "MOIS_SPECIFIQUE":
        mois = params.get("mois", "")
        champ = params.get("champ")
        return _fetch_client(fetch_client_mois_specifique, nom_client=nom_client, mois=mois, champ=champ)
    elif intent == "SOMME_CONSO_CLIENT":
        return _fetch_client(fetch_client_somme_conso, nom_client=nom_client)
    elif intent == "SOMME_MONTANT_CLIENT":
        return _fetch_client(fetch_client_somme_montant, nom_client=nom_client)
    else:
        return _fetch_client(fetch_client_toutes_factures, nom_client=nom_client)