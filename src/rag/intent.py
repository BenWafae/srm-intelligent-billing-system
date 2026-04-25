# src/rag/intent.py
import requests
import re
import json
import sys
import os
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
QUESTION_LIBRE       : toute autre question qui ne rentre pas dans les catégories ci-dessus
"""

INTENTS_CLIENT = """
MAX_CONSOMMATION     : mois où le client a le plus consommé, consommation maximale, pic de consommation
MIN_CONSOMMATION     : mois où le client a le moins consommé, consommation minimale
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

# ── Mapping mois → nom canonique ──
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

# ════════════════════════════════════════════════════════════
# TOKENS NIVEAU MODULE (utilisés dans plusieurs fonctions)
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
_TOKENS_SERVICE    = ["type de service", "type service", "quel service",
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
    return any(m in q for m in _NOMS_MOIS)

def _extraire_mois(q: str) -> str:
    tokens_tries = sorted(_MAP_MOIS.keys(), key=len, reverse=True)
    for token in tokens_tries:
        if re.search(r'\b' + re.escape(token) + r'\b', q):
            return _MAP_MOIS[token]
    for token in tokens_tries:
        if token in q:
            return _MAP_MOIS[token]
    return ""

def _appeler_llm(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"].strip()


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
            q_val = _normaliser_q(question)
            # ── 1. INFOS_CLIENT sans nom propre ──
            _a_nom_propre = any(
                len(mot) >= 4 and mot[0].isupper()
                for mot in question.split()
            )
            if intent_llm == "INFOS_CLIENT" and not _a_nom_propre:
                print(f"  [VALIDATION] INFOS_CLIENT sans nom propre → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}

            # ── 1b. MIN_CONSOMMATEURS sans contexte min ──
            if intent_llm == "MIN_CONSOMMATEURS":
                _mots_min = ["moins", "faible", "min", "minimum", "bas", "petit", "reduit"]
                if not any(m in q_val for m in _mots_min):
                    print(f"  [VALIDATION] MIN_CONSOMMATEURS sans contexte min → QUESTION_LIBRE")
                    return {"intent": "QUESTION_LIBRE", "params": {}}

            # ── 1c. TOP_CONSOMMATEURS sans contexte max ──
            if intent_llm == "TOP_CONSOMMATEURS":
                _mots_max = ["plus", "eleve", "max", "maximum", "haut", "grand", "top", "fort", "beaucoup"]
                if not any(m in q_val for m in _mots_max):
                    print(f"  [VALIDATION] TOP_CONSOMMATEURS sans contexte max → QUESTION_LIBRE")
                    return {"intent": "QUESTION_LIBRE", "params": {}}

            # ── 2. PAR_AGENCE avec valeur numérique ──
            agence_val = result.get("params", {}).get("agence", "")
            if intent_llm == "PAR_AGENCE" and agence_val and agence_val.strip().isdigit():
             agence_val = result.get("params", {}).get("agence", "")
            if intent_llm == "PAR_AGENCE" and agence_val and agence_val.strip().isdigit():
                print(f"  [VALIDATION] PAR_AGENCE valeur numérique → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}
            _mots_specifiques = ["compteur", "contrat", "numero de", "numero compteur", "numero contrat"]
            _intent_adaptes = ["INFOS_CLIENT", "QUESTION_LIBRE"]
            if any(m in q_val for m in _mots_specifiques) and intent_llm not in _intent_adaptes:
                print(f"  [VALIDATION] mot spécifique → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}
            if intent_llm in ("SOMME_CONSO_MOIS", "SOMME_MONTANT_MOIS"):
                mois_presents = any(m in q_val for m in [
                    "jan", "fev", "mar", "avr", "mai", "jun",
                    "jul", "aou", "sep", "oct", "nov", "dec",
                    "janvier", "fevrier", "mars", "avril", "juin",
                    "juillet", "aout", "septembre", "octobre",
                    "novembre", "decembre"
                ])
                if not mois_presents:
                    print(f"  [VALIDATION] {intent_llm} sans mois → QUESTION_LIBRE")
                    return {"intent": "QUESTION_LIBRE", "params": {}}
            _mots_analytiques = ["par agence", "par service", "par usage", "par mois", "par client", "par type", "moyenne par", "total par", "somme par"]
            if intent_llm == "STATS_GENERALES" and any(m in q_val for m in _mots_analytiques):
                print(f"  [VALIDATION] STATS_GENERALES analytique → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}
            _intents_valides = [
                "LISTE_CLIENTS", "TOP_CONSOMMATEURS", "MIN_CONSOMMATEURS",
                "TOP_MONTANTS", "MIN_MONTANTS", "CLASSEMENT_PAR_MOIS",
                "AGENCE_PAR_CLIENT", "PAR_AGENCE", "PAR_USAGE", "PAR_SERVICE",
                "ALERTES", "STATS_GENERALES", "SOMME_MONTANT_MOIS",
                "SOMME_CONSO_MOIS", "EVOLUTION_MOIS", "QUESTION_LIBRE"
            ]
            if intent_llm not in _intents_valides:
                print(f"  [VALIDATION] Intent inconnu {intent_llm} → QUESTION_LIBRE")
                return {"intent": "QUESTION_LIBRE", "params": {}}
            return result
        except:
            pass
    return {"intent": "QUESTION_LIBRE", "params": {}}
# ════════════════════════════════════════════════════════════
# DÉTECTION INTENT CLIENT
# ════════════════════════════════════════════════════════════

def detecter_intent_client(question: str) -> dict:
    q = _normaliser_intent_q(question)

    # ── ÉTAPE 1 : MOIS_SPECIFIQUE (priorité absolue) ──
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

    # ── ÉTAPE 2 : INFOS_CLIENT champs spécifiques ──
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

    # ── ÉTAPE 2b : SOMME_MONTANT_CLIENT ──
    for token in _TOKENS_SOMME_MONTANT_CLIENT:
        if token in q:
            return {"intent": "SOMME_MONTANT_CLIENT", "params": {}}

    # ── ÉTAPE 3 : SOMME_CONSO_CLIENT ──
    for token in _TOKENS_SOMME_CLIENT:
        if token in q:
            return {"intent": "SOMME_CONSO_CLIENT", "params": {}}

    # ── ÉTAPE 4 : MAX_CONSOMMATION ──
    for token in _TOKENS_MAX_CONSO:
        if token in q:
            return {"intent": "MAX_CONSOMMATION", "params": {}}

    # ── ÉTAPE 5 : MIN_CONSOMMATION ──
    for token in _TOKENS_MIN_CONSO:
        if token in q:
            return {"intent": "MIN_CONSOMMATION", "params": {}}

    # ── ÉTAPE 6 : MAX_MONTANT ──
    for token in _TOKENS_MAX_MONTANT:
        if token in q:
            return {"intent": "MAX_MONTANT", "params": {}}

    # ── ÉTAPE 7 : MIN_MONTANT ──
    for token in _TOKENS_MIN_MONTANT:
        if token in q:
            return {"intent": "MIN_MONTANT", "params": {}}

    # ── ÉTAPE 8 : Historique complet ──
    _tokens_all = [
        "tous les mois", "toutes les factures", "historique",
        "historique complet", "evolution", "l ensemble", "l'ensemble", "chaque mois",
    ]
    for token in _tokens_all:
        if token in q:
            return {"intent": "FACTURES_CLIENT", "params": {}}

    # ── ÉTAPE 9 : Moyenne ──
    if any(t in q for t in ["moyenne", "moyen", "moy"]):
        return {"intent": "MOYENNE_CLIENT", "params": {}}

    # ── ÉTAPE 10 : Infos générales ──
    if any(t in q for t in ["infos", "informations", "fiche", "profil", "tout sur"]):
        return {"intent": "INFOS_CLIENT", "params": {}}

    # ── ÉTAPE 11 : LLM fallback ──
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

Question : {question}

JSON uniquement :
{{"intent": "NOM_INTENT", "params": {{}}}}
Si mois précis ajoute : {{"mois": "Mars"}}
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
        except:
            pass
    return {"intent": "FACTURES_CLIENT", "params": {}}