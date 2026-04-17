import re
import unicodedata
import requests
from src.database import get_resume_excel
from src.rag_general import repondre_question_generale, repondre_question_client


# ─────────────────────────────────────────────────────────
# MOTS FONCTIONNELS — ignorés lors de la détection de noms
# ─────────────────────────────────────────────────────────
MOTS_FONCTIONNELS = {
    "information", "informations", "consommation", "consomation", "facture",
    "factures", "montant", "montants", "mois", "pour", "avec", "dans", "donne",
    "donner", "liste", "lister", "quel", "quelle", "quels", "quelles", "comment",
    "combien", "evolution", "historique", "moyenne", "maximum", "minimum", "mars",
    "avril", "mais", "juin", "juillet", "aout", "septembre", "octobre", "novembre",
    "decembre", "janvier", "fevrier", "alerte", "alertes", "total", "client",
    "clients", "agence", "service", "usage", "contrat", "compteur", "adresse",
    "tous", "toutes", "voir", "afficher", "montrer", "est", "sont", "avoir",
    "etre", "plus", "moins", "tout", "cette", "chez", "leur", "leurs", "plus",
    "periode", "debut", "limite", "paiement", "date", "type", "quand", "depuis",
    "dernier", "derniere", "derniers", "aussi", "avez", "avons", "avait", "etait"
}


# ─────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────

def normaliser(texte: str) -> str:
    """Supprime accents et met en minuscule pour comparaison robuste"""
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte


def extraire_mots_nom(question: str) -> list[str]:
    """
    Extrait uniquement les mots qui ressemblent à des noms propres :
    longueur > 2, pas dans les mots fonctionnels.
    """
    mots = [normaliser(m) for m in re.findall(r'\b\w+\b', question)]
    return [m for m in mots if len(m) > 2 and m not in MOTS_FONCTIONNELS]


# ─────────────────────────────────────────────────────────
# DÉTECTION CLIENT
# ─────────────────────────────────────────────────────────

def detecter_client(question: str, liste_clients: list) -> tuple[str | list | None, str]:
    """
    Retourne (client_trouvé_ou_liste, statut)

    statut :
      "exact"   → un seul client identifié sans ambiguïté → répondre directement
      "ambigu"  → plusieurs clients possibles → demander précision nom complet
      "inconnu" → fragment de nom détecté mais absent de la base → dire inexistant
      "aucun"   → aucun nom propre détecté → question générale

    Exemples :
      "omar"         → exact (Omar Lachkar)        si un seul Omar dans la base
      "omar lachkar" → exact (Omar Lachkar)
      "omar chbani"  → inconnu ("chbani" hors base et hors nom du client trouvé)
      "fatima"       → ambigu si 2 Fatima, exact si 1 seule
      "fatima alami" → inconnu si "alami" n'appartient à aucun client
      "liste clients"→ aucun → question générale
    """
    q_norm = normaliser(question)
    clients_norm = [(c, normaliser(c)) for c in liste_clients]

    # ── Étape 1 : correspondance nom complet exact dans la question ──
    for client_original, client_norm in clients_norm:
        if client_norm in q_norm:
            return client_original, "exact"

    # ── Étape 2 : extraire les mots-noms de la question ──
    mots_nom_question = extraire_mots_nom(question)

    if not mots_nom_question:
        return None, "aucun"

    # ── Étape 3 : classer les mots : dans la base ou hors base ──
    mots_dans_base = [m for m in mots_nom_question
                      if any(m in cn for (_, cn) in clients_norm)]
    mots_hors_base = [m for m in mots_nom_question
                      if not any(m in cn for (_, cn) in clients_norm)]

    # Aucun mot reconnu dans la base → question générale (pas un nom de client)
    if not mots_dans_base:
        return None, "aucun"

    # ── Étape 4 : trouver les clients qui contiennent les mots reconnus ──
    clients_correspondants = []
    for client_original, client_norm in clients_norm:
        if any(m in client_norm for m in mots_dans_base):
            clients_correspondants.append((client_original, client_norm))

    # ── Étape 5 : vérifier si les mots hors base contredisent le(s) client(s) trouvé(s) ──
    if mots_hors_base and clients_correspondants:
        # Un mot hors-base qui n'appartient à aucun des clients trouvés
        # = l'utilisateur a tapé un nom différent → client inexistant
        mots_hors_base_vrais = [
            m for m in mots_hors_base
            if not any(m in cn for (_, cn) in clients_correspondants)
        ]
        if mots_hors_base_vrais:
            return None, "inconnu"

    # ── Étape 6 : résolution finale ──
    if len(clients_correspondants) == 1:
        return clients_correspondants[0][0], "exact"
    elif len(clients_correspondants) > 1:
        return [c[0] for c in clients_correspondants], "ambigu"

    return None, "aucun"


def question_fait_reference(question: str) -> bool:
    """Détecte si la question fait référence implicite à un client mentionné avant"""
    mots_reference = ["son ", "sa ", "ses ", " il ", " elle ", "lui ", "leur "]
    question_lower = question.lower()
    return any(mot in question_lower for mot in mots_reference)


# ─────────────────────────────────────────────────────────
# MODE PDF
# ─────────────────────────────────────────────────────────

def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    """Analyse une facture PDF avec le LLM Mistral"""
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


# ─────────────────────────────────────────────────────────
# MODE EXCEL — POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────────────────

def poser_question_excel(question: str, historique: list = []) -> str:
    """
    RAG complet sur la base Excel.

    CAS 1 — Client exact détecté         → fetcher analytique client
    CAS 2 — Ambiguïté (plusieurs clients) → demander précision
    CAS 3 — Nom inconnu détecté           → dire que le client n'existe pas
    CAS 4 — Référence implicite (il/elle) → chercher client dans l'historique
    CAS 5 — Question générale             → fetcher général par intent
    """
    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    liste_clients = resume["clients"]

    # ── Détection client dans la question ──
    resultat, statut = detecter_client(question, liste_clients)

    # ── CAS 2 : Ambiguïté ──
    if statut == "ambigu":
        noms_formates = "\n".join(f"- {c}" for c in resultat)
        return (
            "⚠️ Plusieurs clients correspondent à votre recherche. "
            "Pouvez-vous préciser le nom complet ?\n\n"
            + noms_formates
        )

    # ── CAS 3 : Client inconnu ──
    if statut == "inconnu":
        return (
            "❌ Ce client n'existe pas dans la base de données. "
            "Veuillez vérifier le nom et réessayer.\n\n"
            "Clients disponibles :\n"
            + "\n".join(f"- {c}" for c in liste_clients)
        )

    client_trouve = resultat if statut == "exact" else None

    # ── CAS 4 : Référence implicite → chercher dans l'historique ──
    if not client_trouve and question_fait_reference(question):
        for msg in reversed(historique):
            res, st = detecter_client(msg["content"], liste_clients)
            if st == "exact":
                client_trouve = res
                break

    # ── Historique texte pour le LLM ──
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    # ── CAS 1 : Client trouvé → RAG analytique client ──
    if client_trouve:
        return repondre_question_client(question, client_trouve, historique_texte)

    # ── CAS 5 : Question générale → RAG par intent ──
    return repondre_question_generale(question, historique_texte)