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
    R : détecter le client dans la question OU dans l'historique
    A : construire un contexte ciblé et complet avec toutes les colonnes
    G : envoyer à Mistral et retourner la réponse
    """

    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    # --- R : RETRIEVAL ---

    # Étape 1 — chercher le client dans la question actuelle
    client_trouve = detecter_client(question, resume["clients"])

    # Étape 2 — si pas trouvé, chercher dans l'historique
    # (cas où l'utilisateur dit "et son adresse ?" sans répéter le nom)
    if not client_trouve:
        for msg in reversed(historique):
            client_dans_historique = detecter_client(msg["content"], resume["clients"])
            if client_dans_historique:
                client_trouve = client_dans_historique
                break  # On prend le plus récent et on s'arrête

    if client_trouve:
        # Client trouvé → récupérer TOUTES ses données depuis la BD
        factures_client = rechercher_client_excel(client_trouve)

        # Infos fixes — identiques sur tous les mois
        premier = factures_client[0]
        contexte = (
            f"=== Informations du client ===\n"
            f"  Nom          : {premier['nom_client']}\n"
            f"  N° Client    : {premier['numero_client']}\n"
            f"  N° Contrat   : {premier['numero_contrat']}\n"
            f"  N° Compteur  : {premier['numero_compteur']}\n"
            f"  Adresse      : {premier['adresse']}\n"
            f"  Agence       : {premier['agence']}\n"
            f"  Usage        : {premier['usage']}\n"
            f"  Type service : {premier['type_service']}\n\n"
            f"=== Historique des factures ({len(factures_client)} mois) ===\n"
        )

        # Détails par mois — données qui changent chaque mois
        for f in factures_client:
            alerte = f"⚠️ {f['alerte']}" if f['alerte'] else "Aucune"
            contexte += (
                f"\n  Mois             : {f['mois_source']}\n"
                f"  Période          : {f['periode_debut']} → {f['periode_fin']}\n"
                f"  Date édition     : {f['date_edition']}\n"
                f"  Consommation     : {f['consommation']} {f['unite']}\n"
                f"  Montant TTC      : {f['montant_ttc']} Dhs\n"
                f"  Date limite pmt  : {f['date_limite_paiement']}\n"
                f"  Alerte           : {alerte}\n"
            )

    else:
        # Aucun client détecté → contexte général
        contexte = (
            f"=== Base de données SRM Souss-Massa ===\n"
            f"  Total factures   : {resume['total']}\n"
            f"  Clients          : {', '.join(resume['clients'])}\n"
            f"  Périodes         : {', '.join(resume['periodes'])}\n"
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

    print("\nTest 4 — Adresse et usage :")
    print("-" * 50)
    print(poser_question_excel("Quelle est l'adresse de Omar et son usage ?"))