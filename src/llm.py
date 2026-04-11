import requests
from src.database import get_resume_excel, rechercher_client_excel


# --- Fonction existante — Mode PDF inchangée ---

def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    """Mode PDF — analyse d'une seule facture"""

    historique_texte = ""
    for msg in historique[:-1]:
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
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


# --- Nouvelles fonctions — Mode Excel avec vrai RAG ---

def detecter_client(question: str, liste_clients: list) -> str | None:
    """
    R du RAG — détecter si un client est mentionné dans la question.
    Compare chaque mot de la question avec la liste des clients en BD.
    Retourne le nom du client trouvé, ou None si aucun.
    """
    question_lower = question.lower()
    for client in liste_clients:
        mots_client = client.lower().split()
        for mot in mots_client:
            if len(mot) > 3 and mot in question_lower:
                return client
    return None


def poser_question_excel(question: str, historique: list = []) -> str:
    """
    Mode Excel — vrai RAG :
    R : détecter le client et récupérer ses données depuis la BD
    A : construire un contexte ciblé et précis
    G : envoyer à Mistral et retourner la réponse
    """

    # Récupérer le résumé global pour savoir ce qu'on a en BD
    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    # --- R : RETRIEVAL ---
    # Détecter si un client est mentionné dans la question
    client_trouve = detecter_client(question, resume["clients"])

    if client_trouve:
        # Client détecté → récupérer UNIQUEMENT ses factures
        factures_client = rechercher_client_excel(client_trouve)

        # Construire le contexte ciblé
        contexte = f"Données du client '{client_trouve}' ({len(factures_client)} factures) :\n\n"
        for f in factures_client:
            alerte = f"| ⚠️ {f['alerte']}" if f['alerte'] else ""
            contexte += (
                f"  Période : {f['mois_source']}"
                f" | Consommation : {f['consommation']} {f['unite']}"
                f" | Montant : {f['montant_ttc']} Dhs"
                f" | Échéance : {f['date_limite_paiement']}"
                f" {alerte}\n"
            )
    else:
        # Pas de client détecté → contexte général
        contexte = (
            f"Base de données SRM Souss-Massa :\n"
            f"  Total factures : {resume['total']}\n"
            f"  Clients disponibles : {', '.join(resume['clients'])}\n"
            f"  Périodes couvertes : {', '.join(resume['periodes'])}\n"
        )

    # --- A : AUGMENTATION ---
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un assistant intelligent de la SRM Souss-Massa, spécialisé dans l'analyse des données de facturation.

Voici les données disponibles :
{contexte}

IMPORTANT : Réponds UNIQUEMENT en te basant sur les données ci-dessus.
Ne suppose aucune période ou donnée qui n'est pas mentionnée explicitement.

Historique de la conversation :
{historique_texte}

Question : {question}

Réponds de façon claire et précise en français.
Si des alertes de consommation élevée sont présentes, mentionne-les.
"""

    # --- G : GENERATION ---
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


# -------- TEST --------
if __name__ == "__main__":

    print("Test 1 — Mode PDF (inchangé) :")
    print("-" * 50)
    texte_test = "Client : Ahmed Alami | Consommation : 901 kWh | Montant TTC : 30 627,46 Dhs"
    print(poser_question(texte_test, "Quel est le montant à payer ?"))

    print("\nTest 2 — RAG avec client mentionné :")
    print("-" * 50)
    print(poser_question_excel("Quel est le montant total de Fatima sur toutes les périodes ?"))

    print("\nTest 3 — RAG question générale :")
    print("-" * 50)
    print(poser_question_excel("Quels clients avez-vous dans la base ?"))