"""
agent.py
========
Agent SRM — Architecture correcte :
  - Le CODE détecte ce que l'utilisateur veut (pas le LLM)
  - Le CODE appelle les outils et récupère les données réelles
  - Mistral reçoit TOUTES les données et rédige uniquement en français
  - Mistral ne calcule jamais, ne devine jamais

Cas gérés :
  1. Rapport mensuel         — "rapport de janvier" / "rapport client X"
  2. Clients à risque        — "qui est à risque" / "anomalies"
  3. Résumé global           — "résume la situation" / "vue globale"
  4. Historique client       — "historique de Dupont"
  5. Comparaison             — "compare X entre jan et fév"
  6. Conseil personnalisé    — "que faire pour Dupont"
  7. Question générale       — tout autre texte libre
"""

import requests
import json
import re

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
# CONFIG OLLAMA
# ─────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "mistral"

MOIS_MAP = {
    "janvier": "01", "février": "02", "fevrier": "02",
    "mars": "03", "avril": "04", "mai": "05", "juin": "06",
    "juillet": "07", "août": "08", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11",
    "décembre": "12", "decembre": "12",
}


# ─────────────────────────────────────────────
# APPEL MISTRAL — uniquement pour rédiger
# ─────────────────────────────────────────────

def _appeler_mistral(prompt: str) -> str:
    """
    Appelle Mistral via Ollama.
    Mistral reçoit toujours des données réelles dans le prompt.
    Il ne fait que rédiger en français.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=300,
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"⚠️ Ollama indisponible : {str(e)}"


# ─────────────────────────────────────────────
# UTILITAIRES — extraction depuis la question
# ─────────────────────────────────────────────

def _extraire_mois(texte: str, annee_defaut: str = "2026") -> list[str]:
    """Extrait les mois mentionnés dans le texte → format YYYY-MM."""
    q = texte.lower()
    annees = re.findall(r"\b(20\d{2})\b", q)
    annee = annees[0] if annees else annee_defaut

    mois_directs = re.findall(r"\d{4}-\d{2}", q)
    if mois_directs:
        return mois_directs

    trouves = []
    for nom, num in MOIS_MAP.items():
        if nom in q:
            mois = f"{annee}-{num}"
            if mois not in trouves:
                trouves.append(mois)
    return trouves


def _extraire_client(texte: str, clients_connus: list) -> str | None:
    """Trouve un nom de client dans le texte."""
    q = texte.lower()
    for c in clients_connus:
        if c.lower() in q:
            return c
    return None


# ─────────────────────────────────────────────
# DÉTECTION — le CODE décide quoi faire
# ─────────────────────────────────────────────

def _detecter_intention(question: str, clients: list, periodes: list) -> dict:
    """
    Analyse la question par mots-clés et retourne :
    {
      "type": str,          — type de demande détecté
      "client": str|None,   — client mentionné
      "mois": list,         — mois mentionnés
      "params": dict,       — paramètres supplémentaires
    }
    Mistral n'intervient PAS ici. C'est du Python pur.
    """
    q = question.lower()
    client = _extraire_client(q, clients)
    mois   = _extraire_mois(q)

    # ── Rapport mensuel ──
    if any(w in q for w in ["rapport", "bilan", "synthèse mensuelle", "synthese mensuelle"]):
        return {"type": "rapport", "client": client, "mois": mois, "params": {}}

    # ── Clients à risque / anomalies / surconsommation ──
    if any(w in q for w in ["risque", "danger", "critique", "anomalie", "alerte",
                              "surconso", "surconsommation", "dépasse", "depasse",
                              "problème", "probleme", "inquiet"]):
        seuil = 20.0
        m = re.search(r"(\d+)\s*%", q)
        if m:
            seuil = float(m.group(1))
        return {"type": "risque", "client": client, "mois": mois, "params": {"seuil": seuil}}

    # ── Résumé global / situation générale ──
    if any(w in q for w in ["résume", "resume", "résumé", "résumé", "situation",
                              "global", "général", "general", "vue d'ensemble",
                              "vue densemble", "overview", "tous les clients"]):
        return {"type": "global", "client": None, "mois": mois, "params": {}}

    # ── Conseil personnalisé ──
    if any(w in q for w in ["conseil", "recommand", "que faire", "quoi faire",
                              "action", "solution", "aide", "suggère", "suggere"]):
        return {"type": "conseil", "client": client, "mois": mois, "params": {}}

    # ── Comparaison entre deux mois ──
    if any(w in q for w in ["compar", "évolution", "evolution", "différence",
                              "difference", "entre"]) and len(mois) >= 2:
        return {"type": "comparaison", "client": client, "mois": mois, "params": {}}

    # ── Historique d'un client ──
    if client and any(w in q for w in ["historique", "histoir", "évolution",
                                        "evolution", "passé", "passe", "tendance"]):
        return {"type": "historique", "client": client, "mois": mois, "params": {}}

    # ── Client mentionné sans contexte précis → historique par défaut ──
    if client:
        return {"type": "historique", "client": client, "mois": mois, "params": {}}

    # ── Mois mentionné sans client → rapport du mois ──
    if mois:
        return {"type": "rapport", "client": None, "mois": mois, "params": {}}

    # ── Fallback → résumé global ──
    return {"type": "global", "client": None, "mois": [], "params": {}}


# ─────────────────────────────────────────────
# COLLECTE DE DONNÉES — Python appelle les outils
# ─────────────────────────────────────────────

def _collecter_donnees(intention: dict, clients: list, periodes: list) -> dict:
    """
    En fonction de l'intention détectée, appelle les bons outils Python
    et retourne TOUTES les données nécessaires pour Mistral.
    Mistral n'intervient PAS ici.
    """
    t       = intention["type"]
    client  = intention["client"]
    mois    = intention["mois"]
    params  = intention["params"]
    donnees = {}

    # ── RAPPORT MENSUEL ──
    if t == "rapport":
        # Stats globales toujours incluses
        donnees["stats_globales"] = get_stats_globales()

        # Si un mois est mentionné → comparaison tous clients
        if len(mois) >= 2:
            donnees["comparaison_globale"] = comparer_tous_clients(mois[0], mois[-1])
        elif len(mois) == 1 and len(periodes) >= 2:
            # Comparer le mois mentionné avec le précédent
            idx = periodes.index(mois[0]) if mois[0] in periodes else -1
            if idx > 0:
                donnees["comparaison_globale"] = comparer_tous_clients(
                    periodes[idx - 1], mois[0]
                )
        else:
            # Pas de mois précis → prendre les 2 dernières périodes
            if len(periodes) >= 2:
                donnees["comparaison_globale"] = comparer_tous_clients(
                    periodes[-2], periodes[-1]
                )

        # Si un client est mentionné → ajouter son historique
        if client:
            donnees["historique_client"] = get_historique_client(client)

        # Anomalies toujours incluses dans un rapport
        donnees["anomalies"] = detecter_surconsommation(20.0)

    # ── CLIENTS À RISQUE ──
    elif t == "risque":
        seuil = params.get("seuil", 20.0)
        donnees["anomalies"] = detecter_surconsommation(seuil)
        donnees["stats_globales"] = get_stats_globales()

        # Si un client spécifique est mentionné
        if client:
            donnees["historique_client"] = get_historique_client(client)

    # ── RÉSUMÉ GLOBAL ──
    elif t == "global":
        donnees["stats_globales"] = get_stats_globales()
        donnees["anomalies"]      = detecter_surconsommation(20.0)
        if len(periodes) >= 2:
            donnees["comparaison_globale"] = comparer_tous_clients(
                periodes[-2], periodes[-1]
            )

    # ── CONSEIL PERSONNALISÉ ──
    elif t == "conseil":
        donnees["anomalies"]      = detecter_surconsommation(20.0)
        donnees["stats_globales"] = get_stats_globales()
        if client:
            donnees["historique_client"] = get_historique_client(client)
        if len(periodes) >= 2:
            donnees["comparaison_globale"] = comparer_tous_clients(
                periodes[-2], periodes[-1]
            )

    # ── COMPARAISON ──
    elif t == "comparaison":
        if client and len(mois) >= 2:
            donnees["comparaison_client"] = comparer_deux_mois(client, mois[0], mois[-1])
        elif len(mois) >= 2:
            donnees["comparaison_globale"] = comparer_tous_clients(mois[0], mois[-1])
        elif client:
            donnees["historique_client"] = get_historique_client(client)

    # ── HISTORIQUE CLIENT ──
    elif t == "historique":
        if client:
            donnees["historique_client"] = get_historique_client(client)
            donnees["stats_globales"]    = get_stats_globales()
            # Comparaison derniers mois disponibles pour ce client
            if len(periodes) >= 2:
                donnees["comparaison_client"] = comparer_deux_mois(
                    client, periodes[-2], periodes[-1]
                )

    return donnees


# ─────────────────────────────────────────────
# CONSTRUCTION DU PROMPT — données réelles → Mistral
# ─────────────────────────────────────────────

def _construire_prompt(question: str, intention: dict, donnees: dict,
                        historique_texte: str, periodes: list) -> str:
    """
    Construit un prompt COMPACT envoyé à Mistral.
    On limite les données pour éviter le timeout :
    - Max 10 anomalies (les plus critiques)
    - Max 10 clients dans les comparaisons
    - Stats globales résumées en texte simple
    """
    t      = intention["type"]
    client = intention["client"]
    mois   = intention["mois"]

    # ── Résumé compact des données (pas tout le JSON brut) ──
    lignes_donnees = []

    # Stats globales
    if "stats_globales" in donnees:
        s = donnees["stats_globales"]
        lignes_donnees.append(
            f"STATS GLOBALES : {s.get('nb_clients', '?')} clients, "
            f"{s.get('nb_factures', '?')} factures, "
            f"{s.get('montant_total_ttc', 0):,.0f} Dhs total"
        )
        if s.get("client_plus_gros_consommateur"):
            c = s["client_plus_gros_consommateur"]
            lignes_donnees.append(
                f"Plus gros consommateur : {c['client']} ({c['total_conso']:,.0f})"
            )
        if s.get("periode_la_plus_chargee"):
            p = s["periode_la_plus_chargee"]
            lignes_donnees.append(
                f"Période la plus chargée : {p['mois']} ({p['total_conso']:,.0f})"
            )

    # Anomalies — max 10 critiques
    if "anomalies" in donnees:
        anomalies = donnees["anomalies"]
        critiques = [a for a in anomalies if a.get("gravite") == "critique"][:5]
        elevees   = [a for a in anomalies if a.get("gravite") == "élevée"][:3]
        moderees  = [a for a in anomalies if a.get("gravite") == "modérée"][:2]
        top       = critiques + elevees + moderees

        lignes_donnees.append(
            f"\nANOMALIES DÉTECTÉES : {len(anomalies)} au total "
            f"({len(critiques)} critiques, {len(elevees)} élevées, "
            f"{len([a for a in anomalies if a.get('gravite') == 'modérée'])} modérées)"
        )
        lignes_donnees.append("Top anomalies :")
        for a in top:
            lignes_donnees.append(
                f"  - {a['client']} ({a.get('mois_anomalie','?')}) : "
                f"+{a.get('ecart_pct', 0):.1f}% — {a.get('gravite','?')}"
            )

    # Comparaison globale — max 10 clients
    if "comparaison_globale" in donnees:
        comp      = donnees["comparaison_globale"]
        en_hausse = [r for r in comp if r.get("tendance") == "hausse"]
        en_baisse = [r for r in comp if r.get("tendance") == "baisse"]
        alertes   = [r for r in comp if r.get("alerte")]

        lignes_donnees.append(
            f"\nCOMPARAISON GLOBALE : {len(en_hausse)} en hausse, "
            f"{len(en_baisse)} en baisse, {len(alertes)} alertes"
        )

        # Top hausses
        top_hausse = sorted(
            [r for r in comp if r.get("pct_conso") is not None],
            key=lambda x: x.get("pct_conso", 0), reverse=True
        )[:5]
        if top_hausse:
            lignes_donnees.append("Plus fortes hausses :")
            for r in top_hausse:
                lignes_donnees.append(
                    f"  - {r['client']} : {r.get('pct_conso', 0):+.1f}%"
                )

        # Top baisses
        top_baisse = sorted(
            [r for r in comp if r.get("pct_conso") is not None],
            key=lambda x: x.get("pct_conso", 0)
        )[:3]
        if top_baisse:
            lignes_donnees.append("Plus fortes baisses :")
            for r in top_baisse:
                lignes_donnees.append(
                    f"  - {r['client']} : {r.get('pct_conso', 0):+.1f}%"
                )

    # Comparaison client spécifique
    if "comparaison_client" in donnees:
        c = donnees["comparaison_client"]
        if "erreur" not in c:
            lignes_donnees.append(
                f"\nCOMPARAISON {c.get('client','?')} : "
                f"{c.get('pct_conso', 0):+.1f}% de variation, "
                f"tendance : {c.get('tendance','?')}, "
                f"alerte : {'oui' if c.get('alerte') else 'non'}"
            )

    # Historique client — max 6 mois
    if "historique_client" in donnees:
        hist = donnees["historique_client"][:6]
        if hist:
            nom = client or "Client"
            lignes_donnees.append(f"\nHISTORIQUE {nom} (derniers mois) :")
            for h in hist:
                lignes_donnees.append(
                    f"  - {h.get('mois_source','?')} : "
                    f"{h.get('consommation', 0):,.0f} {h.get('unite','')} — "
                    f"{h.get('montant_ttc', 0):,.2f} Dhs"
                )

    donnees_resumees = "\n".join(lignes_donnees)

    # ── Instructions selon le type ──
    instructions = {
        "rapport": (
            "Rédige un rapport mensuel professionnel et structuré.\n"
            "Structure : 1) Résumé exécutif (2-3 phrases) "
            "2) Clients en alerte avec chiffres exacts "
            "3) Tendances générales "
            "4) Recommandations concrètes (3 maximum).\n"
            "Utilise les vrais chiffres. Sois précis et professionnel."
        ),
        "risque": (
            "Identifie et analyse les clients à risque.\n"
            "Structure : 1) Clients critiques avec chiffres "
            "2) Clients en surveillance "
            "3) Actions recommandées par priorité.\n"
            "Sois direct et factuel."
        ),
        "global": (
            "Fais une synthèse claire de la situation globale.\n"
            "Structure : 1) Vue d'ensemble "
            "2) Tendances générales "
            "3) Points d'attention "
            "4) Conclusion.\n"
            "Sois concis mais complet."
        ),
        "conseil": (
            f"Donne des conseils concrets au gestionnaire SRM.\n"
            f"{'Focus sur : ' + client if client else 'Conseils pour tout le portefeuille.'}\n"
            "Structure : 1) Diagnostic 2) Risques 3) Actions prioritaires 4) Suivi suggéré."
        ),
        "comparaison": (
            "Analyse et commente la comparaison de consommation.\n"
            "Structure : 1) Résultat avec chiffres exacts "
            "2) Analyse de la variation "
            "3) Interprétation et conseil.\n"
            "Ne recalcule rien — utilise les chiffres fournis."
        ),
        "historique": (
            f"Analyse l'historique de consommation"
            f"{' de ' + client if client else ''}.\n"
            "Structure : 1) Tendance générale "
            "2) Mois remarquables "
            "3) Recommandation."
        ),
    }

    instruction = instructions.get(t,
        "Réponds à la question en utilisant uniquement les données fournies. "
        "Sois clair, structuré et professionnel."
    )

    prompt = f"""Tu es un expert analyste pour la société SRM (gestion de consommation eau/énergie).
Tu aides le gestionnaire à comprendre et piloter la consommation de ses clients.

{f"Historique :{chr(10)}{historique_texte}" if historique_texte.strip() else ""}

Question : {question}

Données réelles de la base SRM :
{donnees_resumees}

Périodes disponibles : {', '.join(periodes[-6:]) if periodes else 'non disponibles'}

Instructions : {instruction}

Règles :
- Utilise UNIQUEMENT les données ci-dessus
- Cite les vrais noms et vrais chiffres
- Réponds en français professionnel
- Utilise ⚠️ pour les alertes, ✅ pour les points positifs
- Réponse courte et structurée (max 300 mots)

Réponse :"""

    return prompt


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────

def run_agent(user_message: str, historique: list = None) -> dict:
    """
    Lance l'agent SRM.

    Flux :
      1. Code détecte l'intention (pas le LLM)
      2. Code collecte toutes les données réelles (pas le LLM)
      3. Mistral reçoit les données et rédige uniquement

    Retourne :
      {
        "reponse"        : str
        "outils_appeles" : list
        "donnees_brutes" : dict
        "intention"      : dict
        "succes"         : bool
        "messages"       : list
      }
    """
    if historique is None:
        historique = []

    # Historique en texte pour le contexte
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Gestionnaire" if msg["role"] == "user" else "Agent"
        historique_texte += f"{role} : {msg['content']}\n"

    # ── Charger le contexte de base ──
    try:
        clients  = get_liste_clients()
        periodes = get_periodes_disponibles()
    except Exception as e:
        reponse = f"❌ Impossible d'accéder à la base de données : {str(e)}"
        return {
            "reponse": reponse, "outils_appeles": [], "donnees_brutes": {},
            "intention": {}, "succes": False,
            "messages": historique + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reponse},
            ]
        }

    # ── Étape 1 : CODE détecte l'intention ──
    intention = _detecter_intention(user_message, clients, periodes)

    # ── Étape 2 : CODE collecte les données réelles ──
    donnees = _collecter_donnees(intention, clients, periodes)

    # Construire la liste des outils appelés (pour affichage dans Streamlit)
    outils_appeles = []
    for nom_outil, resultat in donnees.items():
        outils_appeles.append({
            "outil":    nom_outil,
            "params":   intention,
            "resultat": resultat,
        })

    # ── Étape 3 : Mistral reçoit les données et rédige ──
    if not donnees:
        # Aucune donnée collectée — Mistral répond en mode général
        prompt = f"""Tu es un assistant SRM. L'utilisateur demande : "{user_message}"
Tu n'as pas de données spécifiques sur ce sujet.
Réponds poliment en expliquant ce que tu peux faire :
- Générer des rapports mensuels
- Identifier les clients à risque
- Résumer la situation globale
- Donner des conseils sur la consommation
- Comparer des périodes
- Analyser l'historique d'un client
Réponds en français."""
        reponse = _appeler_mistral(prompt)
    else:
        prompt  = _construire_prompt(
            user_message, intention, donnees, historique_texte, periodes
        )
        reponse = _appeler_mistral(prompt)

    # Fallback si Ollama indisponible
    if reponse.startswith("⚠️ Ollama indisponible"):
        reponse = _fallback_sans_llm(donnees, intention)

    # Mettre à jour l'historique
    historique_maj = historique.copy()
    historique_maj.append({"role": "user",      "content": user_message})
    historique_maj.append({"role": "assistant",  "content": reponse})

    return {
        "reponse":        reponse,
        "outils_appeles": outils_appeles,
        "donnees_brutes": donnees,
        "intention":      intention,
        "succes":         True,
        "messages":       historique_maj,
    }


# ─────────────────────────────────────────────
# FALLBACK SANS LLM — si Ollama est indisponible
# ─────────────────────────────────────────────

def _fallback_sans_llm(donnees: dict, intention: dict) -> str:
    """
    Si Ollama est indisponible, affiche les données brutes
    de façon lisible sans LLM.
    """
    lignes = ["⚠️ Ollama indisponible — données brutes récupérées :\n"]

    if "anomalies" in donnees:
        anomalies = donnees["anomalies"]
        lignes.append(f"**Anomalies détectées : {len(anomalies)}**")
        for a in anomalies[:5]:
            lignes.append(
                f"  - {a['client']} ({a['mois_anomalie']}) : "
                f"+{a['ecart_pct']:.1f}% — gravité : {a['gravite']}"
            )

    if "stats_globales" in donnees:
        s = donnees["stats_globales"]
        lignes.append(
            f"\n**Stats globales** : {s['nb_clients']} clients, "
            f"{s['nb_factures']} factures, "
            f"{s['montant_total_ttc']:,.0f} Dhs total"
        )

    if "comparaison_globale" in donnees:
        comp = donnees["comparaison_globale"]
        en_hausse = [r for r in comp if r.get("tendance") == "hausse"]
        en_baisse = [r for r in comp if r.get("tendance") == "baisse"]
        lignes.append(
            f"\n**Comparaison** : {len(en_hausse)} en hausse, "
            f"{len(en_baisse)} en baisse"
        )

    if "historique_client" in donnees:
        hist = donnees["historique_client"]
        lignes.append(f"\n**Historique** : {len(hist)} entrées trouvées")

    return "\n".join(lignes)


# ─────────────────────────────────────────────
# RACCOURCIS DIRECTS — inchangés pour les onglets 1-2-3
# ─────────────────────────────────────────────

def run_comparaison_directe(client_nom: str, mois_1: str, mois_2: str) -> dict:
    """Comparaison directe sans LLM — onglet 1."""
    return comparer_deux_mois(client_nom, mois_1, mois_2)


def run_detection_directe(seuil: float = 20.0) -> list:
    """Détection directe sans LLM — onglet 2."""
    return detecter_surconsommation(seuil)


def run_comparaison_globale(mois_1: str, mois_2: str) -> list:
    """Comparaison globale directe sans LLM — onglet 3."""
    return comparer_tous_clients(mois_1, mois_2)