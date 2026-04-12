import requests
from src.database import get_resume_excel, rechercher_client_excel
from src.text_to_sql import repondre_question_generale


def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    """Mode PDF — analyse d'une seule facture — inchangé"""

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


def detecter_client(question: str, liste_clients: list) -> str | None:
    """Détecte si un client est mentionné dans la question — inchangé"""
    question_lower = question.lower()
    for client in liste_clients:
        mots_client = client.lower().split()
        for mot in mots_client:
            if len(mot) > 3 and mot in question_lower:
                return client
    return None


def question_fait_reference(question: str) -> bool:
    """
    Détecte si la question fait référence à quelqu'un
    mentionné avant dans la conversation.
    Ex: "quelle est SON adresse ?" → True
    Ex: "quels clients existent ?" → False
    """
    mots_reference = ["son ", "sa ", "ses ", " il ", " elle ", "lui", "leur"]
    question_lower = question.lower()
    return any(mot in question_lower for mot in mots_reference)


def poser_question_excel(question: str, historique: list = []) -> str:
    """
    Mode Excel — RAG complet :

    Questions sur client spécifique :
    R : detecter_client() dans question ou historique
    A : contexte ciblé avec toutes les colonnes du client
    G : Mistral répond

    Questions générales :
    R : Text-to-SQL — Mistral génère SQL → Python exécute → résultat exact
    A : résultat SQL compact envoyé à Mistral
    G : Mistral répond en français
    """

    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    # --- R : RETRIEVAL ---

    # Étape 1 — client mentionné dans la question actuelle ?
    client_trouve = detecter_client(question, resume["clients"])

    # Étape 2 — pas de client mais référence à quelqu'un (son/sa/ses/il/elle)
    # → chercher le dernier client mentionné dans l'historique
    if not client_trouve and question_fait_reference(question):
        for msg in reversed(historique):
            client_dans_historique = detecter_client(msg["content"], resume["clients"])
            if client_dans_historique:
                client_trouve = client_dans_historique
                break

    # --- A : AUGMENTATION + G : GENERATION ---

    if client_trouve:
        # ── CAS 1 : Question sur un client spécifique ──
        # Contexte ciblé — toutes les données du client
        factures_client = rechercher_client_excel(client_trouve)
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
        for f in factures_client:
            contexte += (
                f"\n  Mois             : {f['mois_source']}\n"
                f"  Période          : {f['periode_debut']} → {f['periode_fin']}\n"
                f"  Date édition     : {f['date_edition']}\n"
                f"  Consommation     : {f['consommation']} {f['unite']}\n"
                f"  Montant TTC      : {f['montant_ttc']} Dhs\n"
                f"  Date limite pmt  : {f['date_limite_paiement']}\n"
            )

        # Historique conversation
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
"""
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False}
        )
        return response.json()["response"]

    else:
        # ── CAS 2 : Question générale → Text-to-SQL ──
        # Pas de 72 lignes envoyées — Mistral génère le SQL
        # Python exécute → résultat exact → Mistral répond
        historique_texte = ""
        for msg in historique[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"

        return repondre_question_generale(question, historique_texte)


# -------- TEST --------
if __name__ == "__main__":

    print("Test 1 — Mode PDF :")
    print("-" * 50)
    texte_test = "Client : Ahmed Alami | Consommation : 901 kWh | Montant TTC : 30 627,46 Dhs"
    print(poser_question(texte_test, "Quel est le montant à payer ?"))

    print("\nTest 2 — RAG client spécifique :")
    print("-" * 50)
    print(poser_question_excel("Quel est le montant total de Fatima ?"))

    print("\nTest 3 — Question générale → Text-to-SQL :")
    print("-" * 50)
    print(poser_question_excel("Quels clients existent dans la base ?"))

    print("\nTest 4 — Question analytique → Text-to-SQL :")
    print("-" * 50)
    print(poser_question_excel("Quel est l'usage majoritaire parmi tous les clients ?"))

    print("\nTest 5 — Référence historique :")
    print("-" * 50)
    historique_test = [
        {"role": "user", "content": "montant de Omar"},
        {"role": "assistant", "content": "Le montant total d'Omar est 2471.52 Dhs"}
    ]
    print(poser_question_excel("quelle est son adresse ?", historique_test))