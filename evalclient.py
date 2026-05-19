"""
eval_client.py
══════════════════════════════════════════════════════════════
Script d'évaluation automatique — Assistant Client SRM
Basé sur les tests réels du document "Test semain 4"

Usage :
    python eval_client.py

Résultat :
    - Score global
    - Score par catégorie
    - Liste des échecs avec détail
    - Fallback rate (règles vs LLM)
══════════════════════════════════════════════════════════════
"""

import sys
import os
import time

# ── Ajuster les paths selon ton archi ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))

# ══════════════════════════════════════════════════════════════
# CONTRAT DE TEST — remplace par un vrai numéro de contrat
# présent dans ta base (celui utilisé dans tes tests Word)
# ══════════════════════════════════════════════════════════════
CONTRAT_TEST = "0005567205/2063205"

# ══════════════════════════════════════════════════════════════
# DATASET — toutes les questions de ton document Word
# Format : (question, [mots_attendus_dans_réponse], catégorie, chemin_attendu)
# chemin_attendu : "regle" | "llm" | "general"
# ══════════════════════════════════════════════════════════════
DATASET = [

    # ── CATÉGORIE 1 : INFOS COMPTE ──
    ("donner moi mes infos",
     ["N° Client", "N° Contrat", "Agence"],
     "INFOS_COMPTE", "regle"),

    ("mon adress",
     ["Adresse", "Inezgane"],
     "INFOS_COMPTE", "regle"),

    ("mon numero de contrat",
     ["N° Contrat", "0005567205"],
     "INFOS_COMPTE", "regle"),

    ("mon compteur",
     ["N° Compteur", "8306"],
     "INFOS_COMPTE", "regle"),

    # ── CATÉGORIE 2 : MOIS SPÉCIFIQUE ──
    ("quel est ma consomation en janvier 2026",
     ["760", "kWh", "Janvier"],
     "MOIS_SPECIFIQUE", "regle"),

    ("quel est ma conso en avrile",
     ["655", "kWh", "Avril"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture en novembre 2025",
     ["701", "679", "Novembre"],
     "MOIS_SPECIFIQUE", "regle"),

    ("combien j ai payer en mars",
     ["729", "Dhs", "Mars"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma consomation en octobre",
     ["471", "kWh", "Octobre"],
     "MOIS_SPECIFIQUE", "regle"),

    ("donner moi ma facture en janvier",
     ["Janvier", "760", "737"],
     "MOIS_SPECIFIQUE", "regle"),

    ("quel est ma consommation en janvier",
     ["760", "kWh"],
     "MOIS_SPECIFIQUE", "regle"),

    # ── CATÉGORIE 3 : CE MOIS / MOIS PRÉCÉDENT ──
    ("ma facture de ce mois",
     ["Mai 2026", "446"],
     "MOIS_RELATIF", "regle"),

    ("ma facture le mois derniers",
     ["Avril 2026", "655"],
     "MOIS_RELATIF", "regle"),

    ("quel est ma consomationn en ce mois",
     ["446", "kWh", "Mai"],
     "MOIS_RELATIF", "regle"),

    ("quel est ma consomation en mois precedente",
     ["655", "kWh", "Avril"],
     "MOIS_RELATIF", "regle"),

    # ── CATÉGORIE 4 : MAX / MIN ──
    ("quel est le mois ou j ai plus consomme",
     ["Juillet", "1,939", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("quand j ai le moins consomme",
     ["Mai", "446", "MINIMUM"],
     "MAX_MIN", "regle"),

    ("le mois ou j ai le moins consomme",
     ["Mai", "446", "MINIMUM"],
     "MAX_MIN", "regle"),

    ("mon montant le plus eleve",
     ["Juillet", "1,880", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("ma facture la plus chere",
     ["Juillet", "1,880", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("uel est ma consomation la plus eleve",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    ("ma consommation la plus elevee",
     ["Juillet", "1,939", "MAXIMUM"],
     "MAX_MIN", "regle"),

    ("quel est ma consomation la plus eleve",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    ("ma consomation maximal",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    ("ma conso max",
     ["Juillet", "1,939"],
     "MAX_MIN", "regle"),

    # ── CATÉGORIE 5 : SOMME / TOTAL ──
    ("donner moi la somme de ma consomation",
     ["9,920", "kWh", "12"],
     "SOMME", "regle"),

    ("combien j ai payer en total",
     ["9,622", "Dhs", "12"],
     "SOMME", "regle"),

    ("quel est la somme de ma consomation",
     ["9,920", "kWh"],
     "SOMME", "regle"),

    # ── CATÉGORIE 6 : HISTORIQUE / EVOLUTION ──
    ("mon historique",
     ["Octobre 2025", "Juillet 2026", "Septembre 2026"],
     "HISTORIQUE", "regle"),

    ("toute mes factures",
     ["Octobre 2025", "Juillet 2026", "12"],
     "HISTORIQUE", "regle"),

    # ── CATÉGORIE 7 : MOYENNE / STATS ──
    ("ma moyenne",
     ["826", "kWh", "801", "Dhs"],
     "MOYENNE", "regle"),

    ("mes stats",
     ["826", "kWh", "801", "Dhs"],
     "MOYENNE", "regle"),

    # ── CATÉGORIE 8 : TOP N ──
    ("les trois mois ou j ai plus consomme",
     ["Juillet 2026", "Juin 2026", "Aout 2026"],
     "TOP_N", "regle"),

    ("les deux mois le moins consomme",
     ["Mai 2026", "Octobre 2025"],
     "TOP_N", "regle"),

    ("quels sont les trois mois les plus consomme",
     ["Juillet 2026", "Juin 2026", "Aout 2026"],
     "TOP_N", "regle"),

    ("les trois mois les moins consomme",
     ["Mai 2026", "Octobre 2025", "Fevrier 2026"],
     "TOP_N", "regle"),

    ("les 4 mois les plus consommes",
     ["Juillet 2026", "Juin 2026", "Aout 2026", "Janvier 2026"],
     "TOP_N", "regle"),

    # ── CATÉGORIE 9 : COMPARAISON ──
    ("comparer ma consomation en janvier et sep",
     ["Janvier 2026", "Septembre 2026", "15.4"],
     "COMPARAISON", "regle"),

    ("comparer ma conso en ce mois avec mois dernier",
     ["Mai 2026", "Avril 2026"],
     "COMPARAISON", "regle"),

    ("janvier vs mars",
     ["Janvier 2026", "Mars 2026"],
     "COMPARAISON", "regle"),

    # ── CATÉGORIE 10 : BUG DÉTECTÉ ──
    # Ce cas échoue dans ton document — la réponse retourne juste Avril
    # au lieu de comparer ce mois vs mois précédent
    ("ma consomation par rapport au mois dernier",
     ["Mai", "Avril", "vs"],       # doit contenir les DEUX mois
     "BUG_CONNU", "regle"),

    # ── CATÉGORIE 11 : QUESTIONS GÉNÉRALES SRM ──
    ("quels document jaurais besoin pour sabonner en eau",
     ["Formulaire", "pièce d'identité"],
     "GENERAL_SRM", "general"),

    ("svp je veux passer un stage srm que je dois faire",
     ["stages@srm-sm.ma", "convention"],
     "GENERAL_SRM", "general"),

    ("je veux travaille a srm que je dois faire",
     ["mafoamanagement", "brainman"],
     "GENERAL_SRM", "general"),

    ("comment s abonner en eau",
     ["Formulaire", "pièce d'identité"],
     "GENERAL_SRM", "general"),

    ("quels documents je seais besoin pour faire un branchement",
     ["Formulaire", "pièce d'identité", "titre de propriété"],
     "GENERAL_SRM", "general"),

    ("je veux contacter srm quel est numero ou email",
     ["08 02 03 12 12", "Contact@srm-sm.ma"],
     "GENERAL_SRM", "general"),
]

# ══════════════════════════════════════════════════════════════
# COMPTEUR FALLBACK — patch pour mesurer le fallback rate
# ══════════════════════════════════════════════════════════════
_fallback_count = 0
_total_count    = 0

def _patch_fallback():
    """
    Patche repondre_client_connecte pour compter les appels au LLM fallback.
    Ne modifie pas le comportement, juste ajoute un compteur.
    """
    try:
        import src.rag.client_connecte as module
        original_fallback = module._fallback_llm

        def _fallback_patched(question, numero_contrat):
            global _fallback_count
            _fallback_count += 1
            return original_fallback(question, numero_contrat)

        module._fallback_llm = _fallback_patched
        return True
    except Exception as e:
        print(f"⚠️  Patch fallback impossible : {e}")
        return False

# ══════════════════════════════════════════════════════════════
# AFFICHAGE
# ══════════════════════════════════════════════════════════════

VERT   = "\033[92m"
ROUGE  = "\033[91m"
JAUNE  = "\033[93m"
BLEU   = "\033[94m"
RESET  = "\033[0m"
GRAS   = "\033[1m"

def _check(reponse: str, mots_attendus: list) -> bool:
    reponse_lower = reponse.lower()
    return all(mot.lower() in reponse_lower for mot in mots_attendus)

def _barre_progression(score: float, largeur: int = 20) -> str:
    plein = round(score * largeur)
    vide  = largeur - plein
    if score >= 0.85:
        couleur = VERT
    elif score >= 0.65:
        couleur = JAUNE
    else:
        couleur = ROUGE
    return couleur + "█" * plein + "░" * vide + RESET

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    global _total_count, _fallback_count

    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  ÉVALUATION ASSISTANT CLIENT SRM{RESET}")
    print(f"  Contrat de test : {CONTRAT_TEST}")
    print(f"  Questions       : {len(DATASET)}")
    print(f"{'═'*60}{RESET}\n")

    # Importer le dispatcher
    try:
        from src.rag.client_connecte import repondre_client_connecte
    except ImportError:
        try:
            from rag.client_connecte import repondre_client_connecte
        except ImportError as e:
            print(f"{ROUGE}❌ Import impossible : {e}{RESET}")
            print("   Vérifie que tu lances le script depuis la racine du projet.")
            return

    _patch_fallback()

    resultats    = []
    par_categorie = {}
    temps_total  = 0

    for question, mots_attendus, categorie, chemin in DATASET:
        _total_count += 1
        debut = time.time()

        try:
            reponse = repondre_client_connecte(question, CONTRAT_TEST)
        except Exception as e:
            reponse = f"ERREUR : {e}"

        duree = time.time() - debut
        temps_total += duree
        succes = _check(reponse, mots_attendus)

        resultats.append({
            "question"     : question,
            "categorie"    : categorie,
            "chemin"       : chemin,
            "succes"       : succes,
            "duree"        : duree,
            "reponse_court": reponse[:100].replace("\n", " "),
            "mots_attendus": mots_attendus,
        })

        # Stats par catégorie
        if categorie not in par_categorie:
            par_categorie[categorie] = {"total": 0, "reussis": 0}
        par_categorie[categorie]["total"]   += 1
        par_categorie[categorie]["reussis"] += 1 if succes else 0

        # Affichage en temps réel
        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"  {icone} [{categorie:15s}] '{question[:45]}'")
        if not succes:
            print(f"       {ROUGE}Attendu  : {mots_attendus}{RESET}")
            print(f"       {JAUNE}Réponse  : {reponse[:120].replace(chr(10), ' ')}{RESET}")

    # ── RÉSULTATS GLOBAUX ──
    total    = len(resultats)
    reussis  = sum(1 for r in resultats if r["succes"])
    score    = reussis / total
    fallback_rate = _fallback_count / _total_count if _total_count else 0

    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  RÉSULTATS{RESET}")
    print(f"{'═'*60}{RESET}")
    print(f"\n  Score global  : {GRAS}{reussis}/{total}{RESET}  "
          f"{_barre_progression(score)}  {GRAS}{score*100:.1f}%{RESET}")
    print(f"  Temps moyen   : {temps_total/total*1000:.0f} ms/question")
    print(f"  Fallback rate : {fallback_rate*100:.1f}%  "
          f"({'⚠️ Trop élevé' if fallback_rate > 0.3 else '✅ Acceptable'})")

    # ── RÉSULTATS PAR CATÉGORIE ──
    print(f"\n{GRAS}  PAR CATÉGORIE :{RESET}")
    print(f"  {'Catégorie':<20} {'Score':>8}  Barre")
    print(f"  {'─'*20} {'─'*8}  {'─'*22}")

    for cat, stats in sorted(par_categorie.items()):
        s = stats["reussis"] / stats["total"]
        icone = "✅" if s == 1.0 else ("⚠️ " if s >= 0.7 else "❌")
        print(f"  {cat:<20} {stats['reussis']}/{stats['total']:>2}     "
              f"{_barre_progression(s, 12)}  {icone}")

    # ── ÉCHECS DÉTAILLÉS ──
    echecs = [r for r in resultats if not r["succes"]]
    if echecs:
        print(f"\n{GRAS}  ÉCHECS DÉTAILLÉS ({len(echecs)}) :{RESET}")
        for e in echecs:
            print(f"\n  {ROUGE}▶ [{e['categorie']}]{RESET} {e['question']}")
            print(f"    Attendu  : {e['mots_attendus']}")
            print(f"    Obtenu   : {e['reponse_court']}")
    else:
        print(f"\n  {VERT}🎉 Aucun échec !{RESET}")

    # ── RECOMMANDATIONS ──
    print(f"\n{GRAS}  RECOMMANDATIONS :{RESET}")
    bug_connu = par_categorie.get("BUG_CONNU", {})
    if bug_connu.get("reussis", 0) < bug_connu.get("total", 1):
        print(f"  {ROUGE}▶ BUG : 'par rapport au mois dernier' → comparaison non déclenchée{RESET}")
        print(f"    Fix : dans étape 2.5, ajouter résolution du mois actuel implicite")
        print(f"    quand un seul mois est résolu + token 'par rapport'")

    if fallback_rate > 0.3:
        print(f"  {JAUNE}▶ Fallback rate élevé ({fallback_rate*100:.0f}%) → ajouter tokens{RESET}")

    score_general = par_categorie.get("GENERAL_SRM", {})
    if score_general:
        s = score_general["reussis"] / score_general["total"]
        if s < 0.9:
            print(f"  {JAUNE}▶ Questions générales SRM à {s*100:.0f}% → revoir TOKENS_GENERAL_SRM{RESET}")

    print(f"\n{'═'*60}\n")


if __name__ == "__main__":
    main()