import sys
import os

# ════════════════════════════════════════════
# CHEMINS — tous les modules du projet
# ════════════════════════════════════════════
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag"))
sys.path.insert(0, os.path.join(BASE_DIR, "src", "rag_client"))

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.database import init_db, verifier_login

app = FastAPI()
templates = Jinja2Templates(directory=str(os.path.join(BASE_DIR, "templates")))

init_db()
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
# PAGES RÔLES — temporaires pour tester
# ════════════════════════════════════════════
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
    data = await request.json()
    nom_fichier = data.get("nom_fichier", "")
    from src.database import reset_fichier_excel
    n = reset_fichier_excel(nom_fichier)
    return {"supprimees": n, "nom_fichier": nom_fichier}

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

    from src.llm import poser_question_excel
    reponse = poser_question_excel(question, [], nom_fichier=nom_fichier)
    return {"reponse": reponse}

@app.post("/api/chat/employe/pdf")
async def chat_employe_pdf(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return {"reponse": "Session expirée."}

    data = await request.json()
    question = data.get("question", "")
    client = data.get("client", "")

    from src.database import get_texte_pdf_client
    from src.llm import poser_question

    texte = get_texte_pdf_client(client)
    if not texte:
        return {"reponse": f"Aucun PDF trouvé pour {client}."}

    reponse = poser_question(texte, question, [])
    return {"reponse": reponse}

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
    
    from src.rag.client_connecte import repondre_client_connecte
    reponse = repondre_client_connecte(question, numero_contrat, "")
    
    return {"reponse": reponse}
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