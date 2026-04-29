import re
import json

from rag.mode import _normaliser_q
from rag.intent import _appeler_llm, _extraire_mois, _contient_mois
from rag_client.intent import _detecter_champ_infos

from rag_client.fetchers import (
    get_infos, get_mois_specifique,
    get_max_consommation, get_min_consommation,
    get_max_montant, get_min_montant,
    get_somme_montant, get_somme_conso, get_moyenne,
    get_evolution, get_par_annee,
    get_top_n_conso, get_top_n_montant,
    get_derniers_n_mois, get_premiers_n_mois
)

from rag_client.tokens import (
    _TOKENS_MONTANT_MAX, _TOKENS_MONTANT_MIN,
    _TOKENS_CONSO_MAX, _TOKENS_CONSO_MIN,
    _TOKENS_SOMME_MONTANT, _TOKENS_SOMME_CONSO,
    _TOKENS_EVOLUTION, _TOKENS_MOYENNE,
    _TOKENS_INFOS, _TOKENS_MOIS,
    _TOKENS_CHAMP_MONTANT, _TOKENS_CHAMP_CONSO,
    INTENTS_CLIENT_CONNECTE
)

# ════════════════════════════════════════════
# MOTS ANGLAIS
# ════════════════════════════════════════════
_MOTS_ANGLAIS = [
    "last", "year", "month", "show", "give",
    "what", "when", "how", "much", "my",
    "consumption", "amount", "invoice", "bill"
]

# ════════════════════════════════════════════
# EXTRACTION NOMBRE (pour top N)
# ════════════════════════════════════════════
def _extraire_nombre(q: str) -> int:
    _MOTS_NOMBRES = {
        "un": 1, "une": 1, "deux": 2, "trois": 3,
        "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
        "huit": 8, "neuf": 9, "dix": 10
    }
    match = re.search(r'\b(\d+)\b', q)
    if match:
        return int(match.group(1))
    for mot, val in _MOTS_NOMBRES.items():
        if mot in q:
            return val
    return 3  # valeur par défaut

# ════════════════════════════════════════════
# EXTRACTION ANNÉE
# ════════════════════════════════════════════
def _extraire_annee(q: str) -> str:
    match = re.search(r'\b(202[0-9])\b', q)
    if match:
        return match.group(1)
    if any(t in q for t in ["annee derniere", "l annee derniere", "an passe", "annee passee", "last year"]):
        return "2025"
    if any(t in q for t in ["cette annee", "annee actuelle", "annee en cours", "this year"]):
        return "2026"
    return ""

# ════════════════════════════════════════════
# TOKENS TOP N
# ════════════════════════════════════════════
_TOKENS_TOP_N_CONSO = [
     "mois les plus consomme", "mois les moins consomme",
    "plus consomme", "moins consomme",
    "consomme le plus", "consomme le moins",
    "top conso", "pic conso",
]

_TOKENS_TOP_N_MONTANT = [
     "mois les plus chers", "mois les moins chers",
    "mois les plus eleves", "mois les moins eleves",
    "factures les plus cheres", "factures les moins cheres",
    "plus cher", "moins cher", "plus eleve",
    "chere", "cher", "eleve", "haut",
]

_TOKENS_DERNIERS = [
    "derniers mois", "dernier mois", "les derniers",
    "recents", "recent", "derniere periode",
]

_TOKENS_PREMIERS = [
    "premiers mois", "premier mois", "les premiers",
    "debut", "premiere periode",
]

# ════════════════════════════════════════════
# FALLBACK LLM
# ════════════════════════════════════════════
def _fallback_llm(question: str, numero_contrat: str) -> str:
    prompt = f"""Tu es un assistant pour un client SRM (eau et électricité au Maroc).
Les données couvrent : Octobre 2025 à Septembre 2026.
"last year" ou "année dernière" = 2025.
"this year" ou "cette année" = 2026.

Intents disponibles :
MAX_MONTANT       : mois où j'ai payé le plus
MIN_MONTANT       : mois où j'ai payé le moins
MAX_CONSOMMATION  : mois où j'ai le plus consommé
MIN_CONSOMMATION  : mois où j'ai le moins consommé
SOMME_MONTANT     : total de ce que j'ai payé
SOMME_CONSO       : total de ce que j'ai consommé
EVOLUTION         : historique complet, toutes les factures
MOYENNE           : moyenne mensuelle
INFOS             : informations du compte
MOIS_SPECIFIQUE   : facture d'un mois précis
PAR_ANNEE         : factures d'une année précise
TOP_N_CONSO       : les N mois les plus/moins consommés
TOP_N_MONTANT     : les N mois les plus/moins chers
DERNIERS_N        : les N derniers mois
PREMIERS_N        : les N premiers mois
HORS_SUJET        : question sans rapport avec les factures

EXEMPLES :
"le mois que je consomme beaucoup" → MAX_CONSOMMATION
"quand est ce que j ai beaucoup depense" → MAX_MONTANT
"donne moi tout" → EVOLUTION
"c est quoi ma moyenne" → MOYENNE
"resume moi mes factures" → EVOLUTION
"je veux voir mes 3 premiers mois" → PREMIERS_N avec n=3
"les mois ou j ai peu consomme" → MIN_CONSOMMATION
"montre moi les 5 factures les plus cheres" → TOP_N_MONTANT avec n=5, ordre=DESC
"factures recentes" → DERNIERS_N avec n=3
"bonjour", "merci", "aide moi" → HORS_SUJET
"quel temps fait il" → HORS_SUJET

Question : {question}

Réponds UNIQUEMENT avec un JSON valide :
{{"intent": "NOM_INTENT", "params": {{}}}}
Ajoute selon l'intent :
- mois précis : {{"mois": "Janvier"}}
- année : {{"annee": "2025"}}
- nombre N : {{"n": 3}}
- ordre : {{"ordre": "DESC"}} pour plus/élevé, {{"ordre": "ASC"}} pour moins/faible
"""
    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intent = result.get("intent", "")
            params = result.get("params", {})

            if intent == "HORS_SUJET":
                return (
                    "Je suis votre assistant SRM dédié à vos factures. "
                    "Je ne peux répondre qu'aux questions concernant "
                    "vos consommations, montants, ou informations de compte."
                )

            mois  = params.get("mois", "")
            annee = params.get("annee", "")
            n     = int(params.get("n", 3))
            ordre = params.get("ordre", "DESC")

            if intent == "MAX_MONTANT":
                return get_max_montant(numero_contrat)
            elif intent == "MIN_MONTANT":
                return get_min_montant(numero_contrat)
            elif intent == "MAX_CONSOMMATION":
                return get_max_consommation(numero_contrat)
            elif intent == "MIN_CONSOMMATION":
                return get_min_consommation(numero_contrat)
            elif intent == "SOMME_MONTANT":
                return get_somme_montant(numero_contrat)
            elif intent == "SOMME_CONSO":
                return get_somme_conso(numero_contrat)
            elif intent == "EVOLUTION":
                return get_evolution(numero_contrat)
            elif intent == "MOYENNE":
                return get_moyenne(numero_contrat)
            elif intent == "INFOS":
                return get_infos(numero_contrat)
            elif intent == "MOIS_SPECIFIQUE" and mois:
                return get_mois_specifique(numero_contrat, mois)
            elif intent == "PAR_ANNEE" and annee:
                return get_par_annee(numero_contrat, annee)
            elif intent == "TOP_N_CONSO":
                return get_top_n_conso(numero_contrat, n, ordre)
            elif intent == "TOP_N_MONTANT":
                return get_top_n_montant(numero_contrat, n, ordre)
            elif intent == "DERNIERS_N":
                return get_derniers_n_mois(numero_contrat, n)
            elif intent == "PREMIERS_N":
                return get_premiers_n_mois(numero_contrat, n)

        except Exception:
            pass

    return (
        "Je n'ai pas bien compris votre question. "
        "Vous pouvez me demander par exemple :\n"
        "• Le mois où j'ai le plus consommé\n"
        "• Les 3 mois les plus chers\n"
        "• Mes factures de 2025\n"
        "• Mon historique complet"
    )
# ════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════
def repondre_client_connecte(question: str, numero_contrat: str, historique: str = "") -> str:
    
    # ── Détection anglais sur question brute ──
    question_lower = question.lower()
    mots_bruts = question_lower.split()
    if any(m in mots_bruts for m in _MOTS_ANGLAIS):
        return _fallback_llm(question, numero_contrat)

    q = _normaliser_q(question)
    q = re.sub(r'^(et|mais|aussi|donc|alors|puis)\s+', '', q)

    # ══════════════════════════════════════════
    # ÉTAPE 0 — CHAMP PRÉCIS
    # ══════════════════════════════════════════
    champ = _detecter_champ_infos(q)
    if champ:
        return get_infos(numero_contrat, champ)

    # ══════════════════════════════════════════
    # ÉTAPE 1 — ANNÉE PRÉCISE
    # ══════════════════════════════════════════
    annee = _extraire_annee(q)
    if annee:
        return get_par_annee(numero_contrat, annee)

    # ══════════════════════════════════════════
    # ÉTAPE 2 — TOP N
    # ══════════════════════════════════════════
    _detect_nombre = re.search(r'\b(\d+|deux|trois|quatre|cinq)\b', q)
    if _detect_nombre:
        n = _extraire_nombre(q)
        if any(t in q for t in _TOKENS_DERNIERS):
            return get_derniers_n_mois(numero_contrat, n)
        if any(t in q for t in _TOKENS_PREMIERS):
            return get_premiers_n_mois(numero_contrat, n)
        if any(t in q for t in _TOKENS_TOP_N_MONTANT):
            ordre = "ASC" if any(t in q for t in ["moins", "faible", "bas", "petit"]) else "DESC"
            return get_top_n_montant(numero_contrat, n, ordre)
        if any(t in q for t in _TOKENS_TOP_N_CONSO):
            ordre = "ASC" if any(t in q for t in ["moins", "faible", "bas", "petit"]) else "DESC"
            return get_top_n_conso(numero_contrat, n, ordre)

    # ══════════════════════════════════════════
    # ÉTAPE 3 — MOIS SPÉCIFIQUE
    # ══════════════════════════════════════════
    if _contient_mois(q) and any(t in q for t in _TOKENS_MOIS):
        mois = _extraire_mois(q)
        champ_mois = None
        if any(t in q for t in _TOKENS_CHAMP_MONTANT) and not any(t in q for t in _TOKENS_CHAMP_CONSO):
            champ_mois = "montant"
        elif any(t in q for t in _TOKENS_CHAMP_CONSO) and not any(t in q for t in _TOKENS_CHAMP_MONTANT):
            champ_mois = "consommation"
        return get_mois_specifique(numero_contrat, mois, champ_mois)

    # ══════════════════════════════════════════
    # ÉTAPE 4 — RÈGLES EXACTES
    # ══════════════════════════════════════════
    if any(t in q for t in _TOKENS_MONTANT_MAX):
        return get_max_montant(numero_contrat)
    if any(t in q for t in _TOKENS_MONTANT_MIN):
        return get_min_montant(numero_contrat)
    if any(t in q for t in _TOKENS_CONSO_MAX):
        return get_max_consommation(numero_contrat)
    if any(t in q for t in _TOKENS_CONSO_MIN):
        return get_min_consommation(numero_contrat)
    if any(t in q for t in _TOKENS_SOMME_MONTANT):
        return get_somme_montant(numero_contrat)
    if any(t in q for t in _TOKENS_SOMME_CONSO):
        return get_somme_conso(numero_contrat)
    if any(t in q for t in _TOKENS_EVOLUTION):
        return get_evolution(numero_contrat)
    if any(t in q for t in _TOKENS_MOYENNE):
        return get_moyenne(numero_contrat)
    if any(t in q for t in _TOKENS_INFOS):
        return get_infos(numero_contrat)

    # ══════════════════════════════════════════
    # ÉTAPE 5 — LLM
    # ══════════════════════════════════════════
    return _fallback_llm(question, numero_contrat)