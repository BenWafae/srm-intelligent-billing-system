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

from fastapi import FastAPI, Request, Form
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
@app.get("/admin", response_class=HTMLResponse)
def page_admin(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    user = sessions[session_id]
    return HTMLResponse(f"<h1>Bienvenue Admin — {user['email']} ✓</h1>")

@app.get("/employe", response_class=HTMLResponse)
def page_employe(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    user = sessions[session_id]
    return HTMLResponse(f"<h1>Bienvenue Employé — {user['email']} ✓</h1>")

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