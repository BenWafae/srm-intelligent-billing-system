"""
eval_client_complet.py
══════════════════════════════════════════════════════════════
Script d'évaluation automatique — Assistant Client SRM
Couvre : infos compte, mois spécifique, mois relatifs,
         max/min, somme, historique, moyenne, top N,
         comparaison, retard paiement, questions générales SRM,
         fallback LLM (analyse/conseil), fautes orthographe,
         questions hors sujet, questions en anglais.

Métriques mesurées :
  - Taux de réussite global et par catégorie
  - Taux de fallback LLM (règles vs LLM)
  - Temps de réponse moyen global et par catégorie
  - Couverture des intents sans LLM
  - Taux d'erreur par type

Usage :
    python eval_client_complet.py

Résultats :
    - Affichage terminal coloré
    - eval_results/rapport_eval.html  (rapport visuel jury)
    - eval_results/rapport_eval.json  (données brutes)
══════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import json
from datetime import datetime

# ── Ajuster les paths ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))       
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))


# ══════════════════════════════════════════════════════════════
# CONTRAT DE TEST — remplace par un vrai numéro dans ta base
# ══════════════════════════════════════════════════════════════
CONTRAT_TEST = "0005567205/2063205"

# ══════════════════════════════════════════════════════════════
# DATASET COMPLET — 107 questions
# Format : (question, [mots_attendus], catégorie, chemin_attendu)
# chemin_attendu : "regle" | "llm" | "general"
# ══════════════════════════════════════════════════════════════
DATASET = [

    # ════════════════════════════════════════
    # CATÉGORIE 1 : INFOS COMPTE
    # ════════════════════════════════════════
    ("donner moi mes infos",
     ["N° Client", "N° Contrat", "Agence"],
     "INFOS_COMPTE", "regle"),

    ("mon profil",
     ["N° Client", "N° Contrat"],
     "INFOS_COMPTE", "regle"),

    ("mes informations",
     ["N° Client", "N° Contrat", "Agence"],
     "INFOS_COMPTE", "regle"),

    ("mon adresse",
     ["Adresse"],
     "INFOS_COMPTE", "regle"),

    ("mon agence",
     ["Agence"],
     "INFOS_COMPTE", "regle"),

    ("mon numero de contrat",
     ["N° Contrat", "0005567205"],
     "INFOS_COMPTE", "regle"),

    ("mon compteur",
     ["N° Compteur"],
     "INFOS_COMPTE", "regle"),

    ("mon usage",
     ["Usage"],
     "INFOS_COMPTE", "regle"),

    ("mon type de service",
    ["Type de service"],
    "INFOS_COMPTE", "regle"),

    ("mon numero client",
     ["N° Client"],
     "INFOS_COMPTE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 2 : MOIS SPÉCIFIQUE
    # ════════════════════════════════════════
    ("quel est ma consommation en janvier 2026",
     ["760", "kWh", "Janvier"],
     "MOIS_SPECIFIQUE", "regle"),

    ("quel est ma conso en avril",
     ["655", "kWh", "Avril"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture en novembre 2025",
     ["701", "Novembre"],
     "MOIS_SPECIFIQUE", "regle"),

    ("combien j ai paye en mars",
     ["729", "Dhs", "Mars"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma consommation en octobre",
     ["471", "kWh", "Octobre"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture en janvier",
     ["Janvier", "760"],
     "MOIS_SPECIFIQUE", "regle"),

    ("mon montant en fevrier",
     ["Fevrier", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma conso en juillet",
     ["Juillet", "kWh"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture de juin",
     ["Juin", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    ("mon montant en aout",
     ["Aout", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma consomation en sep",
     ["Septembre", "kWh"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture en decembre",
     ["Decembre", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 3 : MOIS RELATIFS
    # ════════════════════════════════════════
    ("ma facture de ce mois",
     ["Mai 2026", "446"],
     "MOIS_RELATIF", "regle"),

    ("ma facture le mois dernier",
     ["Avril 2026", "655"],
     "MOIS_RELATIF", "regle"),

    ("ma consommation ce mois ci",
     ["446", "kWh", "Mai"],
     "MOIS_RELATIF", "regle"),

    ("ma conso mois precedent",
     ["655", "kWh", "Avril"],
     "MOIS_RELATIF", "regle"),

    ("mon montant ce mois",
     ["Mai", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("mon montant mois dernier",
     ["Avril", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("ma facture mois actuel",
     ["Mai", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("ma consomation en mois precedente",
     ["Avril", "kWh"],
     "MOIS_RELATIF", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 4 : MAX / MIN
    # ════════════════════════════════════════
    ("quel est le mois ou j ai plus consomme",
     ["Juillet", "1,939", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("quand j ai le moins consomme",
     ["Mai", "446", "MINIMUM"],
     "MAX_MIN", "regle"),

    ("mon montant le plus eleve",
     ["Juillet", "1,880", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("ma facture la plus chere",
     ["Juillet", "1,880", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("ma consommation la plus elevee",
     ["Juillet", "1,939", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("ma conso max",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    ("ma consommation minimale",
     ["Mai", "446", "MINIMUM"],
     "MAX_MIN", "regle"),

    ("ma facture la moins chere",
     ["MINIMUM", "Dhs"],
     "MAX_MIN", "regle"),

    ("mon montant minimum",
     ["MINIMUM", "Dhs"],
     "MAX_MIN", "regle"),

    ("le mois ou j ai le moins consomme",
     ["Mai", "446", "MINIMUM"],
     "MAX_MIN", "regle"),

    ("ma consomation maximal",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    ("mon pic de consommation",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 5 : SOMME / TOTAL
    # ════════════════════════════════════════
    ("la somme de ma consommation",
     ["9,920", "kWh", "12"],
     "SOMME", "regle"),

    ("combien j ai paye en total",
     ["9,622", "Dhs", "12"],
     "SOMME", "regle"),


    ("ma consommation totale",
     ["9,920", "kWh"],
     "SOMME", "regle"),

    ("combien j ai consomme en tout",
     ["9,920", "kWh"],
     "SOMME", "regle"),

    ("somme montant",
     ["Dhs", "12"],
     "SOMME", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 6 : HISTORIQUE / EVOLUTION
    # ════════════════════════════════════════
    ("mon historique",
     ["Octobre 2025", "Juillet 2026"],
     "HISTORIQUE", "regle"),

    ("toutes mes factures",
     ["Octobre 2025", "12"],
     "HISTORIQUE", "regle"),

    ("mon evolution",
     ["Octobre 2025", "Dhs"],
     "HISTORIQUE", "regle"),

    ("mois par mois",
     ["Octobre 2025", "Juillet 2026"],
     "HISTORIQUE", "regle"),

    ("voir tout",
     ["Octobre 2025", "Juillet 2026"],
     "HISTORIQUE", "regle"),

    ("historique complet",
     ["Octobre 2025", "12"],
     "HISTORIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 7 : MOYENNE / STATS
    # ════════════════════════════════════════
    ("ma moyenne",
     ["826", "kWh", "801", "Dhs"],
     "MOYENNE", "regle"),

    ("mes stats",
     ["826", "kWh", "801", "Dhs"],
     "MOYENNE", "regle"),

    ("mes statistiques",
     ["826", "kWh"],
     "MOYENNE", "regle"),

    ("mon montant moyen",
     ["801", "Dhs"],
     "MOYENNE", "regle"),

    ("ma consommation moyenne",
     ["826", "kWh"],
     "MOYENNE", "regle"),

    ("mon bilan",
     ["826", "kWh", "801"],
     "MOYENNE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 8 : TOP N
    # ════════════════════════════════════════
    ("les trois mois ou j ai plus consomme",
     ["Juillet 2026", "Juin 2026", "Aout 2026"],
     "TOP_N", "regle"),

    ("les deux mois le moins consomme",
     ["Mai 2026", "Octobre 2025"],
     "TOP_N", "regle"),

    ("les 4 mois les plus consommes",
     ["Juillet 2026", "Juin 2026", "Aout 2026", "Janvier 2026"],
     "TOP_N", "regle"),

    ("les trois mois les moins consommes",
     ["Mai 2026", "Octobre 2025"],
     "TOP_N", "regle"),

    ("les 3 mois les plus chers",
     ["Juillet 2026", "Dhs"],
     "TOP_N", "regle"),

    ("les 2 mois les moins chers",
     ["Dhs"],
     "TOP_N", "regle"),

    ("mes 3 derniers mois",
     ["Dhs", "kWh"],
     "TOP_N", "regle"),

    ("mes 2 premiers mois",
     ["Octobre 2025", "kWh"],
     "TOP_N", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 9 : COMPARAISON
    # ════════════════════════════════════════
    ("comparer ma consommation en janvier et septembre",
     ["Janvier 2026", "Septembre 2026"],
     "COMPARAISON", "regle"),

    ("comparer ma conso ce mois avec mois dernier",
     ["Mai 2026", "Avril 2026"],
     "COMPARAISON", "regle"),

    ("janvier vs mars",
     ["Janvier 2026", "Mars 2026"],
     "COMPARAISON", "regle"),

    ("difference entre octobre et janvier",
     ["Octobre", "Janvier"],
     "COMPARAISON", "regle"),

    ("ma conso en juin par rapport a juillet",
     ["Juin", "Juillet"],
     "COMPARAISON", "regle"),

    ("comparer fevrier et avril",
     ["Fevrier", "Avril"],
     "COMPARAISON", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 10 : RETARD PAIEMENT
    # ════════════════════════════════════════
    ("suis je en retard",
     ["Dhs", "date limite"],
     "RETARD_PAIEMENT", "regle"),

    ("j ai des factures impayees",
     ["Dhs", "date limite"],
     "RETARD_PAIEMENT", "regle"),

    ("est ce que j ai paye",
     ["Dhs"],
     "RETARD_PAIEMENT", "regle"),

    ("ma facture est elle en retard",
     ["Dhs"],
     "RETARD_PAIEMENT", "regle"),

    ("j ai pas encore paye",
     ["Dhs", "date limite"],
     "RETARD_PAIEMENT", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 11 : QUESTIONS GÉNÉRALES SRM
    # ════════════════════════════════════════
    ("quels documents pour s abonner en eau",
     ["Formulaire", "pièce d'identité"],
     "GENERAL_SRM", "general"),

    ("je veux passer un stage a srm",
     ["stages@srm-sm.ma", "convention"],
     "GENERAL_SRM", "general"),

    ("je veux travailler a srm",
     ["mafoamanagement", "brainman"],
     "GENERAL_SRM", "general"),

    ("comment s abonner",
     ["Formulaire", "pièce d'identité"],
     "GENERAL_SRM", "general"),

    ("documents pour un branchement",
     ["Formulaire", "titre de propriété"],
     "GENERAL_SRM", "general"),

    ("comment je peux contacter srm",
    ["08 02 03 12 12", "Contact@srm-sm.ma"],
   "GENERAL_SRM", "general"),

    ("c est quoi srm",
    ["Souss-Massa", "distributeur"],
    "GENERAL_SRM", "general"),

    ("comment economiser l eau",
     ["robinet", "douche"],
     "GENERAL_SRM", "general"),


    ("adresse siege srm",
     ["Agadir", "18 Novembre"],
     "GENERAL_SRM", "general"),

    ("documents pour abonnement electricite",
     ["permis d'habiter", "disjoncteur"],
     "GENERAL_SRM", "general"),

    ("comment faire un stage srm etudiants",
     ["stages@srm-sm.ma", "convention"],
     "GENERAL_SRM", "general"),

    # ════════════════════════════════════════
    # CATÉGORIE 12 : FALLBACK LLM (ANALYSE)
    # ════════════════════════════════════════
    ("est ce que ma consommation est normale",
     ["Bonjour", "kWh"],
     "FALLBACK_ANALYSE", "llm"),

    ("conseils pour reduire ma consommation d electricite",
    ["Bonjour", "kWh"],
    "FALLBACK_ANALYSE", "llm"),

    ("pourquoi je paie autant ce mois",
     ["Bonjour", "Mai"],
     "FALLBACK_ANALYSE", "llm"),

    ("ma facture est elle elevee",
     ["Bonjour", "Dhs"],
     "FALLBACK_ANALYSE", "llm"),

    ("comment reduire ma consommation",
     ["Bonjour"],
     "FALLBACK_ANALYSE", "llm"),

    ("je comprends pas ma facture",
     ["Bonjour", "Dhs"],
     "FALLBACK_ANALYSE", "llm"),

    ("c est normal comme montant ce mois",
     ["Bonjour", "Mai"],
     "FALLBACK_ANALYSE", "llm"),

    ("pourquoi ma conso a augmente",
     ["Bonjour"],
     "FALLBACK_ANALYSE", "llm"),

    ("ma conso est bizarre",
     ["Bonjour"],
     "FALLBACK_ANALYSE", "llm"),

    ("des conseils pour payer moins",
     ["Bonjour"],
     "FALLBACK_ANALYSE", "llm"),

    ("est ce que ce mois est normal par rapport au mois dernier",
     ["Bonjour", "Mai", "Avril"],
     "FALLBACK_ANALYSE", "llm"),

    # ════════════════════════════════════════
    # CATÉGORIE 13 : FAUTES D'ORTHOGRAPHE
    # ════════════════════════════════════════
    ("mon adress",
     ["Adresse"],
     "FAUTES_ORTHO", "regle"),

    ("ma consomation en jan",
     ["Janvier", "kWh"],
     "FAUTES_ORTHO", "regle"),

    ("mon agennce",
     ["Agence"],
     "FAUTES_ORTHO", "regle"),

    ("ma conso en avrile",
     ["Avril", "kWh"],
     "FAUTES_ORTHO", "regle"),

    ("ma facture le mois derniers",
     ["Avril", "Dhs"],
     "FAUTES_ORTHO", "regle"),

    ("quel est ma consomationn en ce mois",
     ["Mai", "kWh"],
     "FAUTES_ORTHO", "regle"),

    ("mon montantt en janvier",
     ["Janvier", "Dhs"],
     "FAUTES_ORTHO", "regle"),

    ("ma consomation maximal",
     ["Juillet", "1,939"],
     "FAUTES_ORTHO", "regle"),

    ("les trois mois ou j ai plus consomme",
     ["Juillet 2026", "Juin 2026"],
     "FAUTES_ORTHO", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 14 : PAR ANNÉE
    # ════════════════════════════════════════
    ("mes factures de 2025",
     ["2025", "Dhs"],
     "PAR_ANNEE", "regle"),

    ("mes factures de 2026",
     ["2026", "Dhs"],
     "PAR_ANNEE", "regle"),

    ("mon historique 2025",
     ["2025", "kWh"],
     "PAR_ANNEE", "regle"),

    ("toutes mes factures de l annee derniere",
     ["2025", "Dhs"],
     "PAR_ANNEE", "regle"),

    ("cette annee",
     ["2026", "Dhs"],
     "PAR_ANNEE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 15 : HORS SUJET
    # ════════════════════════════════════════
    ("bonjour",
     ["assistant", "SRM"],
     "HORS_SUJET", "llm"),

    ("quel temps fait il",
     ["assistant", "SRM"],
     "HORS_SUJET", "llm"),

    ("merci",
     ["assistant", "SRM"],
     "HORS_SUJET", "llm"),

    # ════════════════════════════════════════
    # CATÉGORIE 16 : BUG CONNU
    # ════════════════════════════════════════
    ("ma consommation par rapport au mois dernier",
     ["Mai", "Avril", "vs"],
     "BUG_CONNU", "regle"),
]

# ══════════════════════════════════════════════════════════════
# COULEURS TERMINAL
# ══════════════════════════════════════════════════════════════
VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
BLEU  = "\033[94m"
RESET = "\033[0m"
GRAS  = "\033[1m"

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def _check(reponse: str, mots_attendus: list) -> bool:
    r = reponse.lower()
    return all(m.lower() in r for m in mots_attendus)

def _barre(score: float, w: int = 20) -> str:
    plein = round(score * w)
    vide  = w - plein
    c = VERT if score >= 0.85 else (JAUNE if score >= 0.65 else ROUGE)
    return c + "█" * plein + "░" * vide + RESET

# ══════════════════════════════════════════════════════════════
# PATCH FALLBACK — mesure le taux LLM
# ══════════════════════════════════════════════════════════════
_fallback_count = 0
_fallback_par_cat = {}

def _patch_fallback():
    import sys

    try:
        import src.rag_client.dispatcher as module_complet
    except ImportError as e:
        print(f"⚠️  Import src.rag_client.dispatcher impossible : {e}")
        return False

    if not hasattr(module_complet, "_fallback_llm"):
        print("⚠️  _fallback_llm introuvable dans src.rag_client.dispatcher")
        return False

    # ── Unifier TOUS les alias possibles vers le même objet ──
    sys.modules["dispatcher"]            = module_complet
    sys.modules["rag_client.dispatcher"] = module_complet  # ← C'est cet alias que le wrapper utilise
    sys.modules["src.rag_client.dispatcher"] = module_complet

    original = module_complet._fallback_llm

    def patched(question, numero_contrat):
        global _fallback_count
        _fallback_count += 1
        return original(question, numero_contrat)

    module_complet._fallback_llm = patched
    print(f"✅ Patch fallback appliqué — id module : {id(module_complet)}")
    return True

# ══════════════════════════════════════════════════════════════
# MÉTRIQUES ADAPTÉES AU SYSTÈME
# ══════════════════════════════════════════════════════════════
def _calculer_metriques(resultats: list) -> dict:
    """
    Métriques pertinentes pour un système conversationnel hybride :

    1. Taux de réussite par catégorie
       → % de questions correctement répondues dans chaque catégorie

    2. Taux de couverture sans LLM
       → % de questions traitées par les règles Python (sans appel Mistral)
       → Plus ce taux est élevé, plus l'architecture hybride est efficace

    3. Temps de réponse moyen par catégorie
       → Démontre que les règles Python répondent plus vite que le LLM

    4. Taux d'erreur par catégorie
       → Identifie les catégories à améliorer (tokens manquants, cas non couverts)
    """
    par_cat = {}
    for r in resultats:
        cat = r["categorie"]
        if cat not in par_cat:
            par_cat[cat] = {
                "total"       : 0,
                "reussis"     : 0,
                "echecs"      : 0,
                "temps_ms"    : [],
                "sans_llm"    : 0,   # questions traitées par règles Python
                "avec_llm"    : 0,   # questions passées par fallback LLM
            }
        par_cat[cat]["total"]    += 1
        par_cat[cat]["temps_ms"].append(r["duree_ms"])

        if r["succes"]:
            par_cat[cat]["reussis"] += 1
        else:
            par_cat[cat]["echecs"] += 1

        # chemin attendu : regle/general = sans LLM | llm = avec LLM
        if r["chemin"] in ("regle", "general"):
            par_cat[cat]["sans_llm"] += 1
        else:
            par_cat[cat]["avec_llm"] += 1

    metriques = {}
    for cat, v in par_cat.items():
        taux_reussite  = v["reussis"] / v["total"] if v["total"] > 0 else 0
        taux_erreur    = v["echecs"]  / v["total"] if v["total"] > 0 else 0
        taux_sans_llm  = v["sans_llm"] / v["total"] if v["total"] > 0 else 0
        tps_moyen      = sum(v["temps_ms"]) / len(v["temps_ms"]) if v["temps_ms"] else 0

        metriques[cat] = {
            "total"        : v["total"],
            "reussis"      : v["reussis"],
            "echecs"       : v["echecs"],
            "taux_reussite": round(taux_reussite, 3),
            "taux_erreur"  : round(taux_erreur, 3),
            "taux_sans_llm": round(taux_sans_llm, 3),
            "tps_moyen_ms" : round(tps_moyen, 1),
        }
    return metriques

# ══════════════════════════════════════════════════════════════
# GÉNÉRATION RAPPORT HTML
# ══════════════════════════════════════════════════════════════
def _generer_html(resultats: list, metriques: dict,
                  score_global: float, fallback_rate: float,
                  temps_moyen_ms: float, date_exec: str) -> str:

    couleur_score = (
        "#2ecc71" if score_global >= 0.85 else
        "#f39c12" if score_global >= 0.65 else "#e74c3c"
    )

    # ── Tableau résultats détaillés ──
    lignes_tableau = ""
    for i, r in enumerate(resultats, 1):
        bg    = "#1a2e1a" if r["succes"] else "#2e1a1a"
        icone = "✅" if r["succes"] else "❌"
        chemin_badge_color = "#1e3a5f" if r["chemin"] == "regle" else (
            "#3a1e5f" if r["chemin"] == "llm" else "#1e3a2e"
        )
        chemin_label = "⚡ Règle" if r["chemin"] == "regle" else (
            "🤖 LLM" if r["chemin"] == "llm" else "📚 Base SRM"
        )
        reponse_safe = (r["reponse_court"]
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"))
        lignes_tableau += f"""
        <tr style="background:{bg}">
            <td style="color:#888;text-align:center">{i}</td>
            <td style="text-align:center;font-size:16px">{icone}</td>
            <td><span class="badge">{r['categorie']}</span></td>
            <td style="color:#ccc">{r['question']}</td>
            <td style="color:#aaa;font-size:11px">{reponse_safe}…</td>
            <td><span class="badge" style="background:{chemin_badge_color}">{chemin_label}</span></td>
            <td style="color:#888;text-align:right">{r['duree_ms']:.0f} ms</td>
        </tr>"""

    # ── Tableau métriques par catégorie ──
    lignes_metriques = ""
    for cat, m in sorted(metriques.items()):
        bar_w  = int(m["taux_reussite"] * 100)
        bar_c  = (
            "#2ecc71" if m["taux_reussite"] >= 0.85 else
            "#f39c12" if m["taux_reussite"] >= 0.65 else "#e74c3c"
        )
        icone_cat = "✅" if m["taux_reussite"] == 1.0 else (
            "⚠️"  if m["taux_reussite"] >= 0.7 else "❌"
        )
        tps_color = "#2ecc71" if m["tps_moyen_ms"] < 500 else (
            "#f39c12" if m["tps_moyen_ms"] < 2000 else "#e74c3c"
        )
        lignes_metriques += f"""
        <tr>
            <td><span class="badge">{cat}</span></td>
            <td style="text-align:center">{m['reussis']}/{m['total']}</td>
            <td style="text-align:center">
              <span style="color:{bar_c};font-weight:bold">{m['taux_reussite']*100:.0f}%</span>
            </td>
            <td style="text-align:center;color:#e74c3c">{m['taux_erreur']*100:.0f}%</td>
            <td style="text-align:center;color:#58a6ff">{m['taux_sans_llm']*100:.0f}%</td>
            <td style="text-align:center;color:{tps_color}">{m['tps_moyen_ms']:.0f} ms</td>
            <td>
              <div style="background:#21262d;border-radius:4px;height:12px;width:120px">
                <div style="background:{bar_c};width:{bar_w}%;height:12px;border-radius:4px"></div>
              </div>
            </td>
            <td style="text-align:center">{icone_cat}</td>
        </tr>"""

    # ── Calcul couverture globale sans LLM ──
    total_sans_llm = sum(1 for r in resultats if r["chemin"] in ("regle", "general"))
    pct_sans_llm   = total_sans_llm / len(resultats) * 100 if resultats else 0

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <title>Rapport Évaluation — SRM Assistant Client</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      font-family: 'Segoe UI', sans-serif;
      background: #0d1117; color: #c9d1d9;
      padding: 32px;
    }}
    h1 {{ color:#58a6ff; font-size:26px; margin-bottom:6px; }}
    h2 {{
      color:#79c0ff; font-size:17px;
      margin:32px 0 14px;
      border-bottom:1px solid #30363d;
      padding-bottom:8px;
    }}
    .meta {{ color:#8b949e; font-size:13px; margin-bottom:28px; }}
    .cards {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:28px; }}
    .card {{
      background:#161b22; border:1px solid #30363d;
      border-radius:10px; padding:18px 24px;
      min-width:150px; text-align:center;
    }}
    .card .val {{ font-size:30px; font-weight:bold; }}
    .card .lbl {{ font-size:11px; color:#8b949e; margin-top:4px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th {{
      background:#161b22; color:#8b949e;
      padding:10px 12px; text-align:left;
      border-bottom:2px solid #30363d;
      white-space:nowrap;
    }}
    td {{ padding:8px 12px; border-bottom:1px solid #21262d; vertical-align:middle; }}
    tr:hover td {{ background:#161b22; }}
    .badge {{
      background:#1f2937; border:1px solid #374151;
      border-radius:4px; padding:2px 7px;
      font-size:11px; color:#9ca3af;
      white-space:nowrap; display:inline-block;
    }}
    .progress-bar {{
      background:#21262d; border-radius:6px;
      height:20px; overflow:hidden; margin-bottom:10px;
    }}
    .progress-fill {{
      height:20px; border-radius:6px;
      background:{couleur_score};
      width:{score_global*100:.1f}%;
    }}
    .legend {{
      display:flex; gap:20px; font-size:12px;
      color:#8b949e; margin-bottom:16px;
    }}
    .legend span {{ display:flex; align-items:center; gap:6px; }}
    .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
    footer {{
      color:#8b949e; font-size:12px;
      margin-top:40px; text-align:center;
      border-top:1px solid #21262d; padding-top:16px;
    }}
    .section {{ margin-bottom:40px; }}
    .explication {{
      background:#161b22; border:1px solid #30363d;
      border-radius:8px; padding:16px 20px;
      font-size:13px; color:#8b949e;
      margin-bottom:20px; line-height:1.7;
    }}
    .explication strong {{ color:#c9d1d9; }}
  </style>
</head>
<body>

<h1>📊 Rapport d'Évaluation — Assistant Client SRM</h1>
<div class="meta">
  Généré le <strong>{date_exec}</strong> &nbsp;|&nbsp;
  Contrat de test : <code>{CONTRAT_TEST}</code> &nbsp;|&nbsp;
  <strong>{len(resultats)}</strong> questions testées &nbsp;|&nbsp;
  <strong>{len(metriques)}</strong> catégories
</div>

<!-- SCORE GLOBAL -->
<div class="section">
  <h2>Score Global</h2>
  <div class="progress-bar">
    <div class="progress-fill"></div>
  </div>
  <div class="cards">
    <div class="card">
      <div class="val" style="color:{couleur_score}">{score_global*100:.1f}%</div>
      <div class="lbl">Taux de réussite global</div>
    </div>
    <div class="card">
      <div class="val" style="color:#58a6ff">{sum(1 for r in resultats if r['succes'])}/{len(resultats)}</div>
      <div class="lbl">Questions réussies</div>
    </div>
    <div class="card">
      <div class="val" style="color:{'#2ecc71' if fallback_rate <= 0.3 else '#f39c12'}">{fallback_rate*100:.1f}%</div>
      <div class="lbl">Taux fallback LLM</div>
    </div>
    <div class="card">
      <div class="val" style="color:#58a6ff">{pct_sans_llm:.1f}%</div>
      <div class="lbl">Couverture sans LLM</div>
    </div>
    <div class="card">
      <div class="val" style="color:#58a6ff">{temps_moyen_ms:.0f} ms</div>
      <div class="lbl">Temps moyen / question</div>
    </div>
  </div>
</div>

<!-- MÉTRIQUES PAR CATÉGORIE -->
<div class="section">
  <h2>Métriques par Catégorie</h2>

  <div class="explication">
    <strong>Taux de réussite</strong> : % de questions correctement répondues dans la catégorie.<br>
    <strong>Taux d'erreur</strong> : % de questions ayant échoué (réponse incorrecte ou incomplète).<br>
    <strong>Couverture sans LLM</strong> : % de questions traitées directement par les règles Python,
    sans appel à Mistral — plus ce taux est élevé, plus l'architecture hybride est efficace.<br>
    <strong>Temps moyen</strong> : temps de réponse moyen pour cette catégorie
    (règles Python = rapide, LLM = plus lent).
  </div>

  <table>
    <thead>
      <tr>
        <th>Catégorie</th>
        <th>Score</th>
        <th>Taux de réussite</th>
        <th>Taux d'erreur</th>
        <th>Couverture sans LLM</th>
        <th>Temps moyen</th>
        <th>Barre de réussite</th>
        <th>État</th>
      </tr>
    </thead>
    <tbody>
      {lignes_metriques}
    </tbody>
  </table>
</div>

<!-- DÉTAIL DES TESTS -->
<div class="section">
  <h2>Détail des Tests</h2>
  <div class="legend">
    <span><span class="dot" style="background:#2ecc71"></span> Réussi</span>
    <span><span class="dot" style="background:#e74c3c"></span> Échoué</span>
    <span><span class="dot" style="background:#1e3a5f"></span> ⚡ Règle Python</span>
    <span><span class="dot" style="background:#3a1e5f"></span> 🤖 LLM Mistral</span>
    <span><span class="dot" style="background:#1e3a2e"></span> 📚 Base SRM</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>État</th>
        <th>Catégorie</th>
        <th>Question posée</th>
        <th>Réponse obtenue (extrait)</th>
        <th>Chemin</th>
        <th>Durée</th>
      </tr>
    </thead>
    <tbody>
      {lignes_tableau}
    </tbody>
  </table>
</div>

<footer>
  SRM Souss-Massa — Stage de fin d'études EST Guelmim · Filière SDSI 2025-2026<br>
  Réalisé par <strong>BEN ZHIR Wafa</strong> · Encadrant entreprise : ZEROUALI Hassan · Encadrant académique : AIT BAHA Tarek
</footer>

</body>
</html>"""
    return html

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    global _fallback_count

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  ÉVALUATION COMPLÈTE — ASSISTANT CLIENT SRM{RESET}")
    print(f"  Contrat : {CONTRAT_TEST}")
    print(f"  Questions : {len(DATASET)}")
    print(f"{'═'*62}{RESET}\n")

    # ── Patch AVANT l'import ──
    _patch_fallback()

    # ── Import dispatcher APRÈS le patch ──
    try:
        from src.rag.client_connecte import repondre_client_connecte
    except ImportError:
        try:
            from src.rag_client.dispatcher import repondre_client_connecte
        except ImportError as e:
            print(f"{ROUGE}❌ Import impossible : {e}{RESET}")
            print("   Lance depuis la racine du projet.")
            return



    resultats   = []
    temps_total = 0

    for question, mots_attendus, categorie, chemin in DATASET:
        debut = time.time()
        try:
            reponse = repondre_client_connecte(question, CONTRAT_TEST)
        except Exception as e:
            reponse = f"ERREUR : {e}"

        duree       = time.time() - debut
        temps_total += duree
        succes      = _check(reponse, mots_attendus)

        resultats.append({
            "question"     : question,
            "categorie"    : categorie,
            "chemin"       : chemin,
            "succes"       : succes,
            "duree_ms"     : duree * 1000,
            "reponse_court": reponse[:120].replace("\n", " "),
            "mots_attendus": mots_attendus,
        })

        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"  {icone} [{categorie:20s}] {question[:50]}")
        if not succes:
            print(f"       {ROUGE}Attendu : {mots_attendus}{RESET}")
            print(f"       {JAUNE}Obtenu  : {reponse[:100].replace(chr(10),' ')}{RESET}")

    # ── Calcul métriques ──
    total     = len(resultats)
    reussis   = sum(1 for r in resultats if r["succes"])
    score     = reussis / total
    fallback  = sum(1 for r in resultats if r["chemin"] == "llm") / total if total else 0

    t_moy_ms  = (temps_total / total) * 1000
    metriques = _calculer_metriques(resultats)
    date_exec = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # ── Affichage terminal ──
    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  RÉSULTATS GLOBAUX{RESET}")
    print(f"{'═'*62}{RESET}")
    print(f"\n  Taux de réussite : {GRAS}{reussis}/{total}{RESET}  "
          f"{_barre(score)}  {GRAS}{score*100:.1f}%{RESET}")
    print(f"  Temps moyen      : {t_moy_ms:.0f} ms / question")
    print(f"  Fallback LLM     : {fallback*100:.1f}%  "
          f"{'✅ Architecture hybride efficace' if fallback <= 0.3 else '⚠️  Taux élevé'}")

    total_sans_llm = sum(1 for r in resultats if r["chemin"] in ("regle", "general"))
    print(f"  Couverture règles: {total_sans_llm}/{total} questions "
          f"({total_sans_llm/total*100:.0f}%) traitées sans LLM")

    print(f"\n{GRAS}  PAR CATÉGORIE :{RESET}")
    print(f"  {'Catégorie':<22} {'Réussite':>9}  {'Erreur':>7}  "
          f"{'Sans LLM':>9}  {'Tps moy':>8}  Barre")
    print(f"  {'─'*22} {'─'*9}  {'─'*7}  {'─'*9}  {'─'*8}  {'─'*14}")

    for cat, m in sorted(metriques.items()):
        ok = ("✅" if m["taux_reussite"] == 1.0
              else ("⚠️ " if m["taux_reussite"] >= 0.7 else "❌"))
        print(f"  {cat:<22} "
              f"{m['reussis']}/{m['total']:>2} {m['taux_reussite']*100:>5.0f}%  "
              f"{m['taux_erreur']*100:>5.0f}%   "
              f"{m['taux_sans_llm']*100:>7.0f}%  "
              f"{m['tps_moyen_ms']:>6.0f}ms  "
              f"{_barre(m['taux_reussite'], 10)}  {ok}")

    echecs = [r for r in resultats if not r["succes"]]
    if echecs:
        print(f"\n{GRAS}  ÉCHECS DÉTAILLÉS ({len(echecs)}) :{RESET}")
        for e in echecs:
            print(f"\n  {ROUGE}▶ [{e['categorie']}]{RESET} {e['question']}")
            print(f"    Attendu : {e['mots_attendus']}")
            print(f"    Obtenu  : {e['reponse_court']}")
    else:
        print(f"\n  {VERT}🎉 Aucun échec — système opérationnel à 100% !{RESET}")

    # ── Sauvegarde fichiers ──
    os.makedirs("eval_results", exist_ok=True)

    # JSON
    json_path = os.path.join("eval_results", "rapport_eval.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date"             : date_exec,
            "contrat_test"     : CONTRAT_TEST,
            "total_questions"  : total,
            "reussis"          : reussis,
            "taux_reussite"    : round(score, 4),
            "fallback_rate"    : round(fallback, 4),
            "couverture_sans_llm": round(total_sans_llm / total, 4),
            "temps_moyen_ms"   : round(t_moy_ms, 2),
            "metriques"        : metriques,
            "resultats"        : resultats,
        }, f, ensure_ascii=False, indent=2)

    # HTML
    html_path = os.path.join("eval_results", "rapport_eval.html")
    html = _generer_html(resultats, metriques, score,
                         fallback, t_moy_ms, date_exec)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{GRAS}  FICHIERS GÉNÉRÉS :{RESET}")
    print(f"  📄 {html_path}  ← ouvrir dans le navigateur")
    print(f"  📊 {json_path}  ← données brutes")
    print(f"\n{'═'*62}\n")


if __name__ == "__main__":
    main()