# src/rag/intent.py
import requests
import re
import json
import sys
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.mode import _normaliser_q
from normalisation import normaliser_usage


INTENTS_DISPONIBLES = """
LISTE_CLIENTS        : liste des clients, qui existe, combien de clients, tous les clients
TOP_CONSOMMATEURS    : qui consomme le plus, consommation la plus élevée, classement consommation
MIN_CONSOMMATEURS    : qui consomme le moins, consommation faible, consommation minimale, plus faible consommation 
TOP_MONTANTS         : qui paie le plus, montant le plus élevé, facture la plus chère, classement montant
MIN_MONTANTS         : qui paie le moins, montant le plus faible, facture la moins chère
CLASSEMENT_PAR_MOIS  : classer clients par montant ou consommation pour chaque mois, voir classement mois par mois
AGENCE_PAR_CLIENT    : agence de chaque client, quelle agence pour chaque client, agence de tous les clients, lister agence par client
PAR_AGENCE           : clients d'une agence, quelle agence, combien par agence
PAR_USAGE            : usage domestique, force motrice, commercial, administratif, type d'usage, quels usages existent, professionnel, agricole
PAR_SERVICE          : eau, électricité, type de service, combien utilisent eau vs electricite, lister clients eau ou electricite
ALERTES              : alertes, qui a des alertes, factures avec alerte
STATS_GENERALES      : total, moyenne, somme, montant global, statistiques générales
SOMME_MONTANT_MOIS   : somme des montants, total des montants, montant total en janvier, combien a-t-on payé en mars, montant global d'un mois
SOMME_CONSO_MOIS     : somme de consommation en un mois précis, total consommé en janvier, combien a-t-on consommé en mars
EVOLUTION_MOIS       : évolution, progression, mois par mois, historique général, tendance
TOP_MOIS_CONSO       : les N mois les plus consommés, les N mois les moins consommés, top mois consommation
QUESTION_LIBRE       : toute autre question qui ne rentre pas dans les catégories ci-dessus
"""

INTENTS_CLIENT = """
MAX_CONSOMMATION     : mois où le client a le plus consommé, consommation maximale, pic de consommation,les N mois les plus consommés pour ce client
MIN_CONSOMMATION     : mois où le client a le moins consommé, consommation minimale,les N mois les moins consommés pour ce client
SOMME_MONTANT_CLIENT : somme totale des montants du client sur tous les mois, total payé, combien a-t-il payé en tout
MAX_MONTANT          : mois où le client a payé le plus, montant maximum, facture la plus chère
MIN_MONTANT          : mois où le client a payé le moins, montant minimum, facture la moins chère
SOMME_CONSO_CLIENT   : somme totale de consommation du client sur tous les mois, total consommé, combien a-t-il consommé en tout
EVOLUTION_CLIENT     : évolution, progression, tendance, historique du client
MOYENNE_CLIENT       : moyenne, consommation moyenne, montant moyen du client
INFOS_CLIENT         : adresse, numéro client, contrat, compteur, agence, infos générales, usage, type service
MOIS_SPECIFIQUE      : consommation ou montant d'un mois précis, facture de tel mois
FACTURES_CLIENT      : toutes les factures, liste des factures, historique complet, tous les mois
"""

_MAP_MOIS = {
    "jan": "Janvier", "janv": "Janvier", "janvier": "Janvier",
    "fev": "Fevrier", "fevr": "Fevrier", "fevrier": "Fevrier", "feb": "Fevrier",
    "mar": "Mars", "mars": "Mars",
    "avr": "Avril", "avril": "Avril", "apr": "Avril",
    "mai": "Mai", "may": "Mai",
    "jun": "Juin", "juin": "Juin",
    "jul": "Juillet", "juil": "Juillet", "juillet": "Juillet",
    "aou": "Aout", "aout": "Aout", "aug": "Aout",
    "sep": "Septembre", "sept": "Septembre", "septembre": "Septembre",
    "oct": "Octobre", "octobre": "Octobre",
    "nov": "Novembre", "novembre": "Novembre",
    "dec": "Decembre", "decembre": "Decembre",
}

_NOMS_MOIS = list(_MAP_MOIS.keys())
_MOIS_FR_NOMS = [
    "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"
]

# ════════════════════════════════════════════════════════════
# TOKENS (tous inchangés)
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

_TOKENS_SOMME_CLIENT = [
    "somme totale", "somme de consomme", "somme des consomme",
    "somme de conso", "somme des conso", "consomme totale", "consomme total",
    "total consomme", "total de consomme", "total conso", "total de conso",
    "totale consomme", "totale de consomme", "totale conso", "totale de conso",
    "combien a consomme en tout", "combien a-t-il consomme", "combien a consomme",
    "en tout", "cumul", "cumulee", "cumulees",
    "sur tous les mois", "sur l ensemble", "global", "globale",
]


_TOKENS_SOMME_MONTANT_CLIENT = [
    "somme totale montant", "somme totale de montant", "somme totale des montant",
    "somme montant", "somme de montant", "somme des montant",
    "somme mantant", "somme de mantant", "somme monton", "somme montan", "somme mntant",
    "total paye", "total de montant", "total des montant", "total montant",
    "montant total", "montant totale", "montant cumule", "montant global", "montant cumulee",
    "combien a-t-il paye", "combien a-t-elle paye", "combien a paye",
    "combien il a paye", "combien elle a paye", "combien paye",
    "combien a depense", "combien a-t-il depense", "combien a-t-elle depense",
    "montant sur tous les mois", "montant sur l ensemble", "montant en tout",
    "montant cumule sur", "montant total sur", "paye en tout", "depense en tout",
    "total des factures", "somme des factures", "somme totale des factures",
    "mantant total", "mantant global", "monton total", "montan total", "mntant total",
    "mantant cumule", "monton cumule",
]

_TOKENS_SOMME_MONTANT_MOIS = [
    "somme de montant", "somme des montant", "somme du montant", "somme montant",
    "somme de mantant", "somme des mantant", "somme mantant",
    "somme de monton", "somme des monton", "somme monton",
    "somme de montan", "somme des montan", "somme montan",
    "somme de mntant", "somme mntant",
    "total montant", "total de montant", "total des montant", "total du montant",
    "total mantant", "total de mantant", "total monton", "total de monton",
    "total montan", "total de montan", "total mntant",
    "montant total", "montant totale", "montant global", "montant cumule",
    "montants total", "montants totaux", "montants cumules",
    "mantant total", "mantant totale", "mantant global",
    "monton total", "monton totale", "monton global",
    "montan total", "montan global", "mntant total",
    "combien a-t-on paye", "combien ont paye", "combien a paye",
    "combien on paye", "combien depense", "combien a-t-on depense",
]

_TOKENS_MAX_CONSO = [
    "le plus consomme", "consomme le plus", "a le plus consomme",
    "consomme maximale", "consomme la plus elevee", "pic de consomme",
    "mois ou il a le plus consomme", "mois ou elle a le plus consomme",
    "mois ou le client a le plus consomme", "mois ou le client a le plus",
    "mois a le plus consomme", "mois a le plus",
    "quel mois a le plus", "quel mois consomme le plus",
    "mois avec le plus", "mois avec la plus grande",
    "mois maximum", "mois max", "plus consomme",
    "plus elevee", "plus eleve", "la plus haute", "plus haute",
    "le plus grand", "la plus grande",
]


_TOKENS_MIN_CONSO = [
    "le moins consomme", "consomme le moins", "a le moins consomme",
    "consomme minimale", "consomme la plus faible",
    "mois ou il a le moins consomme", "mois ou elle a le moins consomme",
    "mois ou le client a le moins consomme", "mois ou le client a le moins",
    "mois a le moins consomme", "mois a le moins",
    "quel mois a le moins", "quel mois consomme le moins",
    "mois avec le moins", "mois avec la plus faible",
    "mois minimum", "mois min", "moins consomme",
    "plus faible consomme", "moins elevee", "moins eleve",
    "la moins eleve", "la moins elevee",
    "faible consomme", "consomme faible", "consomme basse",
    "la plus basse", "plus basse",
    "a une consomme min", "a une consomme minimale",
    "min consomme", "consomme min", "consomme minimale", "consomme minimum",
    "plus petite consomme",
]


_TOKENS_MAX_MONTANT = [
    "le plus paye", "montant le plus eleve",
    "facture la plus chere", "paie le plus", "paye le plus",
    "montant maximum", "montant maximal", "a le plus paye",
    "mois ou il a le plus paye", "mois ou elle a le plus paye",
    "mois a le plus paye", "quel mois a le plus paye",
    "le plus cher",
]

_TOKENS_MIN_MONTANT = [
    "le moins paye", "moins cher", "montant le plus faible",
    "facture la moins chere", "paie le moins", "paye le moins",
    "montant minimum", "montant minimal", "a le moins paye",
    "mois ou il a le moins paye", "mois ou elle a le moins paye",
    "mois a le moins paye", "quel mois a le moins paye",
]

_TOKENS_USAGE      = ["usage", "type d usage", "type usage", "quel usage",
                      "quel est l usage", "quel est son usage",
                      "montrer les ussages", "usagges", "usaage"]
_TOKENS_ADRESSE    = ["adresse", "ou habite", "ou se trouve", "quelle adresse"]
_TOKENS_AGENCE     = ["agence", "quelle agence", "quel agence",
                      "quelle est son agence", "quel est son agence"]
_TOKENS_SERVICE    = ["type de service", "type service", "quel service", "service de",
                      "quel est le service", "son service", "quel service utulise",
                      "quel est son service", "quel est le service", "quel type de service"]
_TOKENS_CONTRAT    = ["contrat", "numero de contrat", "n contrat", "numero contrat"]
_TOKENS_COMPTEUR   = ["compteur", "numero de compteur", "n compteur", "numero compteur"]
_TOKENS_NUMERO_CLI = ["numero client", "n client", "numero de client", "id client", "nb client"]

print("Tokens définis avec succès.")
print(f"SOMME_MONTANT_MOIS   : {len(_TOKENS_SOMME_MONTANT_MOIS)} tokens")
print(f"SOMME_MONTANT_CLIENT : {len(_TOKENS_SOMME_MONTANT_CLIENT)} tokens")


# ════════════════════════════════════════════════════════════
# NORMALISATION
# ════════════════════════════════════════════════════════════

def _normaliser_verbes(q: str) -> str:
    q = re.sub(r'consom+[a-z]*', 'consomme', q)
    q = re.sub(r'pai+e+[a-z]*', 'paye', q)
    q = re.sub(r'pay[eé]+[a-z]*', 'paye', q)
    return q

def _normaliser_intent_q(question: str) -> str:
    q = _normaliser_q(question)
    q = _normaliser_verbes(q)
    return q

def _contient_mois(q: str) -> bool:
    if any(m in q for m in _NOMS_MOIS):
        return True
    _TOKENS_RELATIFS = [
        "ce mois", "mois actuel", "mois courant", "mois en cours",
        "mois dernier", "le mois dernier", "mois passe", "mois precedent",
        "dernier mois",
    ]
    return any(t in q for t in _TOKENS_RELATIFS)
def _resoudre_mois_relatif(q: str) -> str:
    maintenant = datetime.now()
    _TOKENS_MOIS_ACTUEL = [
        "ce mois", "mois actuel", "mois courant",
        "mois en cours", "mois ci", "mois present",
    ]
    _TOKENS_MOIS_DERNIER = [
        "mois dernier", "le mois dernier", "mois passe",
        "mois precedent", "dernier mois",
    ]
    if any(t in q for t in _TOKENS_MOIS_ACTUEL):
        return _MOIS_FR_NOMS[maintenant.month - 1]
    if any(t in q for t in _TOKENS_MOIS_DERNIER):
        mois_precedent = maintenant - relativedelta(months=1)
        return _MOIS_FR_NOMS[mois_precedent.month - 1]
    return ""

def _extraire_mois(q: str) -> str:
    mois_relatif = _resoudre_mois_relatif(q)
    if mois_relatif:
        return mois_relatif
    tokens_tries = sorted(_MAP_MOIS.keys(), key=len, reverse=True)
    for token in tokens_tries:
        if re.search(r'\b' + re.escape(token) + r'\b', q):
            return _MAP_MOIS[token]
    for token in tokens_tries:
        if token in q:
            return _MAP_MOIS[token]
    return ""

import os

def _appeler_llm(prompt: str) -> str:
    OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"].strip()


# ════════════════════════════════════════════════════════════
# VALIDATION EN 3 COUCHES — protection anti-hallucination LLM
# ════════════════════════════════════════════════════════════

_INTENT_REQUIRED_EVIDENCE = {
    "TOP_CONSOMMATEURS": {
            "au_moins_un":    ["consomme", "conso", "consome", "consomation","consomaation","consoo","consommation",
            "consomateur", "consommateur", 
        "consomatrice", "consommatrice",
],
        "au_moins_un_de": [
        "plus", "eleve", "max", "maximum", "haut", "top","elevee",
        "beaucoup", "bzaf", "enormement", "fort", "grande",
        "grand", "gros", "grosse", "important", "record",
        "premier", "premiere", "meilleur",
    ],
    },
    "MIN_CONSOMMATEURS": {
        "au_moins_un": [
        "consomme", "conso", "consome",        # variantes correctes
        "consomation", "consommation",           # fautes fréquentes  
        "consomateur", "consommateur",          # "grand consomateur"
        "consomatrice", "consommatrice",],
        "au_moins_un_de": [
        "moins", "faible", "min", "minimum", "bas", "petit",
        "peu", "rien", "leger", "legere", "reduit",]
    },
    "TOP_MONTANTS": {
        "au_moins_un":    ["montant", "paye", "paie", "facture", "depense"],
        "au_moins_un_de": ["plus", "eleve", "max", "cher", "haut"],
    },
    "MIN_MONTANTS": {
        "au_moins_un":    ["montant", "paye", "paie", "facture"],
        "au_moins_un_de": ["moins", "faible", "min", "bas", "petit"],
    },
    "SOMME_CONSO_MOIS": {
        "au_moins_un":    ["jan","fev","mar","avr","mai","jun",
                           "jul","aou","sep","oct","nov","dec",
                           "janvier","fevrier","mars","avril","juin",
                           "juillet","aout","septembre","octobre",
                           "novembre","decembre"],
        "au_moins_un_de": ["somme","total","consomme","conso","combien"],
    },
    "SOMME_MONTANT_MOIS": {
        "au_moins_un":    ["jan","fev","mar","avr","mai","jun",
                           "jul","aou","sep","oct","nov","dec",
                           "janvier","fevrier","mars","avril","juin",
                           "juillet","aout","septembre","octobre",
                           "novembre","decembre"],
        "au_moins_un_de": ["montant","somme","total","paye","mantant","depense"],
    },
    "PAR_AGENCE": {
        "au_moins_un": ["agence"],
    },
    "PAR_SERVICE": {
        "au_moins_un": ["eau", "elec", "electricit", "service"],
    },
    "PAR_USAGE": {
        "au_moins_un": ["usage", "domestique", "professionnel", "agricole", "pro", "dom"],
    },
    "ALERTES": {
        "au_moins_un": ["alerte", "alertes"],
    },
    "STATS_GENERALES": {
        "aucun_de": ["par agence", "par service", "par usage",
                     "par mois", "chaque", "agence", "service",
                     "usage", "eau", "elec"],
    },
    "EVOLUTION_MOIS": {
        "au_moins_un": ["evolution", "mois", "progression",
                        "historique", "tendance", "periode"],
    },
}


def _valider_params(intent: str, params: dict, q_norm: str) -> dict:
    params_propres = dict(params)

    if "mois" in params_propres:
        mois_brut = params_propres.get("mois", "")
        mois_depuis_q = _extraire_mois(q_norm)
        if mois_depuis_q:
            params_propres["mois"] = mois_depuis_q
            if mois_brut != mois_depuis_q:
                print(f"  [PARAMS] mois corrigé : '{mois_brut}' → '{mois_depuis_q}'")
        else:
            print(f"  [PARAMS] mois '{mois_brut}' non trouvé dans la question → supprimé")
            params_propres.pop("mois", None)

    if "agence" in params_propres:
        agence_val = str(params_propres.get("agence", ""))
        if agence_val.strip().isdigit() or len(agence_val.strip()) < 3:
            print(f"  [PARAMS] agence invalide rejetée : '{agence_val}'")
            params_propres.pop("agence", None)

    if "usage" in params_propres:
        usage_brut = params_propres.get("usage", "")
        usage_norm = normaliser_usage(usage_brut) if usage_brut else None
        if usage_norm:
            params_propres["usage"] = usage_norm
        else:
            print(f"  [PARAMS] usage '{usage_brut}' non normalisable → supprimé")
            params_propres.pop("usage", None)

    return params_propres


def _valider_coherence(intent: str, params: dict) -> bool:
    intents_mois_obligatoire = ["SOMME_CONSO_MOIS", "SOMME_MONTANT_MOIS"]
    if intent in intents_mois_obligatoire:
        if not params.get("mois"):
            print(f"  [COHERENCE] {intent} sans mois dans params → rejeté")
            return False
    return True


def valider_intent_complet(intent: str, params: dict, q_norm: str) -> tuple:
    """Retourne (intent_validé, params_validés) ou ('QUESTION_LIBRE', {})"""
    regles = _INTENT_REQUIRED_EVIDENCE.get(intent)
    if regles:
        if "au_moins_un" in regles:
            if not any(t in q_norm for t in regles["au_moins_un"]):
                print(f"  [V1] {intent} rejeté — token obligatoire absent")
                return "QUESTION_LIBRE", {}
        if "au_moins_un_de" in regles:
            if not any(t in q_norm for t in regles["au_moins_un_de"]):
                print(f"  [V1] {intent} rejeté — contexte absent")
                return "QUESTION_LIBRE", {}
        if "aucun_de" in regles:
            if any(t in q_norm for t in regles["aucun_de"]):
                print(f"  [V1] {intent} rejeté — token poison présent")
                return "QUESTION_LIBRE", {}

    params_propres = _valider_params(intent, params, q_norm)

    if not _valider_coherence(intent, params_propres):
        return "QUESTION_LIBRE", {}

    return intent, params_propres
# ════════════════════════════════════════════════════════════
# DÉTECTION QUESTIONS AMBIGUËS
# Appelée en PREMIER dans dispatcher.py avant toute règle
# Retourne un message de clarification ou None
# ════════════════════════════════════════════════════════════
# si par exemple user pose question ambigue comme somme et il n a ps preciser somme de quoi et dans quel mois faut qu il recoit comme reponse msg de demande clarrificattion

# Mots qui seuls sont trop vagues pour traiter
_MOTS_SEULS_VAGUES = {
    "somme", "total", "liste", "montant", "consomme", "conso",
    "agence", "client", "alerte", "evolution", "service", "usage",
    "facture", "factures", "eau", "elec", "electricite"
}
 
def detecter_question_ambigue(question: str):
    q = _normaliser_q(question)
    q = _normaliser_verbes(q)
    mots = [m for m in q.split() if len(m) > 1]

    # ── Variables globales (utilisées dans tous les cas) ─────────────
    _demande_somme   = any(t in q for t in ["somme", "total", "combien"])
    _demande_conso   = any(t in q for t in [
        "consomme", "conso", "consommation", "consomation", "consome"
    ])
    _demande_montant = any(t in q for t in [
        "montant", "mantant", "monton", "paye", "paie", "depense"
    ])
    _a_mois   = bool(_extraire_mois(q))
    _a_client = any(t in q for t in ["client", "clients"])
    _a_nom    = any(len(m) >= 4 and m[0].isupper() for m in question.split())

    # ── NOUVEAU : détecter un nom propre même après normalisation (minuscules) ──
    _MOTS_CLES_CONNUS = {
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
        "dhs", "kwh", "m3", "statistique", "stat", "moyen", "moyenne",
        "moi", "me", "mon", "ma", "mes", "lui", "leur", "leurs",
        "donner", "donne", "donnez", "montrer", "montrez", "montrons",
        "afficher", "affichez", "voir", "lister", "listez",
        "quel", "quelle", "quels", "quelles", "combien", "comment",
        "somme", "total", "cumul", "cumulee", "cumules",
        "tous", "toutes", "chaque", "ensemble", "global", "generale",
        "max", "min", "plus", "moins", "eleve", "faible", "haut", "bas",
        "top", "grand", "grande", "petit", "petite", "fort", "forte",
        "eau", "elec", "electricite", "electricit", "electr",
        "usage", "usages", "domestique", "professionnel", "agricole",
        "pro", "dom", "agri",
        "type", "types", "service", "services",
        "agence", "agences", "inezgane", "taroudant", "tiznit",
        "alerte", "alertes", "facture", "factures",
        "periode", "periodes", "date", "limite", "paiement",
        "numero", "contrat", "compteur", "adresse",
        "evolution", "progression", "historique", "tendance",
        "classement", "classements", "rang", "ranking",
        "statistique", "statistiques", "stats",
        "information", "informations", "infos", "fiche", "profil",
    }
    _mots_inconnus = [
        m for m in q.split()
        if len(m) >= 3 and m not in _MOTS_CLES_CONNUS
    ]
    # Un nom client est détecté si : majuscule dans la question originale
    # OU mot(s) inconnu(s) des mots-clés présents après normalisation
    _a_nom_client = _a_nom or len(_mots_inconnus) >= 1

    _detect_classement = any(t in q for t in [
        "grand", "grande", "gros", "grosse",
        "plus", "max", "eleve", "elevee", "top", "fort", "importante",
        "moins", "faible", "petit", "min"
    ])
    _verbes_action = [
        "donne moi", "donnez moi", "montrer moi", "afficher",
        "donner", "montrer", "voir", "quel est le", "quelle est la"
    ]
    _a_verbe_action = any(t in q for t in _verbes_action)

    # ════════════════════════════════════════════════════════
    # CAS 1 — mot seul trop vague
    # ════════════════════════════════════════════════════════
    if len(mots) == 1 and mots[0] in _MOTS_SEULS_VAGUES:
        mot = mots[0]

        if mot == "liste":
            return (
                "Vous voulez une liste, mais **liste de quoi ?**\n\n"
                "Je peux vous lister :\n"
                "- *Liste des clients*\n"
                "- *Liste des agences*\n"
                "- *Liste des alertes*\n"
                "- *Liste des clients par service (eau / électricité)*"
            )
        if mot == "somme":
            return (
                "Vous demandez une somme, mais **somme de quoi ?**\n\n"
                "Précisez par exemple :\n"
                "- *Somme de consommation en janvier*\n"
                "- *Somme des montants en mars*"
            )
        if mot == "total":
            return (
                "Vous demandez un total, mais **total de quoi ?**\n\n"
                "Précisez par exemple :\n"
                "- *Total consommation en janvier*\n"
                "- *Total montant en mars*\n"
                "- *Statistiques générales* (pour tout voir)"
            )
        if mot in ["montant", "mantant", "monton"]:
            return (
                "Vous demandez un montant, mais **montant de qui ou de quel mois ?**\n\n"
                "Précisez par exemple :\n"
                "- *Montant total en janvier*\n"
                "- *Quel client a le montant le plus élevé ?*\n"
                "- *Montant de Fatima*"
            )
        if mot in ["consomme", "conso", "consommation"]:
            return (
                "Vous parlez de consommation, mais **consommation de qui ou de quel mois ?**\n\n"
                "Précisez par exemple :\n"
                "- *Qui consomme le plus ?*\n"
                "- *Total consommation en janvier*\n"
                "- *Consommation de Fatima*"
            )
        if mot == "agence":
            return (
                "Vous parlez d'agence, mais **quelle information sur les agences ?**\n\n"
                "Précisez par exemple :\n"
                "- *Liste des agences*\n"
                "- *Clients de l'agence Agadir*\n"
                "- *Agence de chaque client*"
            )
        if mot in ["client", "clients"]:
            return (
                "Vous parlez de clients, mais **quelle information sur les clients ?**\n\n"
                "Précisez par exemple :\n"
                "- *Liste des clients*\n"
                "- *Combien de clients ?*\n"
                "- *Clients de l'agence Agadir*"
            )
        if mot in ["alerte", "alertes"]:
            return (
                "Vous parlez d'alertes, mais **quelle information sur les alertes ?**\n\n"
                "Précisez par exemple :\n"
                "- *Qui a des alertes ?*\n"
                "- *Combien de clients ont une alerte ?*\n"
                "- *Liste des alertes*"
            )
        if mot == "evolution":
            return (
                "Vous parlez d'évolution, mais **évolution de quoi ?**\n\n"
                "Précisez par exemple :\n"
                "- *Évolution des consommations mois par mois*\n"
                "- *Évolution des montants*"
            )
        if mot in ["usage", "usages"]:
            return (
                "Vous parlez d'usage, mais **quelle information sur les usages ?**\n\n"
                "Précisez par exemple :\n"
                "- *Clients usage domestique*\n"
                "- *Clients usage professionnel*\n"
                "- *Clients usage agricole*"
            )
        if mot in ["service", "services"]:
            return (
                "Vous parlez de service, mais **quel service vous intéresse ?**\n\n"
                "Précisez par exemple :\n"
                "- *Clients qui utilisent l'eau*\n"
                "- *Clients qui utilisent l'électricité*\n"
                "- *Combien de clients par service ?*"
            )
        if mot in ["eau", "elec", "electricite"]:
            return (
                "Vous parlez du service **eau/électricité**, "
                "mais **quelle information souhaitez-vous ?**\n\n"
                "Précisez par exemple :\n"
                "- *Clients qui utilisent l'eau*\n"
                "- *Combien de clients électricité ?*\n"
                "- *Consommation eau en janvier*"
            )
        if mot in ["facture", "factures"]:
            return (
                "Vous parlez de factures, mais **factures de qui ou de quel mois ?**\n\n"
                "Précisez par exemple :\n"
                "- *Toutes les factures de Fatima*\n"
                "- *Facture de janvier*\n"
                "- *Combien de factures ?*"
            )
        # Mot seul générique
        return (
            f"La question « **{question}** » est trop courte.\n\n"
            "Pouvez-vous préciser ce que vous cherchez ?\n"
            "Par exemple :\n"
            "- *Qui consomme le plus ?*\n"
            "- *Liste des clients*\n"
            "- *Montant total en janvier*"
        )

    # ════════════════════════════════════════════════════════
    # CAS 2b — combo "somme total" / "total somme" / "total global"
    # sans aucun sujet ni mois → trop vague
    # ════════════════════════════════════════════════════════
    _combos_doublement_vagues = [
        lambda: "somme" in q and "total" in q,
        lambda: ("total" in q or "somme" in q) and "global" in q,
    ]
    _a_sujet_reel = _demande_conso or _demande_montant or _a_mois or _a_client or _a_nom

    if not _a_sujet_reel and not _detect_classement:
        for test in _combos_doublement_vagues:
            if test():
                return (
                    "Vous demandez un total ou une somme, mais **de quoi ?**\n\n"
                    "Précisez par exemple :\n"
                    "- *Total consommation en janvier*\n"
                    "- *Somme des montants en mars*\n"
                    "- *Statistiques générales* (pour tout voir)"
                )

    # ════════════════════════════════════════════════════════
    # CAS 2 — sujet présent mais mois manquant
    # "somme conso" / "total montant" sans mois ni client ni nom
    # ════════════════════════════════════════════════════════
    if (_demande_somme and _demande_conso
            and not _a_mois and not _a_client and not _a_nom_client  # ← _a_nom_client
            and not _detect_classement):
        return (
            "Vous demandez une somme de consommation, "
            "mais **pour quel mois ?**\n\n"
            "Précisez par exemple :\n"
            "- *Somme de consommation en janvier*\n"
            "- *Total consommé en mars 2026*"
        )

    if (_demande_somme and _demande_montant
            and not _a_mois and not _a_client and not _a_nom_client  # ← _a_nom_client
            and not _detect_classement):
        return (
            "Vous demandez une somme de montants, "
            "mais **pour quel mois ?**\n\n"
            "Précisez par exemple :\n"
            "- *Total montant en janvier*\n"
            "- *Combien a-t-on payé en mars ?*"
        )

    # ════════════════════════════════════════════════════════
    # CAS 3 — verbe d'action + montant/somme sans contexte suffisant
    # ════════════════════════════════════════════════════════

    # Sous-cas 3a : verbe + montant seul (sans mois, sans client, sans nom, sans classement)
    if (_a_verbe_action
            and _demande_montant
            and not _demande_conso
            and not _a_mois
            and not _a_client
            and not _a_nom_client  # ← _a_nom_client
            and not _detect_classement):
        return (
            "Vous demandez un montant, mais **montant de qui ou de quel mois ?**\n\n"
            "Précisez par exemple :\n"
            "- *Montant total en janvier*\n"
            "- *Quel client a le montant le plus élevé ?*\n"
            "- *Montant de Fatima*"
        )

    # Sous-cas 3b : verbe + somme/total seul (sans mois, sans nom, sans classement)
    _demande_total_somme = any(t in q for t in ["total", "somme"])
    if (_a_verbe_action
            and _demande_total_somme
            and not _demande_conso
            and not _demande_montant
            and not _a_mois
            and not _a_client
            and not _a_nom_client  # ← _a_nom_client
            and not _detect_classement):
        return (
            "Vous demandez un total ou une somme, "
            "mais **de quoi et pour quel mois ?**\n\n"
            "Précisez par exemple :\n"
            "- *Total consommation en janvier*\n"
            "- *Somme des montants en mars*\n"
            "- *Statistiques générales* (pour tout voir)"
        )

    # Sous-cas 3c : verbe sans aucun sujet reconnaissable
    _a_sujet_clair = any(t in q for t in [
        "client", "clients", "agence", "agences", "alerte", "alertes",
        "consomme", "consome", "conso", "consommation", "consomation",
        "montant", "mantant", "facture", "factures",
        "service", "usage", "evolution",
        "classement", "liste", "statistique", "stat", "stats",
        "eau", "elec", "electricite",
         "infos", "information", "informations", "fiche", "profil","info"
         "adresse", "adress", "contrat", "compteur", "numero",
         "agence", "usage", "type", "service"
    ])
    if (_a_verbe_action
            and not _a_sujet_clair
            and not _demande_total_somme
            and not _demande_montant):
        return (
            "Je n'ai pas compris **ce que vous souhaitez voir**.\n\n"
            "Pouvez-vous préciser ? Par exemple :\n"
            "- *Donne moi la liste des clients*\n"
            "- *Montre moi les alertes*\n"
            "- *Quel est le montant total en janvier ?*\n"
            "- *Afficher les clients par agence*"
        )

    return None  # question assez précise → continuer normalement
# ════════════════════════════════════════════════════════════
# DÉTECTION INTENT GÉNÉRAL
# ════════════════════════════════════════════════════════════

def detecter_intent(question: str) -> dict:
    q = _normaliser_q(question)

    # ── RÈGLE 1 : AGENCE_PAR_CLIENT ──
    if any(t in q for t in _TOKENS_AGENCE_PAR_CLIENT):
        print(f"  [RÈGLE INTENT] AGENCE_PAR_CLIENT détecté sans LLM")
        return {"intent": "AGENCE_PAR_CLIENT", "params": {}}

    # ── RÈGLE 2 : TOP_MONTANTS ──
    _tokens_top_montants = [
        "montant le plus eleve", "montant le plus haut", "montant maximum",
        "montant max", "facture la plus chere", "paie le plus", "paye le plus",
        "qui paie le plus", "qui paye le plus", "montant eleve",
        "client le plus cher", "client qui paie le plus",
    ]
    if any(t in q for t in _tokens_top_montants):
        mois = _extraire_mois(q)
        return {"intent": "TOP_MONTANTS", "params": {"mois": mois} if mois else {}}

    # ── RÈGLE 3 : MIN_MONTANTS ──
    _tokens_min_montants = [
        "montant le plus faible", "montant le plus bas", "montant minimum",
        "montant min", "facture la moins chere", "paie le moins", "paye le moins",
        "qui paie le moins", "qui paye le moins", "montant faible",
        "client le moins cher", "client qui paie le moins",
    ]
    if any(t in q for t in _tokens_min_montants):
        mois = _extraire_mois(q)
        return {"intent": "MIN_MONTANTS", "params": {"mois": mois} if mois else {}}

    # ── RÈGLE 4 : TOP_CONSOMMATEURS ──
    _tokens_top_conso = [
        "consomme le plus", "consommation la plus elevee", "consommation elevee",
        "consommation maximum", "consommation max", "plus grand consommateur",
        "qui consomme le plus",
    ]
    if any(t in q for t in _tokens_top_conso):
        mois = _extraire_mois(q)
        return {"intent": "TOP_CONSOMMATEURS", "params": {"mois": mois} if mois else {}}

    # ── RÈGLE 5 : MIN_CONSOMMATEURS ──
    _tokens_min_conso = [
        "consomme le moins", "consommation la plus faible", "consommation faible",
        "consommation minimum", "consommation min", "plus petit consommateur",
        "qui consomme le moins",
    ]
    if any(t in q for t in _tokens_min_conso):
        mois = _extraire_mois(q)
        return {"intent": "MIN_CONSOMMATEURS", "params": {"mois": mois} if mois else {}}
    # ── RÈGLE : TOP_MOIS_CONSO général ──
    _TOKENS_TOP_MOIS_GENERAL = [
        "les mois les plus consomme", "les mois les moins consomme",
        "mois les plus consomme", "mois les moins consomme",
        "top mois consomme", "mois avec le plus de consomme",
        "mois avec le moins de consomme", "mois les plus eleve",
        "mois les plus faible", "les mois plus consomme",
        "les mois moins consomme", "mois qui a le plus consomme",
        "mois qui a le moins consomme",
    ]
    if any(t in q for t in _TOKENS_TOP_MOIS_GENERAL):
        _est_min = any(t in q for t in [
            "moins", "faible", "min", "minimum", "petit", "bas"
        ])
        _n = None
        _match_n = re.search(r'\b(\d+)\b', q)
        if _match_n:
            n = int(_match_n.group(1))
            if 1 <= n <= 24:
                _n = n
        _LETTRES_N = {
            "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
            "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
        }
        for mot, val in _LETTRES_N.items():
            if re.search(r'\b' + mot + r'\b', q):
                _n = val
                break
        return {
            "intent": "TOP_MOIS_CONSO",
            "params": {
                "ordre": "asc" if _est_min else "desc",
                "limit": _n if _n else 5
            }
        }
    # ── Fallback LLM ──
    prompt = f"""Tu es un classificateur de questions. Tu dois identifier l'intent de la question posée.

Voici les intents disponibles :
{INTENTS_DISPONIBLES}

Question : {question}

Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre, sans explication, sans markdown.
Format exact :
{{"intent": "NOM_INTENT", "params": {{}}}}

Si la question mentionne un mois précis, ajoute : {{"mois": "Octobre 2025"}}
Si la question mentionne une agence précise, ajoute : {{"agence": "Agadir Nord"}}
Si la question mentionne un usage précis, retourne UNIQUEMENT le mot brut tel qu'écrit dans la question, ex: {{"usage": "pro"}}
Si la question mentionne un service précis (eau ou electricite), ajoute : {{"service": "eau"}} ou {{"service": "electricite"}}

JSON :"""

    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intent_llm = result.get("intent", "QUESTION_LIBRE")
            params_llm = result.get("params", {})
            q_norm_val = _normaliser_q(question)

            # Whitelist des intents reconnus
            _intents_valides = [
                "LISTE_CLIENTS", "TOP_CONSOMMATEURS", "MIN_CONSOMMATEURS",
                "TOP_MONTANTS", "MIN_MONTANTS", "CLASSEMENT_PAR_MOIS",
                "AGENCE_PAR_CLIENT", "PAR_AGENCE", "PAR_USAGE", "PAR_SERVICE",
                "ALERTES", "STATS_GENERALES", "SOMME_MONTANT_MOIS",
                "SOMME_CONSO_MOIS", "EVOLUTION_MOIS","TOP_MOIS_CONSO", "QUESTION_LIBRE"
            ]
            if intent_llm not in _intents_valides:
                print(f"  [VALIDATION] Intent inconnu {intent_llm} → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}

            # ── Validation en 3 couches ──
            intent_final, params_final = valider_intent_complet(
                intent_llm, params_llm, q_norm_val
            )
            return {"intent": intent_final, "params": params_final}

        except Exception as e:
            print(f"  [INTENT] Erreur parsing JSON : {e}")
            pass

    return {"intent": "QUESTION_LIBRE", "params": {}}


# ════════════════════════════════════════════════════════════
# DÉTECTION INTENT CLIENT  
# ════════════════════════════════════════════════════════════
def detecter_intent_client(question: str) -> dict:
    q = _normaliser_intent_q(question)

    _mots_conso_montant = ["consomme", "conso", "montant", "facture", "combien", "paye"]
    _TOKENS_CHAMP_DATE    = ["date", "limite", "echeance", "date limite", "date paiement", "date limit"]
    _TOKENS_CHAMP_MONTANT = ["montant", "paye", "ttc", "dhs", "prix", "cout", "paie"]
    _TOKENS_CHAMP_CONSO   = ["consomme", "conso", "kwh", "m3"]

    if _contient_mois(q) and any(t in q for t in _mots_conso_montant):
        _tokens_tous = ["tous les mois", "chaque mois", "sur tous", "l ensemble"]
        if not any(t in q for t in _tokens_tous):
            mois_extrait = _extraire_mois(q)
            champ = None
            if any(t in q for t in _TOKENS_CHAMP_DATE):
                champ = "date_limite"
            elif any(t in q for t in _TOKENS_CHAMP_MONTANT) and not any(t in q for t in _TOKENS_CHAMP_CONSO):
                champ = "montant"
            elif any(t in q for t in _TOKENS_CHAMP_CONSO) and not any(t in q for t in _TOKENS_CHAMP_MONTANT):
                champ = "consommation"
            print(f"  [PRÉ-DÉTECTION CLIENT] MOIS_SPECIFIQUE → mois='{mois_extrait}' champ='{champ}'")
            return {"intent": "MOIS_SPECIFIQUE", "params": {"mois": mois_extrait, "champ": champ}}

    if any(t in q for t in _TOKENS_USAGE):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "usage"}}
    if any(t in q for t in _TOKENS_ADRESSE):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "adresse"}}
    if any(t in q for t in _TOKENS_AGENCE):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "agence"}}
    if any(t in q for t in _TOKENS_SERVICE):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "service"}}
    if any(t in q for t in _TOKENS_CONTRAT):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "contrat"}}
    if any(t in q for t in _TOKENS_COMPTEUR):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "compteur"}}
    if any(t in q for t in _TOKENS_NUMERO_CLI):
        return {"intent": "INFOS_CLIENT", "params": {"champ": "numero_client"}}

    for token in _TOKENS_SOMME_MONTANT_CLIENT:
        if token in q:
            return {"intent": "SOMME_MONTANT_CLIENT", "params": {}}

    for token in _TOKENS_SOMME_CLIENT:
        if token in q:
            return {"intent": "SOMME_CONSO_CLIENT", "params": {}}

    # ── Détection top N mois pour client ──
    _TOKENS_TOP_MOIS_CLIENT = [
        "les mois les plus consomme", "les mois les moins consomme",
        "mois les plus consomme", "mois les moins consomme",
        "top mois", "mois avec le plus", "mois avec le moins",
        "mois les plus eleve", "mois les plus faible",
        "les mois plus consomme", "les mois moins consomme",
        "mois ou il a le plus consomme", "mois ou elle a le plus consomme",
        "mois ou il a le moins consomme", "mois ou elle a le moins consomme",
    ]
    _est_top_mois_client = any(t in q for t in _TOKENS_TOP_MOIS_CLIENT)

    # Détection N dans la question
    _n_mois = None
    _match_n = re.search(r'\b(\d+)\b', q)
    if _match_n:
        n = int(_match_n.group(1))
        if 1 <= n <= 24:
            _n_mois = n
    _LETTRES_N = {
        "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
        "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    }
    for mot, val in _LETTRES_N.items():
        if re.search(r'\b' + mot + r'\b', q):
            _n_mois = val
            break

    if _est_top_mois_client:
        _est_min = any(t in q for t in [
            "moins", "faible", "min", "minimum", "petit", "bas"
        ])
        intent_top = "MIN_CONSOMMATION" if _est_min else "MAX_CONSOMMATION"
        limit_top = _n_mois if _n_mois else 5
        print(f"  [PRÉ-DÉTECTION CLIENT] {intent_top} top mois → limit={limit_top}")
        return {"intent": intent_top, "params": {"limit": limit_top}}

    for token in _TOKENS_MAX_CONSO:
        if token in q:
            return {"intent": "MAX_CONSOMMATION", "params": {"limit": 1}}

    for token in _TOKENS_MIN_CONSO:
        if token in q:
            return {"intent": "MIN_CONSOMMATION", "params": {"limit": 1}}

    for token in _TOKENS_MAX_MONTANT:
        if token in q:
            return {"intent": "MAX_MONTANT", "params": {}}

    for token in _TOKENS_MIN_MONTANT:
        if token in q:
            return {"intent": "MIN_MONTANT", "params": {}}

    _tokens_all = [
        "tous les mois", "toutes les factures", "historique",
        "historique complet", "evolution", "l ensemble", "l'ensemble", "chaque mois",
    ]
    for token in _tokens_all:
        if token in q:
            return {"intent": "FACTURES_CLIENT", "params": {}}

    if any(t in q for t in ["moyenne", "moyen", "moy"]):
        return {"intent": "MOYENNE_CLIENT", "params": {}}

    if any(t in q for t in ["infos", "informations", "fiche", "profil", "tout sur"]):
        return {"intent": "INFOS_CLIENT", "params": {}}

    # ── LLM fallback client ──
    prompt = f"""Tu es un classificateur de questions sur un client.

Voici les intents disponibles :
{INTENTS_CLIENT}

RÈGLES :
- SOMME ou TOTAL sur tous les mois → SOMME_CONSO_CLIENT
- "tous les mois", "historique" → FACTURES_CLIENT
- UN mois précis → MOIS_SPECIFIQUE avec le mois dans params
- mois avec conso MAX → MAX_CONSOMMATION
- mois avec conso MIN → MIN_CONSOMMATION
- usage, adresse, agence, service, contrat → INFOS_CLIENT
- "les N mois les plus consommés" → MAX_CONSOMMATION avec limit dans params
- "les N mois les moins consommés" → MIN_CONSOMMATION avec limit dans params

Question : {question}

JSON uniquement :
{{"intent": "NOM_INTENT", "params": {{}}}}
Si mois précis ajoute : {{"mois": "Mars"}}
Si N mois demandés ajoute : {{"limit": N}}
"""
    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intents_valides = [
                "MAX_CONSOMMATION", "MIN_CONSOMMATION",
                "MAX_MONTANT", "MIN_MONTANT",
                "SOMME_CONSO_CLIENT", "SOMME_MONTANT_CLIENT", "EVOLUTION_CLIENT",
                "MOYENNE_CLIENT", "INFOS_CLIENT",
                "MOIS_SPECIFIQUE", "FACTURES_CLIENT"
            ]
            if result.get("intent") in intents_valides:
                return result
        except Exception as e:
            print(f"  [INTENT CLIENT] Erreur parsing JSON : {e}")
            pass

    return {"intent": "FACTURES_CLIENT", "params": {}}