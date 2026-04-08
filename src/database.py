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
    conn.commit()
    conn.close()

def enregistrer_facture(donnees: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO factures (
            numero_client, numero_contrat, nom_client, adresse,
            usage, periode_debut, periode_fin, date_facture,
            date_limite_paiement, consommation, type_service, montant_total_ttc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("numero_client"),
        donnees.get("numero_contrat"),
        donnees.get("nom_client"),
        donnees.get("adresse"),
        donnees.get("usage"),
        donnees.get("periode_debut"),
        donnees.get("periode_fin"),
        donnees.get("date_facture"),
        donnees.get("date_limite_paiement"),
        donnees.get("consommation"),
        donnees.get("type_service"),
        donnees.get("montant_total_ttc")
    ))
    conn.commit()
    conn.close()

def get_all_factures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factures")
    rows = cursor.fetchall()
    conn.close()
    return rows