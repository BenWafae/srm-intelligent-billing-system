"""
agent_tools.py
==============
Outils utilisés par l'agent pour analyser les données de consommation.

Chaque fonction est un "outil" que l'agent peut appeler de façon autonome.
L'agent décide lui-même quels outils appeler selon la demande de l'utilisateur.

Outils disponibles :
  - get_liste_clients()              → liste tous les clients en base
  - get_periodes_disponibles()       → liste les mois/périodes disponibles
  - get_historique_client(client)    → toutes les lignes d'un client
  - comparer_deux_mois(client, m1, m2) → comparaison détaillée entre 2 mois
  - comparer_tous_clients(m1, m2)    → comparaison de tous les clients
  - detecter_surconsommation(seuil)  → clients dont la conso dépasse le seuil
  - get_stats_globales()             → statistiques générales sur la base
"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")


# ─────────────────────────────────────────────
# HELPERS internes
# ─────────────────────────────────────────────

def _connect():
    """Ouvre une connexion SQLite et retourne (conn, cursor)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # accès par nom de colonne
    return conn, conn.cursor()


def _rows_to_dicts(rows) -> list[dict]:
    """Convertit des sqlite3.Row en list[dict]."""
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# OUTIL 1 — Liste des clients
# ─────────────────────────────────────────────

def get_liste_clients() -> list[str]:
    """
    Retourne la liste des noms de clients présents en base.
    L'agent utilise cet outil pour savoir quels clients existent
    avant d'effectuer une comparaison.
    """
    conn, cursor = _connect()
    cursor.execute("""
        SELECT DISTINCT nom_client
        FROM factures_excel
        ORDER BY nom_client
    """)
    clients = [r["nom_client"] for r in cursor.fetchall()]
    conn.close()
    return clients


# ─────────────────────────────────────────────
# OUTIL 2 — Périodes disponibles
# ─────────────────────────────────────────────

def get_periodes_disponibles(nom_client: Optional[str] = None) -> list[str]:
    """
    Retourne les mois/périodes disponibles en base.
    Si nom_client est fourni, filtre pour ce client uniquement.

    Exemple de retour : ["2024-01", "2024-02", "2024-03"]
    """
    conn, cursor = _connect()
    if nom_client:
        cursor.execute("""
            SELECT DISTINCT mois_source
            FROM factures_excel
            WHERE nom_client LIKE ?
            ORDER BY mois_source
        """, (f"%{nom_client}%",))
    else:
        cursor.execute("""
            SELECT DISTINCT mois_source
            FROM factures_excel
            ORDER BY mois_source
        """)
    periodes = [r["mois_source"] for r in cursor.fetchall() if r["mois_source"]]
    conn.close()
    return periodes


# ─────────────────────────────────────────────
# OUTIL 3 — Historique complet d'un client
# ─────────────────────────────────────────────

def get_historique_client(nom_ou_numero: str) -> list[dict]:
    """
    Retourne toutes les factures d'un client (toutes périodes confondues),
    triées par date croissante.

    L'agent utilise cet outil pour construire l'historique
    avant de calculer des tendances ou anomalies.
    """
    conn, cursor = _connect()
    terme = f"%{nom_ou_numero}%"
    cursor.execute("""
        SELECT
            nom_client,
            numero_client,
            mois_source,
            periode_debut,
            periode_fin,
            consommation,
            unite,
            montant_ttc,
            usage,
            type_service,
            agence,
            alerte
        FROM factures_excel
        WHERE nom_client LIKE ? OR numero_client LIKE ?
        ORDER BY mois_source ASC
    """, (terme, terme))
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


# ─────────────────────────────────────────────
# OUTIL 4 — Comparaison entre deux mois (un client)
# ─────────────────────────────────────────────

def comparer_deux_mois(nom_ou_numero: str, mois_1: str, mois_2: str) -> dict:
    """
    Compare la consommation et le montant d'un client entre deux mois.

    Paramètres :
      - nom_ou_numero : nom ou numéro du client
      - mois_1 : ex. "2024-01"
      - mois_2 : ex. "2024-02"

    Retourne un dict avec :
      - client         : nom du client
      - mois_1 / mois_2 : données brutes
      - delta_conso    : variation de consommation (valeur + %)
      - delta_montant  : variation du montant (valeur + %)
      - tendance       : "hausse" / "baisse" / "stable"
      - alerte         : True si hausse > 20%
    """
    conn, cursor = _connect()
    terme = f"%{nom_ou_numero}%"

    def _get_mois(mois: str):
        cursor.execute("""
            SELECT nom_client, mois_source, consommation, montant_ttc, unite, usage
            FROM factures_excel
            WHERE (nom_client LIKE ? OR numero_client LIKE ?)
              AND mois_source = ?
            LIMIT 1
        """, (terme, terme, mois))
        row = cursor.fetchone()
        return dict(row) if row else None

    d1 = _get_mois(mois_1)
    d2 = _get_mois(mois_2)
    conn.close()

    # Cas données manquantes
    if not d1 or not d2:
        manquants = []
        if not d1:
            manquants.append(mois_1)
        if not d2:
            manquants.append(mois_2)
        return {
            "erreur": f"Données introuvables pour {nom_ou_numero} sur : {', '.join(manquants)}",
            "client": nom_ou_numero
        }

    conso_1 = float(d1["consommation"] or 0)
    conso_2 = float(d2["consommation"] or 0)
    mont_1  = float(d1["montant_ttc"] or 0)
    mont_2  = float(d2["montant_ttc"] or 0)

    delta_conso  = conso_2 - conso_1
    delta_montant = mont_2 - mont_1

    pct_conso  = round((delta_conso  / conso_1 * 100), 2) if conso_1 != 0 else None
    pct_montant = round((delta_montant / mont_1  * 100), 2) if mont_1 != 0 else None

    if pct_conso is None:
        tendance = "indéterminée"
    elif abs(pct_conso) <= 5:
        tendance = "stable"
    elif pct_conso > 0:
        tendance = "hausse"
    else:
        tendance = "baisse"

    return {
        "client": d1["nom_client"],
        "mois_1": {
            "periode": mois_1,
            "consommation": conso_1,
            "montant_ttc": mont_1,
            "unite": d1.get("unite", ""),
            "usage": d1.get("usage", ""),
        },
        "mois_2": {
            "periode": mois_2,
            "consommation": conso_2,
            "montant_ttc": mont_2,
            "unite": d2.get("unite", ""),
            "usage": d2.get("usage", ""),
        },
        "delta_conso": round(delta_conso, 3),
        "delta_montant": round(delta_montant, 2),
        "pct_conso": pct_conso,
        "pct_montant": pct_montant,
        "tendance": tendance,
        "alerte": (pct_conso is not None and pct_conso > 20),
    }


# ─────────────────────────────────────────────
# OUTIL 5 — Comparaison de TOUS les clients entre deux mois
# ─────────────────────────────────────────────

def comparer_tous_clients(mois_1: str, mois_2: str) -> list[dict]:
    """
    Compare la consommation de TOUS les clients entre deux mois.

    Retourne une liste triée par variation décroissante (les plus fortes hausses en tête).
    Chaque élément contient les mêmes champs que comparer_deux_mois().
    Idéal pour générer un rapport global ou détecter rapidement les cas critiques.
    """
    clients = get_liste_clients()
    resultats = []

    for client in clients:
        r = comparer_deux_mois(client, mois_1, mois_2)
        if "erreur" not in r:
            resultats.append(r)

    # Trier par % de variation décroissant
    resultats.sort(
        key=lambda x: x["pct_conso"] if x["pct_conso"] is not None else 0,
        reverse=True
    )
    return resultats


# ─────────────────────────────────────────────
# OUTIL 6 — Détection de surconsommation
# ─────────────────────────────────────────────

def detecter_surconsommation(seuil_pct: float = 20.0) -> list[dict]:
    """
    Détecte automatiquement les clients en surconsommation.

    Méthode :
      - Calcule la consommation moyenne de chaque client sur TOUS ses mois
      - Identifie les mois où la consommation dépasse la moyenne de X%
      - Retourne la liste des anomalies triées par gravité (% d'écart décroissant)

    Paramètre :
      - seuil_pct : % au-delà de la moyenne qui déclenche l'alerte (défaut : 20%)

    Retourne une liste de dicts :
      {
        client, mois_anomalie, consommation, moyenne_client,
        ecart_pct, gravite ("critique" / "élevée" / "modérée")
      }
    """
    conn, cursor = _connect()
    cursor.execute("""
        SELECT
            nom_client,
            mois_source,
            consommation,
            AVG(consommation) OVER (PARTITION BY nom_client) AS moyenne_client,
            COUNT(*) OVER (PARTITION BY nom_client) AS nb_mois
        FROM factures_excel
        WHERE consommation IS NOT NULL AND consommation > 0
        ORDER BY nom_client, mois_source
    """)
    rows = _rows_to_dicts(cursor.fetchall())
    conn.close()

    anomalies = []
    for r in rows:
        moy = float(r["moyenne_client"] or 0)
        conso = float(r["consommation"] or 0)
        if moy == 0:
            continue
        ecart_pct = round((conso - moy) / moy * 100, 2)
        if ecart_pct >= seuil_pct:
            if ecart_pct >= 50:
                gravite = "critique"
            elif ecart_pct >= 30:
                gravite = "élevée"
            else:
                gravite = "modérée"

            anomalies.append({
                "client": r["nom_client"],
                "mois_anomalie": r["mois_source"],
                "consommation": round(conso, 3),
                "moyenne_client": round(moy, 3),
                "ecart_pct": ecart_pct,
                "gravite": gravite,
                "nb_mois_historique": r["nb_mois"],
            })

    anomalies.sort(key=lambda x: x["ecart_pct"], reverse=True)
    return anomalies


# ─────────────────────────────────────────────
# OUTIL 7 — Statistiques globales
# ─────────────────────────────────────────────

def get_stats_globales() -> dict:
    """
    Retourne des statistiques générales sur la base de données.
    L'agent utilise cet outil pour répondre à des questions comme
    "quel est l'état général des consommations ?"

    Retourne :
      - nb_clients, nb_periodes, nb_factures
      - conso_totale, conso_moyenne, montant_total
      - client_max_conso, client_min_conso
      - periode_la_plus_chargee
    """
    conn, cursor = _connect()

    cursor.execute("SELECT COUNT(DISTINCT nom_client) FROM factures_excel")
    nb_clients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT mois_source) FROM factures_excel")
    nb_periodes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM factures_excel")
    nb_factures = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(consommation), AVG(consommation), SUM(montant_ttc) FROM factures_excel")
    r = cursor.fetchone()
    conso_totale = round(r[0] or 0, 3)
    conso_moyenne = round(r[1] or 0, 3)
    montant_total = round(r[2] or 0, 2)

    cursor.execute("""
        SELECT nom_client, SUM(consommation) as total
        FROM factures_excel GROUP BY nom_client ORDER BY total DESC LIMIT 1
    """)
    r = cursor.fetchone()
    client_max = {"client": r[0], "total_conso": round(r[1], 3)} if r else None

    cursor.execute("""
        SELECT nom_client, SUM(consommation) as total
        FROM factures_excel GROUP BY nom_client ORDER BY total ASC LIMIT 1
    """)
    r = cursor.fetchone()
    client_min = {"client": r[0], "total_conso": round(r[1], 3)} if r else None

    cursor.execute("""
        SELECT mois_source, SUM(consommation) as total
        FROM factures_excel GROUP BY mois_source ORDER BY total DESC LIMIT 1
    """)
    r = cursor.fetchone()
    periode_max = {"mois": r[0], "total_conso": round(r[1], 3)} if r else None

    conn.close()
    return {
        "nb_clients": nb_clients,
        "nb_periodes": nb_periodes,
        "nb_factures": nb_factures,
        "conso_totale": conso_totale,
        "conso_moyenne_par_facture": conso_moyenne,
        "montant_total_ttc": montant_total,
        "client_plus_gros_consommateur": client_max,
        "client_plus_petit_consommateur": client_min,
        "periode_la_plus_chargee": periode_max,
    }


# ─────────────────────────────────────────────
# REGISTRE DES OUTILS (utilisé par agent.py)
# ─────────────────────────────────────────────

TOOLS_REGISTRY = {
    "get_liste_clients": {
        "fn": get_liste_clients,
        "description": "Liste tous les clients présents en base de données",
        "params": {}
    },
    "get_periodes_disponibles": {
        "fn": get_periodes_disponibles,
        "description": "Liste les mois disponibles en base, optionnellement filtrés par client",
        "params": {"nom_client": "str (optionnel)"}
    },
    "get_historique_client": {
        "fn": get_historique_client,
        "description": "Retourne tout l'historique de consommation d'un client",
        "params": {"nom_ou_numero": "str"}
    },
    "comparer_deux_mois": {
        "fn": comparer_deux_mois,
        "description": "Compare la consommation d'un client entre deux mois donnés",
        "params": {"nom_ou_numero": "str", "mois_1": "str (ex: 2024-01)", "mois_2": "str"}
    },
    "comparer_tous_clients": {
        "fn": comparer_tous_clients,
        "description": "Compare tous les clients entre deux mois, triés par variation",
        "params": {"mois_1": "str", "mois_2": "str"}
    },
    "detecter_surconsommation": {
        "fn": detecter_surconsommation,
        "description": "Détecte automatiquement les anomalies de consommation selon un seuil %",
        "params": {"seuil_pct": "float (défaut 20.0)"}
    },
    "get_stats_globales": {
        "fn": get_stats_globales,
        "description": "Retourne les statistiques globales de la base de données",
        "params": {}
    },
}