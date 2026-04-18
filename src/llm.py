import re
import unicodedata
import requests
from src.database import get_resume_excel
from src.rag_general import repondre_question_generale, repondre_question_client


# ─────────────────────────────────────────────────────────
# MOTS FONCTIONNELS — ignorés lors de la détection de noms
# ─────────────────────────────────────────────────────────
MOTS_FONCTIONNELS = {
    # verbes courants
    "information", "informations", "consommation", "consomation", "facture",
    "factures", "montant", "montants", "mois", "pour", "avec", "dans", "donne",
    "donner", "liste", "lister", "quel", "quelle", "quels", "quelles", "comment",
    "combien", "evolution", "historique", "moyenne", "maximum", "minimum",
    "alerte", "alertes", "total", "client", "clients", "agence", "service",
    "usage", "contrat", "compteur", "adresse", "tous", "toutes", "voir",
    "afficher", "montrer", "est", "sont", "avoir", "etre", "plus", "moins",
    "tout", "cette", "chez", "leur", "leurs", "periode", "debut", "limite",
    "paiement", "date", "type", "quand", "depuis", "dernier", "derniere",
    "derniers", "aussi", "avez", "avons", "avait", "etait", "comparer",
    "compare", "comparaison", "entre", "versus", "levolution", "donnez",
    "infos", "info", "quelle", "quel", "quels",
    # mois
    "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
    "octobre", "novembre", "decembre", "janvier", "fevrier",
    # ✅ AJOUTS — mots qui causaient de faux positifs
    "existe", "existent", "existant", "existants", "disponible", "disponibles",
    "enregistre", "enregistres", "enregistree", "enregistrees",
    "qui", "que", "quoi", "lequel", "laquelle", "lesquels", "lesquelles",
    "votre", "notre", "mon", "ton", "son", "mes", "tes", "ses",
    "nous", "vous", "ils", "elles", "lui", "eux",
    "base", "donnees", "systeme", "application", "fichier",
    "nouveau", "nouvelle", "nouveaux", "nouvelles",
    "nombre", "nbre", "nbr", "fois", "encore", "deja",
    "avoir", "avons", "avez", "avait", "avaient",
    "etre", "suis", "sommes", "etes", "etaient",
    "faire", "fait", "faites", "faisons",
    "vouloir", "veux", "veut", "voulez",
    "pouvoir", "peux", "peut", "pouvez",
    "savoir", "sais", "sait", "savez",
}

# ─────────────────────────────────────────────────────────
# QUESTIONS GÉNÉRALES — patterns qui ne concernent JAMAIS
# un client spécifique, peu importe les mots qu'elles contiennent
# ─────────────────────────────────────────────────────────
PATTERNS_QUESTION_GENERALE = [
    r"\bcombien\b.*(client|facture|enregistrement)",
    r"\b(liste|lister|afficher|montrer|donner)\b.*(client|tous|toutes)",
    r"\b(tous|toutes)\b.*(client|facture)",
    r"\bquels?\b.*(client|facture|enregistrement).*(exist|disponible|base|avoir)",
    r"\bquels?\b\s+(sont|etaient?)\b.*(client)",
    r"\bnombre\b.*(client|facture)",
    r"\bkombien\b",   # faute fréquente
    r"\btotal\b.*(client|facture|enregistrement)",
    r"\bstatistique",
    r"\bresume\b",
    r"\bbilan\b",
    r"\bagence",
    r"\busage",
    r"\bclassement\b",
    r"\bevolution\b",
    r"\balerte",
    r"\bservice",
]


def est_question_generale(question: str) -> bool:
    """
    Retourne True si la question porte clairement sur la base entière
    et non sur un client spécifique.
    """
    q = normaliser(question)
    for pattern in PATTERNS_QUESTION_GENERALE:
        if re.search(pattern, q):
            return True
    return False


def normaliser(texte: str) -> str:
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte


def extraire_mots_nom(question: str) -> list[str]:
    mots = [normaliser(m) for m in re.findall(r'\b\w+\b', question)]
    return [m for m in mots if len(m) > 2 and m not in MOTS_FONCTIONNELS]


# ─────────────────────────────────────────────────────────
# DÉTECTION CLIENT
# ─────────────────────────────────────────────────────────

def detecter_client(question: str, liste_clients: list) -> tuple[str | list | None, str]:
    """
    Retourne (client_trouvé_ou_liste, statut)

    statut :
      "exact"   → un seul client identifié
      "ambigu"  → plusieurs clients possibles
      "aucun"   → aucun client détecté → question générale
    """
    # ✅ Si c'est clairement une question générale, ne pas chercher de client
    if est_question_generale(question):
        return None, "aucun"

    q_norm = normaliser(question)
    clients_norm = [(c, normaliser(c)) for c in liste_clients]

    # ── Étape 1 : correspondance nom complet exact ──
    for client_original, client_norm in clients_norm:
        if client_norm in q_norm:
            return client_original, "exact"

    # ── Étape 2 : extraire les mots-noms ──
    mots_nom_question = extraire_mots_nom(question)

    if not mots_nom_question:
        return None, "aucun"

    # ── Étape 3 : mots reconnus dans la base ──
    mots_dans_base = [m for m in mots_nom_question
                      if any(m in cn for (_, cn) in clients_norm)]

    if not mots_dans_base:
        return None, "aucun"

    # ✅ Vérification supplémentaire : les mots trouvés ressemblent-ils
    # vraiment à des prénoms/noms ? (longueur >= 4 et pas trop génériques)
    mots_plausibles = [m for m in mots_dans_base if len(m) >= 4]
    if not mots_plausibles:
        return None, "aucun"

    # ── Étape 4 : clients correspondants ──
    clients_correspondants = []
    for client_original, client_norm in clients_norm:
        if any(m in client_norm for m in mots_plausibles):
            clients_correspondants.append((client_original, client_norm))

    # ── Étape 5 : résolution finale ──
    if len(clients_correspondants) == 1:
        return clients_correspondants[0][0], "exact"
    elif len(clients_correspondants) > 1:
        return [c[0] for c in clients_correspondants], "ambigu"

    return None, "aucun"


def question_fait_reference(question: str) -> bool:
    # ✅ Ne pas activer la référence implicite sur des questions générales
    if est_question_generale(question):
        return False
    mots_reference = ["son ", "sa ", "ses ", " il ", " elle ", "lui ", "leur "]
    question_lower = question.lower()
    return any(mot in question_lower for mot in mots_reference)


# ─────────────────────────────────────────────────────────
# MODE PDF
# ─────────────────────────────────────────────────────────

def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
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
    CAS 1 — Client exact détecté         → fetcher analytique client
    CAS 2 — Ambiguïté (plusieurs clients) → demander précision
    CAS 3 — Référence implicite (il/elle) → chercher dans l'historique
    CAS 4 — Question générale             → fetcher général par intent
    """
    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    liste_clients = resume["clients"]

    # ── Détection client ──
    resultat, statut = detecter_client(question, liste_clients)

    # ── CAS 2 : Ambiguïté ──
    if statut == "ambigu":
        noms_formates = "\n".join(f"- {c}" for c in resultat)
        return (
            "⚠️ Plusieurs clients correspondent à votre recherche. "
            "Pouvez-vous préciser le nom complet ?\n\n"
            + noms_formates
        )

    client_trouve = resultat if statut == "exact" else None

    # ── CAS 3 : Référence implicite → chercher dans l'historique ──
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

    # ── CAS 4 : Question générale ──
    return repondre_question_generale(question, historique_texte)