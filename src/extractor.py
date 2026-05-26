import requests
import json
import re
import os


def extraire_infos_facture(texte: str) -> dict:
    prompt = f"""Tu es un extracteur de données spécialisé dans les factures SRM (eau et électricité).

Analyse ce texte de facture et retourne UNIQUEMENT un objet JSON valide avec ces champs exacts :

{{
  "numero_client": "...",
  "numero_contrat": "...",
  "nom_client": "...",
  "adresse": "...",
  "usage": "...",
  "periode_debut": "...",
  "periode_fin": "...",
  "date_facture": "...",
  "date_limite_paiement": "...",
  "consommation": 0.0,
  "type_service": "eau" ou "electricite",
  "montant_total_ttc": 0.0
}}

Si une information est absente, mets null.
Ne retourne rien d'autre que le JSON, sans explication.

Texte de la facture :
{texte}
"""

    OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    resultat = response.json()["response"]

    # Extraire le JSON de la réponse
    match = re.search(r'\{.*\}', resultat, re.DOTALL)
    if match:
        return json.loads(match.group())
    else:
        return {}


# -------- TEST --------
if __name__ == "__main__":
    texte_test = """
    N° Client : A10AB120/460 000001
    N° Contrat : 0003333337 / 1836412
    Client : Samira Cherkaoui
    Adresse : Rue Ibn Batouta 7 - Tiznit
    Usage : USAGE DOMESTIQUE
    Période : 01/03/2025 au 31/03/2025
    Date facture : 10/04/2025
    Date limite : 30/04/2025
    Consommation : 32 m³
    Total : 221,68 Dhs
    """
    infos = extraire_infos_facture(texte_test)
    print(json.dumps(infos, indent=2, ensure_ascii=False))