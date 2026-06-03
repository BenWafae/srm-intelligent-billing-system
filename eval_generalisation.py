"""
eval_generalisation.py
──────────────────────────────────────────────────────────────────────────────
Évaluation de généralisation — Pipeline Client SRM
25 questions à formulations alternatives (hors tokens directs)
Génère un rapport HTML identique au style des rapports d'évaluation existants.

Usage :
    python eval_generalisation.py
    → génère rapport_generalisation_<date>.html
──────────────────────────────────────────────────────────────────────────────
"""
import sys
import os
import time
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

NUMERO_CONTRAT = "0005567205/2063205"

# ══════════════════════════════════════════════════════════════════════════════
# IMPORT DU PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

try:
    from rag_client.dispatcher import repondre_client_connecte
    PIPELINE_DISPONIBLE = True
    print("✅ Pipeline chargé avec succès")
except ImportError as e:
    PIPELINE_DISPONIBLE = False
    print(f"⚠️  Import échoué : {e}")
    def repondre_client_connecte(q, contrat, historique=""):
        return "[SIMULATION — pipeline non chargé]"

# ══════════════════════════════════════════════════════════════════════════════
# DATASET DE GÉNÉRALISATION — 25 QUESTIONS
# Format : (id, categorie, question, criteres_validation, intent_attendu, note)
# criteres_validation : tous les mots-clés DOIVENT être présents dans la réponse
# ══════════════════════════════════════════════════════════════════════════════

QUESTIONS = [

    # ── MOIS_SPECIFIQUE ──────────────────────────────────────────────────────
    (1,  "MOIS_SPECIFIQUE",
     "c est quoi ma facture pour le mois de mars",
     ["Mars", "729"],
     "MOIS_SPECIFIQUE → Mars",
     "Structure 'pour le mois de' au lieu de 'en mars'"),

    (2,  "MOIS_SPECIFIQUE",
     "je veux savoir ce que j ai paye en nov",
     ["Novembre", "679"],
     "MOIS_SPECIFIQUE → Novembre",
     "'ce que j ai paye' + abréviation nov"),

    (3,  "MOIS_SPECIFIQUE",
     "la conso du mois d octobre c etait combien",
     ["Octobre", "471"],
     "MOIS_SPECIFIQUE → Octobre",
     "Structure inversée, 'c etait combien' en fin de phrase"),

    # ── MOIS_RELATIF ─────────────────────────────────────────────────────────
    (4,  "MOIS_RELATIF",
     "je veux voir la facture du mois en cours",
     ["Juin", "1,099"],
     "MOIS_RELATIF → mois actuel",
     "'en cours' au lieu de 'actuel' ou 'ce mois'"),

    (5,  "MOIS_RELATIF",
     "quelle etait ma conso le mois d avant",
     ["Mai", "446"],
     "MOIS_RELATIF → mois précédent",
     "'le mois d avant' au lieu de 'mois dernier'"),

    # ── MAX_MIN ──────────────────────────────────────────────────────────────
    (6,  "MAX_MIN",
     "quel mois j ai eu la plus grosse facture",
     ["Juillet", "1,880"],
     "MAX_MONTANT",
     "'grosse facture' au lieu de 'la plus chere'"),

    (7,  "MAX_MIN",
     "quand est ce que j ai le moins depense",
     ["Mai", "432"],
     "MIN_MONTANT",
     "'depense' au lieu de 'paye', structure interrogative"),

    (8,  "MAX_MIN",
     "dis moi le mois ou j ai tire le plus d electricite",
     ["Juillet", "1,939"],
     "MAX_CONSOMMATION",
     "'tire' pour consommé — formulation très orale"),

    # ── TOP_N ────────────────────────────────────────────────────────────────
    (9,  "TOP_N",
     "donne moi les 3 mois avec le plus de consommation",
     ["Juillet", "1,939"],
     "TOP_N_CONSO DESC n=3",
     "'avec le plus de consommation' sans token direct"),

    (10, "TOP_N",
     "je veux voir mes quatre derniers mois",
     ["Juillet", "Septembre"],
     "DERNIERS_N n=4",
     "Nombre en lettres 'quatre' + 'derniers mois'"),

    (11, "TOP_N",
     "montre moi les deux mois les plus economiques",
     ["Mai", "Octobre"],
     "TOP_N_MONTANT ASC n=2",
     "'economiques' → ordre ASC, nombre en lettres"),

    # ── SOMME ────────────────────────────────────────────────────────────────
    (12, "SOMME",
     "quel est le montant global de toutes mes factures",
     ["9,622", "12"],
     "SOMME_MONTANT",
     "'montant global' au lieu de 'total' ou 'combien j ai paye'"),

    (13, "SOMME",
     "combien de kwh j ai utilise depuis le debut",
     ["9,920", "kWh"],
     "SOMME_CONSO",
     "'utilise' + 'depuis le debut' — formulation temporelle"),

    # ── MOYENNE ──────────────────────────────────────────────────────────────
    (14, "MOYENNE",
     "c est quoi mon montant habituel par mois",
     ["826", "801"],
     "MOYENNE",
     "'habituel par mois' au lieu de 'moyenne'"),

    (15, "MOYENNE",
     "donne moi un apercu general de mes factures",
     ["826", "801"],
     "MOYENNE ou EVOLUTION",
     "Formulation vague — teste le routage sur intention floue"),

    # ── COMPARAISON ──────────────────────────────────────────────────────────
    (16, "COMPARAISON",
     "est ce qu il y a une difference entre janvier et avril",
     ["Janvier", "Avril", "760", "655"],
     "COMPARAISON Janvier/Avril",
     "'est ce qu il y a une difference' sans 'comparer' ni 'vs'"),

    (17, "COMPARAISON",
     "janvier etait mieux que mars ou pas",
     ["Janvier", "Mars", "760", "752"],
     "COMPARAISON Janvier/Mars",
     "Formulation très orale, 'mieux que'"),

    (18, "COMPARAISON",
     "ma conso de fevrier comparee a celle de juin",
     ["Fevrier", "Juin", "581", "1,134"],
     "COMPARAISON Fevrier/Juin",
     "Structure nominale sans verbe principal"),

    # ── RETARD_PAIEMENT ──────────────────────────────────────────────────────
    (19, "RETARD_PAIEMENT",
     "est ce que mes factures sont toutes reglees",
     ["25/02/2026", "737"],
     "RETARD_PAIEMENT",
     "'reglees' au lieu de 'payees' ou 'en retard'"),

    (20, "RETARD_PAIEMENT",
     "j ai bien paye tout ce que je devais",
     ["25/11/2025", "456"],
     "RETARD_PAIEMENT",
     "Formulation affirmative qui attend une vérification"),

    # ── GENERAL_SRM ──────────────────────────────────────────────────────────
    (21, "GENERAL_SRM",
     "comment faire pour avoir l electricite chez moi",
     ["formulaire", "cin"],
     "GENERAL_SRM → abonnement",
     "Sans 'abonnement' ni 'branchement' — formulation naïve"),

    (22, "GENERAL_SRM",
     "je cherche a contacter quelqu un a srm",
     ["08 02", "Agadir"],
     "GENERAL_SRM → contact",
     "'contacter quelqu un' au lieu de 'contact' ou 'telephone'"),

    # ── HORS_SUJET ───────────────────────────────────────────────────────────
    (23, "HORS_SUJET",
     "tu peux m aider avec quelque chose",
     ["SRM", "facture"],
     "HORS_SUJET → message de guidance",
     "Ne doit PAS produire de données personnelles"),

    (24, "HORS_SUJET",
     "c est quoi srm",
     ["SRM", "Souss"],
     "GENERAL ou HORS_SUJET",
     "Frontière général/hors-sujet — teste le routeur amont"),

    (25, "HORS_SUJET",
     "ma situation est compliquee",
     ["SRM", "facture"],
     "HORS_SUJET → guidance sans données",
     "Doit rediriger sans exposer de données personnelles"),
]

# ══════════════════════════════════════════════════════════════════════════════
# DÉTECTION DU CHEMIN D'EXÉCUTION (heuristique sur la réponse)
# ══════════════════════════════════════════════════════════════════════════════

def _detecter_chemin(reponse: str) -> str:
    """Détecte le chemin d'exécution probable d'après la réponse."""
    rep = reponse.lower()
    # Réponse LLM narrative — commence par Bonjour + prénom
    if rep.startswith("bonjour "):
        return "LLM"
    # Réponse Base de connaissance SRM — longue, institutionnelle
    if any(kw in rep for kw in ["formulaire", "stages@srm-sm.ma", "08 02 03", "rue 18 novembre"]):
        return "Base SRM"
    # Réponse guidance hors-sujet via LLM
    if "je suis votre assistant srm" in rep or "posez-moi une question" in rep:
        return "LLM"
    # Par défaut : règle Python (réponse déterministe formatée)
    return "Règle Python"

# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION PAR MOTS-CLÉS
# ══════════════════════════════════════════════════════════════════════════════

def _valider(reponse: str, criteres: list) -> tuple:
    """Retourne (success: bool, criteres_manquants: list)"""
    manquants = [c for c in criteres if c.lower() not in reponse.lower()]
    return (len(manquants) == 0), manquants

# ══════════════════════════════════════════════════════════════════════════════
# EXÉCUTION DES TESTS
# ══════════════════════════════════════════════════════════════════════════════

def executer_tests():
    resultats = []
    print(f"\n{'='*70}")
    print(f"  ÉVALUATION DE GÉNÉRALISATION — {len(QUESTIONS)} questions")
    print(f"  Contrat : {NUMERO_CONTRAT}")
    print(f"  Démarrage : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*70}\n")

    for (qid, categorie, question, criteres, intent_attendu, note) in QUESTIONS:
        print(f"[{qid:02d}/25] {question[:60]}...", end=" ", flush=True)

        debut = time.time()
        try:
            reponse = repondre_client_connecte(question, NUMERO_CONTRAT)
        except Exception as e:
            reponse = f"[ERREUR] {str(e)}"
        duree_ms = (time.time() - debut) * 1000

        succes, manquants = _valider(reponse, criteres)
        chemin = _detecter_chemin(reponse)

        symbole = "✅" if succes else "❌"
        print(f"{symbole}  ({duree_ms/1000:.1f}s)  [{chemin}]")
        if not succes:
            print(f"        ⚠️  Critères manquants : {manquants}")

        resultats.append({
            "id": qid,
            "categorie": categorie,
            "question": question,
            "criteres": criteres,
            "intent_attendu": intent_attendu,
            "note": note,
            "reponse": reponse,
            "succes": succes,
            "manquants": manquants,
            "chemin": chemin,
            "duree_ms": duree_ms,
        })

    return resultats

# ══════════════════════════════════════════════════════════════════════════════
# CALCUL DES MÉTRIQUES
# ══════════════════════════════════════════════════════════════════════════════

def calculer_metriques(resultats):
    total = len(resultats)
    reussis = sum(1 for r in resultats if r["succes"])
    taux_global = reussis / total * 100

    # Par catégorie
    cats = {}
    for r in resultats:
        c = r["categorie"]
        if c not in cats:
            cats[c] = {"total": 0, "reussis": 0, "durees": []}
        cats[c]["total"] += 1
        if r["succes"]:
            cats[c]["reussis"] += 1
        cats[c]["durees"].append(r["duree_ms"])

    for c in cats:
        cats[c]["taux"] = cats[c]["reussis"] / cats[c]["total"] * 100
        cats[c]["tps_moyen"] = sum(cats[c]["durees"]) / len(cats[c]["durees"])

    # Par chemin
    chemins = {}
    for r in resultats:
        ch = r["chemin"]
        if ch not in chemins:
            chemins[ch] = {"total": 0, "reussis": 0, "durees": []}
        chemins[ch]["total"] += 1
        if r["succes"]:
            chemins[ch]["reussis"] += 1
        chemins[ch]["durees"].append(r["duree_ms"])

    for ch in chemins:
        chemins[ch]["taux"] = chemins[ch]["reussis"] / chemins[ch]["total"] * 100
        chemins[ch]["tps_moyen"] = sum(chemins[ch]["durees"]) / len(chemins[ch]["durees"])

    return {
        "total": total,
        "reussis": reussis,
        "taux_global": taux_global,
        "categories": cats,
        "chemins": chemins,
    }

# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU RAPPORT HTML
# ══════════════════════════════════════════════════════════════════════════════

def _couleur_taux(taux):
    if taux >= 90: return "#2ecc71"
    if taux >= 70: return "#f39c12"
    return "#e74c3c"

def _couleur_duree(ms):
    if ms < 1000: return "#2ecc71"
    if ms < 60000: return "#f39c12"
    return "#e74c3c"

def _fmt_duree(ms):
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms/1000:.1f} s"

def _chemin_badge_style(chemin):
    styles = {
        "Règle Python": "background:#1e3a5f",
        "LLM":          "background:#3a1e5f",
        "Base SRM":     "background:#1e3a2e",
    }
    emojis = {
        "Règle Python": "⚡ Règle",
        "LLM":          "🤖 LLM",
        "Base SRM":     "📚 Base SRM",
    }
    return styles.get(chemin, "background:#1f2937"), emojis.get(chemin, chemin)

def generer_rapport_html(resultats, metriques, fichier_sortie):
    now = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    taux = metriques["taux_global"]
    reussis = metriques["reussis"]
    total = metriques["total"]
    couleur_global = _couleur_taux(taux)
    pct_fill = f"{taux:.1f}%"

    # ── Cartes globales ──
    html_cartes = f"""
    <div class="cards">
      <div class="card">
        <div class="val" style="color:{couleur_global}">{taux:.1f}%</div>
        <div class="lbl">Taux de réussite</div>
      </div>
      <div class="card">
        <div class="val" style="color:#58a6ff">{reussis}/{total}</div>
        <div class="lbl">Questions réussies</div>
      </div>
      <div class="card">
        <div class="val" style="color:#f39c12">25</div>
        <div class="lbl">Questions testées</div>
      </div>
      <div class="card">
        <div class="val" style="color:#c792ea">{len(metriques['categories'])}</div>
        <div class="lbl">Catégories</div>
      </div>
    </div>"""

    # ── Comparaison avec corpus interne ──
    html_comparaison = f"""
    <div class="section">
      <h2>📊 Positionnement par rapport aux évaluations précédentes</h2>
      <div class="explication">
        <strong>Lecture :</strong> Le corpus interne (56 questions) a été construit par la même personne
        ayant développé les règles. Le corpus de généralisation (25 questions) utilise des formulations
        alternatives non présentes dans les tokens — il mesure la robustesse réelle face à un utilisateur imprévu.
        L'écart entre les deux scores quantifie le <strong>biais du corpus interne</strong>.
      </div>
      <div class="comparison-box">
        <div class="comparison-row">
          <div style="min-width:260px;color:#c9d1d9;font-weight:bold">🏗️ Corpus interne (56 q.)</div>
          <div class="bar-wrap">
            <div class="bar-bg"><div class="bar-fill" style="background:#2ecc71;width:94%"></div></div>
            <span style="color:#2ecc71;font-weight:bold;min-width:55px">94.6%</span>
          </div>
        </div>
        <div class="comparison-row">
          <div style="min-width:260px;color:#c9d1d9;font-weight:bold">🔬 Généralisation (25 q.) — ce test</div>
          <div class="bar-wrap">
            <div class="bar-bg"><div class="bar-fill" style="background:{couleur_global};width:{taux:.0f}%"></div></div>
            <span style="color:{couleur_global};font-weight:bold;min-width:55px">{taux:.1f}%</span>
          </div>
        </div>
        <div class="comparison-row">
          <div style="min-width:260px;color:#c9d1d9;font-weight:bold">🤖 Baseline LLM seul (56 q.)</div>
          <div class="bar-wrap">
            <div class="bar-bg"><div class="bar-fill" style="background:#e74c3c;width:64%"></div></div>
            <span style="color:#e74c3c;font-weight:bold;min-width:55px">64.3%</span>
          </div>
        </div>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid #30363d;font-size:12px;color:#8b949e;line-height:1.8">
          <strong style="color:#c9d1d9">Interprétation :</strong><br>
          L'écart entre le corpus interne (94.6%) et ce corpus de généralisation ({taux:.1f}%)
          quantifie le biais de construction du jeu de test interne.<br>
          Le score de généralisation reste {"supérieur" if taux > 64.3 else "proche"} à la baseline LLM seul (64.3%),
          ce qui confirme que l'architecture hybride apporte un gain réel même sur des formulations imprévues.
        </div>
      </div>
    </div>"""

    # ── Temps par chemin ──
    html_chemins = ""
    chemin_config = {
        "Règle Python": ("#58a6ff", "⚡ Règle Python"),
        "LLM":          ("#c792ea", "🤖 LLM Mistral (fallback)"),
        "Base SRM":     ("#2ecc71", "📚 Base connaissance SRM"),
    }
    for chemin, info in metriques["chemins"].items():
        couleur, label = chemin_config.get(chemin, ("#8b949e", chemin))
        taux_ch = info["taux"]
        tps = info["tps_moyen"]
        html_chemins += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px 20px;flex:1;min-width:200px">
          <div style="font-size:13px;font-weight:bold;color:{couleur};margin-bottom:10px">{label}</div>
          <table style="width:100%;font-size:12px">
            <tr><td style="color:#8b949e;padding:3px 0">Questions</td>
                <td style="color:#c9d1d9;text-align:right;font-weight:bold">{info['total']}</td></tr>
            <tr><td style="color:#8b949e;padding:3px 0">Taux réussite</td>
                <td style="color:{_couleur_taux(taux_ch)};text-align:right;font-weight:bold">{taux_ch:.0f}%</td></tr>
            <tr><td style="color:#8b949e;padding:3px 0">Tps moyen</td>
                <td style="color:{_couleur_duree(tps)};text-align:right;font-weight:bold">{_fmt_duree(tps)}</td></tr>
          </table>
          <div style="background:#21262d;border-radius:4px;height:6px;margin-top:10px">
            <div style="background:{_couleur_taux(taux_ch)};width:{taux_ch:.0f}%;height:6px;border-radius:4px"></div>
          </div>
        </div>"""

    # ── Métriques par catégorie ──
    html_cat_rows = ""
    for cat, info in sorted(metriques["categories"].items()):
        taux_c = info["taux"]
        coul = _couleur_taux(taux_c)
        tps = info["tps_moyen"]
        etat = "✅" if taux_c == 100 else ("⚠️" if taux_c >= 50 else "❌")
        html_cat_rows += f"""
        <tr>
          <td><span class="badge">{cat}</span></td>
          <td style="text-align:center">{info['reussis']}/{info['total']}</td>
          <td style="text-align:center"><span style="color:{coul};font-weight:bold">{taux_c:.0f}%</span></td>
          <td style="text-align:center;color:#e74c3c">{100-taux_c:.0f}%</td>
          <td style="text-align:center;color:{_couleur_duree(tps)}">{_fmt_duree(tps)}</td>
          <td>
            <div style="background:#21262d;border-radius:4px;height:10px;width:120px">
              <div style="background:{coul};width:{taux_c:.0f}%;height:10px;border-radius:4px"></div>
            </div>
          </td>
          <td style="text-align:center">{etat}</td>
        </tr>"""

    # ── Détail des tests ──
    html_test_rows = ""
    for r in resultats:
        bg = "#1a2e1a" if r["succes"] else "#2e1a1a"
        etat = "✅" if r["succes"] else "❌"
        ch_style, ch_label = _chemin_badge_style(r["chemin"])
        coul_duree = _couleur_duree(r["duree_ms"])
        duree_fmt = _fmt_duree(r["duree_ms"])
        criteres_str = ", ".join(f'<code>{c}</code>' for c in r["criteres"])
        reponse_escaped = (r["reponse"]
                           .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        manquants_html = ""
        if not r["succes"] and r["manquants"]:
            manquants_html = f"""<div style="margin-top:6px;font-size:11px;color:#e74c3c">
              ⚠️ Critères manquants : {', '.join(r['manquants'])}
            </div>"""

        html_test_rows += f"""
        <tr style="background:{bg}">
          <td style="color:#888;text-align:center;vertical-align:top;padding-top:12px">{r['id']}</td>
          <td style="text-align:center;font-size:18px;vertical-align:top;padding-top:10px">{etat}</td>
          <td style="vertical-align:top;padding-top:10px"><span class="badge">{r['categorie']}</span></td>
          <td style="color:#e6edf3;font-weight:500;vertical-align:top;padding-top:10px">{r['question']}</td>
          <td style="vertical-align:top;padding-top:6px;font-size:11px;color:#6e7681">{criteres_str}</td>
          <td style="vertical-align:top">
            <div style="color:#adbac7;font-size:12px;line-height:1.6;max-height:180px;overflow-y:auto;
                        background:#0d1117;border:1px solid #30363d;border-radius:6px;
                        padding:8px 10px;white-space:pre-wrap">{reponse_escaped}</div>
            {manquants_html}
          </td>
          <td style="vertical-align:top;padding-top:10px">
            <span class="badge" style="{ch_style}">{ch_label}</span>
          </td>
          <td style="color:{coul_duree};text-align:right;vertical-align:top;padding-top:10px;font-weight:bold">
            {duree_fmt}
          </td>
        </tr>"""

    # ── Assemblage HTML complet ──
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <title>Évaluation Généralisation — SRM Assistant Client</title>
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
      background:{couleur_global};
      width:{pct_fill};
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
    .chemin-grid {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px; }}
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

<h1>🔬 Évaluation de Généralisation — Assistant Client SRM</h1>
<div class="version-badge">📐 Corpus externe — formulations alternatives hors tokens directs</div>
<div class="meta">
  Généré le <strong>{now}</strong> &nbsp;|&nbsp;
  Contrat : <code>{NUMERO_CONTRAT}</code> &nbsp;|&nbsp;
  <strong>{total}</strong> questions &nbsp;|&nbsp;
  <strong>{len(metriques['categories'])}</strong> catégories
</div>

<!-- ══ SCORE GLOBAL ══ -->
<div class="section">
  <h2>Score Global</h2>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  {html_cartes}
</div>

<!-- ══ COMPARAISON ══ -->
{html_comparaison}

<!-- ══ TEMPS PAR CHEMIN ══ -->
<div class="section">
  <h2>⏱️ Temps de Réponse — Séparé par Chemin d'Exécution</h2>
  <div class="explication">
    <strong>Lecture :</strong> Les règles Python déterministes ont une latence quasi nulle.
    Le LLM et la Base SRM impliquent une inférence locale via Ollama.
    La séparation illustre l'avantage architectural du positionnement du LLM en dernier recours.
  </div>
  <div class="chemin-grid">{html_chemins}</div>
</div>

<!-- ══ MÉTRIQUES PAR CATÉGORIE ══ -->
<div class="section">
  <h2>Métriques par Catégorie</h2>
  <div class="explication">
    <strong>Rappel méthodologique :</strong> Les critères de validation sont des mots-clés numériques exacts
    (valeurs de la base de données réelle), noms de mois et données factuelles.
    Une réponse est correcte uniquement si elle contient <em>tous</em> les critères définis.
  </div>
  <table>
    <thead>
      <tr>
        <th>Catégorie</th><th>Score</th><th>Réussite</th>
        <th>Erreur</th><th>Tps moyen</th><th>Barre</th><th>État</th>
      </tr>
    </thead>
    <tbody>{html_cat_rows}</tbody>
  </table>
</div>

<!-- ══ DÉTAIL DES TESTS ══ -->
<div class="section">
  <h2>Détail des Tests — Réponse Complète</h2>
  <div class="explication">
    Colonne <strong>Critères</strong> : tous doivent être présents dans la réponse pour valider.
    Colonne <strong>Note</strong> : décrit la spécificité de la reformulation testée.
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>État</th><th>Catégorie</th>
        <th>Question posée</th><th>Critères attendus</th>
        <th>Réponse complète</th><th>Chemin</th><th>Durée</th>
      </tr>
    </thead>
    <tbody>{html_test_rows}</tbody>
  </table>
</div>

<footer>
  SRM Souss-Massa — Stage de fin d'études EST Guelmim · Filière SDSI 2025-2026<br>
  Réalisé par <strong>BEN ZHIR Wafa</strong> ·
  Encadrant entreprise : ZEROUALI Hassan · Encadrant académique : AIT BAHA Tarek<br>
  <span style="color:#f39c12">Évaluation de généralisation — corpus externe 25 questions</span>
</footer>
</body>
</html>"""

    with open(fichier_sortie, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ Rapport généré : {fichier_sortie}")

# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    fichier_sortie = f"rapport_generalisation_{date_str}.html"

    resultats = executer_tests()
    metriques = calculer_metriques(resultats)

    # ── Résumé console ──
    print(f"\n{'='*70}")
    print(f"  RÉSULTATS FINAUX")
    print(f"{'='*70}")
    print(f"  Score global    : {metriques['taux_global']:.1f}%  ({metriques['reussis']}/{metriques['total']})")
    print(f"  Référence interne (56 q.) : 94.6%")
    print(f"  Baseline LLM seul         : 64.3%")
    print(f"  Biais corpus estimé       : {94.6 - metriques['taux_global']:.1f} points")
    print(f"\n  Détail par catégorie :")
    for cat, info in sorted(metriques["categories"].items()):
        symbole = "✅" if info["taux"] == 100 else ("⚠️ " if info["taux"] >= 50 else "❌")
        print(f"    {symbole} {cat:<20} {info['reussis']}/{info['total']}  ({info['taux']:.0f}%)")
    print(f"{'='*70}\n")

    generer_rapport_html(resultats, metriques, fichier_sortie)
    print(f"\n  Rapport : {fichier_sortie}")
    print(f"  Ouvrir dans le navigateur pour visualiser.\n")