"""
eval_generalisation.py
══════════════════════════════════════════════════════════════
Script d'évaluation — Assistant Client SRM
Test de régression — 56 questions sélectionnées
══════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))

CONTRAT_TEST = "0005567205/2063205"

DATASET = [

    # ════════════════════════════════════════
    # CATÉGORIE 1 : INFOS COMPTE — 5 questions
    # ════════════════════════════════════════
    ("donner moi mes infos",
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

    ("mon type de service",
     ["Type de service"],
     "INFOS_COMPTE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 2 : MOIS SPÉCIFIQUE — 5 questions
    # ════════════════════════════════════════
    ("donner ma conso en jan",
     ["Janvier", "kWh"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma facture de nov 2025",
     ["Novembre", "2025"],
     "MOIS_SPECIFIQUE", "regle"),

    ("combien j ai paye en mars",
     ["Mars", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    ("ma conso en juillet",
     ["Juillet", "kWh"],
     "MOIS_SPECIFIQUE", "regle"),

    ("je veux voir ma facture de octobre",
     ["Octobre", "Dhs"],
     "MOIS_SPECIFIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 3 : MOIS RELATIFS — 4 questions
    # ════════════════════════════════════════
    ("pouvez vous me donner ma facture de ce mois",
     ["Juin", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("quel est ma facture de mois dernier",
     ["Mai", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("ma facture mois actuel",
     ["Juin", "Dhs"],
     "MOIS_RELATIF", "regle"),

    ("ma conso mois precedent",
     ["Mai", "kWh"],
     "MOIS_RELATIF", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 4 : MAX / MIN — 4 questions
    # ════════════════════════════════════════
    ("les trois mois que je consomme le plus",
     ["Juillet", "kWh"],
     "MAX_MIN", "regle"),

    ("quand j ai le moins consomme",
     ["MINIMUM", "kWh"],
     "MAX_MIN", "regle"),

    ("ma facture la plus chere",
     ["Juillet", "MAXIMUM", "Dhs"],
     "MAX_MIN", "regle"),

    ("mon montant minimum",
     ["MINIMUM", "Dhs"],
     "MAX_MIN", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 5 : SOMME — 3 questions
    # ════════════════════════════════════════
    ("combien j ai paye en total",
     ["Dhs", "12"],
     "SOMME", "regle"),

    ("ma consommation totale",
     ["kWh"],
     "SOMME", "regle"),

    ("combien j ai consomme en tout",
     ["kWh"],
     "SOMME", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 6 : HISTORIQUE — 3 questions
    # ════════════════════════════════════════
    ("mon historique",
     ["Octobre 2025", "Dhs"],
     "HISTORIQUE", "regle"),

    ("toutes mes factures",
     ["Octobre 2025", "12"],
     "HISTORIQUE", "regle"),

    ("mon evolution",
     ["Octobre 2025", "Dhs"],
     "HISTORIQUE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 7 : MOYENNE — 3 questions
    # ════════════════════════════════════════
    ("ma moyenne",
     ["kWh", "Dhs"],
     "MOYENNE", "regle"),

    ("mes statistiques",
     ["kWh"],
     "MOYENNE", "regle"),

    ("mon bilan",
     ["kWh", "Dhs"],
     "MOYENNE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 8 : TOP N — 4 questions
    # ════════════════════════════════════════
    ("les trois mois ou j ai plus consomme",
     ["Juillet", "kWh"],
     "TOP_N", "regle"),

    ("les deux mois le moins consomme",
     ["kWh"],
     "TOP_N", "regle"),

    ("mes 3 derniers mois",
     ["Dhs", "kWh"],
     "TOP_N", "regle"),

    ("mes 2 premiers mois",
     ["Octobre 2025", "kWh"],
     "TOP_N", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 9 : COMPARAISON — 4 questions
    # ════════════════════════════════════════
    ("comparer ma consommation en janvier et septembre",
     ["Janvier", "Septembre"],
     "COMPARAISON", "regle"),

    ("janvier vs mars",
     ["Janvier", "Mars"],
     "COMPARAISON", "regle"),

    ("difference entre octobre et janvier",
     ["Octobre", "Janvier"],
     "COMPARAISON", "regle"),

    ("comparer fevrier et avril",
     ["Fevrier", "Avril"],
     "COMPARAISON", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 10 : RETARD PAIEMENT — 3 questions
    # ════════════════════════════════════════
    ("suis je en retard",
     ["Dhs", "date limite"],
     "RETARD_PAIEMENT", "regle"),

    ("est ce que j ai paye",
     ["Dhs"],
     "RETARD_PAIEMENT", "regle"),

    ("j ai pas encore paye",
     ["Dhs", "date limite"],
     "RETARD_PAIEMENT", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 11 : GENERAL SRM — 4 questions
    # ════════════════════════════════════════
    ("quels documents pour s abonner en eau",
     ["Formulaire"],
     "GENERAL_SRM", "general"),

    ("je veux passer un stage a srm",
     ["stages@srm-sm.ma", "convention"],
     "GENERAL_SRM", "general"),

    ("comment economiser l eau",
     ["robinet"],
     "GENERAL_SRM", "general"),

    ("adresse siege srm",
     ["Agadir", "18 Novembre"],
     "GENERAL_SRM", "general"),

    # ════════════════════════════════════════
    # CATÉGORIE 12 : FALLBACK ANALYSE — 4 questions
    # ════════════════════════════════════════
    ("est ce que ma consommation est normale",
     ["Bonjour", "kWh"],
     "FALLBACK_ANALYSE", "llm"),

    ("pourquoi je paie plus ce mois",
     ["Bonjour", "Juin"],
     "FALLBACK_ANALYSE", "llm"),

    ("expliquer pourquoi ma consomation de ce mois est plus elevee que celle du mois precedent",
     ["Bonjour", "Juin", "Mai"],
     "FALLBACK_ANALYSE", "llm"),

    ("donner moi des conseils pour reduire ma consomation",
     ["Bonjour"],
     "FALLBACK_ANALYSE", "llm"),

    # ════════════════════════════════════════
    # CATÉGORIE 13 : FAUTES ORTHO — 3 questions
    # ════════════════════════════════════════
    ("ma consomation en jan",
     ["Janvier", "kWh"],
     "FAUTES_ORTHO", "regle"),

    ("mon agennce",
     ["Agence"],
     "FAUTES_ORTHO", "regle"),

    ("ma facture le mois derniers",
     ["Mai", "Dhs"],
     "FAUTES_ORTHO", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 14 : PAR ANNÉE — 3 questions
    # ════════════════════════════════════════
    ("mes factures de 2025",
     ["2025", "Dhs"],
     "PAR_ANNEE", "regle"),

    ("toutes mes factures de l annee derniere",
     ["2025", "Dhs"],
     "PAR_ANNEE", "regle"),

    ("mes factures de 2026",
     ["2026", "Dhs"],
     "PAR_ANNEE", "regle"),

    # ════════════════════════════════════════
    # CATÉGORIE 15 : HORS SUJET — 3 questions
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
    # CATÉGORIE 16 : BUG CONNU — 1 question
    # ════════════════════════════════════════
    ("ma consommation par rapport au mois dernier",
     ["Juin", "Mai"],
     "BUG_CONNU", "regle"),

]

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
# PATCH FALLBACK
# ══════════════════════════════════════════════════════════════
_fallback_count = 0

def _patch_fallback():
    try:
        import src.rag_client.dispatcher as module_complet
    except ImportError as e:
        print(f"⚠️  Import impossible : {e}")
        return False
    if not hasattr(module_complet, "_fallback_llm"):
        return False
    sys.modules["dispatcher"]                = module_complet
    sys.modules["rag_client.dispatcher"]     = module_complet
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
# MÉTRIQUES
# ══════════════════════════════════════════════════════════════
def _calculer_metriques(resultats):
    par_cat = {}
    for r in resultats:
        cat = r["categorie"]
        if cat not in par_cat:
            par_cat[cat] = {"total": 0, "reussis": 0, "echecs": 0,
                            "temps_ms": [], "sans_llm": 0, "avec_llm": 0}
        par_cat[cat]["total"]    += 1
        par_cat[cat]["temps_ms"].append(r["duree_ms"])
        if r["succes"]:
            par_cat[cat]["reussis"] += 1
        else:
            par_cat[cat]["echecs"] += 1
        if r["chemin"] in ("regle", "general"):
            par_cat[cat]["sans_llm"] += 1
        else:
            par_cat[cat]["avec_llm"] += 1
    metriques = {}
    for cat, v in par_cat.items():
        metriques[cat] = {
            "total"        : v["total"],
            "reussis"      : v["reussis"],
            "echecs"       : v["echecs"],
            "taux_reussite": round(v["reussis"] / v["total"], 3),
            "taux_erreur"  : round(v["echecs"]  / v["total"], 3),
            "taux_sans_llm": round(v["sans_llm"] / v["total"], 3),
            "tps_moyen_ms" : round(sum(v["temps_ms"]) / len(v["temps_ms"]), 1),
        }
    return metriques


# ══════════════════════════════════════════════════════════════
# CALCUL TEMPS MOYENS PAR CHEMIN  ← NOUVEAU
# ══════════════════════════════════════════════════════════════
def _calculer_temps_par_chemin(resultats):
    """
    Retourne un dict avec le temps moyen (ms), le nb de questions
    et le taux de réussite pour chaque chemin :
      regle   → ⚡ Règle Python
      general → 📚 Base de connaissance SRM
      llm     → 🤖 LLM Mistral (fallback)
    """
    chemins = {}
    for r in resultats:
        ch = r["chemin"]
        if ch not in chemins:
            chemins[ch] = {"temps": [], "reussis": 0, "total": 0}
        chemins[ch]["temps"].append(r["duree_ms"])
        chemins[ch]["total"] += 1
        if r["succes"]:
            chemins[ch]["reussis"] += 1

    result = {}
    for ch, v in chemins.items():
        result[ch] = {
            "nb"           : v["total"],
            "tps_moyen_ms" : round(sum(v["temps"]) / len(v["temps"]), 1),
            "tps_min_ms"   : round(min(v["temps"]), 1),
            "tps_max_ms"   : round(max(v["temps"]), 1),
            "taux_reussite": round(v["reussis"] / v["total"], 3),
            "reussis"      : v["reussis"],
        }
    return result


# ══════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════
def _generer_html(resultats, metriques, score_global, fallback_rate,
                  temps_moyen_ms, date_exec, temps_par_chemin):

    couleur_score = (
        "#2ecc71" if score_global >= 0.85 else
        "#f39c12" if score_global >= 0.65 else "#e74c3c"
    )

    total_sans_llm = sum(1 for r in resultats if r["chemin"] in ("regle", "general"))
    pct_sans_llm   = total_sans_llm / len(resultats) * 100 if resultats else 0

    # ── Bloc temps par chemin  ← NOUVEAU ──────────────────────────
    CHEMIN_META = {
        "regle"  : ("⚡ Règle Python",            "#1e3a5f", "#58a6ff"),
        "general": ("📚 Base connaissance SRM",   "#1e3a2e", "#2ecc71"),
        "llm"    : ("🤖 LLM Mistral (fallback)",  "#3a1e5f", "#c792ea"),
    }

    def _fmt_ms(ms):
        if ms < 1000:
            return f"{ms:.0f} ms"
        return f"{ms/1000:.1f} s"

    blocs_chemin = ""
    for ch in ["regle", "general", "llm"]:
        if ch not in temps_par_chemin:
            continue
        v      = temps_par_chemin[ch]
        label, bg_c, txt_c = CHEMIN_META[ch]
        bar_w  = int(v["taux_reussite"] * 100)
        bar_c  = "#2ecc71" if v["taux_reussite"] >= 0.85 else ("#f39c12" if v["taux_reussite"] >= 0.65 else "#e74c3c")
        tps_color = "#2ecc71" if v["tps_moyen_ms"] < 1000 else ("#f39c12" if v["tps_moyen_ms"] < 30000 else "#e74c3c")

        blocs_chemin += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px 20px;flex:1;min-width:220px">
          <div style="font-size:13px;font-weight:bold;color:{txt_c};margin-bottom:10px">{label}</div>
          <table style="width:100%;font-size:12px">
            <tr>
              <td style="color:#8b949e;padding:3px 0">Questions</td>
              <td style="color:#c9d1d9;text-align:right;font-weight:bold">{v["nb"]}</td>
            </tr>
            <tr>
              <td style="color:#8b949e;padding:3px 0">Taux réussite</td>
              <td style="color:{bar_c};text-align:right;font-weight:bold">{v["taux_reussite"]*100:.0f}%</td>
            </tr>
            <tr>
              <td style="color:#8b949e;padding:3px 0">Tps moyen</td>
              <td style="color:{tps_color};text-align:right;font-weight:bold">{_fmt_ms(v["tps_moyen_ms"])}</td>
            </tr>
            <tr>
              <td style="color:#8b949e;padding:3px 0">Tps min</td>
              <td style="color:#c9d1d9;text-align:right">{_fmt_ms(v["tps_min_ms"])}</td>
            </tr>
            <tr>
              <td style="color:#8b949e;padding:3px 0">Tps max</td>
              <td style="color:#c9d1d9;text-align:right">{_fmt_ms(v["tps_max_ms"])}</td>
            </tr>
          </table>
          <div style="background:#21262d;border-radius:4px;height:6px;margin-top:10px">
            <div style="background:{bar_c};width:{bar_w}%;height:6px;border-radius:4px"></div>
          </div>
        </div>"""

    # ── Tableau résultats ──────────────────────────────────────────
    lignes_tableau = ""
    for i, r in enumerate(resultats, 1):
        bg    = "#1a2e1a" if r["succes"] else "#2e1a1a"
        icone = "✅" if r["succes"] else "❌"
        chemin_badge_color = (
            "#1e3a5f" if r["chemin"] == "regle" else
            "#3a1e5f" if r["chemin"] == "llm"   else "#1e3a2e"
        )
        chemin_label = (
            "⚡ Règle"   if r["chemin"] == "regle" else
            "🤖 LLM"     if r["chemin"] == "llm"   else "📚 Base SRM"
        )
        reponse_html = (
            r["reponse_complete"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        # couleur durée selon chemin
        if r["chemin"] == "regle":
            tps_c = "#2ecc71" if r["duree_ms"] < 500 else "#f39c12"
        elif r["chemin"] == "general":
            tps_c = "#f39c12" if r["duree_ms"] < 60000 else "#e74c3c"
        else:
            tps_c = "#f39c12" if r["duree_ms"] < 120000 else "#e74c3c"

        lignes_tableau += f"""
        <tr style="background:{bg}">
            <td style="color:#888;text-align:center;vertical-align:top;padding-top:12px">{i}</td>
            <td style="text-align:center;font-size:18px;vertical-align:top;padding-top:10px">{icone}</td>
            <td style="vertical-align:top;padding-top:10px"><span class="badge">{r['categorie']}</span></td>
            <td style="color:#e6edf3;font-weight:500;vertical-align:top;padding-top:10px">{r['question']}</td>
            <td style="vertical-align:top">
              <div style="color:#adbac7;font-size:12px;line-height:1.6;max-height:200px;overflow-y:auto;
                          background:#0d1117;border:1px solid #30363d;border-radius:6px;
                          padding:8px 10px;white-space:pre-wrap">{reponse_html}</div>
            </td>
            <td style="vertical-align:top;padding-top:10px">
              <span class="badge" style="background:{chemin_badge_color}">{chemin_label}</span>
            </td>
            <td style="color:{tps_c};text-align:right;vertical-align:top;padding-top:10px;font-weight:bold">
              {_fmt_ms(r['duree_ms'])}
            </td>
        </tr>"""

    # ── Tableau métriques ──────────────────────────────────────────
    lignes_metriques = ""
    for cat, m in sorted(metriques.items()):
        bar_w = int(m["taux_reussite"] * 100)
        bar_c = (
            "#2ecc71" if m["taux_reussite"] >= 0.85 else
            "#f39c12" if m["taux_reussite"] >= 0.65 else "#e74c3c"
        )
        icone_cat = "✅" if m["taux_reussite"] == 1.0 else ("⚠️" if m["taux_reussite"] >= 0.7 else "❌")
        tps_color = (
            "#2ecc71" if m["tps_moyen_ms"] < 500 else
            "#f39c12" if m["tps_moyen_ms"] < 60000 else "#e74c3c"
        )
        lignes_metriques += f"""
        <tr>
            <td><span class="badge">{cat}</span></td>
            <td style="text-align:center">{m['reussis']}/{m['total']}</td>
            <td style="text-align:center"><span style="color:{bar_c};font-weight:bold">{m['taux_reussite']*100:.0f}%</span></td>
            <td style="text-align:center;color:#e74c3c">{m['taux_erreur']*100:.0f}%</td>
            <td style="text-align:center;color:#58a6ff">{m['taux_sans_llm']*100:.0f}%</td>
            <td style="text-align:center;color:{tps_color}">{_fmt_ms(m['tps_moyen_ms'])}</td>
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
  <title>Rapport Évaluation — SRM Assistant Client</title>
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
    .chemin-grid {{
      display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px;
    }}
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
    .legend {{
      display:flex; gap:20px; font-size:12px;
      color:#8b949e; margin-bottom:14px; flex-wrap:wrap;
    }}
    .legend span {{ display:flex; align-items:center; gap:5px; }}
    .dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
    .section {{ margin-bottom:44px; }}
    .explication {{
      background:#161b22; border:1px solid #30363d;
      border-radius:8px; padding:14px 18px;
      font-size:12px; color:#8b949e;
      margin-bottom:18px; line-height:1.7;
    }}
    .explication strong {{ color:#c9d1d9; }}
    footer {{
      color:#8b949e; font-size:11px;
      margin-top:40px; text-align:center;
      border-top:1px solid #21262d; padding-top:16px;
    }}
  </style>
</head>
<body>

<h1>📊 Rapport d'Évaluation — Assistant Client SRM</h1>
<div class="meta">
  Généré le <strong>{date_exec}</strong> &nbsp;|&nbsp;
  Contrat : <code>{CONTRAT_TEST}</code> &nbsp;|&nbsp;
  <strong>{len(resultats)}</strong> questions &nbsp;|&nbsp;
  <strong>{len(metriques)}</strong> catégories
</div>

<!-- ══ SCORE GLOBAL ══ -->
<div class="section">
  <h2>Score Global</h2>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="cards">
    <div class="card">
      <div class="val" style="color:{couleur_score}">{score_global*100:.1f}%</div>
      <div class="lbl">Taux de réussite</div>
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
  </div>
</div>

<!-- ══ TEMPS PAR CHEMIN ← NOUVEAU ══ -->
<div class="section">
  <h2>⏱️ Temps de Réponse — Séparé par Chemin d'Exécution</h2>
  <div class="explication">
    <strong>Pourquoi séparer les temps ?</strong> Le temps moyen global est trompeur car il mélange
    des chemins de nature très différente. Les règles Python sont déterministes et quasi-instantanées,
    tandis que le LLM Mistral et la base de connaissance impliquent des appels réseau ou des inférences locales.
    Afficher un temps moyen unique masquerait cet avantage architectural clé.<br>
    <strong>Note :</strong> Les temps de la Base SRM et du LLM incluent le temps d'inférence de Mistral via Ollama en local.
  </div>
  <div class="chemin-grid">
    {blocs_chemin}
  </div>
</div>

<!-- ══ MÉTRIQUES PAR CATÉGORIE ══ -->
<div class="section">
  <h2>Métriques par Catégorie</h2>
  <div class="explication">
    <strong>Taux de réussite</strong> : % de questions correctement répondues.<br>
    <strong>Taux d'erreur</strong> : % de questions ayant échoué.<br>
    <strong>Couverture sans LLM</strong> : % traité par les règles Python sans appel à Mistral.<br>
    <strong>Temps moyen</strong> : affiché dans l'unité adaptée (ms ou s). Vert &lt; 500 ms, Orange &lt; 60 s, Rouge ≥ 60 s.
  </div>
  <table>
    <thead>
      <tr>
        <th>Catégorie</th><th>Score</th><th>Réussite</th>
        <th>Erreur</th><th>Sans LLM</th><th>Tps moyen</th>
        <th>Barre</th><th>État</th>
      </tr>
    </thead>
    <tbody>{lignes_metriques}</tbody>
  </table>
</div>

<!-- ══ DÉTAIL DES TESTS ══ -->
<div class="section">
  <h2>Détail des Tests — Réponse Complète</h2>
  <div class="legend">
    <span><span class="dot" style="background:#2ecc71"></span> Réussi</span>
    <span><span class="dot" style="background:#e74c3c"></span> Échoué</span>
    <span><span class="dot" style="background:#1e3a5f"></span> ⚡ Règle Python</span>
    <span><span class="dot" style="background:#3a1e5f"></span> 🤖 LLM Mistral</span>
    <span><span class="dot" style="background:#1e3a2e"></span> 📚 Base SRM</span>
  </div>
  <div class="explication">
    La colonne <strong>Durée</strong> est colorée selon le chemin :
    Vert = rapide (règle Python), Orange = acceptable (LLM/Base), Rouge = lent.
    La comparaison visuelle entre chemins illustre l'avantage des règles déterministes.
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>État</th><th>Catégorie</th>
        <th>Question posée</th><th>Réponse complète de l'assistant</th>
        <th>Chemin</th><th>Durée</th>
      </tr>
    </thead>
    <tbody>{lignes_tableau}</tbody>
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
    print(f"{GRAS}  ÉVALUATION — ASSISTANT CLIENT SRM{RESET}")
    print(f"  Contrat : {CONTRAT_TEST}")
    print(f"  Questions : {len(DATASET)}")
    print(f"{'═'*62}{RESET}\n")

    _patch_fallback()

    try:
        from src.rag.client_connecte import repondre_client_connecte
    except ImportError:
        try:
            from src.rag_client.dispatcher import repondre_client_connecte
        except ImportError as e:
            print(f"{ROUGE}❌ Import impossible : {e}{RESET}")
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
            "question"         : question,
            "categorie"        : categorie,
            "chemin"           : chemin,
            "succes"           : succes,
            "duree_ms"         : duree * 1000,
            "reponse_complete" : reponse,
            "reponse_court"    : reponse[:120].replace("\n", " "),
            "mots_attendus"    : mots_attendus,
        })

        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"  {icone} [{categorie:20s}] {question[:55]}")
        if not succes:
            print(f"       {ROUGE}Attendu : {mots_attendus}{RESET}")
            print(f"       {JAUNE}Obtenu  : {reponse[:100].replace(chr(10),' ')}{RESET}")

    total     = len(resultats)
    reussis   = sum(1 for r in resultats if r["succes"])
    score     = reussis / total
    fallback  = sum(1 for r in resultats if r["chemin"] == "llm") / total
    t_moy_ms  = (temps_total / total) * 1000
    metriques        = _calculer_metriques(resultats)
    temps_par_chemin = _calculer_temps_par_chemin(resultats)   # ← NOUVEAU
    date_exec        = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # ── Affichage terminal ──────────────────────────────────────────
    print(f"\n{GRAS}{'═'*62}{RESET}")
    print(f"{GRAS}  RÉSULTATS GLOBAUX{RESET}")
    print(f"{'═'*62}{RESET}")
    print(f"\n  Taux de réussite : {GRAS}{reussis}/{total}{RESET}  {_barre(score)}  {GRAS}{score*100:.1f}%{RESET}")
    fallback_msg = "✅ Architecture hybride efficace" if fallback <= 0.3 else "⚠️  Taux élevé"
    print(f"  Fallback LLM     : {fallback*100:.1f}%  {fallback_msg}")

    total_sans_llm = sum(1 for r in resultats if r["chemin"] in ("regle", "general"))
    print(f"  Couverture règles: {total_sans_llm}/{total} ({total_sans_llm/total*100:.0f}%) sans LLM")

    # ── Temps par chemin — terminal ────────────────────────────────
    LABELS = {"regle": "⚡ Règle Python  ", "general": "📚 Base SRM      ", "llm": "🤖 LLM Mistral   "}
    print(f"\n{GRAS}  TEMPS MOYEN PAR CHEMIN :{RESET}")
    print(f"  {'Chemin':<22} {'N':>4}  {'Réussite':>9}  {'Tps moyen':>12}  {'Tps min':>10}  {'Tps max':>10}")
    print(f"  {'─'*22} {'─'*4}  {'─'*9}  {'─'*12}  {'─'*10}  {'─'*10}")
    for ch in ["regle", "general", "llm"]:
        if ch not in temps_par_chemin:
            continue
        v = temps_par_chemin[ch]
        def _fmt(ms):
            return f"{ms:.0f} ms" if ms < 1000 else f"{ms/1000:.1f} s"
        ok = "✅" if v["taux_reussite"] == 1.0 else ("⚠️ " if v["taux_reussite"] >= 0.7 else "❌")
        print(f"  {LABELS.get(ch, ch):<22} {v['nb']:>4}  "
              f"{v['reussis']}/{v['nb']} {v['taux_reussite']*100:>5.0f}%  "
              f"{_fmt(v['tps_moyen_ms']):>12}  {_fmt(v['tps_min_ms']):>10}  {_fmt(v['tps_max_ms']):>10}  {ok}")

    print(f"\n{GRAS}  PAR CATÉGORIE :{RESET}")
    print(f"  {'Catégorie':<22} {'Réussite':>9}  {'Erreur':>7}  {'Sans LLM':>9}  {'Tps moy':>10}  Barre")
    print(f"  {'─'*22} {'─'*9}  {'─'*7}  {'─'*9}  {'─'*10}  {'─'*14}")
    for cat, m in sorted(metriques.items()):
        ok = "✅" if m["taux_reussite"] == 1.0 else ("⚠️ " if m["taux_reussite"] >= 0.7 else "❌")
        tms = m['tps_moyen_ms']
        tms_str = f"{tms:.0f} ms" if tms < 1000 else f"{tms/1000:.1f} s"
        print(f"  {cat:<22} {m['reussis']}/{m['total']:>2} {m['taux_reussite']*100:>5.0f}%  "
              f"{m['taux_erreur']*100:>5.0f}%   {m['taux_sans_llm']*100:>7.0f}%  "
              f"{tms_str:>10}  {_barre(m['taux_reussite'], 10)}  {ok}")

    echecs = [r for r in resultats if not r["succes"]]
    if echecs:
        print(f"\n{GRAS}  ÉCHECS ({len(echecs)}) :{RESET}")
        for e in echecs:
            print(f"\n  {ROUGE}▶ [{e['categorie']}]{RESET} {e['question']}")
            print(f"    Attendu : {e['mots_attendus']}")
            print(f"    Obtenu  : {e['reponse_court']}")
    else:
        print(f"\n  {VERT}🎉 100% — aucun échec !{RESET}")

    # ── Sauvegarde ──────────────────────────────────────────────────
    os.makedirs("eval_results", exist_ok=True)

    json_path = os.path.join("eval_results", "rapport_eval.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date"               : date_exec,
            "contrat_test"       : CONTRAT_TEST,
            "total_questions"    : total,
            "reussis"            : reussis,
            "taux_reussite"      : round(score, 4),
            "fallback_rate"      : round(fallback, 4),
            "couverture_sans_llm": round(total_sans_llm / total, 4),
            "temps_par_chemin"   : temps_par_chemin,          # ← NOUVEAU
            "metriques"          : metriques,
            "resultats"          : resultats,
        }, f, ensure_ascii=False, indent=2)

    html_path = os.path.join("eval_results", "rapport_eval.html")
    html = _generer_html(resultats, metriques, score, fallback,
                         t_moy_ms, date_exec, temps_par_chemin)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{GRAS}  FICHIERS GÉNÉRÉS :{RESET}")
    print(f"  📄 {html_path}")
    print(f"  📊 {json_path}")
    print(f"\n{'═'*62}\n")


if __name__ == "__main__":
    main()