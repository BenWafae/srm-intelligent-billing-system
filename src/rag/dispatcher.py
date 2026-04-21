# src/rag/dispatcher.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from normalisation import normaliser_usage
from rag.mode import detecter_mode_reponse, _normaliser_q
from rag.intent import detecter_intent, detecter_intent_client
from rag.fetchers_generaux import (
    fetch_liste_clients, fetch_top_consommateurs, fetch_min_consommateurs,
    fetch_min_consommateurs_par_service, fetch_max_consommateurs_par_service,
    fetch_top_montants, fetch_classement_par_mois, fetch_par_agence,
    fetch_par_usage, fetch_par_service, fetch_alertes,
    fetch_stats_generales, fetch_evolution_mois, fetch_question_libre,
    fetch_somme_conso_mois
)
from rag.fetchers_client import (
    fetch_client_max_consommation, fetch_client_min_consommation,
    fetch_client_max_montant, fetch_client_min_montant,
    fetch_client_evolution, fetch_client_moyenne, fetch_client_infos,
    fetch_client_mois_specifique, fetch_client_toutes_factures,
    fetch_client_somme_conso
)


def repondre_question_generale(question: str, historique_texte: str) -> str:
    mode = detecter_mode_reponse(question)
    print(f"  [MODE] {mode}")

    q_norm = _normaliser_q(question)

    _sujet_facture = any(t in q_norm for t in ["facture", "factures", "fact", "enregistrement", "enregistrements", "ligne", "lignes"])
    _sujet_client  = any(t in q_norm for t in ["client", "clients", "abonne", "abonnes"])
    _sujet_mois    = any(t in q_norm for t in ["mois", "periode", "periodes"])
    _sujet_agence  = any(t in q_norm for t in ["agence", "agences"])
    _sujet_alerte  = any(t in q_norm for t in ["alerte", "alertes"])
    _sujet_service = any(t in q_norm for t in ["type de service", "types de service", "type service", "types service"])

    demande_eau    = any(m in q_norm for m in ["eau", "eauu", "eeau"])
    demande_elec   = any(m in q_norm for m in ["elec", "electricit", "electr"])
    demande_faible = any(m in q_norm for m in ["faible", "minimum", "minimale", "plus faible"])
    demande_elevee = any(m in q_norm for m in ["eleve", "plus grand", "maximum", "haut", "top"])

    usage_detecte = None
    _mots_usage_contexte = any(t in q_norm for t in [
        "usage", "usages", "type usage",
        "professionnel", "domestique", "agricole",
        "pro", "dom", "agri"
    ])

    if _mots_usage_contexte:
        for mot in q_norm.split():
            result = normaliser_usage(mot)
            if result:
                usage_detecte = result
                break
        if usage_detecte is None:
            mots = q_norm.split()
            for i in range(len(mots) - 1):
                bigramme = mots[i] + " " + mots[i+1]
                result = normaliser_usage(bigramme)
                if result:
                    usage_detecte = result
                    break

    _sujet_usage_par_client = (
        any(t in q_norm for t in ["chaque client", "pour chaque", "par client"]) and
        any(t in q_norm for t in ["usage", "usages", "type", "types"])
    )

    if _sujet_usage_par_client:
        return fetch_par_usage(usage=None, mode="detail")

    if usage_detecte and any(t in q_norm for t in ["client", "clients", "qui", "liste", "lister", "combien"]):
        return fetch_par_usage(usage=usage_detecte, mode=mode)

    # ── MODE COUNT ──
    if mode == "count":
        if _sujet_facture and not _sujet_client:
            return fetch_stats_generales(mode="count", question=question)
        if _sujet_client and not _sujet_facture and not demande_eau and not demande_elec:
            return fetch_liste_clients(mode="count")
        if _sujet_mois and not _sujet_facture and not _sujet_client:
            return fetch_evolution_mois(mode="count")
        if _sujet_agence:
            return fetch_par_agence(agence=None, mode="count")
        if _sujet_alerte:
            return fetch_alertes(mode="count")
        if demande_eau and not demande_elec:
            return fetch_par_service(service="eau", mode="count")
        if demande_elec and not demande_eau:
            return fetch_par_service(service="electricite", mode="count")
        if demande_eau and demande_elec:
            return fetch_par_service(service=None, mode="count")

    # ── MODE LIST ──
    if mode == "list":
        if _sujet_agence and not _sujet_client:
            return fetch_par_agence(agence=None, mode="list")
        if _sujet_alerte:
            return fetch_alertes(mode="list")
        if demande_eau and not demande_elec:
            return fetch_par_service(service="eau", mode="list")
        if demande_elec and not demande_eau:
            return fetch_par_service(service="electricite", mode="list")

    # ── Pré-détection service / conso ──
    if demande_faible and demande_eau and not demande_elec:
        return fetch_min_consommateurs_par_service(service="eau", mode=mode)
    if demande_faible and demande_elec and not demande_eau:
        return fetch_min_consommateurs_par_service(service="electricite", mode=mode)
    if demande_elevee and demande_eau and not demande_elec:
        return fetch_max_consommateurs_par_service(service="eau", mode=mode)
    if demande_elevee and demande_elec and not demande_eau:
        return fetch_max_consommateurs_par_service(service="electricite", mode=mode)

    if _sujet_service and not demande_eau and not demande_elec:
        return fetch_par_service(service=None, mode=mode)
    if demande_eau and demande_elec:
        return fetch_par_service(service=None, mode=mode)
    if demande_eau and not demande_elec and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return fetch_par_service(service="eau", mode=mode)
    if demande_elec and not demande_eau and any(m in q_norm for m in ["combien", "liste", "quels", "client", "utilis"]):
        return fetch_par_service(service="electricite", mode=mode)

    # ── LLM pour les cas restants ──
    print(f"  [RAG] Détection intent...")
    resultat = detecter_intent(question)
    intent = resultat.get("intent", "QUESTION_LIBRE")
    params = resultat.get("params", {})
    print(f"  [RAG] Intent : {intent} | Params : {params} | Mode : {mode}")

    if intent == "LISTE_CLIENTS":
        return fetch_liste_clients(mode=mode)
    elif intent == "TOP_CONSOMMATEURS":
        return fetch_top_consommateurs(mois=params.get("mois"), mode=mode)
    elif intent == "MIN_CONSOMMATEURS":
        return fetch_min_consommateurs(mois=params.get("mois"), mode=mode)
    elif intent == "TOP_MONTANTS":
        return fetch_top_montants(mois=params.get("mois"), mode=mode)
    elif intent == "CLASSEMENT_PAR_MOIS":
        return fetch_classement_par_mois(mode=mode)
    elif intent == "PAR_AGENCE":
        return fetch_par_agence(agence=params.get("agence"), mode=mode)
    elif intent == "PAR_USAGE":
        usage_brut = params.get("usage")
        usage_norm = normaliser_usage(usage_brut) if usage_brut else None
        return fetch_par_usage(usage=usage_norm, mode=mode)
    elif intent == "PAR_SERVICE":
        return fetch_par_service(service=params.get("service"), mode=mode)
    elif intent == "ALERTES":
        return fetch_alertes(mode=mode)
    elif intent == "STATS_GENERALES":
        return fetch_stats_generales(mode=mode, question=question)
    elif intent == "EVOLUTION_MOIS":
        return fetch_evolution_mois(mode=mode)
    elif intent == "SOMME_CONSO_MOIS":
        mois = params.get("mois", "")
        if not mois:
            return "Veuillez préciser le mois souhaité."
        return fetch_somme_conso_mois(mois)
    else:
        return fetch_question_libre(question, historique_texte)


def repondre_question_client(question: str, nom_client: str, historique_texte: str) -> str:
    print(f"  [RAG CLIENT] Détection intent pour {nom_client}...")
    resultat = detecter_intent_client(question)
    intent = resultat.get("intent", "FACTURES_CLIENT")
    params = resultat.get("params", {})
    print(f"  [RAG CLIENT] Intent : {intent} | Params : {params}")

    if intent == "MAX_CONSOMMATION":
        return fetch_client_max_consommation(nom_client)
    elif intent == "MIN_CONSOMMATION":
        return fetch_client_min_consommation(nom_client)
    elif intent == "MAX_MONTANT":
        return fetch_client_max_montant(nom_client)
    elif intent == "MIN_MONTANT":
        return fetch_client_min_montant(nom_client)
    elif intent == "EVOLUTION_CLIENT":
        return fetch_client_evolution(nom_client)
    elif intent == "MOYENNE_CLIENT":
        return fetch_client_moyenne(nom_client)
    elif intent == "INFOS_CLIENT":
        # ── Passer le champ précis si détecté ──
        champ = params.get("champ")
        return fetch_client_infos(nom_client, champ=champ)
    elif intent == "MOIS_SPECIFIQUE":
        mois = params.get("mois", "")
        return fetch_client_mois_specifique(nom_client, mois)
    elif intent == "SOMME_CONSO_CLIENT":
        return fetch_client_somme_conso(nom_client)
    else:
        return fetch_client_toutes_factures(nom_client)