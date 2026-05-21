import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587


# ════════════════════════════════════════════════════════════
# ENVOI EMAIL UNIQUE
# ════════════════════════════════════════════════════════════

def envoyer_email(destinataire: str, sujet: str, corps_html: str) -> dict:
    """
    Envoie un email HTML à un destinataire.

    Retourne :
    {
        "succes": bool,
        "destinataire": str,
        "erreur": str | None
    }
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = destinataire

        # Corps HTML
        msg.attach(MIMEText(corps_html, "html", "utf-8"))

        # Connexion SMTP Gmail
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, destinataire, msg.as_string())

        return {
            "succes"       : True,
            "destinataire" : destinataire,
            "erreur"       : None
        }

    except Exception as e:
        return {
            "succes"       : False,
            "destinataire" : destinataire,
            "erreur"       : str(e)
        }


# ════════════════════════════════════════════════════════════
# ENVOI EN MASSE
# ════════════════════════════════════════════════════════════

def envoyer_alertes_masse(clients_detectes: list[dict]) -> dict:
    """
    Envoie les alertes à tous les clients détectés.
    Ignore les clients sans email.

    Retourne un rapport :
    {
        "total"        : int,
        "envoyes"      : int,
        "sans_email"   : int,
        "erreurs"      : int,
        "details"      : list[dict]
    }
    """
    from src.agent.email_templates import (
        generer_email_html,
        generer_sujet_email
    )
    from src.database import enregistrer_alerte

    rapport = {
        "total"      : len(clients_detectes),
        "envoyes"    : 0,
        "sans_email" : 0,
        "erreurs"    : 0,
        "details"    : []
    }

    for client in clients_detectes:
        email = client.get("email")
        
        # Récupérer la source (défaut "manuel" si non définie)
        source = client.get("source", "manuel")

        # Client sans email → on note et on passe
        if not email:
            rapport["sans_email"] += 1
            rapport["details"].append({
                "nom"          : client.get("nom_client"),
                "email"        : None,
                "statut"       : "sans_email",
                "erreur"       : None
            })
            # Enregistrer dans l'historique comme sans_email AVEC LA SOURCE
            sujet = generer_sujet_email(client)
            enregistrer_alerte(client, sujet, False, statut="sans_email", source=source)
            continue

        # Générer le contenu
        sujet      = generer_sujet_email(client)
        corps_html = generer_email_html(client)

        # Envoyer
        resultat = envoyer_email(email, sujet, corps_html)

        # Enregistrer dans l'historique AVEC LA SOURCE
        enregistrer_alerte(client, sujet, resultat["succes"], source=source)

        if resultat["succes"]:
            rapport["envoyes"] += 1
            rapport["details"].append({
                "nom"    : client.get("nom_client"),
                "email"  : email,
                "statut" : "envoye",
                "erreur" : None
            })
        else:
            rapport["erreurs"] += 1
            rapport["details"].append({
                "nom"    : client.get("nom_client"),
                "email"  : email,
                "statut" : "erreur",
                "erreur" : resultat["erreur"]
            })

    return rapport