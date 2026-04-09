import requests

def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    
    # Construire l'historique en texte
    historique_texte = ""
    for msg in historique[:-1]:  # Exclure la dernière question déjà dans le prompt
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un assistant intelligent spécialisé dans l'analyse de factures SRM (eau et électricité).

Voici le contenu de la facture :
{texte_facture}

Historique de la conversation :
{historique_texte}

Nouvelle question du client : {question}

Réponds de façon claire et précise en français, en tenant compte du contexte de la conversation.
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