import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "srm.db")

def _connexion():
    return sqlite3.connect(DB_PATH)

# ════════════════════════════════════════════
# INFOS CLIENT
# ════════════════════════════════════════════

def get_infos(numero_contrat: str, champ: str = None) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT nom_client, agence, usage, type_service,
           adresse, numero_client, numero_contrat, numero_compteur,
           date_limite_paiement
    FROM factures_excel
    WHERE numero_contrat = ?
    ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2) DESC
    LIMIT 1
""", (numero_contrat,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Aucune information trouvée."

    _MAP = {
        "agence"   : f"**Agence :** {row[1]}",
        "usage"    : f"**Usage :** {row[2]}",
        "service"  : f"**Type de service :** {row[3]}",
        "adresse"  : f"**Adresse :** {row[4]}",
        "client"   : f"**N° Client :** {row[5]}",
        "contrat"  : f"**N° Contrat :** {row[6]}",
        "compteur" : f"**N° Compteur :** {row[7]}",
        "date_limite" : f"📅 **Date limite de paiement :** {row[8]}",
    }

    if champ and champ in _MAP:
        return _MAP[champ]

    return f"""📋 **Informations de votre compte :**

- N° Client : **{row[5]}**
- N° Contrat : **{row[6]}**
- N° Compteur : **{row[7]}**
- Adresse : **{row[4]}**
- Agence : **{row[1]}**
- Usage : **{row[2]}**
- Type service : **{row[3]}**"""

# ════════════════════════════════════════════
# MOIS SPÉCIFIQUE
# ════════════════════════════════════════════

def get_mois_specifique(numero_contrat: str, mois: str, champ: str = None, annee: str = "") -> str:
    from normalisation import normaliser_mois
    mois_norm = normaliser_mois(mois)
    
    # Si année précisée : chercher "Janvier 2026", sinon juste "Janvier"
    pattern = f"%{mois_norm}%{annee}%" if annee else f"%{mois_norm}%"
    
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc,
               periode_debut, periode_fin, date_limite_paiement
        FROM factures_excel
        WHERE numero_contrat = ? AND mois_source LIKE ?
    """, (numero_contrat, pattern))
    row = cursor.fetchone()
    conn.close()

    if not row:
        label = f"**{mois_norm} {annee}**" if annee else f"**{mois_norm}**"
        return f"Aucune facture trouvée pour {label}."

    if champ == "montant":
        return f"💰 Votre montant en **{row[0]}** : → **{row[3]:,.2f} Dhs**"
    if champ == "consommation":
        return f"⚡💧 Votre consommation en **{row[0]}** : → **{row[1]:,} {row[2]}**"

    return f"""🧾 **Votre facture — {row[0]} :**

- Période : {row[4]} → {row[5]}
- Consommation : **{row[1]:,} {row[2]}**
- Montant TTC : **{row[3]:,.2f} Dhs**
- Date limite paiement : {row[6]}"""


# ════════════════════════════════════════════
# MAX / MIN CONSOMMATION
# ════════════════════════════════════════════

def get_max_consommation(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY consommation DESC
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Aucune donnée trouvée."
    return f"📈 Votre consommation maximale :\n🏆 **{row[0]}** : {row[1]:,} {row[2]} ← MAXIMUM"


def get_min_consommation(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY consommation ASC
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Aucune donnée trouvée."
    return f"📉 Votre consommation minimale :\n🔻 **{row[0]}** : {row[1]:,} {row[2]} ← MINIMUM"


# ════════════════════════════════════════════
# MAX / MIN MONTANT
# ════════════════════════════════════════════

def get_max_montant(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY montant_ttc DESC
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Aucune donnée trouvée."
    return f"💰 Votre montant maximum :\n🏆 **{row[0]}** : {row[1]:,.2f} Dhs ← MAXIMUM"


def get_min_montant(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY montant_ttc ASC
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Aucune donnée trouvée."
    return f"💰 Votre montant minimum :\n🔻 **{row[0]}** : {row[1]:,.2f} Dhs ← MINIMUM"


# ════════════════════════════════════════════
# SOMME / MOYENNE
# ════════════════════════════════════════════

def get_somme_montant(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ROUND(SUM(montant_ttc), 2), ROUND(AVG(montant_ttc), 2),
               ROUND(MIN(montant_ttc), 2), ROUND(MAX(montant_ttc), 2),
               COUNT(*) as nb_mois
        FROM factures_excel
        WHERE numero_contrat = ?
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return "Aucune donnée trouvée."
    return f"""💰 **Total de vos paiements :**

- Montant total cumulé : **{row[0]:,.2f} Dhs**
- Nombre de mois : {row[4]}
- Montant moyen : {row[1]:,.2f} Dhs
- Montant minimum : {row[2]:,.2f} Dhs
- Montant maximum : {row[3]:,.2f} Dhs"""


def get_somme_conso(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ROUND(SUM(consommation), 2), ROUND(AVG(consommation), 2),
               ROUND(MIN(consommation), 2), ROUND(MAX(consommation), 2),
               unite, COUNT(*) as nb_mois
        FROM factures_excel
        WHERE numero_contrat = ?
        GROUP BY unite
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return "Aucune donnée trouvée."
    return f"""⚡💧 **Total de votre consommation :**

- Consommation totale : **{row[0]:,} {row[4]}**
- Nombre de mois : {row[5]}
- Consommation moyenne : {row[1]:,} {row[4]}
- Consommation minimum : {row[2]:,} {row[4]}
- Consommation maximum : {row[3]:,} {row[4]}"""


def get_moyenne(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ROUND(AVG(consommation), 2), ROUND(MIN(consommation), 2),
               ROUND(MAX(consommation), 2), unite,
               ROUND(AVG(montant_ttc), 2), ROUND(MIN(montant_ttc), 2),
               ROUND(MAX(montant_ttc), 2), COUNT(*)
        FROM factures_excel
        WHERE numero_contrat = ?
        GROUP BY unite
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Aucune donnée trouvée."
    # barre visuelle simple (sur 10)
    def _barre(val, min_val, max_val, longueur=8):
        if max_val == min_val:
            return "█" * longueur
        ratio = (val - min_val) / (max_val - min_val)
        plein = round(ratio * longueur)
        return "█" * plein + "░" * (longueur - plein)

    barre_conso   = _barre(row[0], row[1], row[2])
    barre_montant = _barre(row[4], row[5], row[6])
    return f""" **Vos statistiques sur {row[7]} mois :**

**⚡ Consommation**
| | Valeur |
|---|---|
| Moyenne | **{row[0]:,} {row[3]}** |
| Minimum | {row[1]:,} {row[3]} |
| Maximum | {row[2]:,} {row[3]} |

Min {_barre(row[1], row[1], row[2])} Max
     {barre_conso} ← votre moyenne

**💰 Montants**
| | Valeur |
|---|---|
| Moyenne | **{row[4]:,.2f} Dhs** |
| Minimum | {row[5]:,.2f} Dhs |
| Maximum | {row[6]:,.2f} Dhs |

Min {_barre(row[5], row[5], row[6])} Max
     {barre_montant} ← votre moyenne"""


# ════════════════════════════════════════════
# EVOLUTION
# ════════════════════════════════════════════

def get_evolution(numero_contrat: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune donnée trouvée."

    total_montant = sum(r[3] for r in rows)
    total_conso   = sum(r[1] for r in rows)
    moy_montant   = total_montant / len(rows)
    moy_conso     = total_conso   / len(rows)
    unite         = rows[0][2]

    # ── Tableau Markdown ──
    lignes = [
        " **Votre historique complet :**\n",
        "| Mois | Consommation | Montant | Tendance |",
        "|------|-------------|---------|----------|",
    ]

    for i, r in enumerate(rows):
        # tendance par rapport au mois précédent
        if i == 0:
            tendance = "—"
        elif r[3] > rows[i-1][3]:
            tendance = "📈 ↑"
        elif r[3] < rows[i-1][3]:
            tendance = "📉 ↓"
        else:
            tendance = "➡️ ="

        # marqueur si au-dessus de la moyenne
        flag = " 🔴" if r[3] > moy_montant * 1.2 else (" 🟢" if r[3] < moy_montant * 0.8 else "")

        lignes.append(
            f"| **{r[0]}** | {r[1]:,} {r[2]} | {r[3]:,.2f} Dhs{flag} | {tendance} |"
        )

    lignes.append(f"\n **Résumé :** {len(rows)} mois | "
                  f"Total : **{total_montant:,.2f} Dhs** | "
                  f"Moyenne : **{moy_montant:,.2f} Dhs/mois** | "
                  f"Conso totale : **{total_conso:,} {unite}**")
    lignes.append("\n🔴 = mois élevé (+20% vs moyenne)  🟢 = mois économique (-20% vs moyenne)")

    return "\n".join(lignes)


# ════════════════════════════════════════════
# PAR ANNÉE
# ════════════════════════════════════════════

def get_par_annee(numero_contrat: str, annee: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ? AND mois_source LIKE ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (numero_contrat, f"%{annee}%"))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"Aucune facture trouvée pour l'année **{annee}**."
    lignes = [f"📅 **Vos factures de {annee} :**\n"]
    total_montant = sum(r[3] for r in rows)
    total_conso = sum(r[1] for r in rows)
    for r in rows:
        lignes.append(f"- **{r[0]}** : {r[1]:,} {r[2]} | {r[3]:,.2f} Dhs")
    lignes.append(f"\n📊 Total {annee} : **{total_conso:,} {rows[0][2]}** | **{total_montant:,.2f} Dhs**")
    return "\n".join(lignes)


# ════════════════════════════════════════════
# TOP N MOIS
# ════════════════════════════════════════════

def get_top_n_conso(numero_contrat: str, n: int, ordre: str = "DESC") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, consommation, unite
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY consommation {ordre}
        LIMIT ?
    """, (numero_contrat, n))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune donnée trouvée."
    label = "plus consommés" if ordre == "DESC" else "moins consommés"
    lignes = [f"📊 **Vos {n} mois les {label} :**\n"]
    for i, r in enumerate(rows, 1):
        lignes.append(f"{i}. **{r[0]}** : {r[1]:,} {r[2]}")
    return "\n".join(lignes)


def get_top_n_montant(numero_contrat: str, n: int, ordre: str = "DESC") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT mois_source, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY montant_ttc {ordre}
        LIMIT ?
    """, (numero_contrat, n))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune donnée trouvée."
    label = "plus chers" if ordre == "DESC" else "moins chers"
    lignes = [f"💰 **Vos {n} mois les {label} :**\n"]
    for i, r in enumerate(rows, 1):
        lignes.append(f"{i}. **{r[0]}** : {r[1]:,.2f} Dhs")
    return "\n".join(lignes)


# ════════════════════════════════════════════
# DERNIERS / PREMIERS N MOIS
# ════════════════════════════════════════════

def get_derniers_n_mois(numero_contrat: str, n: int) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2) DESC
        LIMIT ?
    """, (numero_contrat, n))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune donnée trouvée."
    rows = list(reversed(rows))
    lignes = [f"📅 **Vos {n} derniers mois :**\n"]
    for r in rows:
        lignes.append(f"- **{r[0]}** : {r[1]:,} {r[2]} | {r[3]:,.2f} Dhs")
    return "\n".join(lignes)


def get_premiers_n_mois(numero_contrat: str, n: int) -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, consommation, unite, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2) ASC
        LIMIT ?
    """, (numero_contrat, n))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "Aucune donnée trouvée."
    lignes = [f"📅 **Vos {n} premiers mois :**\n"]
    for r in rows:
        lignes.append(f"- **{r[0]}** : {r[1]:,} {r[2]} | {r[3]:,.2f} Dhs")
    return "\n".join(lignes)
# ════════════════════════════════════════════
# COMPARAISON ENTRE 2 MOIS
# ════════════════════════════════════════════

def get_comparaison(numero_contrat: str, mois1: str, mois2: str) -> str:
    conn = _connexion()
    cursor = conn.cursor()

    resultats = []
    for mois in [mois1, mois2]:
        cursor.execute("""
            SELECT mois_source, consommation, unite, montant_ttc
            FROM factures_excel
            WHERE numero_contrat = ? AND mois_source LIKE ?
        """, (numero_contrat, f"%{mois}%"))
        row = cursor.fetchone()
        if row:
            resultats.append(row)

    conn.close()

    if len(resultats) < 2:
        return "Je n'ai pas trouvé les deux mois demandés."

    r1, r2 = resultats[0], resultats[1]
    diff_conso   = r2[1] - r1[1]
    diff_montant = r2[3] - r1[3]
    sens_conso   = "↑ augmenté" if diff_conso   > 0 else "↓ diminué"
    sens_montant = "↑ augmenté" if diff_montant > 0 else "↓ diminué"
    pct_conso    = round(abs(diff_conso)   / r1[1] * 100, 1) if r1[1] else 0
    pct_montant  = round(abs(diff_montant) / r1[3] * 100, 1) if r1[3] else 0
    emoji_conso   = "📈" if diff_conso   > 0 else "📉"
    emoji_montant = "📈" if diff_montant > 0 else "📉"
    return f""" **Comparaison {r1[0]} vs {r2[0]} :**

| | {r1[0]} | {r2[0]} | Évolution |
|---|---|---|---|
| ⚡ Consommation | {r1[1]:,} {r1[2]} | {r2[1]:,} {r2[2]} | {emoji_conso} {sens_conso} {pct_conso}% |
| 💰 Montant | {r1[3]:,.2f} Dhs | {r2[3]:,.2f} Dhs | {emoji_montant} {sens_montant} {pct_montant}% |"""
