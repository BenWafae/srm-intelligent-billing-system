import re
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.mode import _normaliser_q
from rag.intent import _appeler_llm, _extraire_mois, _contient_mois
from rag.fetchers_client import (
    fetch_client_max_consommation, fetch_client_min_consommation,
    fetch_client_max_montant, fetch_client_min_montant,
    fetch_client_evolution, fetch_client_moyenne, fetch_client_infos,
    fetch_client_mois_specifique, fetch_client_toutes_factures,
    fetch_client_somme_conso, fetch_client_somme_montant
)

# ════════════════════════════════════════════
# TOKENS — langage personnel du client
# ════════════════════════════════════════════

# INFOS : uniquement les questions générales sur le profil complet
_TOKENS_INFOS = [
    "mes infos", "mon profil", "mes informations", "mes info", "mes information",
    "qui suis je", "mon compte", "infos", "mon identite",
    "donner moi mes infos", "voir mon profil",
]

# Champs précis — détectés AVANT l'intent INFOS général
_TOKENS_CHAMP_USAGE    = ["usage", "mon usage", "quel usage", "type usage", "quel est mon usage"]
_TOKENS_CHAMP_AGENCE   = ["agence", "mon agence", "quelle agence", "quel agence"]
_TOKENS_CHAMP_ADRESSE  = ["adresse", "mon adresse", "ou j habite", "ou je suis", "habite"]
_TOKENS_CHAMP_SERVICE  = ["service", "mon service", "quel service", "type service", "quel est mon service"]
_TOKENS_CHAMP_CONTRAT  = ["contrat", "mon contrat", "numero contrat", "n contrat"]
_TOKENS_CHAMP_COMPTEUR = ["compteur", "mon compteur", "numero compteur", "n compteur", "n compt"]
_TOKENS_CHAMP_CLIENT   = ["numero client", "mon numero", "n client", "identifiant"]

_TOKENS_MONTANT_MAX = [
    "mon montant le plus eleve", "mon montant max",
    "ma facture la plus chere", "j ai le plus paye",
    "mois ou j ai le plus paye", "mon maximum",
    "mon mois le plus cher", "montant max", "montant eleve",
    "montant le plus eleve", "montant le plus haut",
    "facture chere", "facture elevee", "facture max",
    "j ai paye beaucoup", "j ai beaucoup paye",
    "mois ou j ai paye le plus", "mois cher",
    "mois couteux", "mois le plus cher",
    "mon montant eleve", "mon montant haut",
    "paye le plus", "plus paye", "max montant",
    "montant maximum", "montant maximal",
    "mantant max", "mantant eleve", "monton max",
    "facture la plus grande", "ma plus grande facture",
    "mon pic montant", "pic facture",
]

_TOKENS_MONTANT_MIN = [
    "mon montant le plus faible", "mon montant min",
    "ma facture la moins chere", "j ai le moins paye",
    "mois ou j ai le moins paye", "mon minimum",
    "mon mois le moins cher", "montant min", "montant faible",
    "montant le plus faible", "montant le plus bas",
    "facture pas chere", "facture faible", "facture min",
    "j ai paye peu", "j ai peu paye",
    "mois ou j ai paye le moins", "mois pas cher",
    "mois le moins cher", "mois le plus bas",
    "mon montant faible", "mon montant bas",
    "paye le moins", "moins paye", "min montant",
    "montant minimum", "montant minimal",
    "mantant min", "mantant faible", "monton min",
    "facture la plus petite", "ma plus petite facture",
    "mon minimum facture",
]

_TOKENS_CONSO_MAX = [
    "ma consommation la plus elevee", "ma conso max",
    "mois ou j ai le plus consomme", "j ai le plus consomme",
    "ma consommation maximale", "mon pic de consommation",
    "mois ou j ai consomme le plus",
    "ma conso eleve", "ma conso elevee",
    "ma consommation eleve", "ma consommation elevee",
    "mois ou j ai plus consomme", "mois ou j ai consomme plus",
    "j ai plus consomme", "conso eleve", "conso elevee",
    "consomme le plus", "plus consomme", "mois max conso",
    "conso max", "mon max conso", "max consommation",
    "consommation max", "consommation elevee", "consommation eleve",
    "consomme beaucoup", "forte consommation", "grande consommation",
    "mois fort", "mois eleve", "pic conso", "sommet conso",
    "consomation eleve", "consomation max", "consomation elevee",
    "consome le plus", "consome beaucoup", "consome eleve",
    "kwh eleve", "kwh max", "m3 eleve", "m3 max",
]

_TOKENS_CONSO_MIN = [
    "ma consommation la plus faible", "ma conso min",
    "mois ou j ai le moins consomme", "j ai le moins consomme",
    "ma consommation minimale", "mois ou j ai consomme le moins",
    "ma conso faible", "ma conso basse",
    "ma consommation faible", "ma consommation basse",
    "mois ou j ai moins consomme", "mois ou j ai consomme moins",
    "j ai moins consomme", "conso faible", "conso basse",
    "consomme le moins", "moins consomme", "mois min conso",
    "conso min", "mon min conso", "min consommation",
    "consommation min", "consommation faible", "consommation basse",
    "consomme peu", "faible consommation", "petite consommation",
    "mois faible", "mois bas", "mois minimum",
    "consomation faible", "consomation min", "consomation basse",
    "consome le moins", "consome peu", "consome faible",
    "kwh faible", "kwh min", "m3 faible", "m3 min",
]

_TOKENS_SOMME_MONTANT = [
    "combien j ai paye en tout", "total de mes paiements",
    "somme de mes montants", "total mes montants",
    "combien j ai depense", "mon total paye",
    "mes paiements totaux", "total factures",
]

_TOKENS_SOMME_CONSO = [
    "combien j ai consomme en tout", "ma consommation totale",
    "somme de mes consommations", "total ma consommation",
    "cumul de ma consommation", "ma conso totale",
]

_TOKENS_EVOLUTION = [
    "mon historique", "mes factures", "toutes mes factures",
    "mon evolution", "mois par mois", "ma progression",
    "voir tout", "tout afficher", "historique complet", "donner moi tous mes",
]

_TOKENS_MOYENNE = [
    "ma moyenne", "mon montant moyen", "ma consommation moyenne",
    "en moyenne", "montant moyen", "conso moyenne",
]

_TOKENS_MOIS = [
    "mon montant", "ma consommation", "ma facture",
    "combien j ai", "combien ai je", "en janvier", "en janv",
    "en fevrier", "en fev", "en mars",
    "en avril", "en avr", "en mai",
    "en juin", "en juillet", "en juil",
    "en aout", "en aou", "en septembre", "en sept", "en sep",
    "en octobre", "en oct", "en novembre", "en nov",
    "en decembre", "en dec",
]

_TOKENS_CHAMP_MONTANT = ["montant", "mantant", "monton", "paye", "facture", "prix", "cout", "dhs"]
_TOKENS_CHAMP_CONSO   = ["consomme", "conso", "consommation", "consomation", "kwh", "m3"]

INTENTS_CLIENT_CONNECTE = """
MAX_MONTANT       : mois où j'ai payé le plus, ma facture la plus chère
MIN_MONTANT       : mois où j'ai payé le moins, ma facture la moins chère
MAX_CONSOMMATION  : mois où j'ai le plus consommé, ma consommation maximale
MIN_CONSOMMATION  : mois où j'ai le moins consommé, ma consommation minimale
SOMME_MONTANT     : total de ce que j'ai payé, combien j'ai dépensé en tout
SOMME_CONSO       : total de ce que j'ai consommé, ma consommation totale
EVOLUTION         : mon historique, toutes mes factures, mois par mois
MOYENNE           : ma moyenne, montant moyen, consommation moyenne
INFOS             : mes infos, mon profil, mes informations générales
INFOS_CHAMP       : mon usage, mon agence, mon adresse, mon service, mon contrat
MOIS_SPECIFIQUE   : mon montant en janvier, ma consommation en mars
"""

# ════════════════════════════════════════════
# MOTS VIDES — ignorés dans le scoring
# ════════════════════════════════════════════

_MOTS_VIDES = {
    "le", "la", "les", "de", "du", "des", "un", "une",
    "je", "j", "ai", "et", "en", "ou", "est", "ce",
    "que", "qui", "il", "elle", "on", "nous", "vous",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa",
    "ses", "par", "sur", "pour", "dans", "avec", "plus",
    "moi", "toi", "lui", "suis", "quel", "quelle", "quels", "quelles",
    "donner", "donne", "voir", "afficher", "montrer",
}

# ════════════════════════════════════════════
# LEVENSHTEIN — distance entre deux mots
# ════════════════════════════════════════════

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j+1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]

# ════════════════════════════════════════════
# SCORE INTENT
# ════════════════════════════════════════════

def _score_intent(question_normalisee: str, tokens: list) -> float:
    mots_question = question_normalisee.split()
    meilleur_score = 0.0

    for token in tokens:
        if token in question_normalisee:
            return 1.0

        mots_token = [m for m in token.split() if m not in _MOTS_VIDES]
        if not mots_token:
            continue

        mots_importants_q = set(mots_question)
        if all(m in mots_importants_q for m in mots_token):
            meilleur_score = max(meilleur_score, 0.9)
            continue

        correspondances = 0
        for mot_token in mots_token:
            if len(mot_token) < 4:
                if mot_token in mots_importants_q:
                    correspondances += 1
                continue

            seuil = 2 if len(mot_token) >= 8 else 1

            for mot_q in mots_question:
                if len(mot_q) < 3:
                    continue
                dist = _levenshtein(mot_token, mot_q)
                if dist <= seuil:
                    correspondances += 1
                    break

        ratio = correspondances / len(mots_token)
        score_flou = ratio * 0.75
        meilleur_score = max(meilleur_score, score_flou)

    return meilleur_score


# ════════════════════════════════════════════
# DÉTECTION CHAMP PRÉCIS — pour INFOS
# ════════════════════════════════════════════

def _detecter_champ_infos(q: str):
    """
    Retourne le nom du champ précis si le client demande
    une info spécifique (usage, agence, adresse...).
    Retourne None si c'est une demande de profil complet.
    """
    # Ordre important : du plus spécifique au plus général
    if any(t in q for t in _TOKENS_CHAMP_USAGE):
        return "usage"
    if any(t in q for t in _TOKENS_CHAMP_SERVICE):
        return "service"
    if any(t in q for t in _TOKENS_CHAMP_AGENCE):
        return "agence"
    if any(t in q for t in _TOKENS_CHAMP_ADRESSE):
        return "adresse"
    if any(t in q for t in _TOKENS_CHAMP_COMPTEUR):
        return "compteur"
    if any(t in q for t in _TOKENS_CHAMP_CONTRAT):
        return "contrat"
    if any(t in q for t in _TOKENS_CHAMP_CLIENT):
        return "client"
    return None  # profil complet


# ════════════════════════════════════════════
# RÉPONSE CHAMP PRÉCIS — sans toucher à fetchers_client
# ════════════════════════════════════════════

def _repondre_champ_infos(nom_client: str, champ: str) -> str:
    """
    Récupère le profil complet via fetch_client_infos
    puis extrait et retourne uniquement le champ demandé.
    Aucune modification de fetchers_client nécessaire.
    """
    from src.database import rechercher_client_excel

    rows = rechercher_client_excel(nom_client)
    if not rows:
        return f"Aucune donnée trouvée pour {nom_client}."

    row = rows[0]

    _MAP = {
        "usage"    : ("Usage",            row.get("usage", "")),
        "agence"   : ("Agence",           row.get("agence", "")),
        "adresse"  : ("Adresse",          row.get("adresse", "")),
        "service"  : ("Type de service",  row.get("type_service", "")),
        "contrat"  : ("N° Contrat",       row.get("numero_contrat", "")),
        "compteur" : ("N° Compteur",      row.get("numero_compteur", "")),
        "client"   : ("N° Client",        row.get("numero_client", "")),
    }

    if champ in _MAP:
        label, valeur = _MAP[champ]
        return f"**{label} :** {valeur or 'Non disponible'}"

    return fetch_client_infos(nom_client)


# ════════════════════════════════════════════
# DISPATCHER
# ════════════════════════════════════════════

def _dispatcher(intent: str, nom_client: str, mois: str = "", champ_infos: str = None) -> str:
    if intent == "MAX_MONTANT":
        return fetch_client_max_montant(nom_client)
    elif intent == "MIN_MONTANT":
        return fetch_client_min_montant(nom_client)
    elif intent == "MAX_CONSOMMATION":
        return fetch_client_max_consommation(nom_client)
    elif intent == "MIN_CONSOMMATION":
        return fetch_client_min_consommation(nom_client)
    elif intent == "SOMME_MONTANT":
        return fetch_client_somme_montant(nom_client)
    elif intent == "SOMME_CONSO":
        return fetch_client_somme_conso(nom_client)
    elif intent == "EVOLUTION":
        return fetch_client_evolution(nom_client)
    elif intent == "MOYENNE":
        return fetch_client_moyenne(nom_client)
    elif intent == "INFOS":
        if champ_infos:
            return _repondre_champ_infos(nom_client, champ_infos)
        return fetch_client_infos(nom_client)
    elif intent == "MOIS_SPECIFIQUE" and mois:
        return fetch_client_mois_specifique(nom_client, mois)
    return None


# ════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════

_SEUIL_CONFIANCE = 0.60

def repondre_client_connecte(question: str, nom_client: str, historique: str = "") -> str:
    q = _normaliser_q(question)

    # ══════════════════════════════════════════
    # ÉTAPE 0 — CHAMP PRÉCIS (priorité absolue)
    # Si le client demande usage / agence / service / etc.
    # on répond directement sans passer par le scoring
    # ══════════════════════════════════════════
    champ = _detecter_champ_infos(q)
    if champ:
        return _repondre_champ_infos(nom_client, champ)

    # ══════════════════════════════════════════
    # ÉTAPE 1 — MOIS SPÉCIFIQUE
    # ══════════════════════════════════════════
    if _contient_mois(q) and any(t in q for t in _TOKENS_MOIS):
        mois = _extraire_mois(q)
        champ_mois = None
        if any(t in q for t in _TOKENS_CHAMP_MONTANT) and not any(t in q for t in _TOKENS_CHAMP_CONSO):
            champ_mois = "montant"
        elif any(t in q for t in _TOKENS_CHAMP_CONSO) and not any(t in q for t in _TOKENS_CHAMP_MONTANT):
            champ_mois = "consommation"
        return fetch_client_mois_specifique(nom_client, mois, champ=champ_mois)

    # ══════════════════════════════════════════
    # ÉTAPE 2 — SCORING LEVENSHTEIN
    # ══════════════════════════════════════════
    scores = {
        "MAX_MONTANT"     : _score_intent(q, _TOKENS_MONTANT_MAX),
        "MIN_MONTANT"     : _score_intent(q, _TOKENS_MONTANT_MIN),
        "MAX_CONSOMMATION": _score_intent(q, _TOKENS_CONSO_MAX),
        "MIN_CONSOMMATION": _score_intent(q, _TOKENS_CONSO_MIN),
        "SOMME_MONTANT"   : _score_intent(q, _TOKENS_SOMME_MONTANT),
        "SOMME_CONSO"     : _score_intent(q, _TOKENS_SOMME_CONSO),
        "EVOLUTION"       : _score_intent(q, _TOKENS_EVOLUTION),
        "MOYENNE"         : _score_intent(q, _TOKENS_MOYENNE),
        "INFOS"           : _score_intent(q, _TOKENS_INFOS),
    }

    meilleur_intent = max(scores, key=scores.get)
    meilleur_score  = scores[meilleur_intent]

    if meilleur_score >= _SEUIL_CONFIANCE:
        resultat = _dispatcher(meilleur_intent, nom_client)
        if resultat:
            return resultat

    # ══════════════════════════════════════════
    # ÉTAPE 3 — LLM FALLBACK
    # ══════════════════════════════════════════
    prompt = f"""Tu es un assistant pour un client SRM connecté.
Le client s'appelle : {nom_client}
Il pose une question sur SES propres factures uniquement.

Intents disponibles :
{INTENTS_CLIENT_CONNECTE}

Question : {question}

Réponds UNIQUEMENT avec un JSON :
{{"intent": "NOM_INTENT", "params": {{}}}}
Si mois précis ajoute : {{"mois": "Janvier"}}
Si la question n'a aucun rapport avec les factures, réponds :
{{"intent": "HORS_SUJET", "params": {{}}}}
"""
    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intent = result.get("intent", "")
            mois   = result.get("params", {}).get("mois", "")

            if intent == "HORS_SUJET":
                return (
                    "Je suis votre assistant SRM dédié à vos factures. "
                    "Je ne peux répondre qu'aux questions concernant "
                    "vos consommations, montants, ou informations de compte."
                )

            resultat = _dispatcher(intent, nom_client, mois)
            if resultat:
                return resultat

        except Exception:
            pass

    # ══════════════════════════════════════════
    # ÉTAPE 4 — Réponse guidée
    # ══════════════════════════════════════════
    return (
        "Je n'ai pas bien compris votre question. "
        "Vous pouvez me demander par exemple :\n"
        "• Mon montant le plus élevé\n"
        "• Ma consommation en janvier\n"
        "• Mon historique complet\n"
        "• Mes informations de compte"
    )