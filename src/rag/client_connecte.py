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

_TOKENS_INFOS = [
    "mes infos", "mon profil", "mes informations","mes info","mes information"
    "mon adresse", "mon agence", "mon usage",
    "mon contrat", "mon compteur", "mon service",
    "mon numero", "qui suis je", "mon compte",
    "adress","adresse","usage","agence","n compteur","n compt","infos","infos"
]

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
    "voir tout", "tout afficher", "historique complet","donner moi tous mes "
]

_TOKENS_MOYENNE = [
    "ma moyenne", "mon montant moyen", "ma consommation moyenne",
    "en moyenne", "montant moyen", "conso moyenne",
]

_TOKENS_MOIS = [
    "mon montant", "ma consommation", "ma facture",
    "combien j ai", "combien ai je", "en janvier",
    "en fevrier", "en mars", "en avril", "en mai",
    "en juin", "en juillet", "en aout", "en septembre",
    "en octobre", "en novembre", "en decembre",
]

_TOKENS_CHAMP_MONTANT = ["montant", "paye", "facture", "prix", "cout", "dhs"]
_TOKENS_CHAMP_CONSO   = ["consomme", "conso", "consommation", "kwh", "m3"]
_TOKENS_CHAMP_AGENCE  = ["agence"]
_TOKENS_CHAMP_ADRESSE = ["adresse", "habite", "trouve"]
_TOKENS_CHAMP_USAGE   = ["usage", "type"]
_TOKENS_CHAMP_SERVICE = ["service"]
_TOKENS_CHAMP_CONTRAT = ["contrat"]
_TOKENS_CHAMP_COMPTEUR= ["compteur"]

INTENTS_CLIENT_CONNECTE = """
MAX_MONTANT       : mois où j'ai payé le plus, ma facture la plus chère
MIN_MONTANT       : mois où j'ai payé le moins, ma facture la moins chère
MAX_CONSOMMATION  : mois où j'ai le plus consommé, ma consommation maximale
MIN_CONSOMMATION  : mois où j'ai le moins consommé, ma consommation minimale
SOMME_MONTANT     : total de ce que j'ai payé, combien j'ai dépensé en tout
SOMME_CONSO       : total de ce que j'ai consommé, ma consommation totale
EVOLUTION         : mon historique, toutes mes factures, mois par mois
MOYENNE           : ma moyenne, montant moyen, consommation moyenne
INFOS             : mes infos, mon adresse, mon agence, mon usage, mon contrat
MOIS_SPECIFIQUE   : mon montant en janvier, ma consommation en mars
"""


# ════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════

def repondre_client_connecte(question: str, nom_client: str, historique: str = "") -> str:
    q = _normaliser_q(question)

    # ── ÉTAPE 1 : MOIS SPÉCIFIQUE (priorité absolue) ──
    if _contient_mois(q) and any(t in q for t in _TOKENS_MOIS):
        mois = _extraire_mois(q)
        champ = None
        if any(t in q for t in _TOKENS_CHAMP_MONTANT) and not any(t in q for t in _TOKENS_CHAMP_CONSO):
            champ = "montant"
        elif any(t in q for t in _TOKENS_CHAMP_CONSO) and not any(t in q for t in _TOKENS_CHAMP_MONTANT):
            champ = "consommation"
        return fetch_client_mois_specifique(nom_client, mois, champ=champ)

    # ── ÉTAPE 2 : INFOS CLIENT ──
    if any(t in q for t in _TOKENS_INFOS):
        champ = None
        if any(t in q for t in _TOKENS_CHAMP_AGENCE):
            champ = "agence"
        elif any(t in q for t in _TOKENS_CHAMP_ADRESSE):
            champ = "adresse"
        elif any(t in q for t in _TOKENS_CHAMP_USAGE):
            champ = "usage"
        elif any(t in q for t in _TOKENS_CHAMP_SERVICE):
            champ = "service"
        elif any(t in q for t in _TOKENS_CHAMP_CONTRAT):
            champ = "contrat"
        elif any(t in q for t in _TOKENS_CHAMP_COMPTEUR):
            champ = "compteur"
        return fetch_client_infos(nom_client, champ=champ)

    # ── ÉTAPE 3 : SOMME MONTANT ──
    if any(t in q for t in _TOKENS_SOMME_MONTANT):
        return fetch_client_somme_montant(nom_client)

    # ── ÉTAPE 4 : SOMME CONSO ──
    if any(t in q for t in _TOKENS_SOMME_CONSO):
        return fetch_client_somme_conso(nom_client)

    # ── ÉTAPE 5 : MAX MONTANT ──
    if any(t in q for t in _TOKENS_MONTANT_MAX):
        return fetch_client_max_montant(nom_client)

    # ── ÉTAPE 6 : MIN MONTANT ──
    if any(t in q for t in _TOKENS_MONTANT_MIN):
        return fetch_client_min_montant(nom_client)

    # ── ÉTAPE 7 : MAX CONSOMMATION ──
    if any(t in q for t in _TOKENS_CONSO_MAX):
        return fetch_client_max_consommation(nom_client)

    # ── ÉTAPE 8 : MIN CONSOMMATION ──
    if any(t in q for t in _TOKENS_CONSO_MIN):
        return fetch_client_min_consommation(nom_client)

    # ── ÉTAPE 9 : EVOLUTION ──
    if any(t in q for t in _TOKENS_EVOLUTION):
        return fetch_client_evolution(nom_client)

    # ── ÉTAPE 10 : MOYENNE ──
    if any(t in q for t in _TOKENS_MOYENNE):
        return fetch_client_moyenne(nom_client)

    # ── ÉTAPE 11 : LLM FALLBACK ──
    prompt = f"""Tu es un assistant pour un client SRM connecté.
Le client s'appelle : {nom_client}
Il pose une question sur SES propres factures uniquement.

Intents disponibles :
{INTENTS_CLIENT_CONNECTE}

Question : {question}

Réponds UNIQUEMENT avec un JSON :
{{"intent": "NOM_INTENT", "params": {{}}}}
Si mois précis ajoute : {{"mois": "Janvier"}}
"""
    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intent = result.get("intent", "")
            mois   = result.get("params", {}).get("mois", "")

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
                return fetch_client_infos(nom_client)
            elif intent == "MOIS_SPECIFIQUE" and mois:
                return fetch_client_mois_specifique(nom_client, mois)
        except:
            pass

    # ── ÉTAPE 12 : Réponse par défaut ──
    return fetch_client_toutes_factures(nom_client)