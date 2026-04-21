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
SOMME_CONSO_CLIENT   : somme totale de consommation du client sur tous les mois, total consommé, combien a-t-il consommé en tout, somme de ses consommations
EVOLUTION_CLIENT     : évolution, progression, tendance, historique du client
MOYENNE_CLIENT       : moyenne, consommation moyenne, montant moyen du client
INFOS_CLIENT         : adresse, numéro client, contrat, compteur, agence, infos générales
MOIS_SPECIFIQUE      : consommation ou montant d'un mois précis, que s'est-il passé en tel mois, facture de tel mois
FACTURES_CLIENT      : toutes les factures, liste des factures, historique complet, tous les mois
"""

# ── Tokens SOMME_CONSO_CLIENT ──
_TOKENS_SOMME_CLIENT = [
    "somme", "somme de", "somme des",
    "total de consommation", "total consommation",
    "total de conso", "total conso",
    "totale de consommation", "totale consommation",
    "totale de conso",
    "combien a consomme", "combien a-t-il consomme",
    "combien a consomme en tout", "en tout",
    "cumul", "cumulee", "cumulees",
    "sur tous les mois", "sur l ensemble",
    "global", "globale",
]

# ── Tokens MAX_CONSOMMATION ──
# IMPORTANT : ces tokens NE contiennent PAS de noms de mois
# pour ne pas entrer en conflit avec MOIS_SPECIFIQUE
_TOKENS_MAX_CONSO = [
    "le plus consomme",
    "le plus consome",
    "consommation maximale",
    "consommation la plus elevee",
    "consomme le plus",
    "pic de consommation",
    "mois ou il a le plus consomme",
    "mois ou elle a le plus consomme",
    "mois ou le client a le plus",
    "a le plus consomme",
    "a le plus consome",
]

# ── Tokens MIN_CONSOMMATION ──
_TOKENS_MIN_CONSO = [
    "le moins consomme",
    "le moins consome",
    "consommation minimale",
    "consommation la plus faible",
    "consomme le moins",
    "mois ou il a le moins consomme",
    "mois ou elle a le moins consomme",
    "mois ou le client a le moins",
    "a le moins consomme",
    "a le moins consome",
    "plus faible consommation",
    "moins elevee",          # "consommation la moins élevée"
    "moins eleve",           # variante sans accent
    "la moins eleve",
    "la moins elevee",
    "faible consommation",
    "consommation faible",
    "consommation basse",
    "la plus basse",
    "plus basse",
]

# ── Tokens MAX_MONTANT ──
_TOKENS_MAX_MONTANT = [
    "le plus paye",
    "le plus cher",
    "montant le plus eleve",
    "facture la plus chere",
    "paie le plus",
    "paye le plus",
    "montant maximum",
    "montant maximal",
    "a le plus paye",
    "mois ou il a le plus paye",
    "mois ou elle a le plus paye",
]

# ── Tokens MIN_MONTANT ──
_TOKENS_MIN_MONTANT = [
    "le moins paye",
    "moins cher",
    "montant le plus faible",
    "facture la moins chere",
    "paie le moins",
    "paye le moins",
    "montant minimum",
    "montant minimal",
    "a le moins paye",
    "mois ou il a le moins paye",
    "mois ou elle a le moins paye",
]

# ── Liste des noms de mois pour détecter MOIS_SPECIFIQUE ──
# Si la question contient un mois précis + "consommation" → MOIS_SPECIFIQUE
# Cette liste sert à PROTÉGER MOIS_SPECIFIQUE contre les faux positifs MAX/MIN
_NOMS_MOIS = [
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
    "jan", "fev", "mar", "avr", "jul", "aou", "sep", "oct", "nov", "dec",
]


def _contient_mois(q: str) -> bool:
    """Retourne True si la question contient un nom de mois précis."""
    return any(m in q for m in _NOMS_MOIS)


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
    q = _normaliser_q(question)

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 1 — MOIS_SPECIFIQUE en priorité absolue
    # Si la question contient un mois précis ET un mot de consommation/montant
    # → c'est forcément MOIS_SPECIFIQUE, pas MAX ni MIN ni SOMME
    # Exemples protégés :
    #   "consommation de Amal en Janvier"       → MOIS_SPECIFIQUE ✅
    #   "facture de Amal en Avril"              → MOIS_SPECIFIQUE ✅
    #   "que s'est-il passé en Mars"            → MOIS_SPECIFIQUE ✅
    # ════════════════════════════════════════════════════════════
    _mots_conso_montant = [
        "consommation", "conso", "montant", "facture",
        "combien", "que s est il passe", "que s'est-il passe",
        "paye", "consomme",
    ]
    if _contient_mois(q) and any(t in q for t in _mots_conso_montant):
        # Vérifier que ce n'est PAS une question sur "tous les mois"
        _tokens_tous = ["tous les mois", "chaque mois", "sur tous", "l ensemble"]
        if not any(t in q for t in _tokens_tous):
            print(f"  [PRÉ-DÉTECTION CLIENT] MOIS_SPECIFIQUE (mois précis détecté)")
            return {"intent": "MOIS_SPECIFIQUE", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 2 — SOMME_CONSO_CLIENT
    # Exemples :
    #   "quelle est la somme de consommation de Amal"   → SOMME ✅
    #   "total consommé par Amal"                       → SOMME ✅
    #   "combien a-t-il consommé en tout"               → SOMME ✅
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_SOMME_CLIENT:
        if token in q:
            print(f"  [PRÉ-DÉTECTION CLIENT] SOMME_CONSO_CLIENT via '{token}'")
            return {"intent": "SOMME_CONSO_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 3 — MAX_CONSOMMATION
    # Exemples :
    #   "quel est le mois où Amal a le plus consommé"   → MAX ✅
    #   "pic de consommation de Kamal"                  → MAX ✅
    # Note : ces tokens ne contiennent PAS de noms de mois
    # donc pas de conflit avec MOIS_SPECIFIQUE
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MAX_CONSO:
        if token in q:
            print(f"  [PRÉ-DÉTECTION CLIENT] MAX_CONSOMMATION via '{token}'")
            return {"intent": "MAX_CONSOMMATION", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 4 — MIN_CONSOMMATION
    # Exemples :
    #   "quel est le mois où Amal a le moins consommé"  → MIN ✅
    #   "consommation minimale de Tariq"                → MIN ✅
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MIN_CONSO:
        if token in q:
            print(f"  [PRÉ-DÉTECTION CLIENT] MIN_CONSOMMATION via '{token}'")
            return {"intent": "MIN_CONSOMMATION", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 5 — MAX_MONTANT
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MAX_MONTANT:
        if token in q:
            print(f"  [PRÉ-DÉTECTION CLIENT] MAX_MONTANT via '{token}'")
            return {"intent": "MAX_MONTANT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 6 — MIN_MONTANT
    # ════════════════════════════════════════════════════════════
    for token in _TOKENS_MIN_MONTANT:
        if token in q:
            print(f"  [PRÉ-DÉTECTION CLIENT] MIN_MONTANT via '{token}'")
            return {"intent": "MIN_MONTANT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 7 — Historique complet / toutes factures
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
    # ÉTAPE 8 — Moyenne
    # ════════════════════════════════════════════════════════════
    if any(t in q for t in ["moyenne", "moyen", "moy"]):
        return {"intent": "MOYENNE_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 9 — Infos générales
    # ════════════════════════════════════════════════════════════
    if any(t in q for t in ["adresse", "contrat", "compteur", "numero", "agence", "infos"]):
        return {"intent": "INFOS_CLIENT", "params": {}}

    # ════════════════════════════════════════════════════════════
    # ÉTAPE 10 — LLM pour les cas restants
    # ════════════════════════════════════════════════════════════
    prompt = f"""Tu es un classificateur de questions sur un client.

Voici les intents disponibles :
{INTENTS_CLIENT}

RÈGLES IMPORTANTES :
- Si la question demande la SOMME ou le TOTAL de consommation sur tous les mois → SOMME_CONSO_CLIENT
- Si la question demande "tous les mois", "toutes les factures", "historique" → FACTURES_CLIENT
- Si la question mentionne UN mois précis SANS "tous" → MOIS_SPECIFIQUE avec le mois
- Si la question demande le mois avec la consommation MAX → MAX_CONSOMMATION
- Si la question demande le mois avec la consommation MIN → MIN_CONSOMMATION

Question : {question}

Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre, sans explication, sans markdown.
{{"intent": "NOM_INTENT", "params": {{}}}}

Si la question mentionne UN mois précis, ajoute : {{"mois": "Mars"}}

JSON :"""

    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intents_valides = [
                "MAX_CONSOMMATION", "MIN_CONSOMMATION",
                "MAX_MONTANT", "MIN_MONTANT",
                "SOMME_CONSO_CLIENT",
                "EVOLUTION_CLIENT", "MOYENNE_CLIENT",
                "INFOS_CLIENT", "MOIS_SPECIFIQUE", "FACTURES_CLIENT"
            ]
            if result.get("intent") in intents_valides:
                return result
        except:
            pass
    return {"intent": "FACTURES_CLIENT", "params": {}}