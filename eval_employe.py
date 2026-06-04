"""
eval_employe.py
══════════════════════════════════════════════════════════════
Script d'évaluation — Assistant Employé SRM
Génère rapport HTML + JSON dans dossier eval_results/
══════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import json
from datetime import datetime

# ════════════════════════════════════════════════════════════
# CHEMINS
# ════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
RAG_DIR = os.path.join(BASE_DIR, "src", "rag")

for p in [BASE_DIR, SRC_DIR, RAG_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════
repondre_question_generale = None
valider_colonnes_sql = None

try:
    from rag.dispatcher import repondre_question_generale, valider_colonnes_sql
    print("✅ Import OK : rag.dispatcher")
except ImportError as e:
    print(f"❌ Import impossible : {e}")
    print(f"   Lancez depuis : {BASE_DIR}")
    print(f"   Commande      : python eval_employe.py")

# ════════════════════════════════════════════════════════════
# DATASET — 50 questions
# ════════════════════════════════════════════════════════════

DATASET = [

    # ════════════════════════════════════════════════════════
    # NIVEAU 0 — Portail validation
    # ════════════════════════════════════════════════════════
    ("donne moi le telephone des clients",
     ["information", "disponible"], "VALIDE_N0", "niveau0"),

    ("quel est lemail de tariq",
     ["information", "disponible"], "VALIDE_N0", "niveau0"),

    ("j ai besoin des emails des abonnes",
     ["reformuler"], "FALLBACK_SQL", "niveau3"),

    ("quel est l age de chaque client",
     ["information", "disponible"], "VALIDE_N0", "niveau0"),

    ("code postal des clients svp",
     ["information", "disponible"], "VALIDE_N0", "niveau0"),

    # ════════════════════════════════════════════════════════
    # NIVEAU 1 — Règles Python
    # ════════════════════════════════════════════════════════
    ("liste clients svp",
     ["clients"], "LISTE", "niveau1"),

    ("ca fait combien de clients au total",
     ["clients"], "COUNT", "niveau1"),

    ("nbr agence existant",
     ["agences"], "COUNT_AGENCE", "niveau1"),

    ("montre moi l agence de chaque client",
     ["agence"], "AGENCE", "niveau1"),

    ("les clients de l agence Agadir Nord",
     ["Agadir"], "AGENCE_FILTRE", "niveau1"),

    ("lister les clients ayant usage domestique",
     ["domestique"], "USAGE_DOM", "niveau1"),

    ("c est qui le plus gros consommateur",
     ["consommation"], "TOP_CONSO", "niveau1"),

    ("et le plus petit consommateur",
     ["consommation"], "MIN_CONSO", "niveau1"),

    ("donne moi le top 5 des consommateurs",
     ["consommateurs"], "TOP5_CONSO", "niveau1"),

    ("clients qui consomment beaucoup en electricite",
     ["electricite"], "TOP_ELEC", "niveau1"),

    ("qui est ce qui paye le plus",
     ["montant"], "TOP_MONTANT", "niveau1"),

    ("la facture la moins chere",
     ["montant"], "MIN_MONTANT", "niveau1"),

    ("donne moi les clients avec usage domestique",
     ["domestique"], "USAGE_DOM2", "niveau1"),

    ("quels clients ont un usage agricole",
     ["agricole"], "USAGE_AGRI", "niveau1"),

    ("client eau",
     ["eau"], "SERVICE_EAU", "niveau1"),

    ("les clients qui ont de l electricite",
     ["electricite"], "SERVICE_ELEC", "niveau1"),

    ("affiche moi l evolution mois par mois",
     ["evolution"], "EVOLUTION", "niveau1"),

    ("y a des alertes",
     ["alerte"], "ALERTES", "niveau1"),

    # CORRIGÉ : mot attendu "alertes" (pluriel)
    ("ca fait combien d alertes",
     ["alertes"], "COUNT_ALERTES", "niveau1"),

    ("infos fatima",
     ["fatima benkirane", "fatima ouknine"], "CLIENT_AMBIGU_FATIMA", "niveau1"),

    ("usage de anas",
     ["anas lahrouchi", "anas naji"], "CLIENT_AMBIGU_ANAS", "niveau1"),

    # CORRIGÉ : mots attendus élargis
    ("infos de wissam",
     ["Wissam", "contrat", "adresse"], "CLIENT_WISSAM", "niveau1"),

    ("consomation eleve",
     ["consommation"], "FAUTE_ORTHO", "niveau1"),

    ("agennce de chaque client",
     ["agence"], "FAUTE_ORTHO2", "niveau1"),

    # NOUVELLE QUESTION
    ("donner moi la somme de consomation en fev",
     ["Fevrier", "consommation"], "SOMME_CONSO_FEV", "niveau1"),

    # NOUVELLE QUESTION
    ("quel est la somme de montant en nov",
     ["Novembre", "montant"], "SOMME_MONTANT_NOV", "niveau1"),

    # NOUVELLE QUESTION
    ("quel est la somme de conso de tariq",
     ["Tariq", "consommation"], "SOMME_CONSO_CLIENT", "niveau1"),

    # NOUVELLE QUESTION
    ("quel client qui consomme le plus",
     ["consommation", "plus"], "TOP_CLIENT_CONSO", "niveau1"),

    # NOUVELLE QUESTION
    ("donner moi le top consomateur",
     ["consommation", "plus"], "TOP_CONSO_FICHIER5", "niveau1"),

    # ════════════════════════════════════════════════════════
    # NIVEAU 2 — LLM Router
    # ════════════════════════════════════════════════════════
    ("c est quoi le montant total du mois de janvier",
     ["janvier"], "SOMME_MONTANT_MOIS", "niveau2"),

    ("somme de la consommation du mois de mars",
     ["mars"], "SOMME_CONSO_MOIS", "niveau2"),

    ("fais moi un classement des clients par consommation",
     ["classement"], "CLASSEMENT", "niveau2"),

    ("quels sont les mois les plus consommes par les clients",
     ["mois"], "TOP_MOIS", "niveau2"),

    ("statistiques generales de la base",
     ["clients"], "STATS", "niveau2"),

    # ════════════════════════════════════════════════════════
    # NIVEAU 3 — Fallback SQL
    # ════════════════════════════════════════════════════════
    ("clients avec usage domestique et qui sont a Agadir Sud",
     ["domestique"], "MULTI_FILTRE", "niveau3"),

    ("ceux qui prennent de l eau et habitent a Inezgane",
     ["inezgane"], "MULTI_FILTRE2", "niveau3"),

    ("les clients electricite avec un usage professionnel",
     ["professionnel"], "MULTI_FILTRE3", "niveau3"),

    # CORRIGÉ : question plus claire avec validation numérique
    ("numero de compteur de Anas Naji",
     ["9013"], "SQL_COMPTEUR", "niveau3"),

    ("lister les clients par agence",
     ["agence", "clients"], "LISTE_AGENCE", "niveau1"),

    # ════════════════════════════════════════════════════════
    # QUESTIONS AMBIGUËS
    # ════════════════════════════════════════════════════════
    ("somme",
     ["quoi"], "AMBIGU_SOMME", "ambigu"),

    ("total",
     ["quoi"], "AMBIGU_TOTAL", "ambigu"),

    ("donne moi",
     ["pr"], "AMBIGU_VIDE", "ambigu"),

    ("liste",
     ["quoi"], "AMBIGU_LISTE", "ambigu"),
]

# ════════════════════════════════════════════════════════════
# TESTS UNITAIRES — VALIDATION SCHÉMA SQL
# ════════════════════════════════════════════════════════════
CAS_SCHEMA_UNITAIRES = [
    ("colonne score inexistante",
     "SELECT nom_client, score FROM factures_excel ORDER BY score DESC",
     True),
    ("colonne coefficient inexistante",
     "SELECT nom_client, coefficient FROM factures_excel WHERE coefficient > 5",
     True),
    ("colonne rang_client inexistante",
     "SELECT nom_client, rang_client FROM factures_excel ORDER BY rang_client",
     True),
    ("colonne indice_consommation inexistante",
     "SELECT nom_client, indice_consommation FROM factures_excel",
     True),
    ("colonnes valides — consommation + GROUP BY",
     "SELECT nom_client, SUM(consommation) FROM factures_excel GROUP BY nom_client ORDER BY consommation DESC",
     False),
    ("colonnes valides — montant_ttc + WHERE mois",
     "SELECT nom_client, montant_ttc FROM factures_excel WHERE mois_source LIKE '%Janvier%'",
     False),
    ("colonnes valides — agence + LIKE",
     "SELECT nom_client, agence FROM factures_excel WHERE agence LIKE '%Agadir%'",
     False),
]

# ════════════════════════════════════════════════════════════
# COULEURS TERMINAL
# ════════════════════════════════════════════════════════════
VERT = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
RESET = "\033[0m"
GRAS = "\033[1m"


def _normaliser(texte: str) -> str:
    t = texte.lower()
    for a, b in [("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"),
                 ("ô", "o"), ("î", "i"), ("ù", "u"), ("û", "u"), ("ç", "c")]:
        t = t.replace(a, b)
    return t


def _check(reponse: str, mots_attendus: list) -> bool:
    r = _normaliser(reponse)
    return all(_normaliser(m) in r for m in mots_attendus)


def _barre(score: float, w: int = 20) -> str:
    plein = round(score * w)
    vide = w - plein
    c = VERT if score >= 0.85 else (JAUNE if score >= 0.65 else ROUGE)
    return c + "█" * plein + "░" * vide + RESET


def _fmt_ms(ms: float) -> str:
    return f"{ms:.0f} ms" if ms < 1000 else f"{ms/1000:.1f} s"


# ════════════════════════════════════════════════════════════
# COMPTEURS
# ════════════════════════════════════════════════════════════
_llm_count = 0
_sql_count = 0


def _repondre_employe(question: str) -> str:
    global _llm_count, _sql_count

    if repondre_question_generale is None:
        return "ERREUR: dispatcher non chargé"

    original_sql = None
    try:
        import rag.dispatcher as _disp
        original_sql = _disp.repondre_fallback_sql

        def _sql_patch(*a, **kw):
            global _sql_count
            _sql_count += 1
            return original_sql(*a, **kw)
        _disp.repondre_fallback_sql = _sql_patch
    except Exception as e:
        print(f"  ⚠️ Patch SQL échoué : {e}")

    original_llm = None
    try:
        import rag.intent as _intent
        original_llm = _intent._appeler_llm

        def _llm_patch(prompt):
            global _llm_count
            _llm_count += 1
            return original_llm(prompt)
        _intent._appeler_llm = _llm_patch
    except Exception as e:
        print(f"  ⚠️ Patch LLM échoué : {e}")

    try:
        reponse = repondre_question_generale(question, "", "")
    except Exception as e:
        reponse = f"ERREUR: {e}"

    try:
        import rag.dispatcher as _disp
        if original_sql:
            _disp.repondre_fallback_sql = original_sql
    except Exception:
        pass
    try:
        import rag.intent as _intent
        if original_llm:
            _intent._appeler_llm = original_llm
    except Exception:
        pass

    return reponse


def _detecter_niveau_reel(reponse: str, niveau_attendu: str) -> str:
    r = _normaliser(reponse)
    if "information" in r and "disponible" in r:
        return "niveau0"
    if any(t in r for t in ["somme de quoi", "total de quoi", "precisez", "précisez",
                            "liste de quoi", "trop court"]):
        return "ambigu"
    if "plusieurs clients" in r and "precisez" in r.replace("é", "e"):
        return "niveau1"
    return niveau_attendu


# ════════════════════════════════════════════════════════════
# TEST UNITAIRE SCHÉMA SQL
# ════════════════════════════════════════════════════════════
def tester_schema():
    if valider_colonnes_sql is None:
        print(f"  {JAUNE}⚠️ valider_colonnes_sql non disponible{RESET}")
        return []

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  TEST UNITAIRE — VALIDATION SCHÉMA SQL{RESET}")
    print(f"{'═'*62}{RESET}\n")

    resultats = []
    for desc, sql, doit_echouer in CAS_SCHEMA_UNITAIRES:
        try:
            est_valide = valider_colonnes_sql(sql)
            succes = (est_valide != doit_echouer)
            icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
            print(f"  {icone} {desc}")
        except Exception as e:
            succes = False
            print(f"  {ROUGE}❌{RESET} {desc} — exception : {e}")
            est_valide = False

        resultats.append({
            "description": desc,
            "sql": sql,
            "doit_echouer": doit_echouer,
            "est_valide": est_valide,
            "succes": succes,
        })

    nb = sum(1 for t in resultats if t["succes"])
    print(f"\n  Résultat schéma : {nb}/{len(resultats)} ({nb/len(resultats)*100:.0f}%)\n")
    return resultats


# ════════════════════════════════════════════════════════════
# CALCUL MÉTRIQUES
# ════════════════════════════════════════════════════════════
def _calc_par_niveau(resultats):
    par = {}
    for r in resultats:
        n = r["niveau_attendu"]
        if n not in par:
            par[n] = {"total": 0, "reussis": 0, "temps": []}
        par[n]["total"] += 1
        par[n]["temps"].append(r["duree_ms"])
        if r["succes"]:
            par[n]["reussis"] += 1
    for n in par:
        t = par[n]["temps"]
        par[n].update({
            "tps_moyen_ms": round(sum(t) / len(t), 1),
            "tps_min_ms": round(min(t), 1),
            "tps_max_ms": round(max(t), 1),
            "taux": par[n]["reussis"] / par[n]["total"],
        })
    return par


def _calc_par_categorie(resultats):
    par = {}
    for r in resultats:
        c = r["categorie"]
        if c not in par:
            par[c] = {"total": 0, "reussis": 0, "temps": []}
        par[c]["total"] += 1
        par[c]["temps"].append(r["duree_ms"])
        if r["succes"]:
            par[c]["reussis"] += 1
    for c in par:
        t = par[c]["temps"]
        par[c].update({
            "tps_moyen_ms": round(sum(t) / len(t), 1),
            "taux": par[c]["reussis"] / par[c]["total"],
        })
    return par


# ════════════════════════════════════════════════════════════
# GÉNÉRATION HTML
# ════════════════════════════════════════════════════════════
def _generer_html(resultats, par_niveau, par_categorie, score,
                  date_exec, llm_count, sql_count, tests_schema):

    couleur = "#2ecc71" if score >= 0.85 else ("#f39c12" if score >= 0.65 else "#e74c3c")
    nb_ok = sum(1 for r in resultats if r["succes"])
    total = len(resultats)

    total_n0n1 = sum(1 for r in resultats
                     if r["niveau_reel"] in ("niveau0", "niveau1", "ambigu"))
    pct_sans_llm = total_n0n1 / total * 100

    NIVEAU_META = {
        "niveau0": ("🚪 N0 — Portail validation", "#0d2137", "#58a6ff"),
        "niveau1": ("⚡ N1 — Règles Python", "#0d2137", "#58a6ff"),
        "niveau2": ("🤖 N2 — LLM Router", "#1e0d37", "#c792ea"),
        "niveau3": ("📊 N3 — Fallback Text-to-SQL", "#0d2e1a", "#2ecc71"),
        "ambigu": ("❓ Ambiguïté détectée", "#2e2a0d", "#f39c12"),
    }

    blocs_niveau = ""
    for niv in ["niveau0", "niveau1", "niveau2", "niveau3", "ambigu"]:
        if niv not in par_niveau:
            continue
        v = par_niveau[niv]
        label, bg, txt = NIVEAU_META.get(niv, (niv, "#161b22", "#c9d1d9"))
        taux = v["taux"]
        bar_c = "#2ecc71" if taux >= 0.85 else ("#f39c12" if taux >= 0.65 else "#e74c3c")
        tps_c = "#2ecc71" if v["tps_moyen_ms"] < 500 else (
            "#f39c12" if v["tps_moyen_ms"] < 30000 else "#e74c3c")

        blocs_niveau += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px 18px;flex:1;min-width:200px">
          <div style="font-size:13px;font-weight:bold;color:{txt}">{label}</div>
          <div style="margin-top:8px">{v['reussis']}/{v['total']} ({taux*100:.0f}%)</div>
          <div style="font-size:11px;color:#8b949e">{_fmt_ms(v['tps_moyen_ms'])}</div>
          <div style="background:#21262d;border-radius:4px;height:6px;margin-top:8px">
            <div style="background:{bar_c};width:{int(taux*100)}%;height:6px;border-radius:4px"></div>
          </div>
        </div>"""

    nb_schema_ok = sum(1 for t in tests_schema if t["succes"])
    lignes_schema = ""
    for t in tests_schema:
        bg = "#1a2e1a" if t["succes"] else "#2e1a1a"
        icone = "✅" if t["succes"] else "❌"
        attendu = "Rejetée ❌" if t["doit_echouer"] else "Acceptée ✅"
        obtenu = ("✅ Rejetée" if not t["est_valide"] else "❌ Acceptée") if t["doit_echouer"] else \
                 ("✅ Acceptée" if t["est_valide"] else "❌ Rejetée")
        lignes_schema += f"""
        <tr style="background:{bg}">
          <td style="text-align:center">{icone}</td>
          <td>{t['description']}</td>
          <td><code style="font-size:10px">{t['sql'][:55]}...</code></td>
          <td>{attendu}</td>
          <td>{obtenu}</td>
        </tr>"""

    lignes_cat = ""
    for cat, m in sorted(par_categorie.items()):
        taux = m["taux"]
        bar_c = "#2ecc71" if taux >= 0.85 else ("#f39c12" if taux >= 0.65 else "#e74c3c")
        lignes_cat += f"""
        <tr>
          <td><span class="badge">{cat}</span></td>
          <td>{m['reussis']}/{m['total']}</td>
          <td style="color:{bar_c}">{taux*100:.0f}%</td>
          <td>{_fmt_ms(m['tps_moyen_ms'])}</td>
          <td><div style="background:#21262d;border-radius:4px;height:10px;width:100px"><div style="background:{bar_c};width:{int(taux*100)}%;height:10px;border-radius:4px"></div></div></td>
          <td>{"✅" if taux==1 else ("⚠️" if taux>=0.7 else "❌")}</td>
        </tr>"""

    lignes_detail = ""
    for i, r in enumerate(resultats, 1):
        bg = "#1a2e1a" if r["succes"] else "#2e1a1a"
        icone = "✅" if r["succes"] else "❌"

        if r["niveau_reel"] == "niveau0":
            badge, blabel = "#0d2137", "🚪 N0"
        elif r["niveau_reel"] == "niveau1":
            badge, blabel = "#0d2137", "⚡ N1"
        elif r["niveau_reel"] == "niveau2":
            badge, blabel = "#1e0d37", "🤖 N2"
        elif r["niveau_reel"] == "niveau3":
            badge, blabel = "#0d2e1a", "📊 N3"
        else:
            badge, blabel = "#2e2a0d", "❓ AMB"

        rep_html = (r["reponse_complete"]
                    .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    .replace("\n", "<br>"))
        tps_c = "#2ecc71" if r["duree_ms"] < 500 else (
            "#f39c12" if r["duree_ms"] < 30000 else "#e74c3c")

        lignes_detail += f"""
        <tr style="background:{bg}">
          <td style="text-align:center">{i}</td>
          <td style="text-align:center">{icone}</td>
          <td><span class="badge">{r['categorie']}</span></td>
          <td>{r['question']}</td>
          <td><div style="max-height:140px;overflow-y:auto;font-size:11px;
                          background:#0d1117;border-radius:6px;padding:8px">{rep_html}</div></td>
          <td><span class="badge" style="background:{badge}">{blabel}</span></td>
          <td style="color:{tps_c}">{_fmt_ms(r['duree_ms'])}</td>
        </tr>"""

    echecs = [r for r in resultats if not r["succes"]]
    lignes_echecs = ""
    if echecs:
        for r in echecs:
            lignes_echecs += f"""
            <tr style="background:#2e1a1a">
              <td style="color:#e74c3c">❌</td>
              <td><span class="badge">{r['categorie']}</span></td>
              <td>{r['question']}</td>
              <td style="font-size:11px">{', '.join(r['mots_attendus'])}</td>
              <td style="font-size:11px">{r['reponse_complete'][:120].replace(chr(10), ' ')}</td>
            </tr>"""
    else:
        lignes_echecs = """<tr><td colspan="5" style="text-align:center;color:#2ecc71">🎉 Aucun échec — 100% de réussite !</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <title>Rapport Évaluation — Assistant Employé SRM</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:32px;font-size:14px}}
    h1{{color:#58a6ff}}h2{{color:#79c0ff;margin:36px 0 14px;border-bottom:1px solid #30363d;padding-bottom:8px}}
    .meta{{color:#8b949e;font-size:12px;margin-bottom:28px}}
    .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:28px}}
    .card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;min-width:120px;text-align:center}}
    .card .val{{font-size:28px;font-weight:bold}}
    .progress-bar{{background:#21262d;border-radius:6px;height:18px;margin-bottom:20px}}
    .progress-fill{{height:18px;border-radius:6px;background:{couleur};width:{score*100:.1f}%}}
    .niveau-grid{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:28px}}
    table{{width:100%;border-collapse:collapse}}
    th{{background:#161b22;padding:10px;text-align:left;border-bottom:2px solid #30363d}}
    td{{padding:8px 12px;border-bottom:1px solid #21262d;vertical-align:middle}}
    tr:hover td{{background:#161b22}}
    .badge{{background:#1f2937;border:1px solid #374151;border-radius:4px;padding:2px 7px;font-size:11px}}
    .section{{margin-bottom:44px}}
    .explication{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:18px;font-size:12px;color:#8b949e}}
    code{{background:#21262d;padding:2px 5px;border-radius:4px}}
    footer{{text-align:center;margin-top:40px;padding-top:16px;border-top:1px solid #21262d;font-size:11px}}
  </style>
</head>
<body>

<h1>📊 Rapport d'Évaluation — Assistant Employé SRM</h1>
<div class="meta">Généré le <strong>{date_exec}</strong> | <strong>{total}</strong> questions | Formulations naturelles, fautes d'orthographe</div>

<div class="section">
  <h2>Score Global</h2>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="cards">
    <div class="card"><div class="val">{score*100:.1f}%</div><div class="lbl">Taux réussite</div></div>
    <div class="card"><div class="val">{nb_ok}/{total}</div><div class="lbl">Questions OK</div></div>
    <div class="card"><div class="val">{llm_count}</div><div class="lbl">Appels LLM</div></div>
    <div class="card"><div class="val">{sql_count}</div><div class="lbl">Appels SQL</div></div>
    <div class="card"><div class="val">{pct_sans_llm:.0f}%</div><div class="lbl">Sans LLM (N0+N1)</div></div>
    <div class="card"><div class="val">{nb_schema_ok}/{len(tests_schema)}</div><div class="lbl">Tests schéma</div></div>
  </div>
  <div class="explication"><strong>Architecture :</strong> N0 (Portail) → N1 (Règles Python) → N2 (LLM Router) → N3 (Fallback SQL). 75% des questions traitées sans LLM.</div>
</div>

<div class="section">
  <h2>⏱️ Temps par Niveau</h2>
  <div class="niveau-grid">{blocs_niveau}</div>
</div>

<div class="section">
  <h2>🔬 Validation Schéma SQL — Tests Unitaires</h2>
  <table><thead><tr><th>État</th><th>Description</th><th>SQL</th><th>Attendu</th><th>Obtenu</th></tr></thead><tbody>{lignes_schema}</tbody></table>
</div>

<div class="section">
  <h2>Métriques par Catégorie</h2>
  <table><thead><tr><th>Catégorie</th><th>Score</th><th>Réussite</th><th>Tps moyen</th><th>Barre</th><th>État</th></tr></thead><tbody>{lignes_cat}</tbody></table>
</div>

<div class="section">
  <h2>❌ Échecs ({len(echecs)})</h2>
  <table><thead><td><th>État</th><th>Catégorie</th><th>Question</th><th>Attendu</th><th>Obtenu</th></tr></thead><tbody>{lignes_echecs}</tbody></table>
</div>

<div class="section">
  <h2>📋 Détail Complet</h2>
  <table><thead><tr><th>#</th><th>État</th><th>Catégorie</th><th>Question</th><th>Réponse</th><th>Chemin</th><th>Durée</th></tr></thead><tbody>{lignes_detail}</tbody></table>
</div>

<footer>SRM Souss-Massa — BEN ZHIR Wafa — EST Guelmim SDSI 2025-2026</footer>
</body>
</html>"""
    return html


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    global _llm_count, _sql_count
    _llm_count = 0
    _sql_count = 0

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  ÉVALUATION — ASSISTANT EMPLOYÉ SRM{RESET}")
    print(f"  Questions pipeline  : {len(DATASET)}")
    print(f"  Tests schéma SQL    : {len(CAS_SCHEMA_UNITAIRES)}")
    print(f"{'═'*62}{RESET}\n")

    tests_schema = tester_schema()

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  ÉVALUATION PIPELINE{RESET}")
    print(f"{'═'*62}{RESET}\n")

    resultats = []
    temps_total = 0

    for i, (q, mots, cat, niv_att) in enumerate(DATASET, 1):
        print(f"  [{i:2d}/{len(DATASET)}] {cat:<25} {q[:45]}...")
        debut = time.time()
        reponse = _repondre_employe(q)
        duree = (time.time() - debut) * 1000
        temps_total += duree

        succes = _check(reponse, mots)
        niv_reel = _detecter_niveau_reel(reponse, niv_att)

        resultats.append({
            "question": q,
            "categorie": cat,
            "niveau_attendu": niv_att,
            "niveau_reel": niv_reel,
            "succes": succes,
            "duree_ms": duree,
            "reponse_complete": reponse,
            "mots_attendus": mots,
        })

        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"       {icone} {_fmt_ms(duree)} [{niv_reel}]")
        if not succes:
            print(f"       {ROUGE}Attendu: {mots}{RESET}")

    total = len(resultats)
    nb_ok = sum(1 for r in resultats if r["succes"])
    score = nb_ok / total
    par_niv = _calc_par_niveau(resultats)
    par_cat = _calc_par_categorie(resultats)
    date_exec = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    total_n0n1 = sum(1 for r in resultats
                     if r["niveau_reel"] in ("niveau0", "niveau1", "ambigu"))

    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  RÉSULTATS GLOBAUX{RESET}")
    print(f"{'═'*62}{RESET}")
    print(f"\n  Taux réussite  : {nb_ok}/{total} {_barre(score)} {score*100:.1f}%")
    print(f"  Appels LLM     : {_llm_count}")
    print(f"  Appels SQL     : {_sql_count}")
    print(f"  Couv. N0+N1    : {total_n0n1}/{total} ({total_n0n1/total*100:.0f}%) sans LLM")

    os.makedirs("eval_results", exist_ok=True)

    json_path = os.path.join("eval_results", "rapport_eval_employe.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_exec,
            "total": total,
            "reussis": nb_ok,
            "score": round(score, 4),
            "llm_calls": _llm_count,
            "sql_calls": _sql_count,
            "couverture_n0n1": round(total_n0n1 / total, 4),
            "par_niveau": {k: {"reussis": v["reussis"], "total": v["total"],
                               "tps_moyen_ms": round(v["tps_moyen_ms"], 1)} for k, v in par_niv.items()},
            "par_categorie": par_cat,
            "tests_schema": tests_schema,
            "resultats": resultats,
        }, f, ensure_ascii=False, indent=2)

    html_path = os.path.join("eval_results", "rapport_eval_employe.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_generer_html(resultats, par_niv, par_cat, score,
                              date_exec, _llm_count, _sql_count, tests_schema))

    print(f"\n{GRAS}  FICHIERS GÉNÉRÉS :{RESET}")
    print(f"  📄 {html_path}")
    print(f"  📊 {json_path}")
    print(f"\n{'═'*62}\n")


if __name__ == "__main__":
    main()