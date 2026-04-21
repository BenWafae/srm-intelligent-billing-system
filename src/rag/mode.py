# src/rag/mode.py
import unicodedata

_TOKENS_COUNT = {
    "combien", "nombre", "nbr", "nbre", "nb",
    "compter", "comptre", "complez", "comptez", "calculer",  # ✅ virgule ajoutée
    "quantite", "qte", "qt",                                  # ✅ virgule ajoutée
    "effectif", "effectifs",
    "quel est le nombre", "quel est le total",
    "nbr de", "calculer le nbr de",                           # ✅ virgule ajoutée
    "count", "how many",
    "nmbr", "nmbre", "nomb",
    # ✅ Nouveaux patterns courts sans bonne formulation
    "nbr client", "nbr clients",
    "nbr service", "nbr services",
    "nbr usage", "nbr usages",
    "nbr facture", "nbr factures",
    "nbr agence", "nbr agences",
    "nbr alerte", "nbr alertes",
    "nmb client", "nmb service",
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
    "qui consomme", "qui paie", "qui paye", "qui consome",
    "qui consomment",                                         # ✅ virgule ajoutée
    "consommation", "consommations", "consomaatioon",         # ✅ virgule ajoutée
}

_TOKENS_TOP1 = {
    "quel est le client", "quel client", "qui est le client",
    "le client qui", "le client avec",
    "quel est la consommation", "quelle est la consommation",
    "quel est le montant", "quelle est le montant",
    "quel est le plus", "quelle est la plus",
    "qui a la", "qui a le",
    "qui consomme le plus", "qui consomme le moins",
    "qui paie le plus", "qui paie le moins",
    "le plus eleve", "le plus elevee", "la plus elevee",
    "eleve", "elevees",                                       # ✅ virgule ajoutée
    "le plus faible", "la plus faible",
    "le maximum", "le minimum",
}


def _normaliser_q(question: str) -> str:
    q = question.lower().strip()
    q = unicodedata.normalize("NFD", q)
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")
    return q


def detecter_mode_reponse(question: str) -> str:
    q = _normaliser_q(question)

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