import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # facture pdf table

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
        texte_extrait TEXT,
        date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
     # Migration : ajouter texte_extrait si absent
    try:
        cursor.execute("ALTER TABLE factures ADD COLUMN texte_extrait TEXT")
    except:
        pass 
    # factures excel table

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
    # user table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        numero_client TEXT
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
            date_limite_paiement, consommation, type_service, 
            montant_total_ttc, texte_extrait
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees.get("numero_client"), donnees.get("numero_contrat"),
        donnees.get("nom_client"), donnees.get("adresse"),
        donnees.get("usage"), donnees.get("periode_debut"),
        donnees.get("periode_fin"), donnees.get("date_facture"),
        donnees.get("date_limite_paiement"), donnees.get("consommation"),
        donnees.get("type_service"), donnees.get("montant_total_ttc"),
        donnees.get("texte_extrait")
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


def importer_excel_en_db(lignes: list[dict], mode: str = "skip") -> dict:
    """
    Importe les lignes Excel en base.

    mode:
      - "skip"   : ignore les doublons (comportement original)
      - "update" : met à jour les lignes existantes (upsert)
      - "force"  : supprime les doublons et réinsère (remplace tout)

    Retourne: {
        "nouvelles": int,
        "doublons": int,
        "mises_a_jour": int,
        "total_traite": int,
        "mode": str
    }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    nouvelles = 0
    doublons = 0
    mises_a_jour = 0

    for ligne in lignes:
        num_client = str(ligne.get("numero_client", ""))
        periode_debut = str(ligne.get("periode_debut", ""))
        periode_fin = str(ligne.get("periode_fin", ""))

        cursor.execute("""
            SELECT id FROM factures_excel
            WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
        """, (num_client, periode_debut, periode_fin))
        existing = cursor.fetchone()

        if existing:
            if mode == "skip":
                doublons += 1
                continue
            elif mode == "update":
                cursor.execute("""
                    UPDATE factures_excel SET
                        agence = ?, date_edition = ?, numero_contrat = ?,
                        numero_compteur = ?, usage = ?, nom_client = ?,
                        adresse = ?, type_service = ?, consommation = ?,
                        unite = ?, montant_ttc = ?, date_limite_paiement = ?,
                        alerte = ?, mois_source = ?
                    WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
                """, (
                    str(ligne.get("agence", "")),
                    str(ligne.get("date_edition", "")),
                    str(ligne.get("numero_contrat", "")),
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
                    str(ligne.get("mois_source", "")),
                    num_client, periode_debut, periode_fin
                ))
                mises_a_jour += 1
                continue
            elif mode == "force":
                cursor.execute("""
                    DELETE FROM factures_excel
                    WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
                """, (num_client, periode_debut, periode_fin))
                doublons += 1
                # fall through to insert below

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
    return {
        "nouvelles": nouvelles,
        "doublons": doublons,
        "mises_a_jour": mises_a_jour,
        "total_traite": nouvelles + doublons + mises_a_jour,
        "mode": mode
    }


def get_resume_excel() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM factures_excel")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT nom_client FROM factures_excel ORDER BY nom_client")
    clients = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT mois_source FROM factures_excel ORDER BY mois_source")
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
    Ex: 'quel usage est majoritaire ?', 'quelle agence a le plus de clients ?'
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, agence, usage, type_service,
               mois_source, consommation, unite, montant_ttc,
               periode_debut, periode_fin, date_limite_paiement,
               adresse, numero_client, numero_contrat, numero_compteur,
               alerte
        FROM factures_excel
        ORDER BY nom_client, mois_source
    """)
    colonnes = [d[0] for d in cursor.description]
    rows = [dict(zip(colonnes, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def verifier_doublons(lignes: list[dict]) -> dict:
    """
    Vérifie combien de lignes existent déjà en base SANS les insérer.
    Utile pour afficher un aperçu avant import.

    Retourne: {
        "total": int,
        "existantes": int,
        "nouvelles": int,
        "clients_nouveaux": list[str]  -- noms des clients pas encore en base
    }
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existantes = 0
    nouvelles = 0
    clients_nouveaux = set()

    for ligne in lignes:
        num_client = str(ligne.get("numero_client", ""))
        periode_debut = str(ligne.get("periode_debut", ""))
        periode_fin = str(ligne.get("periode_fin", ""))

        cursor.execute("""
            SELECT id FROM factures_excel
            WHERE numero_client = ? AND periode_debut = ? AND periode_fin = ?
        """, (num_client, periode_debut, periode_fin))

        if cursor.fetchone():
            existantes += 1
        else:
            nouvelles += 1
            nom = str(ligne.get("nom_client", num_client))
            clients_nouveaux.add(nom)

    conn.close()
    return {
        "total": existantes + nouvelles,
        "existantes": existantes,
        "nouvelles": nouvelles,
        "clients_nouveaux": sorted(list(clients_nouveaux))
    }


def supprimer_factures_client(nom_ou_numero: str) -> int:
    """Supprime toutes les factures d'un client. Retourne le nombre de lignes supprimées."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    terme = f"%{nom_ou_numero}%"
    cursor.execute("""
        DELETE FROM factures_excel
        WHERE nom_client LIKE ? OR numero_client LIKE ?
    """, (terme, terme))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def reset_base_excel() -> int:
    """Vide entièrement la table factures_excel. Retourne le nombre de lignes supprimées."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM factures_excel")
    total = cursor.fetchone()[0]
    cursor.execute("DELETE FROM factures_excel")
    conn.commit()
    conn.close()
    return total
import hashlib
# hash password sert  a  sécurise le mot de passe, on ne stocke jamais le mot de passe en clair
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
# creer user sert aa cree un compte, retourne False si lemail existe déjà

def creer_user(email: str, password: str, role: str, numero_client: str = None) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (email, password, role, numero_client)
            VALUES (?, ?, ?, ?)
        """, (email, hash_password(password), role, numero_client))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# verifier login ::vérifie email + password, retourne les infos de l'utilisateur ou None
def verifier_login(email: str, password: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, email, role, numero_client 
        FROM users 
        WHERE email = ? AND password = ?
    """, (email, hash_password(password)))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "email": row[1],
            "role": row[2],
            "numero_client": row[3]
        }
    return None
def get_clients_avec_pdf() -> list:
    """Retourne la liste des clients qui ont un PDF importé."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT nom_client 
        FROM factures 
        WHERE nom_client IS NOT NULL AND nom_client != ''
        ORDER BY nom_client
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_texte_pdf_client(nom_client: str) -> str:
    """Retourne le texte extrait du PDF pour un client donné."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT texte_extrait 
        FROM factures 
        WHERE nom_client = ?
        ORDER BY date_enregistrement DESC
        LIMIT 1
    """, (nom_client,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""