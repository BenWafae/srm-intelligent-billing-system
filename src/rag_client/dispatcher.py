# ════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════
import re
import json

from rag.mode import _normaliser_q
from rag.intent import _appeler_llm, _extraire_mois, _contient_mois

from rag.fetchers_client import (
    fetch_client_max_consommation, fetch_client_min_consommation,
    fetch_client_max_montant, fetch_client_min_montant,
    fetch_client_evolution, fetch_client_moyenne, fetch_client_infos,
    fetch_client_mois_specifique, fetch_client_toutes_factures,
    fetch_client_somme_conso, fetch_client_somme_montant
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

from rag_client.normalisation_client import _score_intent
from rag_client.intent import _detecter_champ_infos


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
    # ÉTAPE 0 — CHAMP PRÉCIS
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
    # ÉTAPE 2 — SCORING
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