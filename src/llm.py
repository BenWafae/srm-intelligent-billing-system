import requests

def poser_question(texte_facture: str, question: str) -> str:
    prompt = f"""Tu es un assistant intelligent spécialisé dans l'analyse de factures SRM (eau et électricité).

Voici le contenu d'une facture :
{texte_facture}

Question du client : {question}

Réponds de façon claire et précise en français, en te basant uniquement sur les informations de la facture.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


# -------- TEST --------
if __name__ == "__main__":
    texte_test = "Client : Ahmed Alami | Consommation : 901 kWh | Montant TTC : 30 627,46 Dhs"
    question_test = "Quel est le montant à payer ?"
    print(poser_question(texte_test, question_test))