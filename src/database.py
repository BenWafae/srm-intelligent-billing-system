import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "srm.db")
from datetime import datetime

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
        nom_fichier TEXT,
        date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
# Migration APRÈS le CREATE TABLE
    try:
        cursor.execute("ALTER TABLE factures_excel ADD COLUMN nom_fichier TEXT")
    except:
        pass


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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations_client (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_contrat TEXT NOT NULL,
        titre TEXT NOT NULL,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages_client (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        contenu TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations_client(id)
    )
""")
# Dans init_db() — à ajouter après les tables existantes

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations_employe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_employe TEXT NOT NULL,
        titre TEXT NOT NULL,
        mode TEXT NOT NULL,
        nom_fichier TEXT,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   
    )
""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages_employe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        contenu TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations_employe(id)
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


def importer_excel_en_db(lignes: list[dict], mode: str = "skip", nom_fichier: str = "") -> dict:

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
                unite, montant_ttc, date_limite_paiement, alerte, mois_source, nom_fichier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
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
            str(ligne.get("mois_source", "")),
            nom_fichier 
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

def get_contrats_disponibles() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT nom_client, numero_contrat 
        FROM factures_excel 
        WHERE numero_contrat IS NOT NULL AND numero_contrat != ''
        ORDER BY nom_client
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"nom_client": r[0], "numero_contrat": r[1]} for r in rows]

# liste users
def get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, email, role, numero_client 
        FROM users 
        ORDER BY role, email
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "email": r[1], "role": r[2], "numero_client": r[3]} for r in rows]

def supprimer_user(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True
# recuperer num contrat
def get_nom_client_par_contrat(numero_contrat: str) -> str:
    """Retourne le nom du client depuis son numéro de contrat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT nom_client 
        FROM factures_excel 
        WHERE numero_contrat = ?
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
def get_mois_client(numero_contrat: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT mois_source
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]
def get_fichiers_excel() -> list[str]:
    """Retourne la liste des fichiers Excel importés (distincts)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT nom_fichier 
        FROM factures_excel 
        WHERE nom_fichier IS NOT NULL AND nom_fichier != ''
        ORDER BY nom_fichier
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]
# interface client new tokkens
def get_statut_paiements_client(numero_contrat: str) -> list[dict]:
    """
    Retourne toutes les factures du client avec leur statut de paiement.
    Calcule en Python si la date limite est dépassée.
    Colonnes utilisées : date_limite_paiement, mois_source, montant_ttc
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, date_limite_paiement, montant_ttc
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY periode_debut
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()
 
    aujourd_hui = datetime.now()
    resultats = []
    for mois, date_str, montant in rows:
        en_retard = False
        try:
            date_limite = datetime.strptime(date_str, "%d/%m/%Y")
            en_retard = date_limite < aujourd_hui
        except Exception:
            pass
        resultats.append({
            "mois": mois,
            "date_limite": date_str,
            "montant_ttc": montant,
            "en_retard": en_retard,
        })
    return resultats

def get_derniere_facture_client(numero_contrat: str) -> dict | None:
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc, consommation, unite, periode_debut
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2) DESC
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()

    aujourd_hui = datetime.now()
    for row in rows:
        try:
            date_debut = datetime.strptime(row[4], "%d/%m/%Y")
            if date_debut <= aujourd_hui:
                return {
                    "mois": row[0],
                    "montant": row[1],
                    "consommation": row[2],
                    "unite": row[3]
                }
        except:
            continue
    return None
def get_prochain_paiement_client(numero_contrat: str) -> dict | None:
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, date_limite_paiement, montant_ttc, periode_debut
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()

    aujourd_hui = datetime.now()
    for mois, date_str, montant, periode_debut in rows:
        try:
            # On prend le mois dont la PÉRIODE DE DÉBUT <= aujourd'hui
            # et dont la DATE LIMITE est encore dans le futur
            date_debut = datetime.strptime(periode_debut, "%d/%m/%Y")
            date_limite = datetime.strptime(date_str, "%d/%m/%Y")
            if date_debut <= aujourd_hui and date_limite >= aujourd_hui:
                jours = (date_limite - aujourd_hui).days
                return {
                    "mois"       : mois,
                    "date_limite": date_str,
                    "montant_ttc": montant,
                    "jours"      : jours
                }
        except:
            continue
    return None

def get_historique_client(numero_contrat: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois_source, montant_ttc, consommation, unite
        FROM factures_excel
        WHERE numero_contrat = ?
        ORDER BY SUBSTR(periode_debut,7,4)||SUBSTR(periode_debut,4,2)||SUBSTR(periode_debut,1,2)
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()
    return [{"mois": r[0], "montant": r[1], "consommation": r[2], "unite": r[3]} for r in rows]
 
def get_client_par_numero_contrat(numero_contrat: str) -> dict | None:
    """Retourne les infos d'un client depuis son numéro de contrat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT nom_client, numero_contrat, agence, usage, 
                        type_service, adresse, numero_client, numero_compteur
        FROM factures_excel
        WHERE numero_contrat = ?
        LIMIT 1
    """, (numero_contrat,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "nom_client": row[0],
        "numero_contrat": row[1],
        "agence": row[2],
        "usage": row[3],
        "type_service": row[4],
        "adresse": row[5],
        "numero_client": row[6],
        "numero_compteur": row[7],
    }
# ════════════════════════════════════════════
# PERSISTANCE CONVERSATIONNELLE — CLIENT
# ════════════════════════════════════════════

def creer_conversation(numero_contrat: str, premiere_question: str) -> int:
    """
    Crée une nouvelle conversation et retourne son id.
    Le titre est généré automatiquement depuis les 5 premiers mots
    de la première question du client.
    """
    mots = premiere_question.strip().split()
    titre = " ".join(mots[:5])
    if len(mots) > 5:
        titre += "..."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations_client (numero_contrat, titre)
        VALUES (?, ?)
    """, (numero_contrat, titre))
    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conversation_id


def ajouter_message(conversation_id: int, role: str, contenu: str) -> None:
    """
    Sauvegarde un message dans une conversation.
    role = 'user' (message du client) ou 'assistant' (réponse du chatbot)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages_client (conversation_id, role, contenu)
        VALUES (?, ?, ?)
    """, (conversation_id, role, contenu))
    conn.commit()
    conn.close()


def get_conversations_client(numero_contrat: str) -> list[dict]:
    """
    Retourne toutes les conversations d'un client,
    triées de la plus récente à la plus ancienne.
    Pour affichage dans la sidebar.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, titre, date_creation
        FROM conversations_client
        WHERE numero_contrat = ?
        ORDER BY date_creation DESC
    """, (numero_contrat,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "titre": r[1], "date_creation": r[2]}
        for r in rows
    ]


def get_messages_conversation(conversation_id: int) -> list[dict]:
    """
    Retourne tous les messages d'une conversation dans l'ordre chronologique.
    Pour recharger une ancienne conversation.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, contenu
        FROM messages_client
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def modifier_titre_conversation(conversation_id: int, nouveau_titre: str) -> None:
    """
    Permet au client de renommer une conversation depuis la sidebar.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE conversations_client
        SET titre = ?
        WHERE id = ?
    """, (nouveau_titre.strip(), conversation_id))
    conn.commit()
    conn.close()


def supprimer_conversation(conversation_id: int) -> None:
    """
    Supprime une conversation et tous ses messages.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM messages_client
        WHERE conversation_id = ?
    """, (conversation_id,))
    cursor.execute("""
        DELETE FROM conversations_client
        WHERE id = ?
    """, (conversation_id,))
    conn.commit()
    conn.close()
def reset_fichier_excel(nom_fichier: str) -> int:
    """Supprime toutes les factures d'un fichier Excel précis."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM factures_excel WHERE nom_fichier = ?", (nom_fichier,))
    total = cursor.fetchone()[0]
    cursor.execute("DELETE FROM factures_excel WHERE nom_fichier = ?", (nom_fichier,))
    conn.commit()
    conn.close()
    return total
# ════════════════════════════════════════════════════════════
# PERSISTANCE CONVERSATIONNELLE — EMPLOYÉ
# ════════════════════════════════════════════════════════════

def creer_conversation_employe(email: str, premiere_question: str, 
                                mode: str, nom_fichier: str = "") -> int:
    mots = premiere_question.strip().split()
    titre = " ".join(mots[:5])
    if len(mots) > 5:
        titre += "..."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations_employe (email_employe, titre, mode, nom_fichier)
        VALUES (?, ?, ?, ?)
    """, (email, titre, mode, nom_fichier))
    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conversation_id


def ajouter_message_employe(conversation_id: int, role: str, contenu: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages_employe (conversation_id, role, contenu)
        VALUES (?, ?, ?)
    """, (conversation_id, role, contenu))
    conn.commit()
    conn.close()


def get_conversations_employe(email: str, mode: str = None) -> list[dict]:
    """
    Retourne les conversations d'un employé.
    Si mode précisé → filtre sur 'excel' ou 'pdf'.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if mode:
        cursor.execute("""
            SELECT id, titre, mode, nom_fichier, date_creation
            FROM conversations_employe
            WHERE email_employe = ? AND mode = ?
            ORDER BY date_creation DESC
        """, (email, mode))
    else:
        cursor.execute("""
            SELECT id, titre, mode, nom_fichier, date_creation
            FROM conversations_employe
            WHERE email_employe = ?
            ORDER BY date_creation DESC
        """, (email,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "titre": r[1], "mode": r[2], 
         "nom_fichier": r[3], "date_creation": r[4]}
        for r in rows
    ]


def get_messages_conversation_employe(conversation_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, contenu
        FROM messages_employe
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """, (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def modifier_titre_conversation_employe(conversation_id: int, 
                                         nouveau_titre: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE conversations_employe SET titre = ? WHERE id = ?
    """, (nouveau_titre.strip(), conversation_id))
    conn.commit()
    conn.close()


def supprimer_conversation_employe(conversation_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM messages_employe WHERE conversation_id = ?", 
        (conversation_id,)
    )
    cursor.execute(
        "DELETE FROM conversations_employe WHERE id = ?", 
        (conversation_id,)
    )
    conn.commit()
    conn.close()
def changer_password_client(email: str, nouveau_mdp: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password = ? WHERE email = ?",
        (hash_password(nouveau_mdp), email)
    )
    conn.commit()
    conn.close()
def changer_password_employe(email: str, nouveau_mdp: str) -> None:
    """Change le mot de passe d'un employé."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password = ? WHERE email = ?",
        (hash_password(nouveau_mdp), email)
    )
    conn.commit()
    conn.close()