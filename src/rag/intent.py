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
CLASSEMENT_PAR_MOIS  : classer clients par montant ou consommation pour chaque mois, voir classement mois par mois
PAR_AGENCE           : clients d'une agence, quelle agence, combien par agence
PAR_USAGE            : usage domestique, force motrice, commercial, administratif, type d'usage, quels usages existent, professionnel, agricole
PAR_SERVICE          : eau, électricité, type de service, combien utilisent eau vs electricite, lister clients eau ou electricite
ALERTES              : alertes, qui a des alertes, factures avec alerte
STATS_GENERALES      : total, moyenne, somme, montant global, statistiques générales
SOMME_CONSO_MOIS     : somme de consommation en un mois précis, total consommé en janvier, combien a-t-on consommé en mars
EVOLUTION_MOIS       : évolution, progression, mois par mois, historique général, tendance
QUESTION_LIBRE       : toute autre question qui ne rentre pas dans les catégories ci-dessus
"""

INTENTS_CLIENT = """
MAX_CONSOMMATION     : mois où le client a le plus consommé, consommation maximale, pic de consommation
MIN_CONSOMMATION     : mois où le client a le moins consommé, consommation minimale
MAX_MONTANT          : mois où le client a payé le plus, montant maximum, facture la plus chère
MIN_MONTANT          : mois où le client a payé le moins, montant minimum, facture la moins chère
SOMME_CONSO_CLIENT   : somme totale de consommation du client sur tous les mois, total consommé, combien a-t-il consommé en tout
EVOLUTION_CLIENT     : évolution, progression, tendance, historique du client
MOYENNE_CLIENT       : moyenne, consommation moyenne, montant moyen du client
INFOS_CLIENT         : adresse, numéro client, contrat, compteur, agence, infos générales, usage, type service
MOIS_SPECIFIQUE      : consommation ou montant d'un mois précis, facture de tel mois
FACTURES_CLIENT      : toutes les factures, liste des factures, historique complet, tous les mois
"""

# ── Mapping mois → nom canonique (même format que la base) ──
_MAP_MOIS = {
    "jan":       "Janvier",
    "janv":      "Janvier",
    "janvier":   "Janvier",
    "fev":       "Fevrier",
    "fevr":      "Fevrier",
    "fevrier":   "Fevrier",
    "feb":       "Fevrier",
    "mar":       "Mars",
    "mars":      "Mars",
    "avr":       "Avril",
    "avril":     "Avril",
    "apr":       "Avril",
    "mai":       "Mai",
    "may":       "Mai",
    "jun":       "Juin",
    "juin":      "Juin",
    "jul":       "Juillet",
    "juil":      "Juillet",
    "juillet":   "Juillet",
    "aou":       "Aout",
    "aout":      "Aout",
    "aug":       "Aout",
    "sep":       "Septembre",
    "sept":      "Septembre",
    "septembre": "Septembre",
    "oct":       "Octobre",
    "octobre":   "Octobre",
    "nov":       "Novembre",
    "novembre":  "Novembre",
    "dec":       "Decembre",
    "decembre":  "Decembre",
}

# ── Noms de mois pour détecter présence ──
_NOMS_MOIS = list(_MAP_MOIS.keys())


# ════════════════════════════════════════════════════════════
# NORMALISATION ROBUSTE — appliquée AVANT toute comparaison
# Ramène toutes les variantes/fautes vers une forme canonique
# ════════════════════════════════════════════════════════════

def _normaliser_verbes(q: str) -> str:
    """
    Normalise les verbes consommer et payer sous toutes leurs formes
    (fautes de frappe, lettres doublées, accents oubliés, etc.)

    Exemples couverts :
      consomme / consome / consommee / consomee / consomé / consommé
      consomme / consomm / consom / consome / consomee / consommee
      consommme / consommmee / consomation / consommasion ...
      paye / paie / payé / payee / paiee / paié ...
    """
    # ── Normaliser "consomm..." → "consomme" ──
    # Couvre : consomme, consome, consommé, consomé, consommee,
    #          consomee, consomm, consom, consomation, consommasion, etc.
    q = re.sub(r'consom+[a-z]*', 'consomme', q)

    # ── Normaliser "pay..." / "pai..." → "paye" ──
    # Couvre : paye, payé, payee, paie, paié, paiee, paiement (exclure)
    # On exclut "paiement" pour ne pas casser ce token
    q = re.sub(r'pai+e+[a-z]*', 'paye', q)
    q = re.sub(r'pay[eé]+[a-z]*', 'paye', q)

    return q


def _normaliser_intent_q(question: str) -> str:
    """
    Normalisation complète pour la détection d'intent :
    1. normalisation de base (_normaliser_q)
    2. normalisation des verbes (consommer, payer)
    """
    q = _normaliser_q(question)
    q = _normaliser_verbes(q)
    return q


# ── Tokens SOMME_CONSO_CLIENT ──
# ⚠️ IMPORTANT : ne pas mettre "somme" seul — il est contenu dans "consomme"
#    après normalisation (consom... → consomme), ce qui crée un faux positif.
#    Utiliser uniquement des tokens suffisamment longs et précis.
_TOKENS_SOMME_CLIENT = [
    # "somme" seul → RETIRÉ (faux positif : "consomme" contient "somme")
    "somme totale",
    "somme de consomme", "somme des consomme",
    "somme de conso", "somme des conso",
    # total + consommation (après normalisation "consommation" → "consomme")
    "consomme totale", "consomme total",
    "total consomme", "total de consomme",
    "total conso", "total de conso",
    "totale consomme", "totale de consomme",
    "totale conso", "totale de conso",
    # combien
    "combien a consomme en tout",
    "combien a-t-il consomme",
    "combien a consomme",
    "en tout",
    # autres
    "cumul", "cumulee", "cumulees",
    "sur tous les mois", "sur l ensemble",
    "global", "globale",
]

# ── Tokens MAX_CONSOMMATION ──
# Après normalisation, toutes les variantes de "consommé" → "consomme"
_TOKENS_MAX_CONSO = [
    # forme canonique après normalisation
    "le plus consomme",
    "consomme le plus",
    "a le plus consomme",
    "consomme maximale",
    "consomme la plus elevee",
    "pic de consomme",
    # mois + max
    "mois ou il a le plus consomme",
    "mois ou elle a le plus consomme",
    "mois ou le client a le plus consomme",
    "mois ou le client a le plus",
    "mois a le plus consomme",
    "mois a le plus",
    "quel mois a le plus",
    "quel mois consomme le plus",
    "mois avec le plus",
    "mois avec la plus grande",
    "mois maximum",
    "mois max",
    "plus consomme",
    # superlatifs génériques (après normalisation)
    "plus elevee", "plus eleve",
    "la plus haute", "plus haute",
    "le plus grand", "la plus grande",
]

# ── Tokens MIN_CONSOMMATION ──
_TOKENS_MIN_CONSO = [
    # forme canonique après normalisation
    "le moins consomme",
    "consomme le moins",
    "a le moins consomme",
    "consomme minimale",
    "consomme la plus faible",
    # mois + min
    "mois ou il a le moins consomme",
    "mois ou elle a le moins consomme",
    "mois ou le client a le moins consomme",
    "mois ou le client a le moins",
    "mois a le moins consomme",
    "mois a le moins",
    "quel mois a le moins",
    "quel mois consomme le moins",
    "mois avec le moins",
    "mois avec la plus faible",
    "mois minimum",
    "mois min",
    "moins consomme",
    # superlatifs génériques
    "plus faible consomme", "moins elevee", "moins eleve",
    "la moins eleve", "la moins elevee",
    "faible consomme", "consomme faible", "consomme basse",
    "la plus basse", "plus basse",
]

# ── Tokens MAX_MONTANT ──
_TOKENS_MAX_MONTANT = [
    "le plus paye", "montant le plus eleve",
    "facture la plus chere", "paie le plus", "paye le plus",
    "montant maximum", "montant maximal", "a le plus paye",
    "mois ou il a le plus paye", "mois ou elle a le plus paye",
    "mois a le plus paye", "quel mois a le plus paye",
    "le plus cher",
]

# ── Tokens MIN_MONTANT ──
_TOKENS_MIN_MONTANT = [
    "le moins paye", "moins cher", "montant le plus faible",
    "facture la moins chere", "paie le moins", "paye le moins",
    "montant minimum", "montant minimal", "a le moins paye",
    "mois ou il a le moins paye", "mois ou elle a le moins paye",
    "mois a le moins paye", "quel mois a le moins paye",
]

# ── Tokens champs spécifiques INFOS_CLIENT ──
_TOKENS_USAGE      = ["usage", "type d usage", "type usage", "quel usage", "quel est l usage", "quel est son usage", "montrer les ussages", "usagges", "usaage"]
_TOKENS_ADRESSE    = ["adresse", "ou habite", "ou se trouve", "quelle adresse"]
_TOKENS_AGENCE     = ["agence", "quelle agence", "quel agence", "quelle est son agence", "quel est son agence"]
_TOKENS_SERVICE    = ["type de service", "type service", "quel service", "quel est son service", "quel est le service", "quel type de service"]
_TOKENS_CONTRAT    = ["contrat", "numero de contrat", "n contrat", "numero contrat"]
_TOKENS_COMPTEUR   = ["compteur", "numero de compteur", "n compteur", "numero compteur"]
_TOKENS_NUMERO_CLI = ["numero client", "n client", "numero de client", "id client", "nb client"]


def _contient_mois(q: str) -> bool:
    """Retourne True si la question contient un nom de mois."""
    return any(m in q for m in _NOMS_MOIS)


def _extraire_mois(q: str) -> str:
    """
    Extrait et retourne le nom canonique du mois depuis la question normalisée.
    Priorité aux tokens longs (ex: "janvier" avant "jan").
    Retourne "" si aucun mois trouvé.
    """
    tokens_tries = sorted(_MAP_MOIS.keys(), key=len, reverse=True)
    for token in tokens_tries:
        if re.search(r'\b' + re.escape(token) + r'\b', q):
            return _MAP_MOIS[token]
    # Fallback : sous-chaîne simple
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
Si la question mentionne un usage précis, retourne UNIQUEMENT le mot brut tel qu'écrit dans la question, ex: {{"usage": "pro"}}
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
    # ✅ Utiliser la normalisation ROBUSTE (inclut normalisation des verbes)
    q = _normaliser_intent_q(question)

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 1 — MOIS_SPECIFIQUE (priorité absolue)
    # ════════════════════════════════════════════════════════════
    # Après normalisation : "consommé", "consomé", "consome" → "consomme"
    _mots_conso_montant = [
        "consomme", "conso", "montant", "facture",
        "combien", "paye",
    ]
    if _contient_mois(q) and any(t in q for t in _mots_conso_montant):
        _tokens_tous = ["tous les mois", "chaque mois", "sur tous", "l ensemble"]
        if not any(t in q for t in _tokens_tous):
            mois_extrait = _extraire_mois(q)
            print(f"  [PRÉ-DÉTECTION CLIENT] MOIS_SPECIFIQUE → mois='{mois_extrait}'")
            return {"intent": "MOIS_SPECIFIQUE", "params": {"mois": mois_extrait}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 2 — Champs spécifiques INFOS_CLIENT
    # ════════════════════════════════════════════════════════════
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

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 3 — SOMME_CONSO_CLIENT
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_SOMME_CLIENT:
        if token in q:
            return {"intent": "SOMME_CONSO_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 4 — MAX_CONSOMMATION
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MAX_CONSO:
        if token in q:
            return {"intent": "MAX_CONSOMMATION", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 5 — MIN_CONSOMMATION
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MIN_CONSO:
        if token in q:
            return {"intent": "MIN_CONSOMMATION", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 6 — MAX_MONTANT
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MAX_MONTANT:
        if token in q:
            return {"intent": "MAX_MONTANT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 7 — MIN_MONTANT
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MIN_MONTANT:
        if token in q:
            return {"intent": "MIN_MONTANT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 8 — Historique complet
    # ════════════════════════════════════════════════════════════
    _tokens_all = [
        "tous les mois", "toutes les factures",
        "historique", "historique complet", "evolution",
        "l ensemble", "l'ensemble", "chaque mois",
    ]
    for token in _tokens_all:
        if token in q:
            return {"intent": "FACTURES_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 9 — Moyenne
    # ════════════════════════════════════════════════════════════
    if any(t in q for t in ["moyenne", "moyen", "moy"]):
        return {"intent": "MOYENNE_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 10 — Infos générales complètes
    # ════════════════════════════════════════════════════════════
    if any(t in q for t in ["infos", "informations", "fiche", "profil", "tout sur"]):
        return {"intent": "INFOS_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 11 — LLM fallback
    # ════════════════════════════════════════════════════════════
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
                "SOMME_CONSO_CLIENT", "EVOLUTION_CLIENT",
                "MOYENNE_CLIENT", "INFOS_CLIENT",
                "MOIS_SPECIFIQUE", "FACTURES_CLIENT"
            ]
            if result.get("intent") in intents_valides:
                return result
        except:
            pass
    return {"intent": "FACTURES_CLIENT", "params": {}}