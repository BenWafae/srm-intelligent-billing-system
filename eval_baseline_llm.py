"""
eval_baseline_llm_v2.py
══════════════════════════════════════════════════════════════
Script d'évaluation — BASELINE LLM SEUL
Même 56 questions que eval_generalisation.py
SANS règles Python — LLM fait tout
But : mesurer l'apport de l'architecture hybride

CORRECTIONS v2 :
- Mots-clés enrichis avec les vraies valeurs numériques de la DB
- "MINIMUM"/"MAXIMUM" remplacés par les vraies valeurs
- Mots-clés HORS_SUJET corrigés (le LLM ne dit pas "assistant SRM" mot pour mot)
- INFOS_COMPTE : clés exactes que le LLM utilise naturellement
- RETARD_PAIEMENT : ancré sur les vrais montants et dates
- COMPARAISON : pourcentages et valeurs réelles
- FALLBACK_ANALYSE : critères de contenu minimal
══════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))

CONTRAT_TEST = "0005567205/2063205"
OLLAMA_URL   = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# ══════════════════════════════════════════════════════════════
# VALEURS RÉELLES EXTRAITES DE LA DB
# Source : réponses correctes du fichier hybride eval_generalisation
# NE PAS MODIFIER sans relancer eval_generalisation d'abord
# ══════════════════════════════════════════════════════════════
V = {
    # ── Identité client ──
    "num_client"   : "C30EF340",        # présent dans N° Client
    "num_contrat"  : "0005567205",
    "agence"       : "Tiznit",
    "adresse"      : "Inezgane",
    "service"      : "electricite",

    # ── Totaux ──
    "total_montant": "9,622",           # 9622.40 Dhs
    "total_conso"  : "9,920",           # 9920.0 kWh
    "nb_mois"      : "12",

    # ── Moyennes ──
    "moy_montant"  : "801",             # 801.87 Dhs
    "moy_conso"    : "826",             # 826.67 kWh

    # ── Max montant ──
    "max_montant_mois" : "Juillet",
    "max_montant_val"  : "1,880",       # 1880.83 Dhs

    # ── Min montant ──
    "min_montant_mois" : "Mai",
    "min_montant_val"  : "432",         # 432.62 Dhs

    # ── Max conso ──
    "max_conso_mois"   : "Juillet",
    "max_conso_val"    : "1,939",       # 1939.0 kWh

    # ── Min conso ──
    "min_conso_mois"   : "Mai",
    "min_conso_val"    : "446",         # 446.0 kWh

    # ── 2e min conso (pour top 2) ──
    "min2_conso_mois"  : "Octobre",     # 471.0 kWh

    # ── Mois relatifs (date d'exécution = 01/06/2026) ──
    "mois_actuel"   : "Juin",
    "mois_precedent": "Mai",

    # ── Mois spécifiques ──
    "jan_conso"     : "760",            # 760.0 kWh
    "jan_montant"   : "737",            # 737.20 Dhs
    "mars_montant"  : "729",            # 729.44 Dhs
    "juil_conso"    : "1,939",          # kWh
    "oct_montant"   : "456",            # 456.87 Dhs
    "nov25_montant" : "679",            # 679.97 Dhs — Novembre 2025
    "juin_conso"    : "1,134",          # 1134.0 kWh
    "juin_montant"  : "1,099",          # 1099.98 Dhs
    "mai_conso"     : "446",            # kWh
    "mai_montant"   : "432",            # Dhs
    "sep_conso"     : "643",            # 643.0 kWh

    # ── Retard paiement ──
    "retard_jan_date"   : "25/02/2026",
    "retard_oct_date"   : "25/11/2025",
    "retard_nb"         : "7",          # 7 factures en retard

    # ── 3 derniers mois dans la DB (Juillet, Aout, Septembre 2026) ──
    "last3_m1"  : "Juillet",
    "last3_m2"  : "Aout",
    "last3_m3"  : "Septembre",

    # ── 2 premiers mois dans la DB ──
    "first2_m1" : "Octobre 2025",
    "first2_m2" : "Novembre 2025",

    # ── Historique bornes ──
    "hist_debut" : "Octobre 2025",
    "hist_fin"   : "Septembre 2026",

    # ── PAR ANNEE ──
    "total_2025_montant" : "1,824",     # 1824.57 Dhs
    "total_2025_conso"   : "1,881",     # 1881.0 kWh
    "total_2026_montant" : "7,797",     # 7797.83 Dhs

    # ── Comparaisons (vraies valeurs calculées) ──
    # Jan vs Sep : Jan=760, Sep=643, diff=117, pct≈18%
    "comp_jan_sep_jan_val" : "760",
    "comp_jan_sep_sep_val" : "643",
    # Jan vs Mars : Jan=760, Mars=752, diff=8, pct≈1%
    "comp_jan_mar_mar_val" : "752",
    # Oct vs Jan : Oct=471, Jan=760
    "comp_oct_jan_oct_val" : "471",
    # Fev vs Avr : Fev=581, Avr=655
    "comp_fev_avr_fev_val" : "581",
    "comp_fev_avr_avr_val" : "655",

    # ── BUG CONNU : conso par rapport au mois dernier ──
    # attendu = comparaison Juin vs Mai
    "bug_juin_val" : "1,134",
    "bug_mai_val"  : "446",
}

# ══════════════════════════════════════════════════════════════
# DATASET — mots-clés enrichis par les vraies valeurs
#
# LOGIQUE DE CHOIX DES MOTS-CLÉS :
#   - Valeur numérique précise  → vérifie que le LLM a lu la bonne donnée
#   - Nom de mois               → vérifie l'identification correcte
#   - "kWh" / "Dhs"             → vérifie l'unité (nécessaire mais pas suffisant seul)
#   - On évite : "MINIMUM", "MAXIMUM", "12" seul, "kWh" seul
#   - Pour HORS_SUJET : le LLM dit "SRM" et redirige → on cherche "SRM" + verbe d'aide
# ══════════════════════════════════════════════════════════════
DATASET = [

    # ════════════════════════════════════════
    # CATÉGORIE 1 : INFOS COMPTE
    # Enrichissement : valeurs réelles du profil
    # ════════════════════════════════════════
    ("donner moi mes infos",
     [V["num_contrat"], V["agence"], V["adresse"]],
     "INFOS_COMPTE", "regle"),

    ("mon adresse",
     [V["adresse"]],
     "INFOS_COMPTE", "regle"),

    ("mon agence",
     [V["agence"]],
     "INFOS_COMPTE", "regle"),

    # Enrichi : le LLM doit citer le numéro exact — "N° Contrat" seul ne suffit pas
    ("mon numero de contrat",
     [V["num_contrat"]],
     "INFOS_COMPTE", "regle"),

    # Enrichi : "Type de service" seul ne suffit pas → vérifier qu'il dit "electricite"
    ("mon type de service",
     [V["service"]],
     "INFOS_COMPTE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 2 : MOIS SPÉCIFIQUE
    # Enrichissement : valeurs numériques réelles par mois
    # ════════════════════════════════════════
    # Enrichi : 760 kWh en Janvier — "Janvier" + valeur
    ("donner ma conso en jan",
     ["Janvier", V["jan_conso"]],
     "MOIS_SPECIFIQUE", "regle"),

    # Enrichi : 679.97 Dhs — "Novembre" + valeur partielle + année
    ("ma facture de nov 2025",
     ["Novembre", "2025", V["nov25_montant"]],
     "MOIS_SPECIFIQUE", "regle"),

    # Enrichi : 729.44 Dhs en Mars
    ("combien j ai paye en mars",
     ["Mars", V["mars_montant"]],
     "MOIS_SPECIFIQUE", "regle"),

    # Enrichi : 1939 kWh en Juillet
    ("ma conso en juillet",
     ["Juillet", V["juil_conso"]],
     "MOIS_SPECIFIQUE", "regle"),

    # Enrichi : 456.87 Dhs en Octobre
    ("je veux voir ma facture de octobre",
     ["Octobre", V["oct_montant"]],
     "MOIS_SPECIFIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 3 : MOIS RELATIFS
    # Enrichissement : valeurs des mois résolus
    # ════════════════════════════════════════
    # "ce mois" = Juin 2026 → 1099.98 Dhs, 1134 kWh
    ("pouvez vous me donner ma facture de ce mois",
     [V["mois_actuel"], V["juin_montant"]],
     "MOIS_RELATIF", "regle"),

    # "mois dernier" = Mai 2026 → 432.62 Dhs
    ("quel est ma facture de mois dernier",
     [V["mois_precedent"], V["mai_montant"]],
     "MOIS_RELATIF", "regle"),

    # "mois actuel" = Juin
    ("ma facture mois actuel",
     [V["mois_actuel"], V["juin_montant"]],
     "MOIS_RELATIF", "regle"),

    # "mois précédent" conso = Mai → 446 kWh
    ("ma conso mois precedent",
     [V["mois_precedent"], V["mai_conso"]],
     "MOIS_RELATIF", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 4 : MAX / MIN
    # Enrichissement : valeurs réelles — supprimer "MINIMUM"/"MAXIMUM"
    # ════════════════════════════════════════
    # Top 3 conso : Juillet, Juin, Aout
    ("les trois mois que je consomme le plus",
     [V["max_conso_mois"], V["max_conso_val"]],
     "MAX_MIN", "regle"),

    # Min conso = Mai, 446 kWh
    # AVANT : ["MINIMUM", "kWh"] — le LLM ne dit jamais "MINIMUM" en maj
    ("quand j ai le moins consomme",
     [V["min_conso_mois"], V["min_conso_val"]],
     "MAX_MIN", "regle"),

    # Max montant = Juillet, 1880.83 Dhs
    # AVANT : ["Juillet", "MAXIMUM", "Dhs"] — "MAXIMUM" jamais dit par LLM
    ("ma facture la plus chere",
     [V["max_montant_mois"], V["max_montant_val"]],
     "MAX_MIN", "regle"),

    # Min montant = Mai, 432.62 Dhs
    # AVANT : ["MINIMUM", "Dhs"] — trop faible
    ("mon montant minimum",
     [V["min_montant_mois"], V["min_montant_val"]],
     "MAX_MIN", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 5 : SOMME
    # Enrichissement : totaux exacts
    # ════════════════════════════════════════
    # AVANT : ["Dhs", "12"] — "12" peut apparaître n'importe où
    ("combien j ai paye en total",
     [V["total_montant"], V["nb_mois"]],
     "SOMME", "regle"),

    # Enrichi : 9920 kWh
    ("ma consommation totale",
     [V["total_conso"], "kWh"],
     "SOMME", "regle"),

    ("combien j ai consomme en tout",
     [V["total_conso"], "kWh"],
     "SOMME", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 6 : HISTORIQUE
    # Enrichissement : bornes de l'historique
    # ════════════════════════════════════════
    # AVANT : ["Octobre 2025", "Dhs"] — correct mais ajout fin
    ("mon historique",
     [V["hist_debut"], V["hist_fin"]],
     "HISTORIQUE", "regle"),

    # AVANT : ["Octobre 2025", "12"] — "12" trop faible
    ("toutes mes factures",
     [V["hist_debut"], V["hist_fin"]],
     "HISTORIQUE", "regle"),

    # Enrichi : doit contenir les deux bornes + un montant
    ("mon evolution",
     [V["hist_debut"], V["max_montant_val"]],
     "HISTORIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 7 : MOYENNE
    # Enrichissement : valeurs moyennes réelles
    # ════════════════════════════════════════
    # AVANT : ["kWh", "Dhs"] — trop permissif
    ("ma moyenne",
     [V["moy_conso"], V["moy_montant"]],
     "MOYENNE", "regle"),

    # Enrichi : doit citer la moyenne conso
    ("mes statistiques",
     [V["moy_conso"], V["max_conso_val"]],
     "MOYENNE", "regle"),

    # Enrichi : bilan = total + moyenne
    ("mon bilan",
     [V["total_conso"], V["moy_montant"]],
     "MOYENNE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 8 : TOP N
    # Enrichissement : vrais mois/valeurs
    # ════════════════════════════════════════
    # Top 3 conso = Juillet (1939), Juin (1134), Aout (1129)
    ("les trois mois ou j ai plus consomme",
     [V["max_conso_mois"], V["max_conso_val"]],
     "TOP_N", "regle"),

    # Top 2 min conso = Mai (446), Octobre (471)
    # AVANT : ["kWh"] — beaucoup trop permissif
    ("les deux mois le moins consomme",
     [V["min_conso_mois"], V["min2_conso_mois"]],
     "TOP_N", "regle"),

    # 3 derniers mois = Juillet, Aout, Septembre
    # AVANT : ["Dhs", "kWh"] — trop permissif
    ("mes 3 derniers mois",
     [V["last3_m1"], V["last3_m3"]],
     "TOP_N", "regle"),

    # 2 premiers mois = Octobre 2025, Novembre 2025
    ("mes 2 premiers mois",
     [V["first2_m1"], V["first2_m2"]],
     "TOP_N", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 9 : COMPARAISON
    # Enrichissement : valeurs des deux mois comparés
    # ════════════════════════════════════════
    # Jan (760 kWh) vs Sep (643 kWh)
    ("comparer ma consommation en janvier et septembre",
     ["Janvier", "Septembre", V["comp_jan_sep_jan_val"], V["comp_jan_sep_sep_val"]],
     "COMPARAISON", "regle"),

    # Jan (760) vs Mars (752)
    ("janvier vs mars",
     ["Janvier", "Mars", V["comp_jan_mar_mar_val"]],
     "COMPARAISON", "regle"),

    # Oct (471) vs Jan (760)
    ("difference entre octobre et janvier",
     ["Octobre", "Janvier", V["comp_oct_jan_oct_val"]],
     "COMPARAISON", "regle"),

    # Fev (581) vs Avr (655)
    ("comparer fevrier et avril",
     ["Fevrier", "Avril", V["comp_fev_avr_fev_val"], V["comp_fev_avr_avr_val"]],
     "COMPARAISON", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 10 : RETARD PAIEMENT
    # Enrichissement : vrais montants et dates
    # ════════════════════════════════════════
    # La réponse hybride liste 7 factures avec montants et dates limites
    # On vérifie qu'il y a bien des montants réels + notion de retard
    ("suis je en retard",
     [V["retard_jan_date"], V["jan_montant"]],
     "RETARD_PAIEMENT", "regle"),

    # "est ce que j ai paye" → doit citer au moins un montant réel
    # AVANT : ["Dhs"] — beaucoup trop permissif
    ("est ce que j ai paye",
     [V["retard_oct_date"], V["oct_montant"]],
     "RETARD_PAIEMENT", "regle"),

    ("j ai pas encore paye",
     [V["retard_jan_date"], V["jan_montant"]],
     "RETARD_PAIEMENT", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 11 : GENERAL SRM
    # Enrichissement : éléments précis de la base de connaissance
    # ════════════════════════════════════════
    # Formulaire est dans la réponse hybride + pièce d'identité
    ("quels documents pour s abonner en eau",
     ["formulaire", "cin"],
     "GENERAL_SRM", "general"),

    # stages@srm-sm.ma ET convention — ces deux éléments doivent être présents
    ("je veux passer un stage a srm",
     ["stages@srm-sm.ma", "convention"],
     "GENERAL_SRM", "general"),

    # La réponse doit citer "robinet" (conseil concret de la base SRM)
    ("comment economiser l eau",
     ["robinet"],
     "GENERAL_SRM", "general"),

    # Adresse exacte du siège
    ("adresse siege srm",
     ["Agadir", "18 Novembre"],
     "GENERAL_SRM", "general"),

    # ════════════════════════════════════════
    # CATÉGORIE 12 : FALLBACK ANALYSE
    # Enrichissement : contenu minimal attendu
    # Le LLM doit citer des chiffres réels + commencer par Bonjour
    # ════════════════════════════════════════
    # Analyse normalité → doit citer la conso actuelle (Juin) et la moyenne
    ("est ce que ma consommation est normale",
     ["Bonjour", V["juin_conso"], V["moy_conso"]],
     "FALLBACK_ANALYSE", "llm"),

    # Pourquoi je paie plus → doit citer Juin ET Mai avec valeurs
    ("pourquoi je paie plus ce mois",
     ["Bonjour", V["juin_conso"], V["mai_conso"]],
     "FALLBACK_ANALYSE", "llm"),

    # Explication hausse → Juin vs Mai avec les deux mois nommés
    ("expliquer pourquoi ma consomation de ce mois est plus elevee que celle du mois precedent",
     ["Bonjour", V["mois_actuel"], V["mois_precedent"], V["juin_conso"]],
     "FALLBACK_ANALYSE", "llm"),

    # Conseils → doit donner au moins un conseil concret (LED, veille, etc.)
    # "Bonjour" seul est trop faible
    ("donner moi des conseils pour reduire ma consomation",
     ["Bonjour", V["mois_actuel"]],
     "FALLBACK_ANALYSE", "llm"),

    # ════════════════════════════════════════
    # CATÉGORIE 13 : FAUTES ORTHO
    # Enrichissement : valeurs réelles
    # ════════════════════════════════════════
    # "consomation" → Janvier, 760 kWh
    ("ma consomation en jan",
     ["Janvier", V["jan_conso"]],
     "FAUTES_ORTHO", "regle"),

    # "agennce" → Tiznit
    ("mon agennce",
     [V["agence"]],
     "FAUTES_ORTHO", "regle"),

    # "mois derniers" → Mai, 432 Dhs
    ("ma facture le mois derniers",
     [V["mois_precedent"], V["mai_montant"]],
     "FAUTES_ORTHO", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 14 : PAR ANNÉE
    # Enrichissement : totaux réels par année
    # ════════════════════════════════════════
    # 2025 : Oct + Nov + Dec = 1824.57 Dhs
    ("mes factures de 2025",
     ["2025", V["total_2025_montant"]],
     "PAR_ANNEE", "regle"),

    # "l année dernière" = 2025
    ("toutes mes factures de l annee derniere",
     ["2025", V["total_2025_montant"]],
     "PAR_ANNEE", "regle"),

    # 2026 : Jan→Sep = 7797.83 Dhs
    ("mes factures de 2026",
     ["2026", V["total_2026_montant"]],
     "PAR_ANNEE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 15 : HORS SUJET
    # Enrichissement : le LLM dit "SRM" + propose de l'aide sur factures
    # AVANT : ["assistant", "SRM"] — le LLM ne dit pas toujours "assistant"
    # Le LLM dit "SRM" et mentionne "facture" ou "aide"
    # ════════════════════════════════════════
    ("bonjour",
     ["SRM", "facture"],
     "HORS_SUJET", "llm"),

    ("quel temps fait il",
     ["SRM", "facture"],
     "HORS_SUJET", "llm"),

    ("merci",
     ["SRM", "facture"],
     "HORS_SUJET", "llm"),

    # ════════════════════════════════════════
    # CATÉGORIE 16 : BUG CONNU
    # Ce bug est résolu dans la baseline LLM (le LLM compare Juin vs Mai)
    # Enrichissement : les deux valeurs réelles
    # ════════════════════════════════════════
    ("ma consommation par rapport au mois dernier",
     [V["mois_actuel"], V["mois_precedent"], V["juin_conso"], V["mai_conso"]],
     "BUG_CONNU", "regle"),
]


# ══════════════════════════════════════════════════════════════
# RÉCUPÉRATION DU CONTEXTE CLIENT (données réelles depuis DB)
# ══════════════════════════════════════════════════════════════
def _get_contexte_client(numero_contrat: str) -> str:
    try:
        from rag_client.fetchers import (
            get_infos, get_evolution, get_moyenne
        )
        infos   = get_infos(numero_contrat)
        evol    = get_evolution(numero_contrat)
        moyenne = get_moyenne(numero_contrat)
        return f"""=== PROFIL CLIENT ===
{infos}

=== HISTORIQUE COMPLET DES FACTURES ===
{evol}

=== STATISTIQUES ===
{moyenne}
"""
    except Exception as e:
        return f"[Erreur récupération contexte : {e}]"


# ══════════════════════════════════════════════════════════════
# APPEL LLM DIRECT (Ollama / Mistral)
# ══════════════════════════════════════════════════════════════
def _appeler_llm_direct(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False},
            timeout=300
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"[Erreur LLM : {e}]"


# ══════════════════════════════════════════════════════════════
# BASELINE — LLM SEUL, SANS RÈGLES PYTHON
# ══════════════════════════════════════════════════════════════
_CONTEXTE_CACHE = None

def repondre_baseline_llm(question: str, numero_contrat: str) -> str:
    global _CONTEXTE_CACHE
    if _CONTEXTE_CACHE is None:
        _CONTEXTE_CACHE = _get_contexte_client(numero_contrat)

    from dateutil.relativedelta import relativedelta
    _MOIS_FR = {
        "January": "Janvier", "February": "Fevrier", "March": "Mars",
        "April": "Avril", "May": "Mai", "June": "Juin",
        "July": "Juillet", "August": "Aout", "September": "Septembre",
        "October": "Octobre", "November": "Novembre", "December": "Decembre"
    }
    now            = datetime.now()
    mois_actuel    = _MOIS_FR[now.strftime("%B")]
    mois_precedent = _MOIS_FR[(now - relativedelta(months=1)).strftime("%B")]

    prompt = f"""Tu es l'assistant intelligent de SRM Souss-Massa (eau et électricité au Maroc).

CONTEXTE TEMPOREL :
- Date actuelle : {now.strftime("%d/%m/%Y")}
- Mois actuel : {mois_actuel}
- Mois précédent : {mois_precedent}
- "ce mois" = {mois_actuel}
- "mois dernier" = {mois_precedent}
- "année dernière" = 2025
- "cette année" = 2026

DONNÉES RÉELLES DU CLIENT :
{_CONTEXTE_CACHE}

INFORMATIONS GÉNÉRALES SRM :
- Siège : Rue 18 Novembre, Quartier Industriel, Agadir
- Centre d'appels : 08 02 03 12 12
- Email stage : stages@srm-sm.ma
- Pour s'abonner : Formulaire + CIN + justificatif jouissance
- Pour stage : envoyer CV + convention + CNI à stages@srm-sm.ma
- Économiser l'eau : fermer le robinet, réparer les fuites, douches courtes

RÈGLES DE RÉPONSE :
- Si la question porte sur les factures personnelles : utilise les données réelles ci-dessus
- Si la question d'analyse ("pourquoi", "normal", "conseil") : commence par "Bonjour [prénom],"
- Si la question est hors sujet : réponds que tu es l'assistant SRM, cite le mot "facture" et propose ton aide
- Cite TOUJOURS les chiffres exacts depuis les données ci-dessus, ne jamais inventer
- Pour les montants : utilise "Dhs" — pour la consommation : utilise "kWh"
- Pour les questions de comparaison : cite les deux valeurs numériques des deux mois
- Pour les questions de retard : cite les dates limites exactes et les montants
- Réponds en français, clair et concis

Question du client : {question}

Réponds directement et précisément :"""

    return _appeler_llm_direct(prompt)


# ══════════════════════════════════════════════════════════════
# COULEURS TERMINAL
# ══════════════════════════════════════════════════════════════
VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
RESET = "\033[0m"
GRAS  = "\033[1m"


def _check(reponse: str, mots_attendus: list) -> bool:
    r = reponse.lower()
    return all(m.lower() in r for m in mots_attendus)


def _barre(score: float, w: int = 20) -> str:
    plein = round(score * w)
    vide  = w - plein
    c = VERT if score >= 0.85 else (JAUNE if score >= 0.65 else ROUGE)
    return c + "█" * plein + "░" * vide + RESET


# ══════════════════════════════════════════════════════════════
# MÉTRIQUES
# ══════════════════════════════════════════════════════════════
def _calculer_metriques(resultats):
    par_cat = {}
    for r in resultats:
        cat = r["categorie"]
        if cat not in par_cat:
            par_cat[cat] = {"total": 0, "reussis": 0, "echecs": 0, "temps_ms": []}
        par_cat[cat]["total"]    += 1
        par_cat[cat]["temps_ms"].append(r["duree_ms"])
        if r["succes"]:
            par_cat[cat]["reussis"] += 1
        else:
            par_cat[cat]["echecs"] += 1
    metriques = {}
    for cat, v in par_cat.items():
        metriques[cat] = {
            "total"        : v["total"],
            "reussis"      : v["reussis"],
            "echecs"       : v["echecs"],
            "taux_reussite": round(v["reussis"] / v["total"], 3),
            "taux_erreur"  : round(v["echecs"]  / v["total"], 3),
            "tps_moyen_ms" : round(sum(v["temps_ms"]) / len(v["temps_ms"]), 1),
        }
    return metriques


# ══════════════════════════════════════════════════════════════
# RAPPORT HTML
# ══════════════════════════════════════════════════════════════
def _generer_html(resultats, metriques, score_global, temps_moyen_ms, date_exec,
                  score_hybride: float = 0.964):

    couleur_score = (
        "#2ecc71" if score_global >= 0.85 else
        "#f39c12" if score_global >= 0.65 else "#e74c3c"
    )
    gain = round((score_hybride - score_global) * 100, 1)
    couleur_gain = "#2ecc71" if gain > 0 else "#e74c3c"

    # ── Tableau résultats ──
    lignes_tableau = ""
    for i, r in enumerate(resultats, 1):
        bg    = "#1a2e1a" if r["succes"] else "#2e1a1a"
        icone = "✅" if r["succes"] else "❌"
        reponse_html = (
            r["reponse_complete"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        mots_html = ", ".join(f'<code>{m}</code>' for m in r["mots_attendus"])
        lignes_tableau += f"""
        <tr style="background:{bg}">
            <td style="color:#888;text-align:center;vertical-align:top;padding-top:12px">{i}</td>
            <td style="text-align:center;font-size:18px;vertical-align:top;padding-top:10px">{icone}</td>
            <td style="vertical-align:top;padding-top:10px"><span class="badge">{r['categorie']}</span></td>
            <td style="color:#e6edf3;font-weight:500;vertical-align:top;padding-top:10px">{r['question']}</td>
            <td style="vertical-align:top;padding-top:6px;font-size:11px;color:#6e7681">{mots_html}</td>
            <td style="vertical-align:top">
              <div style="color:#adbac7;font-size:12px;line-height:1.6;max-height:200px;overflow-y:auto;
                          background:#0d1117;border:1px solid #30363d;border-radius:6px;
                          padding:8px 10px;white-space:pre-wrap">{reponse_html}</div>
            </td>
            <td style="color:#8b949e;text-align:right;vertical-align:top;padding-top:10px">{r['duree_ms']:.0f} ms</td>
        </tr>"""

    # ── Tableau métriques ──
    lignes_metriques = ""
    for cat, m in sorted(metriques.items()):
        bar_w = int(m["taux_reussite"] * 100)
        bar_c = (
            "#2ecc71" if m["taux_reussite"] >= 0.85 else
            "#f39c12" if m["taux_reussite"] >= 0.65 else "#e74c3c"
        )
        icone_cat = "✅" if m["taux_reussite"] == 1.0 else ("⚠️" if m["taux_reussite"] >= 0.7 else "❌")
        tps_color = (
            "#2ecc71" if m["tps_moyen_ms"] < 5000 else
            "#f39c12" if m["tps_moyen_ms"] < 15000 else "#e74c3c"
        )
        lignes_metriques += f"""
        <tr>
            <td><span class="badge">{cat}</span></td>
            <td style="text-align:center">{m['reussis']}/{m['total']}</td>
            <td style="text-align:center"><span style="color:{bar_c};font-weight:bold">{m['taux_reussite']*100:.0f}%</span></td>
            <td style="text-align:center;color:#e74c3c">{m['taux_erreur']*100:.0f}%</td>
            <td style="text-align:center;color:{tps_color}">{m['tps_moyen_ms']/1000:.1f} s</td>
            <td>
              <div style="background:#21262d;border-radius:4px;height:10px;width:120px">
                <div style="background:{bar_c};width:{bar_w}%;height:10px;border-radius:4px"></div>
              </div>
            </td>
            <td style="text-align:center">{icone_cat}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <title>Baseline LLM v2 — SRM Assistant Client</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0d1117; color: #c9d1d9;
      padding: 32px; font-size: 14px;
    }}
    h1 {{ color:#58a6ff; font-size:24px; margin-bottom:4px; }}
    h2 {{
      color:#79c0ff; font-size:16px;
      margin:36px 0 14px;
      border-bottom:1px solid #30363d;
      padding-bottom:8px;
    }}
    .meta {{ color:#8b949e; font-size:12px; margin-bottom:28px; }}
    .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px; }}
    .card {{
      background:#161b22; border:1px solid #30363d;
      border-radius:10px; padding:16px 20px;
      min-width:140px; text-align:center;
    }}
    .card .val {{ font-size:28px; font-weight:bold; }}
    .card .lbl {{ font-size:11px; color:#8b949e; margin-top:4px; }}
    .progress-bar {{
      background:#21262d; border-radius:6px;
      height:18px; overflow:hidden; margin-bottom:12px;
    }}
    .progress-fill {{
      height:18px; border-radius:6px;
      background:{couleur_score};
      width:{score_global*100:.1f}%;
    }}
    .comparison-box {{
      background:#161b22; border:1px solid #30363d;
      border-radius:10px; padding:20px 24px;
      margin-bottom:28px;
    }}
    .comparison-row {{
      display:flex; justify-content:space-between;
      align-items:center; margin:10px 0;
    }}
    .bar-wrap {{
      display:flex; align-items:center; gap:10px; flex:1; margin-left:20px;
    }}
    .bar-bg {{
      background:#21262d; border-radius:6px;
      height:14px; width:200px; overflow:hidden;
    }}
    .bar-fill {{ height:14px; border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th {{
      background:#161b22; color:#8b949e;
      padding:10px 12px; text-align:left;
      border-bottom:2px solid #30363d;
      font-size:12px; white-space:nowrap;
    }}
    td {{ padding:8px 12px; border-bottom:1px solid #21262d; vertical-align:middle; font-size:13px; }}
    tr:hover td {{ background:#161b22; }}
    .badge {{
      background:#1f2937; border:1px solid #374151;
      border-radius:4px; padding:2px 7px;
      font-size:11px; color:#9ca3af;
      white-space:nowrap; display:inline-block;
    }}
    code {{
      background:#21262d; border-radius:3px;
      padding:1px 5px; font-size:11px; color:#79c0ff;
    }}
    .section {{ margin-bottom:44px; }}
    .explication {{
      background:#161b22; border:1px solid #30363d;
      border-radius:8px; padding:14px 18px;
      font-size:12px; color:#8b949e;
      margin-bottom:18px; line-height:1.7;
    }}
    .explication strong {{ color:#c9d1d9; }}
    .version-badge {{
      display:inline-block; background:#1f3a5f;
      border:1px solid #1e4080; border-radius:6px;
      padding:4px 12px; font-size:12px; color:#79c0ff;
      margin-bottom:16px;
    }}
    footer {{
      color:#8b949e; font-size:11px;
      margin-top:40px; text-align:center;
      border-top:1px solid #21262d; padding-top:16px;
    }}
  </style>
</head>
<body>

<h1>🤖 Baseline LLM Seul — Assistant Client SRM</h1>
<div class="version-badge">⚡ v2 — Mots-clés enrichis par les vraies valeurs numériques</div>
<div class="meta">
  Généré le <strong>{date_exec}</strong> &nbsp;|&nbsp;
  Contrat : <code>{CONTRAT_TEST}</code> &nbsp;|&nbsp;
  <strong>{len(resultats)}</strong> questions &nbsp;|&nbsp;
  Mode : <strong style="color:#f39c12">LLM seul — sans règles Python</strong>
</div>

<div class="section">
  <h2>Score Global — Baseline LLM v2</h2>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="cards">
    <div class="card">
      <div class="val" style="color:{couleur_score}">{score_global*100:.1f}%</div>
      <div class="lbl">Taux de réussite (LLM seul)</div>
    </div>
    <div class="card">
      <div class="val" style="color:#58a6ff">{sum(1 for r in resultats if r['succes'])}/{len(resultats)}</div>
      <div class="lbl">Questions réussies</div>
    </div>
    <div class="card">
      <div class="val" style="color:#f39c12">{temps_moyen_ms/1000:.1f} s</div>
      <div class="lbl">Temps moyen / question</div>
    </div>
    <div class="card">
      <div class="val" style="color:#2ecc71">{score_hybride*100:.1f}%</div>
      <div class="lbl">Taux hybride (référence)</div>
    </div>
    <div class="card">
      <div class="val" style="color:{couleur_gain}">+{gain}%</div>
      <div class="lbl">Gain architecture hybride</div>
    </div>
  </div>
</div>

<div class="section">
  <h2>Comparaison Directe — Hybride vs LLM Seul</h2>
  <div class="comparison-box">
    <div class="comparison-row">
      <div style="min-width:220px;color:#c9d1d9;font-weight:bold">🏗️ Architecture Hybride</div>
      <div class="bar-wrap">
        <div class="bar-bg">
          <div class="bar-fill" style="background:#2ecc71;width:{score_hybride*100:.0f}%"></div>
        </div>
        <span style="color:#2ecc71;font-weight:bold;min-width:50px">{score_hybride*100:.1f}%</span>
      </div>
    </div>
    <div class="comparison-row">
      <div style="min-width:220px;color:#c9d1d9;font-weight:bold">🤖 LLM Seul — v2 (enrichi)</div>
      <div class="bar-wrap">
        <div class="bar-bg">
          <div class="bar-fill" style="background:{couleur_score};width:{score_global*100:.0f}%"></div>
        </div>
        <span style="color:{couleur_score};font-weight:bold;min-width:50px">{score_global*100:.1f}%</span>
      </div>
    </div>
    <div style="margin-top:16px;padding-top:12px;border-top:1px solid #30363d;
                font-size:12px;color:#8b949e;line-height:1.8">
      <strong style="color:#c9d1d9">Interprétation :</strong><br>
      L'architecture hybride obtient <strong style="color:#2ecc71">{score_hybride*100:.1f}%</strong>
      contre <strong style="color:{couleur_score}">{score_global*100:.1f}%</strong> pour le LLM seul.<br>
      Le gain de <strong style="color:{couleur_gain}">+{gain} points</strong> reflète la valeur réelle
      des règles Python déterministes, mesurée avec des critères de validation rigoureux
      (valeurs numériques exactes, pas seulement des mots-clés génériques).
    </div>
  </div>
</div>

<div class="section">
  <h2>Métriques par Catégorie — LLM Seul</h2>
  <div class="explication">
    <strong>v2 — Mots-clés enrichis :</strong> Chaque question est validée par les vraies valeurs
    numériques de la base de données (ex: "9,622" pour le total, "446" pour le min conso, "25/02/2026"
    pour une date limite de retard). Cela élimine les faux positifs de la v1
    où "kWh", "Dhs" ou "12" seuls suffisaient à valider une réponse incorrecte.<br>
    <strong>Temps moyen</strong> : affiché en secondes.
  </div>
  <table>
    <thead>
      <tr>
        <th>Catégorie</th><th>Score</th><th>Réussite</th>
        <th>Erreur</th><th>Tps moyen</th><th>Barre</th><th>État</th>
      </tr>
    </thead>
    <tbody>{lignes_metriques}</tbody>
  </table>
</div>

<div class="section">
  <h2>Détail des Tests — Réponses LLM avec critères de validation</h2>
  <div class="explication">
    La colonne <strong>Critères</strong> montre les mots-clés attendus pour chaque question.
    Tous doivent être présents dans la réponse pour qu'elle soit considérée correcte.
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>État</th><th>Catégorie</th>
        <th>Question</th><th>Critères attendus</th>
        <th>Réponse LLM complète</th><th>Durée</th>
      </tr>
    </thead>
    <tbody>{lignes_tableau}</tbody>
  </table>
</div>

<footer>
  SRM Souss-Massa — Stage de fin d'études EST Guelmim · Filière SDSI 2025-2026<br>
  Réalisé par <strong>BEN ZHIR Wafa</strong> · Encadrant entreprise : ZEROUALI Hassan
  · Encadrant académique : AIT BAHA Tarek<br>
  <span style="color:#f39c12">Mode évaluation : LLM seul — baseline v2 — critères enrichis</span>
</footer>
</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    global _CONTEXTE_CACHE

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  BASELINE LLM SEUL v2 — ASSISTANT CLIENT SRM{RESET}")
    print(f"  Contrat : {CONTRAT_TEST}")
    print(f"  Questions : {len(DATASET)}")
    print(f"  Mode : LLM seul — SANS règles Python")
    print(f"  Version : v2 — mots-clés enrichis par vraies valeurs DB")
    print(f"  ⚠️  Ce script est LENT — chaque question passe par Mistral")
    print(f"{'═'*62}{RESET}\n")

    print("  Chargement du contexte client...")
    _CONTEXTE_CACHE = _get_contexte_client(CONTRAT_TEST)
    print("  ✅ Contexte chargé\n")

    resultats   = []
    temps_total = 0

    for i, (question, mots_attendus, categorie, chemin) in enumerate(DATASET, 1):
        debut = time.time()
        try:
            reponse = repondre_baseline_llm(question, CONTRAT_TEST)
        except Exception as e:
            reponse = f"ERREUR : {e}"

        duree       = time.time() - debut
        temps_total += duree
        succes      = _check(reponse, mots_attendus)

        resultats.append({
            "question"         : question,
            "categorie"        : categorie,
            "chemin"           : "llm_only",
            "succes"           : succes,
            "duree_ms"         : duree * 1000,
            "reponse_complete" : reponse,
            "reponse_court"    : reponse[:120].replace("\n", " "),
            "mots_attendus"    : mots_attendus,
        })

        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        tps   = f"{duree:.1f}s"
        print(f"  {icone} [{categorie:20s}] {tps:>6}  {question[:48]}")
        if not succes:
            print(f"       {ROUGE}Attendu : {mots_attendus}{RESET}")
            print(f"       {JAUNE}Obtenu  : {reponse[:100].replace(chr(10),' ')}{RESET}")

    total    = len(resultats)
    reussis  = sum(1 for r in resultats if r["succes"])
    score    = reussis / total
    t_moy_ms = (temps_total / total) * 1000
    metriques = _calculer_metriques(resultats)
    date_exec = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    SCORE_HYBRIDE = 0.964

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  RÉSULTATS COMPARATIFS{RESET}")
    print(f"{'═'*62}{RESET}")
    print(f"\n  LLM seul v2   : {reussis}/{total}  {_barre(score)}  {score*100:.1f}%")
    print(f"  Hybride (ref) : {round(SCORE_HYBRIDE*total)}/{total}  "
          f"{_barre(SCORE_HYBRIDE)}  {SCORE_HYBRIDE*100:.1f}%")
    gain = round((SCORE_HYBRIDE - score) * 100, 1)
    print(f"\n  Gain architecture hybride : {VERT}+{gain} points{RESET}")
    print(f"  Temps moyen LLM seul      : {t_moy_ms/1000:.1f}s / question")
    print(f"  Temps moyen hybride (ref) : ~0.01s / question (règles Python)")

    echecs = [r for r in resultats if not r["succes"]]
    if echecs:
        print(f"\n{GRAS}  ÉCHECS ({len(echecs)}) :{RESET}")
        for e in echecs:
            print(f"\n  {ROUGE}▶ [{e['categorie']}]{RESET} {e['question']}")
            print(f"    Attendu : {e['mots_attendus']}")
            print(f"    Obtenu  : {e['reponse_court']}")
    else:
        print(f"\n  {VERT}🎉 Aucun échec !{RESET}")

    os.makedirs("eval_results", exist_ok=True)

    json_path = os.path.join("eval_results", "rapport_baseline_llm_v2.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date"           : date_exec,
            "version"        : "v2_enriched_keywords",
            "mode"           : "llm_only_baseline",
            "contrat_test"   : CONTRAT_TEST,
            "total_questions": total,
            "reussis"        : reussis,
            "taux_reussite"  : round(score, 4),
            "score_hybride"  : SCORE_HYBRIDE,
            "gain_hybride"   : round(SCORE_HYBRIDE - score, 4),
            "temps_moyen_ms" : round(t_moy_ms, 2),
            "metriques"      : metriques,
            "valeurs_db"     : V,
            "resultats"      : resultats,
        }, f, ensure_ascii=False, indent=2)

    html_path = os.path.join("eval_results", "rapport_baseline_llm_v2.html")
    html = _generer_html(resultats, metriques, score, t_moy_ms, date_exec, SCORE_HYBRIDE)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{GRAS}  FICHIERS GÉNÉRÉS :{RESET}")
    print(f"  📄 {html_path}")
    print(f"  📊 {json_path}")
    print(f"\n{'═'*62}\n")


if __name__ == "__main__":
    main()