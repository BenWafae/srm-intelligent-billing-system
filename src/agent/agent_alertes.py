import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "srm.db")


# ════════════════════════════════════════════════════════════
# ÉTAPE 1 — Récupération des données pour la détection
# ════════════════════════════════════════════════════════════

def get_clients_deux_derniers_mois() -> list[dict]:
    """
    Pour chaque client, récupère ses 2 derniers mois
    avec l'email si le client a un compte utilisateur.
    Retourne une liste de dicts prêts pour la détection.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Récupère tous les mois de tous les clients, triés du plus récent au plus ancien
    cursor.execute("""
        SELECT 
            f.numero_contrat,
            f.nom_client,
            f.consommation,
            f.unite,
            f.montant_ttc,
            f.mois_source,
            f.periode_debut,
            f.usage,
            f.agence,
            u.email
        FROM factures_excel f
        LEFT JOIN users u 
            ON f.numero_contrat = u.numero_client
            AND u.role = 'client'
        ORDER BY 
            f.numero_contrat,
            SUBSTR(f.periode_debut,7,4)||SUBSTR(f.periode_debut,4,2)||SUBSTR(f.periode_debut,1,2) DESC
    """)
    colonnes = [d[0] for d in cursor.description]
    rows = [dict(zip(colonnes, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def grouper_par_contrat(rows: list[dict]) -> dict:
    """
    Groupe les lignes par numero_contrat.
    Retourne un dict : { numero_contrat: [mois1, mois2, ...] }
    Les mois sont déjà triés du plus récent au plus ancien.
    """
    groupes = {}
    for row in rows:
        contrat = row["numero_contrat"]
        if contrat not in groupes:
            groupes[contrat] = []
        groupes[contrat].append(row)
    return groupes


# ════════════════════════════════════════════════════════════
# ÉTAPE 2 — Détection (100% Python, zéro LLM)
# ════════════════════════════════════════════════════════════

def detecter_surconsommations(seuil: float) -> list[dict]:
    """
    Détecte les clients en surconsommation.

    Paramètre :
        seuil : pourcentage d'augmentation à partir duquel
                on considère qu'il y a surconsommation (ex: 30.0 = +30%)

    Retourne une liste de dicts, un par client détecté :
    {
        "numero_contrat": str,
        "nom_client": str,
        "email": str | None,
        "mois_actuel": str,
        "conso_actuelle": float,
        "mois_precedent": str,
        "conso_precedente": float,
        "variation_pct": float,
        "unite": str,
        "montant_ttc": float,
        "usage": str,
        "agence": str
    }
    """
    rows = get_clients_deux_derniers_mois()
    groupes = grouper_par_contrat(rows)

    detectes = []

    for numero_contrat, mois_list in groupes.items():
        # Il faut au minimum 2 mois pour comparer
        if len(mois_list) < 2:
            continue

        mois_actuel    = mois_list[0]  # le plus récent
        mois_precedent = mois_list[1]  # le précédent

        conso_actuelle   = mois_actuel.get("consommation") or 0
        conso_precedente = mois_precedent.get("consommation") or 0

        # Éviter la division par zéro
        if conso_precedente == 0:
            continue

        variation_pct = ((conso_actuelle - conso_precedente) / conso_precedente) * 100

        if variation_pct > seuil:
            detectes.append({
                "numero_contrat"   : numero_contrat,
                "nom_client"       : mois_actuel.get("nom_client", ""),
                "email"            : mois_actuel.get("email"),       # None si pas de compte
                "mois_actuel"      : mois_actuel.get("mois_source", ""),
                "conso_actuelle"   : round(conso_actuelle, 2),
                "mois_precedent"   : mois_precedent.get("mois_source", ""),
                "conso_precedente" : round(conso_precedente, 2),
                "variation_pct"    : round(variation_pct, 1),
                "unite"            : mois_actuel.get("unite", ""),
                "montant_ttc"      : mois_actuel.get("montant_ttc", 0),
                "usage"            : mois_actuel.get("usage", ""),
                "agence"           : mois_actuel.get("agence", "")
            })

    # Trier par variation décroissante (le plus critique en premier)
    detectes.sort(key=lambda x: x["variation_pct"], reverse=True)
    return detectes


# ════════════════════════════════════════════════════════════
# ÉTAPE 3 — Sauvegarde du seuil en base (configurable admin)
# ════════════════════════════════════════════════════════════

def sauvegarder_seuil(seuil: float) -> None:
    """Sauvegarde le seuil défini par l'admin en base."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_agent (
            cle TEXT PRIMARY KEY,
            valeur TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO config_agent (cle, valeur)
        VALUES ('seuil_surconsommation', ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (str(seuil),))
    conn.commit()
    conn.close()


def get_seuil() -> float:
    """Récupère le seuil sauvegardé. Retourne 30.0 par défaut."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT valeur FROM config_agent
            WHERE cle = 'seuil_surconsommation'
        """)
        row = cursor.fetchone()
        conn.close()
        return float(row[0]) if row else 30.0
    except Exception:
        conn.close()
        return 30.0
# ════════════════════════════════════════════════════════════
# MODE 2 — Détection par moyenne historique (6 mois)
# ════════════════════════════════════════════════════════════

def detecter_par_moyenne(seuil: float, nb_mois: int = 6) -> list[dict]:
    """
    Détecte les surconsommations en comparant le mois actuel
    à la moyenne des N mois précédents (défaut: 6).

    Plus fiable que la comparaison mois-à-mois car :
    - Élimine les fausses alertes dues à un mois précédent anormalement bas
    - Tient compte du comportement habituel du client sur la durée

    Retourne une liste de dicts enrichis :
    {
        ...mêmes champs que detecter_surconsommations()...
        "moyenne_historique": float,   ← nouveau
        "nb_mois_utilises": int,       ← nouveau
        "mode_detection": "moyenne"    ← nouveau
    }

    Ignoré si le client a moins de 3 mois de données.
    """
    rows = get_clients_deux_derniers_mois()
    groupes = grouper_par_contrat(rows)

    detectes = []

    for numero_contrat, mois_list in groupes.items():

        # Minimum 3 mois requis : 1 actuel + 2 pour la moyenne
        if len(mois_list) < 3:
            continue

        mois_actuel = mois_list[0]  # le plus récent
        conso_actuelle = mois_actuel.get("consommation") or 0

        # Prendre les N mois AVANT le mois actuel pour calculer la moyenne
        mois_historiques = mois_list[1 : nb_mois + 1]  # ex: indices 1 à 6

        consos_historiques = [
            m.get("consommation") or 0
            for m in mois_historiques
            if (m.get("consommation") or 0) > 0
        ]

        # Pas assez de données valides
        if len(consos_historiques) < 2:
            continue

        moyenne = sum(consos_historiques) / len(consos_historiques)

        if moyenne == 0:
            continue

        variation_pct = ((conso_actuelle - moyenne) / moyenne) * 100

        if variation_pct > seuil:
            detectes.append({
                "numero_contrat"    : numero_contrat,
                "nom_client"        : mois_actuel.get("nom_client", ""),
                "email"             : mois_actuel.get("email"),
                "mois_actuel"       : mois_actuel.get("mois_source", ""),
                "conso_actuelle"    : round(conso_actuelle, 2),
                # Pour affichage dans le tableau — on montre la moyenne
                "mois_precedent"    : f"Moyenne {len(consos_historiques)} mois",
                "conso_precedente"  : round(moyenne, 2),
                "variation_pct"     : round(variation_pct, 1),
                "unite"             : mois_actuel.get("unite", ""),
                "montant_ttc"       : mois_actuel.get("montant_ttc", 0),
                "usage"             : mois_actuel.get("usage", ""),
                "agence"            : mois_actuel.get("agence", ""),
                # Champs supplémentaires Mode 2
                "moyenne_historique": round(moyenne, 2),
                "nb_mois_utilises"  : len(consos_historiques),
                "mode_detection"    : "moyenne"
            })

    detectes.sort(key=lambda x: x["variation_pct"], reverse=True)
    return detectes


# ════════════════════════════════════════════════════════════
# DISPATCHER — choisit le bon mode selon paramètre admin
# ════════════════════════════════════════════════════════════

def detecter(seuil: float, mode: str = "precedent") -> list[dict]:
    """
    Point d'entrée unique pour la détection.

    Paramètres :
        seuil : % d'augmentation déclenchant l'alerte
        mode  : "precedent" → Mode 1 (mois précédent)
                "moyenne"   → Mode 2 (moyenne 6 mois)

    Appelé par la route FastAPI /api/admin/agent/detecter
    """
    if mode == "moyenne":
        return detecter_par_moyenne(seuil)
    else:
        return detecter_surconsommations(seuil)