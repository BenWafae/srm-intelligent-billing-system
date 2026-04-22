# src/rag/fetchers_generaux.py
import sqlite3
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from normalisation import normaliser_mois, normaliser_usage
from rag.mode import _normaliser_q

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "srm.db")


def _connexion():
    return sqlite3.connect(DB_PATH)


def fetch_liste_clients(mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, usage, type_service,
               COUNT(*) as nb_mois,
               ROUND(SUM(montant_ttc), 2) as total_ttc
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY nom_client
    """)
    rows = cursor.fetchall()
    conn.close()

    if mode == "count":
        return f"Il y a **{len(rows)} clients** dans la base."
    if mode == "list":
        lignes = [f"Liste des **{len(rows)} clients** :"]
        for i, r in enumerate(rows, 1):
            lignes.append(f"{i}. {r[0]}")
        return "\n".join(lignes)

    lignes = [f"Il y a **{len(rows)} clients** dans la base :\n"]
    for i, r in enumerate(rows, 1):
        lignes.append(
            f"{i}. **{r[0]}** — {r[1]} | {r[2]} | {r[3]} | "
            f"{r[4]} mois | Total cumulé : {r[5]:,.2f} Dhs"
        )
    return "\n".join(lignes)


def fetch_top_consommateurs(mois: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if mois:
        mois = normaliser_mois(mois)
        cursor.execute("""
            SELECT nom_client, consommation, unite, mois_source
            FROM factures_excel
            WHERE mois_source LIKE ?
            ORDER BY consommation DESC
        """, (f"%{mois}%",))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return f"Aucune donnée trouvée pour le mois {mois}."

        eau  = [r for r in rows if r[2] == "m³"]
        elec = [r for r in rows if r[2] == "kWh"]

        if mode in ("top1", "count"):
            lignes = [f"Client avec la consommation la plus élevée en **{mois}** :"]
            if eau:
                lignes.append(f"💧 Eau : **{eau[0][0]}** — {eau[0][1]:,} m³")
            if elec:
                elec_s = sorted(elec, key=lambda r: r[1], reverse=True)
                lignes.append(f"⚡ Électricité : **{elec_s[0][0]}** — {elec_s[0][1]:,} kWh")
            return "\n".join(lignes)

        if mode == "list":
            lignes = [f"Top consommateurs en **{mois}** :"]
            if eau:
                lignes.append(f"💧 Eau : {eau[0][0]} ({eau[0][1]:,} m³)")
            if elec:
                elec_s = sorted(elec, key=lambda r: r[1], reverse=True)
                lignes.append(f"⚡ Électricité : {elec_s[0][0]} ({elec_s[0][1]:,} kWh)")
            return "\n".join(lignes)

        lignes = [f"Client(s) avec la consommation la plus élevée en **{mois}** :\n"]
        if eau:
            lignes.append(f"💧 **Eau** — 🏆 **{eau[0][0]}** : {eau[0][1]:,} m³")
            for i, r in enumerate(eau, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,} m³")
        if elec:
            elec_sorted = sorted(elec, key=lambda r: r[1], reverse=True)
            lignes.append(f"\n⚡ **Électricité** — 🏆 **{elec_sorted[0][0]}** : {elec_sorted[0][1]:,} kWh")
            for i, r in enumerate(elec_sorted, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,} kWh")
        lignes.append("\n⚠️ Classements séparés : eau (m³) ≠ électricité (kWh).")
        return "\n".join(lignes)

    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total_conso DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Aucune donnée trouvée."

        eau  = sorted([r for r in rows if r[2] == "m³"],  key=lambda r: r[1], reverse=True)
        elec = sorted([r for r in rows if r[2] == "kWh"], key=lambda r: r[1], reverse=True)

        if mode in ("top1", "count"):
            lignes = ["Client avec la consommation la plus élevée :"]
            if eau:
                lignes.append(f"💧 Eau : **{eau[0][0]}** — {eau[0][1]:,} m³")
            if elec:
                lignes.append(f"⚡ Électricité : **{elec[0][0]}** — {elec[0][1]:,} kWh")
            return "\n".join(lignes)

        if mode == "list":
            lignes = ["Top consommateurs (tous mois confondus) :"]
            if eau:
                lignes.append(f"💧 Eau : {eau[0][0]} ({eau[0][1]:,} m³)")
            if elec:
                lignes.append(f"⚡ Électricité : {elec[0][0]} ({elec[0][1]:,} kWh)")
            return "\n".join(lignes)

        lignes = ["Classement des consommations (séparé par unité) :\n"]
        if eau:
            lignes.append(f"💧 **Eau (m³)** — 🏆 **{eau[0][0]}**")
            for i, r in enumerate(eau, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,} m³")
        if elec:
            lignes.append(f"\n⚡ **Électricité (kWh)** — 🏆 **{elec[0][0]}**")
            for i, r in enumerate(elec, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,} kWh")
        lignes.append("\n⚠️ Classements séparés : eau (m³) ≠ électricité (kWh).")
        return "\n".join(lignes)


def fetch_min_consommateurs(mois: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()

    if mois:
        mois = normaliser_mois(mois)
        cursor.execute("""
            SELECT nom_client, consommation, unite, mois_source
            FROM factures_excel
            WHERE mois_source LIKE ?
            ORDER BY consommation ASC
        """, (f"%{mois}%",))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return f"Aucune donnée trouvée pour le mois {mois}."

        eau  = [r for r in rows if r[2] == "m³"]
        elec = [r for r in rows if r[2] == "kWh"]

        if mode in ("top1", "count"):
            lignes = [f"Client avec la consommation la plus faible en **{mois}** :"]
            if eau:
                min_eau = min(eau, key=lambda r: r[1])
                lignes.append(f"💧 Eau : **{min_eau[0]}** — {min_eau[1]:,} m³")
            if elec:
                min_elec = min(elec, key=lambda r: r[1])
                lignes.append(f"⚡ Électricité : **{min_elec[0]}** — {min_elec[1]:,} kWh")
            return "\n".join(lignes)

        if mode == "list":
            lignes = [f"Plus faibles consommateurs en **{mois}** :"]
            if eau:
                min_eau = min(eau, key=lambda r: r[1])
                lignes.append(f"💧 Eau : {min_eau[0]} ({min_eau[1]:,} m³)")
            if elec:
                min_elec = min(elec, key=lambda r: r[1])
                lignes.append(f"⚡ Électricité : {min_elec[0]} ({min_elec[1]:,} kWh)")
            return "\n".join(lignes)

        lignes = [f"Client(s) avec la consommation la plus faible en **{mois}** :\n"]
        if eau:
            min_eau = min(eau, key=lambda r: r[1])
            lignes.append(f"💧 Eau — 🔻 **{min_eau[0]}** : {min_eau[1]:,} m³")
            for r in sorted(eau, key=lambda r: r[1]):
                lignes.append(f"  - {r[0]} : {r[1]:,} m³")
        if elec:
            min_elec = min(elec, key=lambda r: r[1])
            lignes.append(f"\n⚡ Électricité — 🔻 **{min_elec[0]}** : {min_elec[1]:,} kWh")
            for r in sorted(elec, key=lambda r: r[1]):
                lignes.append(f"  - {r[0]} : {r[1]:,} kWh")
        lignes.append("\n⚠️ Classements séparés — les unités sont incompatibles.")
        return "\n".join(lignes)

    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total_conso ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Aucune donnée trouvée."

        eau  = [r for r in rows if r[2] == "m³"]
        elec = [r for r in rows if r[2] == "kWh"]

        if mode in ("top1", "count"):
            lignes = ["Client avec la consommation totale la plus faible :"]
            if eau:
                e = sorted(eau, key=lambda r: r[1])[0]
                lignes.append(f"💧 Eau : **{e[0]}** — {e[1]:,} m³")
            if elec:
                e = sorted(elec, key=lambda r: r[1])[0]
                lignes.append(f"⚡ Électricité : **{e[0]}** — {e[1]:,} kWh")
            return "\n".join(lignes)

        if mode == "list":
            lignes = ["Plus faibles consommateurs (tous mois confondus) :"]
            if eau:
                lignes.append(f"💧 Eau : {sorted(eau, key=lambda r: r[1])[0][0]}")
            if elec:
                lignes.append(f"⚡ Électricité : {sorted(elec, key=lambda r: r[1])[0][0]}")
            return "\n".join(lignes)

        lignes = ["Client(s) avec la consommation totale la plus faible :\n"]
        if eau:
            lignes.append("💧 **Eau (m³)** :")
            for i, r in enumerate(sorted(eau, key=lambda r: r[1]), 1):
                prefix = "🔻" if i == 1 else f"  {i}."
                lignes.append(f"{prefix} **{r[0]}** — {r[1]:,} m³")
        if elec:
            lignes.append("\n⚡ **Électricité (kWh)** :")
            for i, r in enumerate(sorted(elec, key=lambda r: r[1]), 1):
                prefix = "🔻" if i == 1 else f"  {i}."
                lignes.append(f"{prefix} **{r[0]}** — {r[1]:,} kWh")
        lignes.append("\n⚠️ Les unités eau (m³) et électricité (kWh) sont incompatibles — classements séparés.")
        return "\n".join(lignes)


def fetch_min_consommateurs_par_service(service: str, mois: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()

    service_norm = service.lower().strip()
    if any(k in service_norm for k in ["elec", "électr"]):
        service_filtre = "electricite"
        service_label = "Électricité"
    else:
        service_filtre = "eau"
        service_label = "Eau"

    if mois:
        mois = normaliser_mois(mois)
        cursor.execute("""
            SELECT nom_client, consommation, unite, mois_source
            FROM factures_excel
            WHERE LOWER(type_service) = ? AND mois_source LIKE ?
            ORDER BY consommation ASC
        """, (service_filtre, f"%{mois}%"))
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            WHERE LOWER(type_service) = ?
            GROUP BY nom_client
            ORDER BY total_conso ASC
        """, (service_filtre,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"Aucune donnée trouvée pour le service {service_label}."

    if mode in ("top1", "list", "count"):
        return f"🔻 Plus faible consommateur **{service_label}** : **{rows[0][0]}** ({rows[0][1]:,} {rows[0][2]})"

    min_val = rows[0][1]
    lignes = [f"Clients **{service_label}** classés par consommation (faible → élevée) :\n"]
    for i, r in enumerate(rows, 1):
        prefix = "🔻" if r[1] == min_val else f"  {i}."
        lignes.append(f"{prefix} **{r[0]}** — {r[1]:,} {r[2]}")
    return "\n".join(lignes)


def fetch_max_consommateurs_par_service(service: str, mois: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()

    service_norm = service.lower().strip()
    if any(k in service_norm for k in ["elec", "électr"]):
        service_filtre = "electricite"
        service_label = "Électricité"
    else:
        service_filtre = "eau"
        service_label = "Eau"

    if mois:
        mois = normaliser_mois(mois)
        cursor.execute("""
            SELECT nom_client, consommation, unite, mois_source
            FROM factures_excel
            WHERE LOWER(type_service) = ? AND mois_source LIKE ?
            ORDER BY consommation DESC
        """, (service_filtre, f"%{mois}%"))
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(consommation), 2) as total_conso, unite
            FROM factures_excel
            WHERE LOWER(type_service) = ?
            GROUP BY nom_client
            ORDER BY total_conso DESC
        """, (service_filtre,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"Aucune donnée trouvée pour le service {service_label}."

    if mode in ("top1", "list", "count"):
        return f"🏆 Plus grand consommateur **{service_label}** : **{rows[0][0]}** ({rows[0][1]:,} {rows[0][2]})"

    max_val = rows[0][1]
    lignes = [f"Clients **{service_label}** classés par consommation (élevée → faible) :\n"]
    for i, r in enumerate(rows, 1):
        prefix = "🏆" if r[1] == max_val else f"  {i}."
        lignes.append(f"{prefix} **{r[0]}** — {r[1]:,} {r[2]}")
    return "\n".join(lignes)


def fetch_top_montants(mois: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if mois:
        mois = normaliser_mois(mois)
        cursor.execute("""
            SELECT nom_client, montant_ttc, mois_source
            FROM factures_excel
            WHERE mois_source LIKE ?
            ORDER BY montant_ttc DESC
        """, (f"%{mois}%",))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return f"Aucune donnée trouvée pour le mois {mois}."

        if mode in ("top1", "count"):
            return f"🏆 Client avec le montant le plus élevé en **{mois}** : **{rows[0][0]}** — {rows[0][1]:,.2f} Dhs"
        if mode == "list":
            return f"🏆 Client avec le montant le plus élevé en **{mois}** : **{rows[0][0]}** ({rows[0][1]:,.2f} Dhs)"

        max_val = rows[0][1]
        tops = [r for r in rows if r[1] == max_val]
        lignes = [f"Client(s) avec le montant le plus élevé en **{mois}** :\n"]
        for r in tops:
            lignes.append(f"🏆 **{r[0]}** — {r[1]:,.2f} Dhs")
        if len(rows) > len(tops):
            lignes.append(f"\nClassement complet ({mois}) :")
            for i, r in enumerate(rows, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,.2f} Dhs")
    else:
        cursor.execute("""
            SELECT nom_client, ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Aucune donnée trouvée."

        if mode in ("top1", "count"):
            return f"🏆 Client avec le montant total le plus élevé : **{rows[0][0]}** — {rows[0][1]:,.2f} Dhs"
        if mode == "list":
            return f"🏆 Client avec le montant total le plus élevé : **{rows[0][0]}** ({rows[0][1]:,.2f} Dhs)"

        max_val = rows[0][1]
        tops = [r for r in rows if r[1] == max_val]
        lignes = ["Client(s) avec le montant total le plus élevé :\n"]
        for r in tops:
            lignes.append(f"🏆 **{r[0]}** — {r[1]:,.2f} Dhs")
        if len(rows) > len(tops):
            lignes.append("\nClassement complet :")
            for i, r in enumerate(rows, 1):
                lignes.append(f"  {i}. {r[0]} — {r[1]:,.2f} Dhs")
    return "\n".join(lignes)


def fetch_classement_par_mois(mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, nom_client, montant_ttc, consommation, unite
        FROM factures_excel
        ORDER BY
            SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2),
            montant_ttc DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    mois_dict = {}
    for r in rows:
        mois = r[0]
        if mois not in mois_dict:
            mois_dict[mois] = []
        mois_dict[mois].append(r)

    if mode in ("list", "top1"):
        lignes = ["Meilleur payeur par mois :"]
        for mois, clients in mois_dict.items():
            lignes.append(f"- **{mois}** : {clients[0][1]} ({clients[0][2]:,.2f} Dhs)")
        return "\n".join(lignes)

    lignes = ["Classement des clients par montant pour chaque mois :\n"]
    for mois, clients in mois_dict.items():
        lignes.append(f"**{mois}** :")
        for i, r in enumerate(clients, 1):
            lignes.append(f"  {i}. {r[1]} — {r[2]:,.2f} Dhs | Conso : {r[3]:,} {r[4]}")
        lignes.append("")
    return "\n".join(lignes)


def fetch_par_agence(agence: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    if agence:
        cursor.execute("""
            SELECT nom_client, usage, type_service,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            WHERE agence LIKE ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (f"%{agence}%",))
        rows = cursor.fetchall()
        conn.close()

        if mode == "count":
            return f"Il y a **{len(rows)} clients** dans l'agence « {agence} »."
        if mode in ("list", "top1"):
            lignes = [f"Clients de l'agence « {agence} » ({len(rows)}) :"]
            for i, r in enumerate(rows, 1):
                lignes.append(f"{i}. {r[0]}")
            return "\n".join(lignes)

        lignes = [f"**{len(rows)} clients** dans l'agence « {agence} » :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Usage : {r[1]} | Service : {r[2]} | "
                f"{r[3]} mois | Total : {r[4]:,.2f} Dhs"
            )
    else:
        cursor.execute("""
            SELECT agence, COUNT(DISTINCT nom_client) as nb_clients,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY agence
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Aucune agence trouvée."

        if mode == "count":
            return f"Il y a **{len(rows)} agences** dans la base."
        if mode in ("list", "top1"):
            lignes = [f"Liste des agences ({len(rows)}) :"]
            for r in rows:
                lignes.append(f"- {r[0]} ({r[1]} clients)")
            return "\n".join(lignes)

        max_clients = rows[0][1]
        top_agences = [r for r in rows if r[1] == max_clients]
        autres = [r for r in rows if r[1] < max_clients]
        lignes = [f"Agences avec le plus de clients (**{max_clients} clients** chacune) :\n"]
        for r in top_agences:
            lignes.append(f"- **{r[0]}** : {r[1]} clients | Total : {r[2]:,.2f} Dhs")
        if autres:
            lignes.append(f"\nAutres agences ({len(autres)}) :")
            for r in autres:
                lignes.append(f"- {r[0]} : {r[1]} client | Total : {r[2]:,.2f} Dhs")
    return "\n".join(lignes)


# ════════════════════════════════════════════════════════════
# ✅ NOUVEAU — Agence de chaque client
# Retourne l'agence rattachée à chaque client,
# groupé par agence en mode detail, liste plate en mode list.
#
# Modes :
#   detail → groupé par agence, avec service et usage
#   list   → liste plate "Client → Agence"
#   count  → nombre de clients et d'agences uniques
#   top1   → identique à list (pas de notion de "top" ici)
# ════════════════════════════════════════════════════════════

def fetch_agence_par_client(mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, type_service, usage
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY agence, nom_client
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "Aucune donnée trouvée."

    if mode == "count":
        agences_uniques = len(set(r[1] for r in rows if r[1]))
        return (
            f"**{len(rows)} clients** répartis dans "
            f"**{agences_uniques} agences**."
        )

    if mode in ("list", "top1"):
        lignes = [f"Agence de chaque client ({len(rows)}) :\n"]
        for r in rows:
            lignes.append(f"- **{r[0]}** → {r[1]}")
        return "\n".join(lignes)

    # ── mode detail : groupé par agence ──
    par_agence = {}
    for r in rows:
        agence = r[1] or "Non définie"
        if agence not in par_agence:
            par_agence[agence] = []
        par_agence[agence].append(r)

    lignes = [f"Agence de chaque client ({len(rows)} clients) :\n"]
    for agence_label, clients in par_agence.items():
        lignes.append(f"🏢 **{agence_label}** ({len(clients)} client(s)) :")
        for r in clients:
            lignes.append(f"   • **{r[0]}** | Service : {r[2]} | Usage : {r[3]}")
        lignes.append("")
    return "\n".join(lignes)


def fetch_par_usage(usage: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()

    if usage:
        usage_normalise = normaliser_usage(usage)
        if usage_normalise is None:
            usage_normalise = usage
        filtre = f"%{usage_normalise}%"
        label = usage_normalise

        cursor.execute("""
            SELECT nom_client, agence, type_service,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            WHERE usage LIKE ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (filtre,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            partie = usage_normalise.replace("USAGE ", "").strip()
            conn2 = _connexion()
            cursor2 = conn2.cursor()
            cursor2.execute("""
                SELECT nom_client, agence, type_service,
                       COUNT(*) as nb_mois,
                       ROUND(SUM(montant_ttc), 2) as total
                FROM factures_excel
                WHERE usage LIKE ?
                GROUP BY nom_client
                ORDER BY nom_client
            """, (f"%{partie}%",))
            rows = cursor2.fetchall()
            conn2.close()

        if not rows:
            return f"Aucun client trouvé pour l'usage « {label} ».\n⚠️ Vérifiez que l'usage existe."

        if mode == "count":
            return f"**{len(rows)} clients** ont l'usage « {label} »."
        if mode in ("list", "top1"):
            lignes = [f"Clients avec usage « {label} » ({len(rows)}) :"]
            for i, r in enumerate(rows, 1):
                lignes.append(f"{i}. {r[0]}")
            return "\n".join(lignes)

        lignes = [f"**{len(rows)} clients** avec usage « {label} » :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Agence : {r[1]} | Service : {r[2]} | "
                f"{r[3]} mois | Total : {r[4]:,.2f} Dhs"
            )
        return "\n".join(lignes)

    else:
        if mode == "count":
            cursor.execute("SELECT COUNT(DISTINCT usage) FROM factures_excel WHERE usage IS NOT NULL")
            nb = cursor.fetchone()[0]
            conn.close()
            return f"Il y a **{nb} types d'usage** différents."

        if mode in ("list", "top1"):
            cursor.execute("""
                SELECT usage, COUNT(DISTINCT nom_client) as nb_clients
                FROM factures_excel
                WHERE usage IS NOT NULL
                GROUP BY usage
                ORDER BY nb_clients DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            lignes = ["Types d'usage disponibles :"]
            for r in rows:
                lignes.append(f"- {r[0]} ({r[1]} clients)")
            return "\n".join(lignes)

        cursor.execute("""
            SELECT nom_client, usage, agence, type_service,
                   COUNT(*) as nb_mois,
                   ROUND(SUM(montant_ttc), 2) as total
            FROM factures_excel
            GROUP BY nom_client
            ORDER BY usage, nom_client
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "Aucune donnée trouvée."

        par_usage = {}
        for r in rows:
            u = r[1] or "Non défini"
            if u not in par_usage:
                par_usage[u] = []
            par_usage[u].append(r)

        lignes = [f"Type d'usage de chaque client ({len(rows)} clients au total) :\n"]
        for usage_label, clients in par_usage.items():
            lignes.append(f"**{usage_label}** ({len(clients)} clients) :")
            for i, r in enumerate(clients, 1):
                lignes.append(
                    f"  {i}. **{r[0]}** | Agence : {r[2]} | Service : {r[3]} | "
                    f"{r[4]} mois | Total : {r[5]:,.2f} Dhs"
                )
            lignes.append("")
        return "\n".join(lignes)


def fetch_par_service(service: str = None, mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()

    if service:
        service_norm = service.lower().strip()
        if any(k in service_norm for k in ["elec", "électr"]):
            service_filtre = "electricite"
            service_label = "Électricité"
        elif any(k in service_norm for k in ["eau", "water"]):
            service_filtre = "eau"
            service_label = "Eau"
        else:
            service_filtre = service_norm
            service_label = service

        cursor.execute("""
            SELECT nom_client, agence, usage,
                   ROUND(SUM(consommation), 2) as total_conso,
                   unite,
                   ROUND(SUM(montant_ttc), 2) as total_ttc,
                   COUNT(*) as nb_mois
            FROM factures_excel
            WHERE LOWER(type_service) = ?
            GROUP BY nom_client
            ORDER BY nom_client
        """, (service_filtre,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"Aucun client trouvé pour le service « {service_label} »."

        if mode == "count":
            return f"**{len(rows)} clients** utilisent le service **{service_label}**."
        if mode in ("list", "top1"):
            lignes = [f"Clients **{service_label}** ({len(rows)}) :"]
            for i, r in enumerate(rows, 1):
                lignes.append(f"{i}. {r[0]}")
            return "\n".join(lignes)

        lignes = [f"Il y a **{len(rows)} clients** qui utilisent le service **{service_label}** :\n"]
        for i, r in enumerate(rows, 1):
            lignes.append(
                f"{i}. **{r[0]}** | Agence : {r[1]} | Usage : {r[2]} | "
                f"Conso totale : {r[3]:,} {r[4]} | Montant total : {r[5]:,.2f} Dhs"
            )
        return "\n".join(lignes)

    else:
        cursor.execute("""
            SELECT LOWER(type_service) as service,
                   COUNT(DISTINCT nom_client) as nb_clients,
                   GROUP_CONCAT(DISTINCT nom_client) as noms,
                   ROUND(SUM(consommation), 2) as total_conso,
                   ROUND(SUM(montant_ttc), 2) as total_ttc
            FROM factures_excel
            GROUP BY LOWER(type_service)
            ORDER BY nb_clients DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        if mode == "count":
            total = sum(r[1] for r in rows)
            parts = [f"{('Électricité' if r[0]=='electricite' else 'Eau')} : {r[1]}" for r in rows]
            return f"**{total} clients** au total — {' | '.join(parts)}."

        if mode in ("list", "top1"):
            lignes = ["Répartition par service :"]
            for r in rows:
                label = "Électricité" if r[0] == "electricite" else "Eau"
                noms = r[2].split(",") if r[2] else []
                lignes.append(f"\n**{label}** ({r[1]} clients) :")
                for nom in noms:
                    lignes.append(f"  - {nom.strip()}")
            return "\n".join(lignes)

        lignes = ["Répartition exacte par type de service :\n"]
        total_clients = sum(r[1] for r in rows)
        lignes.append(f"Total : **{total_clients} clients** répartis comme suit :\n")
        for r in rows:
            service_label = "Électricité" if r[0] == "electricite" else "Eau" if r[0] == "eau" else r[0]
            noms_liste = r[2].split(",") if r[2] else []
            lignes.append(f"💧⚡ **{service_label}** : **{r[1]} clients**")
            for nom in noms_liste:
                lignes.append(f"   • {nom.strip()}")
            lignes.append(f"   Consommation totale : {r[3]:,} | Montant total : {r[4]:,.2f} Dhs\n")
        lignes.append("Chaque client utilise UN SEUL service. Les totaux ci-dessus sont indépendants.")
        return "\n".join(lignes)


def fetch_alertes(mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, mois_source, montant_ttc, alerte
        FROM factures_excel
        WHERE alerte IS NOT NULL AND alerte != '' AND alerte != 'None'
        ORDER BY nom_client, mois_source
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "✅ Aucune alerte trouvée dans la base de données."

    if mode == "count":
        clients_uniques = len(set(r[0] for r in rows))
        return f"⚠️ **{len(rows)} factures** avec alerte concernant **{clients_uniques} clients**."

    if mode in ("list", "top1"):
        clients_uniques = list(set(r[0] for r in rows))
        lignes = [f"⚠️ Clients avec alertes ({len(clients_uniques)}) :"]
        for c in sorted(clients_uniques):
            lignes.append(f"- {c}")
        return "\n".join(lignes)

    lignes = [f"⚠️ **{len(rows)} factures** avec alerte :\n"]
    for r in rows:
        lignes.append(
            f"- **{r[0]}** | {r[1]} | {r[2]} | {r[3]:,.2f} Dhs | Alerte : {r[4]}"
        )
    return "\n".join(lignes)


def fetch_stats_generales(mode: str = "detail", question: str = "") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(DISTINCT nom_client) as nb_clients,
            COUNT(DISTINCT mois_source) as nb_mois,
            COUNT(*) as nb_factures,
            ROUND(SUM(montant_ttc), 2) as total_ttc,
            ROUND(AVG(montant_ttc), 2) as moyenne_ttc,
            ROUND(MAX(montant_ttc), 2) as max_ttc,
            ROUND(MIN(montant_ttc), 2) as min_ttc
        FROM factures_excel
    """)
    r = cursor.fetchone()

    q = _normaliser_q(question)
    sujet_facture  = any(t in q for t in ["facture", "factures", "fact", "fac", "enregistrement", "ligne", "lignes"])
    sujet_client   = any(t in q for t in ["client", "clients", "abonne", "abonnes"])
    sujet_mois     = any(t in q for t in ["mois", "periode", "periodes"])
    sujet_montant  = any(t in q for t in ["montant", "ttc", "dhs", "somme", "total ttc"])
    sujet_moyenne  = any(t in q for t in ["moyenne", "moyen", "moy", "avg"])
    sujet_max      = any(t in q for t in ["maximum", "max", "plus eleve", "plus haut"])
    sujet_min      = any(t in q for t in ["minimum", "min", "plus faible", "plus bas"])

    if mode == "count":
        if sujet_facture and not sujet_client:
            conn.close()
            return f"Il y a **{r[2]} factures** dans la base."
        if sujet_client and not sujet_facture:
            conn.close()
            return f"Il y a **{r[0]} clients** dans la base."
        if sujet_mois and not sujet_facture and not sujet_client:
            conn.close()
            return f"La base couvre **{r[1]} mois**."

    if sujet_facture and not sujet_client and not sujet_mois:
        conn.close()
        return f"Il y a **{r[2]} factures** dans la base."
    if sujet_mois and not sujet_facture and not sujet_client:
        conn.close()
        return f"La base couvre **{r[1]} mois** de facturation."
    if sujet_montant and mode == "count":
        conn.close()
        return f"Le montant total TTC est **{r[3]:,.2f} Dhs**."
    if sujet_moyenne:
        conn.close()
        return f"Le montant moyen par facture est **{r[4]:,.2f} Dhs**."
    if sujet_max and not sujet_min:
        conn.close()
        return f"Le montant maximum enregistré est **{r[5]:,.2f} Dhs**."
    if sujet_min and not sujet_max:
        conn.close()
        return f"Le montant minimum enregistré est **{r[6]:,.2f} Dhs**."

    cursor.execute("""
        SELECT nom_client, ROUND(SUM(montant_ttc), 2) as total
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY total DESC
        LIMIT 1
    """)
    top = cursor.fetchone()
    cursor.execute("""
        SELECT LOWER(type_service), COUNT(DISTINCT nom_client)
        FROM factures_excel
        GROUP BY LOWER(type_service)
    """)
    services = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    nb_eau  = services.get("eau", 0)
    nb_elec = services.get("electricite", 0)

    return f"""📊 **Statistiques générales de la base SRM :**

- Nombre de clients       : **{r[0]}** ({nb_eau} eau · {nb_elec} électricité)
- Nombre de mois couverts : **{r[1]}**
- Nombre de factures      : **{r[2]}**
- Montant total TTC       : **{r[3]:,.2f} Dhs**
- Montant moyen / facture : **{r[4]:,.2f} Dhs**
- Montant maximum         : **{r[5]:,.2f} Dhs**
- Montant minimum         : **{r[6]:,.2f} Dhs**
- Client avec le plus de dépenses : **{top[0]}** ({top[1]:,.2f} Dhs cumulés)"""


def fetch_evolution_mois(mode: str = "detail") -> str:
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source,
               COUNT(DISTINCT nom_client) as nb_clients,
               ROUND(SUM(consommation), 2) as total_conso,
               ROUND(SUM(montant_ttc), 2) as total_ttc,
               ROUND(AVG(montant_ttc), 2) as moyenne_ttc
        FROM factures_excel
        GROUP BY mois_source
        ORDER BY SUBSTR(MIN(periode_debut),7,4)||SUBSTR(MIN(periode_debut),4,2)||SUBSTR(MIN(periode_debut),1,2)
    """)
    rows = cursor.fetchall()
    conn.close()

    if mode == "count":
        return f"La base couvre **{len(rows)} mois** de facturation."
    if mode in ("list", "top1"):
        lignes = [f"Mois disponibles ({len(rows)}) :"]
        for r in rows:
            lignes.append(f"- **{r[0]}** : {r[3]:,.2f} Dhs")
        return "\n".join(lignes)

    lignes = ["📈 **Évolution mois par mois :**\n"]
    for r in rows:
        lignes.append(
            f"- **{r[0]}** : {r[1]} clients | "
            f"Conso totale : {r[2]:,} | "
            f"Montant total : {r[3]:,.2f} Dhs | "
            f"Moyenne : {r[4]:,.2f} Dhs"
        )
    return "\n".join(lignes)


def fetch_somme_conso_mois(mois: str) -> str:
    from normalisation import normaliser_mois
    mois_norm = normaliser_mois(mois)
    conn = _connexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            LOWER(type_service) as service,
            ROUND(SUM(consommation), 2) as total_conso,
            unite,
            COUNT(DISTINCT nom_client) as nb_clients
        FROM factures_excel
        WHERE mois_source LIKE ?
        GROUP BY LOWER(type_service)
    """, (f"%{mois_norm}%",))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"Aucune donnée trouvée pour le mois **{mois_norm}**."

    lignes = [f" Consommation totale en **{mois_norm}** :\n"]
    for r in rows:
        label = "Électricité" if r[0] == "electricite" else "Eau"
        lignes.append(
            f"- **{label}** : {r[1]:,} {r[2]} "
            f"({r[3]} clients)"
        )
    return "\n".join(lignes)


def fetch_question_libre(question: str, historique_texte: str) -> str:
    return (
        "Je ne suis pas sûr de comprendre votre question. "
        "Pourriez-vous la reformuler ou la préciser ?\n\n"
        "Par exemple, vous pouvez me demander :\n"
        "- La liste des clients\n"
        "- Qui consomme le plus / le moins\n"
        "- L'évolution des factures mois par mois\n"
        "- Les clients d'une agence précise\n"
        "- Les alertes en cours\n"
        "- Les statistiques générales"
    )