import google.generativeai as genai
import os
from dotenv import load_dotenv
#  lit le fichier .env et charge ta clé Gemini
load_dotenv() 

# connecte le script à l'API Gemini avec la clé
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
#  choisit le modèle Gemini gratuit et rapide
model = genai.GenerativeModel("gemini-2.0-flash")
# construit le prompt avec le texte de la facture 
# + la question, envoie à Gemini, et retourne la réponse
def poser_question(texte_facture, question):
    prompt = f"""
Tu es un assistant intelligent qui analyse des factures d'eau et d'électricité de la SRM Souss-Massa.

Voici le contenu de la facture :
{texte_facture}

Question du client : {question}

Réponds de manière claire et précise en te basant uniquement sur la facture.
"""
    reponse = model.generate_content(prompt)
    return reponse.text