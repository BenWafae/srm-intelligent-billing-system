import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- Table existante PDF ---
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

    # --- Nouvelle table Excel ---
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


# --- Fonctions existantes —concern le pdf ---

def enregistrer_facture(donnees: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM factures 
        WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
    """, (
        donnees.get("numero_client"),
        donnees.get("periode_debut"),
        donnees.get("periode_fin")
    ))
    existant = cursor.fetchone()
    if existant:
        conn.close()
        return False
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
    return True

def get_all_factures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factures")
    rows = cursor.fetchall()
    conn.close()
    return rows


# --- Nouvelles fonctions Excel ---

def importer_excel_en_db(lignes: list[dict]) -> dict:
    """
    Reçoit la liste de dictionnaires de excel_reader.py
    Insère chaque ligne en BD en évitant les doublons
    Retourne un résumé de l'opération
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    nouvelles = 0
    doublons = 0

    for ligne in lignes:

        # Vérifier si cette facture existe déjà
        # Un client ne peut pas avoir deux factures pour la même période
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
            continue  # On passe à la ligne suivante sans insérer

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
# alors ici par exemple quand user pose un question on envoie le resumeer au llm comme contexte 

def get_resume_excel() -> dict:
    """
    Retourne un résumé global de la BD Excel.
    Utilisé par le RAG comme contexte de base quand
    aucun client spécifique n'est mentionné.
    """
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
    """
    Cœur du RAG — recherche les factures d'un client spécifique.
    Utilisé quand l'utilisateur mentionne un nom ou numéro client.
    Retourne uniquement les données pertinentes, pas les 72 lignes.
    """
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


# -------- TEST --------
if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from src.excel_reader import lire_excel

    # Initialiser la BD
    init_db()
    print("✅ Base de données initialisée.")

    # Importer le fichier Excel
    lignes = lire_excel("data/factures_srm.xlsx")
    resultat = importer_excel_en_db(lignes)
    print(f"✅ Import terminé : {resultat['nouvelles']} nouvelles, {resultat['doublons']} doublons.")

    # Tester le résumé
    resume = get_resume_excel()
    print(f"\n📊 Résumé BD : {resume['total']} factures")
    print(f"👥 Clients : {resume['clients']}")
    print(f"📅 Périodes : {resume['periodes']}")

    # Tester la recherche d'un client
    print("\n🔍 Recherche 'Fatima'...")
    resultats = rechercher_client_excel("Fatima")
    print(f"  {len(resultats)} factures trouvées.")
    for r in resultats:
        print(f"  - {r['mois_source']} : {r['montant_ttc']} Dhs | Alerte: '{r['alerte']}'")