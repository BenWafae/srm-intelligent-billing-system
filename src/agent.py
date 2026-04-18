"""
agent.py
========
Cerveau de l'agent d'analyse de consommation.
Utilise Ollama (Mistral) en local — pas d'API externe, pas de clé.

Fonctionnement :
  1. Reçoit une demande
  2. Détermine automatiquement quels outils appeler
  3. Exécute les outils → données réelles depuis la DB
  4. Envoie les données + la demande à Mistral (Ollama)
  5. Retourne la réponse finale + données brutes (pour les graphiques)
"""

import requests
import json

from src.agent_tools import (
    get_liste_clients,
    get_periodes_disponibles,
    get_historique_client,
    comparer_deux_mois,
    comparer_tous_clients,
    detecter_surconsommation,
    get_stats_globales,
)

# ─────────────────────────────────────────────
# CONFIG OLLAMA — identique à llm.py
# ─────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "mistral"


def _appeler_ollama(prompt: str) -> str:
    """
    Appelle Mistral via Ollama — même méthode que dans llm.py.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Erreur Ollama : {str(e)}"


# ─────────────────────────────────────────────
# ÉTAPE 1 — Décider quel(s) outil(s) appeler
# ─────────────────────────────────────────────

def _choisir_outils(question: str, contexte: str) -> list[dict]:
    """
    Demande à Mistral de décider quels outils appeler
    en fonction de la question. Retourne une liste d'appels.
    """
    outils_disponibles = """
- get_liste_clients : liste tous les clients en base. Params : aucun.
- get_periodes_disponibles : liste les mois disponibles. Params : {"nom_client": "..." (optionnel)}.
- get_historique_client : historique d'un client. Params : {"nom_ou_numero": "..."}.
- comparer_deux_mois : compare un client entre 2 mois. Params : {"nom_ou_numero": "...", "mois_1": "YYYY-MM", "mois_2": "YYYY-MM"}.
- comparer_tous_clients : compare tous les clients entre 2 mois. Params : {"mois_1": "YYYY-MM", "mois_2": "YYYY-MM"}.
- detecter_surconsommation : détecte les anomalies. Params : {"seuil_pct": 20.0 (optionnel)}.
- get_stats_globales : statistiques générales. Params : aucun.
"""

    prompt = f"""Tu es un agent d'analyse de consommation. Tu dois choisir quels outils appeler pour répondre à la question.

Outils disponibles :
{outils_disponibles}

Contexte (périodes et clients connus) :
{contexte}

Question : {question}

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après, sans balises markdown.
Format exact :
[
  {{"outil": "nom_outil", "params": {{}}}}
]

Exemples :
- "compare janvier et février pour client Dupont" → [{{"outil": "comparer_deux_mois", "params": {{"nom_ou_numero": "Dupont", "mois_1": "2024-01", "mois_2": "2024-02"}}}}]
- "détecte les surconsommations" → [{{"outil": "detecter_surconsommation", "params": {{"seuil_pct": 20.0}}}}]
- "statistiques générales" → [{{"outil": "get_stats_globales", "params": {{}}}}]
- "compare tous les clients entre 2024-01 et 2024-02" → [{{"outil": "comparer_tous_clients", "params": {{"mois_1": "2024-01", "mois_2": "2024-02"}}}}]

JSON :"""

    raw = _appeler_ollama(prompt)

    # Nettoyer et parser le JSON
    try:
        debut = raw.find("[")
        fin   = raw.rfind("]") + 1
        if debut != -1 and fin > debut:
            raw_json = raw[debut:fin]
            return json.loads(raw_json)
    except Exception:
        pass

    # Fallback si Mistral ne renvoie pas de JSON propre
    return [{"outil": "get_stats_globales", "params": {}}]


# ─────────────────────────────────────────────
# ÉTAPE 2 — Exécuter un outil
# ─────────────────────────────────────────────

def _executer_outil(nom: str, params: dict):
    """
    Exécute la fonction Python correspondant à l'outil.
    """
    mapping = {
        "get_liste_clients":        lambda p: get_liste_clients(),
        "get_periodes_disponibles": lambda p: get_periodes_disponibles(p.get("nom_client")),
        "get_historique_client":    lambda p: get_historique_client(p["nom_ou_numero"]),
        "comparer_deux_mois":       lambda p: comparer_deux_mois(
                                        p["nom_ou_numero"], p["mois_1"], p["mois_2"]),
        "comparer_tous_clients":    lambda p: comparer_tous_clients(p["mois_1"], p["mois_2"]),
        "detecter_surconsommation": lambda p: detecter_surconsommation(
                                        float(p.get("seuil_pct", 20.0))),
        "get_stats_globales":       lambda p: get_stats_globales(),
    }

    fn = mapping.get(nom)
    if fn is None:
        return {"erreur": f"Outil inconnu : {nom}"}

    try:
        return fn(params)
    except Exception as e:
        return {"erreur": f"Erreur {nom} : {str(e)}"}


# ─────────────────────────────────────────────
# ÉTAPE 3 — Formuler la réponse finale
# ─────────────────────────────────────────────

def _formuler_reponse(question: str, donnees: dict, historique_texte: str) -> str:
    """
    Envoie la question + les données récupérées à Mistral
    pour formuler une réponse claire en français.
    """
    donnees_texte = json.dumps(donnees, ensure_ascii=False, indent=2, default=str)

    prompt = f"""Tu es un expert en analyse de consommation d'eau et d'énergie pour la société SRM.

Historique de la conversation :
{historique_texte}

Question : {question}

Données récupérées depuis la base de données :
{donnees_texte}

Instructions :
- Réponds en français, de façon claire et structurée
- Utilise les vraies données ci-dessus, ne les invente pas
- Signale les alertes importantes avec ⚠️ ou 🔴
- Pour les comparaisons, indique clairement la variation en % et en valeur
- Sois concis mais complet
- Si les données contiennent une erreur, explique-la clairement

Réponse :"""

    return _appeler_ollama(prompt)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────

def run_agent(user_message: str, historique: list = None) -> dict:
    """
    Lance l'agent avec la demande de l'utilisateur.

    Paramètres :
      - user_message : question en langage naturel
      - historique   : liste [{role, content}] pour le contexte multi-tour

    Retourne :
      {
        "reponse"        : str   — réponse finale de l'agent
        "outils_appeles" : list  — outils utilisés + leurs résultats
        "donnees_brutes" : dict  — données récupérées (pour les graphiques)
        "succes"         : bool
      }
    """
    if historique is None:
        historique = []

    # Historique texte pour le contexte
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Utilisateur" if msg["role"] == "user" else "Agent"
        historique_texte += f"{role}: {msg['content']}\n"

    # ── Contexte rapide (clients + périodes disponibles) ──
    try:
        clients  = get_liste_clients()
        periodes = get_periodes_disponibles()
        contexte = (
            f"Clients : {', '.join(clients[:10])}{'...' if len(clients) > 10 else ''}\n"
            f"Périodes : {', '.join(periodes)}"
        )
    except Exception:
        contexte = "Base de données non accessible."

    outils_appeles = []
    donnees_brutes = {}

    # ── Étape 1 : choisir les outils ──
    appels = _choisir_outils(user_message, contexte)

    # ── Étape 2 : exécuter les outils ──
    for appel in appels:
        nom    = appel.get("outil", "")
        params = appel.get("params", {})

        if not nom:
            continue

        resultat = _executer_outil(nom, params)

        outils_appeles.append({
            "outil":    nom,
            "params":   params,
            "resultat": resultat
        })
        donnees_brutes[nom] = resultat

    # ── Étape 3 : formuler la réponse ──
    reponse = _formuler_reponse(user_message, donnees_brutes, historique_texte)

    # Mettre à jour l'historique pour le prochain tour
    historique_maj = historique.copy()
    historique_maj.append({"role": "user",      "content": user_message})
    historique_maj.append({"role": "assistant",  "content": reponse})

    return {
        "reponse":        reponse,
        "outils_appeles": outils_appeles,
        "donnees_brutes": donnees_brutes,
        "succes":         True,
        "messages":       historique_maj
    }


# ─────────────────────────────────────────────
# RACCOURCIS DIRECTS (sans LLM)
# utilisés par agent_app.py pour les graphiques
# ─────────────────────────────────────────────

def run_comparaison_directe(client_nom: str, mois_1: str, mois_2: str) -> dict:
    """Comparaison directe sans LLM — pour les graphiques Streamlit."""
    return comparer_deux_mois(client_nom, mois_1, mois_2)


def run_detection_directe(seuil: float = 20.0) -> list:
    """Détection directe sans LLM — pour les graphiques Streamlit."""
    return detecter_surconsommation(seuil)


def run_comparaison_globale(mois_1: str, mois_2: str) -> list:
    """Comparaison globale directe sans LLM — pour les graphiques Streamlit."""
    return comparer_tous_clients(mois_1, mois_2)