import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.database import init_db, verifier_login

app = FastAPI()
templates = Jinja2Templates(directory=str(os.path.join(os.path.dirname(__file__), "templates")))

# Initialisation base de données
init_db()

# Stockage sessions simple
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
    return HTMLResponse(f"<h1>Bienvenue Client — {user['email']} ✓</h1>")

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