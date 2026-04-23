# src/rag/mode.py
import unicodedata
import re

_TOKENS_COUNT = {
    "combien", "nombre", "nbr", "nbre", "nb",
    "compter", "comptre", "complez", "comptez", "calculer",
    "quantite", "qte", "qt",
    "effectif", "effectifs",
    "quel est le nombre", "quel est le total",
    "nbr de", "calculer le nbr de",
    "count", "how many",
    "nmbr", "nmbre", "nomb",
    # patterns courts sans bonne formulation
    "nbr client", "nbr clients",
    "nbr service", "nbr services",
    "nbr usage", "nbr usages",
    "nbr facture", "nbr factures",
    "nbr agence", "nbr agences",
    "nbr alerte", "nbr alertes",
    "nmb client", "nmb service",
    "nbr d alert","nbr alert","nombre alerte"," nbr alerts"
    # ── ALERTES — toutes variantes COUNT ──────────────────────
    "combien d alerte", "combien d alertes",
    "combien d alert","combien d alerts"
    "combien alertes", "combien alerte",
    "nombre d alerte", "nombre d alertes",
    "nombre alertes", "nombre alerte",
    "nbre alerte", "nbre alertes",
    "nb alerte", "nb alertes",
    "nbr alerte", "nbr alertes",           # déjà présent mais on garde pour clarté
    "quel est le nombre d alerte",
    "quel est le nombre d alertes",
    "donner moi le nombre d alerte",
    "donner moi le nombre d alertes",
    "montrer moi le nombre d alerte",
    "montrer moi le nombre d alertes",
    "montrer moi nbr alerte",
    "montrer moi nbr alertes",
    "afficher le nombre d alerte",
    "afficher le nombre d alertes",
    "total alerte", "total alertes",
    "il y a combien", "ya combien",
    "c est quoi le nombre", "quel chiffre",
}

_TOKENS_LIST = {
    "liste", "lister", "listez", "listons",
    "afficher", "affichez", "affiche",
    "montrer", "montrez", "montre",
    "donner", "donnez", "donne",
    "voir", "voyez",
    "enumerer", "enumerez",
    "citer", "citez",
    "rappeler",
    "quels sont", "quelles sont",
    "qui sont", "qui existe", "qui existent",
    "lesquels", "lesquelles",
    "tous les clients",
    "toutes les factures",
    "l ensemble", "l'ensemble",
    "list", "show", "display", "get all",
    "give me",
    # ── ALERTES — toutes variantes LIST ───────────────────────
    "lister les alertes", "liste des alertes",
    "lister alert","montrer moi les alerts"
    "afficher les alertes", "montrer les alertes",
    "voir les alertes", "donner les alertes",
    "montrer moi les alertes", "montrer moi alerte",
    "afficher moi les alertes", "afficher moi alerte",
    "donner moi les alertes", "donner moi alerte",
    "quelles sont les alertes", "quels sont les alertes",
    "clients avec alerte", "clients ayant alerte",
    "clients en alerte", "factures avec alerte",
    "factures en alerte", "qui a des alertes",
    "qui a une alerte", "qui sont en alerte",
    "afficher alertt","afficher alert","montrer alert"
}

_TOKENS_DETAIL_FORCE = {
    "moyenne", "moyen", "moy",
    "max", "maximum", "plus eleve", "plus haut",
    "min", "minimum", "plus faible", "plus bas",
    "somme", "sum", "total ttc", "montant total",
    "top", "classement", "classer", "rang", "ranking",
    "evolution", "tendance", "progression",
    "statistique", "stat", "stats", "bilan", "resume",
    "detail", "details",
    "comparer", "comparaison", "versus", "vs",
    "historique", "historiq",
    "analyse", "analyser",
    "repartition",
    "consommations", "consomaatioon",
}

_TOKENS_TOP1 = {
    # ── Formulations exactes ou proches ──
    "quel est le client", "quel client", "qui est le client",
    "le client qui", "le client avec",
    "quel est la consommation", "quelle est la consommation",
    "quel est le montant", "quelle est le montant",
    "quel est le plus", "quelle est la plus",
    "qui a la", "qui a le",
    # ── "qui consomme/consome le plus/moins" — toutes variantes ──
    "qui consomme le plus", "qui consomme le moins",
    "qui consome le plus",  "qui consome le moins",
    "qui consomme plus",    "qui consomme moins",
    "qui consome plus",     "qui consome moins",
    # ── "qui paie/paye le plus/moins" ──
    "qui paie le plus",  "qui paie le moins",
    "qui paye le plus",  "qui paye le moins",
    # ── superlatifs ──
    "le plus eleve", "le plus elevee", "la plus elevee",
    "eleve", "elevees",
    "le plus faible", "la plus faible",
    "le maximum", "le minimum",
    # ── "client le plus consomé/consome..." ──
    "client le plus",
    "client la plus",
    # ── "quel client a une consomation..." ──
    "a une consomation", "a une consommation",
    "avec la consomation", "avec la consommation",
    # ── variantes orthographiques "consomé/consome/consomation" ──
    "consomation eleve",  "consomation elevee",
    "consomation faible", "consomation basse",
    "consomation max",    "consomation min",
    "consome le plus",    "consome le moins",
    "consome eleve",      "consome elevee",
    "consome faible",
}


def _normaliser_q(question: str) -> str:
    q = question.lower().strip()
    q = unicodedata.normalize("NFD", q)
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")
    return q


def detecter_mode_reponse(question: str) -> str:
    q = _normaliser_q(question)

    # ── Normalisation légère des verbes pour la détection de mode ──
    q = re.sub(r'consom+[a-z]*', 'consomme', q)
    q = re.sub(r'pai+e+[a-z]*', 'paye', q)
    q = re.sub(r'pay[eé]+[a-z]*', 'paye', q)

    for token in _TOKENS_TOP1:
        if token in q:
            return "top1"

    for token in _TOKENS_DETAIL_FORCE:
        if token in q:
            return "detail"

    for token in _TOKENS_COUNT:
        if token in q:
            return "count"

    for token in _TOKENS_LIST:
        if token in q:
            return "list"

    return "detail"