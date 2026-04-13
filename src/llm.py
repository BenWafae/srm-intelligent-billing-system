import requests
from src.database import get_resume_excel
from src.rag_general import repondre_question_generale, repondre_question_client


def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    """Mode PDF — inchangé"""
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
    """Détecte si la question fait référence à quelqu'un mentionné avant"""
    mots_reference = ["son ", "sa ", "ses ", " il ", " elle ", "lui", "leur"]
    question_lower = question.lower()
    return any(mot in question_lower for mot in mots_reference)


def poser_question_excel(question: str, historique: list = []) -> str:
    """
    Mode Excel — RAG complet :

    CAS 1 — Client détecté :
      → detecter_intent_client() — quel type d'analyse ?
      → fetcher Python ciblé — calcul exact
      → Mistral présente uniquement

    CAS 2 — Question générale :
      → detecter_intent() — quelle catégorie ?
      → fetcher Python ciblé
      → Mistral présente uniquement
    """

    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    # --- Détecter client dans la question ---
    client_trouve = detecter_client(question, resume["clients"])

    # --- Si pas de client, chercher dans l'historique via référence ---
    if not client_trouve and question_fait_reference(question):
        for msg in reversed(historique):
            client_dans_historique = detecter_client(msg["content"], resume["clients"])
            if client_dans_historique:
                client_trouve = client_dans_historique
                break

    # --- Historique texte ---
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    # --- CAS 1 : Client spécifique → RAG analytique client ---
    if client_trouve:
        return repondre_question_client(question, client_trouve, historique_texte)

    # --- CAS 2 : Question générale → RAG par intent ---
    return repondre_question_generale(question, historique_texte)