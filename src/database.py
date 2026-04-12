import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_client TEXT,
            numero_contrat TEXT,
            nom_client TEXT,
            adresse TEXT,
            usage TEXT,
            periode_debut TEXT,
            periode_fin TEXT,
            date_facture TEXT,
            date_limite_paiement TEXT,
            consommation REAL,
            type_service TEXT,
            montant_total_ttc REAL,
            date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factures_excel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agence TEXT,
            date_edition TEXT,
            periode_debut TEXT,
            periode_fin TEXT,
            numero_contrat TEXT,
            numero_client TEXT,
            numero_compteur TEXT,
            usage TEXT,
            nom_client TEXT,
            adresse TEXT,
            type_service TEXT,
            consommation REAL,
            unite TEXT,
            montant_ttc REAL,
            date_limite_paiement TEXT,
            alerte TEXT,
            mois_source TEXT,
            date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def enregistrer_facture(donnees: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM factures
        WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
    """, (donnees.get("numero_client"), donnees.get("periode_debut"), donnees.get("periode_fin")))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("""
        INSERT INTO factures (
            numero_client, numero_contrat, nom_client, adresse,
            usage, periode_debut, periode_fin, date_facture,
            date_limite_paiement, consommation, type_service, montant_total_ttc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("numero_client"), donnees.get("numero_contrat"),
        donnees.get("nom_client"), donnees.get("adresse"),
        donnees.get("usage"), donnees.get("periode_debut"),
        donnees.get("periode_fin"), donnees.get("date_facture"),
        donnees.get("date_limite_paiement"), donnees.get("consommation"),
        donnees.get("type_service"), donnees.get("montant_total_ttc")
    ))
    conn.commit()
    conn.close()
    return True


def get_all_factures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factures")
    rows = cursor.fetchall()
    conn.close()
    return rows


def importer_excel_en_db(lignes: list[dict]) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    nouvelles = 0
    doublons = 0

    for ligne in lignes:
        cursor.execute("""
            SELECT id FROM factures_excel
            WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
        """, (
            str(ligne.get("numero_client", "")),
            str(ligne.get("periode_debut", "")),
            str(ligne.get("periode_fin", ""))
        ))

        if cursor.fetchone():
            doublons += 1
            continue

        cursor.execute("""
            INSERT INTO factures_excel (
                agence, date_edition, periode_debut, periode_fin,
                numero_contrat, numero_client, numero_compteur, usage,
                nom_client, adresse, type_service, consommation,
                unite, montant_ttc, date_limite_paiement, alerte, mois_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(ligne.get("agence", "")),
            str(ligne.get("date_edition", "")),
            str(ligne.get("periode_debut", "")),
            str(ligne.get("periode_fin", "")),
            str(ligne.get("numero_contrat", "")),
            str(ligne.get("numero_client", "")),
            str(ligne.get("numero_compteur", "")),
            str(ligne.get("usage", "")),
            str(ligne.get("nom_client", "")),
            str(ligne.get("adresse", "")),
            str(ligne.get("type_service", "")),
            float(ligne.get("consommation", 0) or 0),
            str(ligne.get("unite", "")),
            float(ligne.get("montant_ttc", 0) or 0),
            str(ligne.get("date_limite_paiement", "")),
            str(ligne.get("alerte", "")),
            str(ligne.get("mois_source", ""))
        ))
        nouvelles += 1

    conn.commit()
    conn.close()
    return {"nouvelles": nouvelles, "doublons": doublons}


def get_resume_excel() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM factures_excel")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT nom_client FROM factures_excel ORDER BY nom_client")
    clients = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT mois_source FROM factures_excel")
    periodes = [r[0] for r in cursor.fetchall()]
    conn.close()
    return {"total": total, "clients": clients, "periodes": periodes}


def rechercher_client_excel(nom_ou_numero: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    terme = f"%{nom_ou_numero}%"
    cursor.execute("""
        SELECT * FROM factures_excel
        WHERE nom_client LIKE ? OR numero_client LIKE ?
        ORDER BY periode_debut
    """, (terme, terme))
    colonnes = [description[0] for description in cursor.description]
    rows = [dict(zip(colonnes, row)) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_toutes_factures_excel() -> list[dict]:
    """
    Retourne toutes les factures pour les questions générales.
    Utilisé quand la question ne concerne pas un client spécifique.
    Ex: 'quel usage est majoritaire ?', 'quelle agence a le plus de clients ?'
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, usage, type_service,
               mois_source, consommation, unite, montant_ttc,
               periode_debut, periode_fin, date_limite_paiement,
               adresse, numero_client, numero_contrat, numero_compteur
        FROM factures_excel
        ORDER BY nom_client, mois_source
    """)
    colonnes = [d[0] for d in cursor.description]
    rows = [dict(zip(colonnes, r)) for r in cursor.fetchall()]
    conn.close()
    return rows