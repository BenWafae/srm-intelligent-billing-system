import sys
import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from src.database import init_db, verifier_login
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.WARNING)

app = FastAPI()  # 1. créer app

app.mount("/static", StaticFiles(directory="src/assets"), name="static")  # 2. monter static

templates = Jinja2Templates(directory=str(os.path.join(BASE_DIR, "templates")))  # 3. templates

init_db()

# ════════════════════════════════════════════════════════════
# AGENT AUTONOME — Scheduler (Tâche 2 — Amélioration)
# ════════════════════════════════════════════════════════════

DB_PATH = os.path.join(BASE_DIR, "data", "srm.db")

def sauvegarder_derniere_execution(date_str: str):
    """Sauvegarde la date de dernière exécution en base."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_agent (
            cle TEXT PRIMARY KEY,
            valeur TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO config_agent (cle, valeur) VALUES ('derniere_execution_auto', ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (date_str,))
    conn.commit()
    conn.close()


def charger_derniere_execution() -> str | None:
    """Charge la date de dernière exécution depuis la base."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT valeur FROM config_agent WHERE cle = 'derniere_execution_auto'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None


def sauvegarder_dernier_resultat(resultat: str, nb_detectes: int, nb_envoyes: int):
    """Sauvegarde le dernier résultat en base."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO config_agent (cle, valeur) VALUES ('dernier_resultat_auto', ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (resultat,))
    cursor.execute("""
        INSERT INTO config_agent (cle, valeur) VALUES ('nb_detectes_auto', ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (str(nb_detectes),))
    cursor.execute("""
        INSERT INTO config_agent (cle, valeur) VALUES ('nb_envoyes_auto', ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (str(nb_envoyes),))
    conn.commit()
    conn.close()


def charger_dernier_resultat():
    """Charge le dernier résultat depuis la base."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT valeur FROM config_agent WHERE cle = 'dernier_resultat_auto'")
        resultat = cursor.fetchone()
        cursor.execute("SELECT valeur FROM config_agent WHERE cle = 'nb_detectes_auto'")
        nb_detectes = cursor.fetchone()
        cursor.execute("SELECT valeur FROM config_agent WHERE cle = 'nb_envoyes_auto'")
        nb_envoyes = cursor.fetchone()
        conn.close()
        return {
            "dernier_resultat": resultat[0] if resultat else None,
            "nb_detectes": int(nb_detectes[0]) if nb_detectes else 0,
            "nb_envoyes": int(nb_envoyes[0]) if nb_envoyes else 0
        }
    except:
        return {"dernier_resultat": None, "nb_detectes": 0, "nb_envoyes": 0}


# Stockage en mémoire du statut de l'agent
agent_status = {
    "actif"              : True,
    "derniere_execution" : charger_derniere_execution(),
    "prochain_run"       : None,
    "dernier_resultat"   : None,
    "nb_detectes"        : 0,
    "nb_envoyes"         : 0,
}

def tache_agent_automatique():
    """
    Fonction principale de l'agent autonome.
    Tourne en arrière-plan selon le planning défini.
    Zéro intervention humaine requise.
    """
    from datetime import datetime
    from src.agent.agent_alertes import detecter, get_seuil
    from src.agent.email_sender import envoyer_alertes_masse
    from src.database import alerte_deja_envoyee

    maintenant = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n[AGENT] ═══ Cycle automatique démarré — {maintenant} ═══")

    try:
        seuil = get_seuil()
        detectes = detecter(seuil, mode="moyenne")

        print(f"[AGENT] Seuil : {seuil}% — {len(detectes)} client(s) détecté(s)")

        # Filtrer : clients avec email ET alerte pas encore envoyée ce mois
        a_envoyer = []
        for c in detectes:
            if not c.get("email"):
                print(f"[AGENT] ⚠ {c['nom_client']} — sans email, ignoré")
                continue
            if alerte_deja_envoyee(c["numero_contrat"], c["mois_actuel"]):
                print(f"[AGENT] ⚠ {c['nom_client']} — alerte déjà envoyée ce mois, ignoré")
                continue
            # ✅ AJOUT DE LA SOURCE "auto" POUR L'AGENT AUTONOME
            c["source"] = "auto"
            a_envoyer.append(c)

        # Envoi
        nb_envoyes = 0
        if a_envoyer:
            rapport = envoyer_alertes_masse(a_envoyer)
            nb_envoyes = rapport.get("envoyes", 0)
            print(f"[AGENT] ✅ {nb_envoyes} email(s) envoyé(s)")
        else:
            print("[AGENT] ✅ Aucune nouvelle alerte à envoyer")

        # Mettre à jour le statut en mémoire
        agent_status["derniere_execution"] = maintenant
        agent_status["dernier_resultat"]   = "succes"
        agent_status["nb_detectes"]        = len(detectes)
        agent_status["nb_envoyes"]         = nb_envoyes

        # Sauvegarder en base pour persistance
        sauvegarder_derniere_execution(maintenant)
        sauvegarder_dernier_resultat("succes", len(detectes), nb_envoyes)

    except Exception as e:
        print(f"[AGENT] ❌ Erreur : {e}")
        agent_status["dernier_resultat"] = f"erreur: {str(e)}"
        sauvegarder_dernier_resultat(f"erreur: {str(e)}", 0, 0)

    print(f"[AGENT] ═══ Cycle terminé ═══\n")


# Démarrage du scheduler
scheduler = BackgroundScheduler(timezone="Africa/Casablanca")

# Job de production : chaque jour à 08h00
scheduler.add_job(
    tache_agent_automatique,
    trigger=CronTrigger(hour=8, minute=0),
    id="agent_prod",
    replace_existing=True
)

scheduler.start()
print("[AGENT] ✅ Scheduler démarré — exécution quotidienne à 08:00")

# Arrêt propre quand FastAPI s'arrête
import atexit
atexit.register(lambda: scheduler.shutdown())
sessions = {}


# ════════════════════════════════════════════
# PAGE LOGIN — GET
# ════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erreur": None}
    )


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = verifier_login(email, password)
    
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"erreur": "Email ou mot de passe incorrect."}
        )
    
    session_id = email + "_session"
    sessions[session_id] = user
    
    role = user["role"]
    response = RedirectResponse(url=f"/{role}", status_code=302)
    response.set_cookie("session_id", session_id)
    return response


# ════════════════════════════════════════════
# PAGE ADMIN
# ════════════════════════════════════════════
@app.get("/admin", response_class=HTMLResponse)
def page_admin(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    user = sessions[session_id]

    from src.database import (
        get_resume_excel, get_clients_avec_pdf,
        get_all_users, get_contrats_disponibles, get_fichiers_excel
    )
    resume = get_resume_excel()
    clients_pdf = get_clients_avec_pdf()
    users = get_all_users()
    contrats = get_contrats_disponibles()
    fichiers = get_fichiers_excel()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "email": user["email"],
            "total_factures": resume["total"],
            "nb_clients": len(resume["clients"]),
            "nb_periodes": len(resume["periodes"]),
            "clients": resume["clients"],
            "nb_clients_pdf": len(clients_pdf),
            "users": users,
            "contrats": contrats,
            "fichiers": fichiers,
        }
    )


# ════════════════════════════════════════════
# ADMIN — APERÇU EXCEL
# ════════════════════════════════════════════
@app.post("/api/admin/apercu-excel")
async def apercu_excel(fichier: UploadFile = File(...)):
    chemin_temp = f"excel_temp_{fichier.filename}"
    try:
        with open(chemin_temp, "wb") as f:
            f.write(await fichier.read())
        from src.excel_reader import lire_excel
        from src.database import verifier_doublons
        lignes = lire_excel(chemin_temp)
        apercu = verifier_doublons(lignes)
        return apercu
    except Exception as e:
        return {"erreur": str(e)}
    finally:
        import gc; gc.collect()
        import time; time.sleep(0.05)
        try:
            if os.path.exists(chemin_temp):
                os.remove(chemin_temp)
        except: pass


# ════════════════════════════════════════════
# ADMIN — IMPORT EXCEL
# ════════════════════════════════════════════
@app.post("/api/admin/import-excel")
async def import_excel(fichier: UploadFile = File(...)):
    chemin_temp = f"excel_temp_{fichier.filename}"
    nom_fichier = fichier.filename
    try:
        with open(chemin_temp, "wb") as f:
            f.write(await fichier.read())
        from src.excel_reader import lire_excel
        from src.database import importer_excel_en_db
        lignes = lire_excel(chemin_temp)
        resultat = importer_excel_en_db(lignes, mode="skip", nom_fichier=nom_fichier)
        return resultat
    except Exception as e:
        return {"erreur": str(e)}
    finally:
        import gc; gc.collect()
        import time; time.sleep(0.05)
        try:
            if os.path.exists(chemin_temp):
                os.remove(chemin_temp)
        except: pass


# ════════════════════════════════════════════
# ADMIN — SUPPRIMER CLIENT
# ════════════════════════════════════════════
@app.post("/api/admin/supprimer-client")
async def supprimer_client(request: Request):
    data = await request.json()
    client = data.get("client", "")
    from src.database import supprimer_factures_client
    n = supprimer_factures_client(client)
    return {"supprimees": n}


# ════════════════════════════════════════════
# ADMIN — RESET FICHIER EXCEL
# ════════════════════════════════════════════
@app.post("/api/admin/reset-fichier")
async def reset_fichier(request: Request):
    try:
        data = await request.json()
        nom_fichier = data.get("nom_fichier", "")
        print(f"Tentative de suppression du fichier: {nom_fichier}")  # Debug
        
        if not nom_fichier:
            return {"supprimees": 0, "erreur": "Nom de fichier manquant"}
        
        from src.database import reset_fichier_excel
        n = reset_fichier_excel(nom_fichier)
        print(f"Nombre de lignes supprimées: {n}")  # Debug
        return {"supprimees": n, "nom_fichier": nom_fichier}
    except Exception as e:
        print(f"Erreur dans reset-fichier: {str(e)}")  # Debug
        return {"supprimees": 0, "erreur": str(e)}


# ════════════════════════════════════════════
# ADMIN — RESET BASE COMPLÈTE
# ════════════════════════════════════════════
@app.post("/api/admin/reset-base")
async def reset_base():
    from src.database import reset_base_excel
    n = reset_base_excel()
    return {"supprimees": n}


# ════════════════════════════════════════════
# ADMIN — IMPORT PDF
# ════════════════════════════════════════════
@app.post("/api/admin/import-pdf")
async def import_pdf(fichier: UploadFile = File(...)):
    chemin_temp = f"pdf_temp_{fichier.filename}"
    with open(chemin_temp, "wb") as f:
        f.write(await fichier.read())
    try:
        from src.pdf_reader import extraire_texte
        from src.extractor import extraire_infos_facture
        from src.database import enregistrer_facture
        texte = extraire_texte(chemin_temp)
        infos = extraire_infos_facture(texte)
        if infos:
            infos["texte_extrait"] = texte
            saved = enregistrer_facture(infos)
            return {"statut": "succes" if saved else "doublon"}
        return {"statut": "erreur"}
    except Exception as e:
        return {"statut": "erreur", "detail": str(e)}
    finally:
        try:
            if os.path.exists(chemin_temp):
                os.remove(chemin_temp)
        except: pass


# ════════════════════════════════════════════
# ADMIN — CRÉER USER
# ════════════════════════════════════════════
@app.post("/api/admin/creer-user")
async def creer_user_route(request: Request):
    data = await request.json()
    from src.database import creer_user
    ok = creer_user(
        email=data.get("email"),
        password=data.get("password"),
        role=data.get("role"),
        numero_client=data.get("numero_contrat")
    )
    return {"succes": ok}


# ════════════════════════════════════════════
# ADMIN — SUPPRIMER USER
# ════════════════════════════════════════════
@app.post("/api/admin/supprimer-user")
async def supprimer_user_route(request: Request):
    data = await request.json()
    from src.database import supprimer_user
    supprimer_user(data.get("user_id"))
    return {"succes": True}


# ════════════════════════════════════════════
# ADMIN — CHANGER MOT DE PASSE UTILISATEUR
# ════════════════════════════════════════════
@app.post("/api/admin/changer-mot-de-passe")
async def admin_changer_mot_de_passe(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    nouveau_mdp = data.get("nouveau_mdp")
    
    if not user_id or not nouveau_mdp:
        return {"succes": False, "erreur": "user_id et nouveau_mdp requis"}
    
    if len(nouveau_mdp) < 4:
        return {"succes": False, "erreur": "Le mot de passe doit contenir au moins 4 caractères"}
    
    from src.database import update_user_password
    success = update_user_password(user_id, nouveau_mdp)
    
    if success:
        return {"succes": True}
    else:
        return {"succes": False, "erreur": "Utilisateur non trouvé"}


# ════════════════════════════════════════════
# ADMIN — AGENT ALERTES (Tâche 2)
# ════════════════════════════════════════════
@app.get("/api/admin/agent/seuil")
def get_seuil_route(request: Request):
    """Retourne le seuil actuel sauvegardé."""
    from src.agent.agent_alertes import get_seuil
    return {"seuil": get_seuil()}


@app.post("/api/admin/agent/seuil")
async def sauvegarder_seuil_route(request: Request):
    """Sauvegarde le nouveau seuil défini par l'admin."""
    data = await request.json()
    seuil = data.get("seuil", 30.0)
    from src.agent.agent_alertes import sauvegarder_seuil
    sauvegarder_seuil(float(seuil))
    return {"succes": True, "seuil": seuil}


@app.get("/api/admin/agent/detecter")
def detecter_route(request: Request, mode: str = "precedent"):
    from src.agent.agent_alertes import detecter, get_seuil
    seuil = get_seuil()
    detectes = detecter(seuil, mode=mode)
    return {
        "seuil"    : seuil,
        "mode"     : mode,
        "total"    : len(detectes),
        "detectes" : detectes
    }


@app.post("/api/admin/agent/envoyer-tous")
async def envoyer_tous_route(request: Request):
    """
    Envoie les alertes à tous les clients détectés.
    Reçoit la liste complète des clients détectés.
    """
    data = await request.json()
    clients = data.get("clients", [])
    # Ajouter source='manuel' pour chaque client
    for client in clients:
        client["source"] = "manuel"
    from src.agent.email_sender import envoyer_alertes_masse
    rapport = envoyer_alertes_masse(clients)
    return rapport


@app.post("/api/admin/agent/envoyer-selection")
async def envoyer_selection_route(request: Request):
    """
    Envoie les alertes uniquement aux clients sélectionnés par l'admin.
    Reçoit une liste de clients sélectionnés.
    """
    data = await request.json()
    clients = data.get("clients", [])
    # Ajouter source='manuel' pour chaque client
    for client in clients:
        client["source"] = "manuel"
    from src.agent.email_sender import envoyer_alertes_masse
    rapport = envoyer_alertes_masse(clients)
    return rapport


@app.post("/api/admin/agent/envoyer-un")
async def envoyer_un_route(request: Request):
    """
    Envoie l'alerte à un seul client.
    Utile pour tester ou envoyer manuellement.
    """
    data = await request.json()
    client = data.get("client", {})
    client["source"] = "manuel"  # Ajouter source
    from src.agent.email_sender import envoyer_alertes_masse
    rapport = envoyer_alertes_masse([client])
    return rapport


# ════════════════════════════════════════════
# ADMIN — HISTORIQUE ALERTES (Amélioration Tâche 2)
# ════════════════════════════════════════════
@app.get("/api/admin/agent/historique")
def get_historique_route(request: Request, limit: int = 50):
    """
    Retourne l'historique des alertes envoyées.
    Paramètre optionnel: limit (nombre max d'alertes, défaut: 50)
    """
    from src.database import get_historique_alertes
    historique = get_historique_alertes(limit)
    return {
        "total": len(historique),
        "historique": historique
    }


@app.get("/api/admin/agent/historique/client/{numero_contrat}")
def get_historique_client_route(request: Request, numero_contrat: str):
    """
    Retourne l'historique des alertes pour un client spécifique.
    """
    from src.database import get_historique_alertes_client
    historique = get_historique_alertes_client(numero_contrat)
    return {
        "numero_contrat": numero_contrat,
        "total": len(historique),
        "historique": historique
    }


@app.delete("/api/admin/agent/historique/{alerte_id}")
async def supprimer_alerte_route(request: Request, alerte_id: int):
    """
    Supprime une alerte spécifique de l'historique.
    """
    from src.database import supprimer_alerte_historique
    success = supprimer_alerte_historique(alerte_id)
    return {"succes": success, "alerte_id": alerte_id}


# ════════════════════════════════════════════════════════════
# AGENT AUTONOME — Routes scheduler
# ════════════════════════════════════════════════════════════
@app.get("/api/admin/agent/statut-auto")
def get_statut_auto(request: Request):
    """Retourne le statut actuel de l'agent automatique."""
    job = scheduler.get_job("agent_prod")
    prochain = None
    if job and job.next_run_time:
        prochain = job.next_run_time.strftime("%d/%m/%Y %H:%M")
    
    # Si la mémoire est vide, charger depuis la base
    if not agent_status["derniere_execution"]:
        saved_exec = charger_derniere_execution()
        if saved_exec:
            agent_status["derniere_execution"] = saved_exec
        
        saved_result = charger_dernier_resultat()
        if saved_result["dernier_resultat"]:
            agent_status["dernier_resultat"] = saved_result["dernier_resultat"]
            agent_status["nb_detectes"] = saved_result["nb_detectes"]
            agent_status["nb_envoyes"] = saved_result["nb_envoyes"]
    
    return {
        "actif"              : agent_status["actif"],
        "derniere_execution" : agent_status["derniere_execution"],
        "prochain_run"       : prochain,
        "dernier_resultat"   : agent_status["dernier_resultat"],
        "nb_detectes"        : agent_status["nb_detectes"],
        "nb_envoyes"         : agent_status["nb_envoyes"],
    }


@app.post("/api/admin/agent/lancer-auto")
def lancer_agent_maintenant(request: Request):
    """
    Lance le cycle agent immédiatement.
    Utile pour tester sans attendre le planning.
    """
    tache_agent_automatique()
    return {
        "succes"             : True,
        "derniere_execution" : agent_status["derniere_execution"],
        "nb_detectes"        : agent_status["nb_detectes"],
        "nb_envoyes"         : agent_status["nb_envoyes"],
    }
@app.post("/api/admin/agent/lancer-auto-ia")
def lancer_agent_avec_ia(request: Request):
    """
    Lance le cycle agent avec enrichissement IA (Mistral).
    Même logique que lancer-auto mais les emails contiennent
    une analyse contextuelle générée par le LLM.
    """
    from src.agent.agent_alertes import detecter, get_seuil
    from src.agent.email_sender import envoyer_email
    from src.agent.email_templates import generer_email_html, generer_sujet_email, generer_analyse_llm
    from src.database import enregistrer_alerte, alerte_deja_envoyee

    seuil = get_seuil()
    detectes = detecter(seuil, mode="moyenne")  # mode par défaut agent auto

    nb_detectes = len(detectes)
    nb_envoyes = 0
    nb_sans_email = 0
    nb_erreurs = 0

    for client in detectes:
        # ⭐ AJOUT 1 : Déterminer le type_service à partir de l'unité ou du service
        unite = client.get("unite", "")
        if "m³" in unite or "m3" in unite:
            client["type_service"] = "eau"
        else:
            client["type_service"] = "électricité"
        
        # ⭐ AJOUT 2 : Si usage est manquant ou vide, mettre une valeur par défaut
        if not client.get("usage"):
            client["usage"] = "non spécifié"
        
        # Vérifier doublon
        if alerte_deja_envoyee(client["numero_contrat"], client["mois_actuel"]):
            print(f"[IA] Doublon ignoré : {client['nom_client']} — {client['mois_actuel']}")
            continue

        client["source"] = "auto"
        sujet = generer_sujet_email(client)

        if not client.get("email"):
            nb_sans_email += 1
            enregistrer_alerte(client, sujet, False, statut="sans_email", source="auto")
            continue

        # Générer analyse LLM — fallback silencieux si Mistral indisponible
        analyse = generer_analyse_llm(client)
        print(f"[IA] Analyse pour {client['nom_client']} : {analyse[:100]}..." if analyse else f"[IA] Pas d'analyse pour {client['nom_client']}")

        # Générer email enrichi
        corps_html = generer_email_html(client, analyse_ia=analyse if analyse else None)

        # Envoyer
        resultat = envoyer_email(client["email"], sujet, corps_html)
        enregistrer_alerte(client, sujet, resultat["succes"], source="auto")

        if resultat["succes"]:
            nb_envoyes += 1
        else:
            nb_erreurs += 1
            print(f"[IA] Erreur envoi {client['nom_client']} : {resultat['erreur']}")

    # Mettre à jour le statut agent
    from datetime import datetime
    agent_status["derniere_execution"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    agent_status["nb_detectes"] = nb_detectes
    agent_status["nb_envoyes"] = nb_envoyes

    return {
        "succes"      : True,
        "nb_detectes" : nb_detectes,
        "nb_envoyes"  : nb_envoyes,
        "nb_sans_email": nb_sans_email,
        "nb_erreurs"  : nb_erreurs,
    }
@app.post("/api/admin/agent/toggle-auto")
async def toggle_agent_auto(request: Request):
    """Active ou désactive le scheduler."""
    data = await request.json()
    activer = data.get("activer", True)
    
    if activer:
        if not scheduler.running:
            scheduler.start()
        job = scheduler.get_job("agent_prod")
        if job:
            job.resume()
        agent_status["actif"] = True
        print("[AGENT] ✅ Agent automatique activé")
    else:
        job = scheduler.get_job("agent_prod")
        if job:
            job.pause()
        agent_status["actif"] = False
        print("[AGENT] ⏸ Agent automatique désactivé")
    
    return {"succes": True, "actif": agent_status["actif"]}


@app.get("/api/admin/agent/alerte-existe")
def alerte_existe_route(request: Request, numero_contrat: str, mois: str):
    """Vérifie si une alerte a déjà été envoyée pour ce client ce mois."""
    from src.database import alerte_deja_envoyee
    existe = alerte_deja_envoyee(numero_contrat, mois)
    return {"existe": existe}

@app.get("/employe", response_class=HTMLResponse)
def page_employe(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")

    user = sessions[session_id]

    from src.database import get_resume_excel, get_fichiers_excel, get_clients_avec_pdf
    resume = get_resume_excel()
    fichiers = get_fichiers_excel()
    clients_pdf = get_clients_avec_pdf()

    return templates.TemplateResponse(
        request=request,
        name="employe.html",
        context={
            "email": user["email"],
            "total_factures": resume["total"],
            "nb_clients": len(resume["clients"]),
            "nb_periodes": len(resume["periodes"]),
            "fichiers": fichiers,
            "clients_pdf": clients_pdf,
        }
    )


@app.post("/api/chat/employe/excel")
async def chat_employe_excel(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"reponse": "Session expirée."}

    data = await request.json()
    question = data.get("question", "")
    nom_fichier = data.get("nom_fichier", "")
    historique = data.get("historique", [])

    from src.llm import poser_question_excel
    reponse = poser_question_excel(question, historique, nom_fichier=nom_fichier)
    return {"reponse": reponse}


@app.post("/api/chat/employe/pdf")
async def chat_employe_pdf(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"reponse": "Session expirée."}

    data = await request.json()
    question = data.get("question", "")
    client = data.get("client", "")
    historique = data.get("historique", [])

    from src.database import get_texte_pdf_client
    from src.llm import poser_question

    texte = get_texte_pdf_client(client)
    if not texte:
        return {"reponse": f"Aucun PDF trouvé pour {client}."}

    reponse = poser_question(texte, question, historique)
    return {"reponse": reponse}


# ════════════════════════════════════════════════════════════
# EMPLOYÉ — CONVERSATIONS PERSISTANTES
# ════════════════════════════════════════════════════════════
@app.get("/api/employe/conversations")
def get_conversations_employe(request: Request, mode: str = None):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"conversations": []}
    user = sessions[session_id]
    from src.database import get_conversations_employe
    convs = get_conversations_employe(user["email"], mode=mode)
    return {"conversations": convs}


@app.post("/api/employe/conversation/creer")
async def creer_conv_employe(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"erreur": "Session expirée"}
    user = sessions[session_id]
    data = await request.json()
    from src.database import creer_conversation_employe
    conv_id = creer_conversation_employe(
        email=user["email"],
        premiere_question=data["premiere_question"],
        mode=data["mode"],
        nom_fichier=data.get("nom_fichier", "")
    )
    return {"conversation_id": conv_id}


@app.post("/api/employe/conversation/ajouter-message")
async def ajouter_message_employe_route(request: Request):
    data = await request.json()
    from src.database import ajouter_message_employe
    for msg in data.get("messages", []):
        ajouter_message_employe(data["conversation_id"], msg["role"], msg["content"])
    return {"succes": True}


@app.get("/api/employe/messages/{conv_id}")
def get_messages_employe(conv_id: int, request: Request):
    from src.database import get_messages_conversation_employe
    messages = get_messages_conversation_employe(conv_id)
    return {"messages": messages}


@app.post("/api/employe/conversation/renommer")
async def renommer_conv_employe(request: Request):
    data = await request.json()
    from src.database import modifier_titre_conversation_employe
    modifier_titre_conversation_employe(data["conversation_id"], data["nouveau_titre"])
    return {"succes": True}


@app.post("/api/employe/conversation/supprimer")
async def supprimer_conv_employe(request: Request):
    data = await request.json()
    from src.database import supprimer_conversation_employe
    supprimer_conversation_employe(data["conversation_id"])
    return {"succes": True}


# Ajoutez après les routes existantes de l'employé
@app.post("/api/employe/changer-mot-de-passe")
async def changer_mdp_employe(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"succes": False, "erreur": "Session expirée"}
    user = sessions[session_id]
    data = await request.json()
    from src.database import verifier_login, changer_password_employe
    if not verifier_login(user["email"], data["ancien_mdp"]):
        return {"succes": False, "erreur": "Mot de passe actuel incorrect"}
    changer_password_employe(user["email"], data["nouveau_mdp"])
    return {"succes": True}


@app.get("/client", response_class=HTMLResponse)
def page_client(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    
    user = sessions[session_id]
    numero_contrat = user["numero_client"]
    
    from src.database import (
        get_nom_client_par_contrat,
        get_derniere_facture_client,
        get_prochain_paiement_client
    )
    
    nom_client = get_nom_client_par_contrat(numero_contrat) or "Client"
    derniere = get_derniere_facture_client(numero_contrat)
    prochain = get_prochain_paiement_client(numero_contrat)
    
    return templates.TemplateResponse(
        request=request,
        name="client.html",
        context={
            "nom_client": nom_client,
            "derniere_montant": f"{derniere['montant']:,.0f}" if derniere else "—",
            "derniere_mois": derniere["mois"] if derniere else "—",
            "derniere_conso": f"{derniere['consommation']:,.0f}" if derniere else "—",
            "derniere_unite": derniere["unite"] if derniere else "—",
            "prochain_date": prochain["date_limite"] if prochain else "Aucune",
            "prochain_jours": prochain["jours"] if prochain else "—",
            "historique": []
        }
    )


@app.post("/api/chat/client")
async def chat_client(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"reponse": "Session expirée."}
    
    user = sessions[session_id]
    numero_contrat = user["numero_client"]
    
    data = await request.json()
    question = data.get("question", "")
    historique_texte = data.get("historique_texte", "")
    
    from src.rag.client_connecte import repondre_client_connecte
    reponse = repondre_client_connecte(question, numero_contrat, historique_texte)
    
    return {"reponse": reponse}


# ════════════════════════════════════════════
# CLIENT — CONVERSATIONS PERSISTANTES
# ════════════════════════════════════════════
@app.get("/api/client/conversations")
def get_conversations(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"conversations": []}
    user = sessions[session_id]
    from src.database import get_conversations_client
    convs = get_conversations_client(user["numero_client"])
    return {"conversations": convs}


@app.post("/api/client/conversation/creer")
async def creer_conv(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"erreur": "Session expirée"}
    user = sessions[session_id]
    data = await request.json()
    from src.database import creer_conversation
    conv_id = creer_conversation(user["numero_client"], data["premiere_question"])
    return {"conversation_id": conv_id}


@app.post("/api/client/conversation/ajouter-message")
async def ajouter_messages(request: Request):
    data = await request.json()
    from src.database import ajouter_message
    for msg in data.get("messages", []):
        ajouter_message(data["conversation_id"], msg["role"], msg["content"])
    return {"succes": True}


@app.get("/api/client/messages/{conv_id}")
def get_messages(conv_id: int, request: Request):
    from src.database import get_messages_conversation
    messages = get_messages_conversation(conv_id)
    return {"messages": messages}


@app.post("/api/client/conversation/renommer")
async def renommer_conversation(request: Request):
    data = await request.json()
    from src.database import modifier_titre_conversation
    modifier_titre_conversation(data["conversation_id"], data["nouveau_titre"])
    return {"succes": True}


@app.post("/api/client/conversation/supprimer")
async def supprimer_conv(request: Request):
    data = await request.json()
    from src.database import supprimer_conversation
    supprimer_conversation(data["conversation_id"])
    return {"succes": True}


# ════════════════════════════════════════════
# CLIENT — TÉLÉCHARGEMENT FACTURE PDF
# ════════════════════════════════════════════
@app.get("/api/client/mois-disponibles")
def mois_disponibles(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"mois": []}
    user = sessions[session_id]
    from src.database import get_mois_client
    return {"mois": get_mois_client(user["numero_client"])}


@app.get("/api/client/telecharger-facture")
def telecharger_facture(request: Request, mois: str):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    user = sessions[session_id]
    from src.rag_client.pdf_facture import generer_pdf_facture
    from fastapi.responses import StreamingResponse
    import io
    pdf = generer_pdf_facture(user["numero_client"], mois)
    if not pdf:
        return {"erreur": "Facture introuvable"}
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=facture_{mois}.pdf"}
    )


@app.post("/api/client/changer-mot-de-passe")
async def changer_mdp(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"succes": False, "erreur": "Session expirée"}
    user = sessions[session_id]
    data = await request.json()
    from src.database import verifier_login, changer_password_client
    if not verifier_login(user["email"], data["ancien_mdp"]):
        return {"succes": False, "erreur": "Mot de passe actuel incorrect"}
    changer_password_client(user["email"], data["nouveau_mdp"])
    return {"succes": True}


# ════════════════════════════════════════════
# DÉCONNEXION
# ════════════════════════════════════════════
@app.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    response = RedirectResponse(url="/")
    response.delete_cookie("session_id")
    return response