import re
import unicodedata
import requests
from src.database import get_resume_excel
from src.rag_general import repondre_question_generale, repondre_question_client


# ─────────────────────────────────────────────────────────
# MOTS FONCTIONNELS
# ─────────────────────────────────────────────────────────
MOTS_FONCTIONNELS = {
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
    "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
    "octobre", "novembre", "decembre", "janvier", "fevrier",
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
    "eleve", "elevee", "elevees", "eleves",
    "faible", "faibles",
    "moins", "plus",
    "mois", "periode",
    "consomme", "consommee", "consommes",
    "paye", "payee", "payes",
    "quel", "quelle", "quels", "quelles",
    "est", "sont", "etait", "etaient",
    "meme", "aussi", "encore",
}

# ─────────────────────────────────────────────────────────
# PATTERNS QUESTIONS GÉNÉRALES
# ✅ Ajout : "quel client consomme...", "qui consomme...",
#            "quel client a une consommation...", etc.
# Ces questions portent sur TOUS les clients, pas un seul.
# ─────────────────────────────────────────────────────────
PATTERNS_QUESTION_GENERALE = [
    # patterns originaux
    r"\bcombien\b.*(client|facture|enregistrement)",
    r"\b(liste|lister|afficher|montrer|donner)\b.*(client|tous|toutes)",
    r"\b(tous|toutes)\b.*(client|facture)",
    r"\bquels?\b.*(client|facture|enregistrement).*(exist|disponible|base|avoir)",
    r"\bquels?\b\s+(sont|etaient?)\b.*(client)",
    r"\bnombre\b.*(client|facture)",
    r"\bkombien\b",
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
    # ✅ NOUVEAUX — questions générales sur la consommation de tous les clients
    r"\bquel\s+client\b",                          # "quel client consomme/a/..."
    r"\bqui\s+consomme\b",                         # "qui consomme le plus/moins"
    r"\bqui\s+paie\b",                             # "qui paie le plus"
    r"\bqui\s+paye\b",                             # "qui paye le plus"
    r"\bqui\s+a\s+(la|le|les|une)\b",              # "qui a la consommation..."
    r"\bclient\s+(avec|qui|a\s+une|ayant)\b",      # "client avec consommation..."
    r"\bquel\s+est\s+le\s+client\b",               # "quel est le client qui..."
    r"\bconsomme\s+(le\s+plus|le\s+moins|eleve|elevee|faible|max|min)\b",
    r"\bconsomme\s+la\s+plus\b",                   # "consomme la plus élevée/faible"
]

MOTS_REFERENCE_IMPLICITE = [
    "son ", "sa ", "ses ", " il ", " elle ", "lui ", "leur ",
    "ce client", "ce meme client", "le meme", "la meme",
    "pour lui", "pour elle", "de lui", "d elle",
    "quel est le mois", "quel mois", "quelle est sa",
    "quel est son", "et sa ", "et son ", "et ses ",
    "et pour", "maintenant", "aussi", "egalement",
]


def est_question_generale(question: str) -> bool:
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


def detecter_client(question: str, liste_clients: list) -> tuple[str | list | None, str]:
    if est_question_generale(question):
        return None, "aucun"

    q_norm = normaliser(question)
    clients_norm = [(c, normaliser(c)) for c in liste_clients]

    # Étape 1 : correspondance nom complet exact
    for client_original, client_norm in clients_norm:
        if client_norm in q_norm:
            return client_original, "exact"

    # Étape 2 : extraire les mots-noms
    mots_nom_question = extraire_mots_nom(question)
    if not mots_nom_question:
        return None, "aucun"

    # Étape 3 : mots reconnus dans la base
    mots_dans_base = [m for m in mots_nom_question
                      if any(m in cn for (_, cn) in clients_norm)]
    if not mots_dans_base:
        return None, "aucun"

    # Étape 4 : filtrer mots plausibles (longueur >= 4)
    mots_plausibles = [m for m in mots_dans_base if len(m) >= 4]
    if not mots_plausibles:
        return None, "aucun"

    # Étape 5 : clients correspondants (mot entier)
    clients_correspondants = []
    for client_original, client_norm in clients_norm:
        for m in mots_plausibles:
            parties_client = client_norm.split()
            if any(partie == m or partie.startswith(m) for partie in parties_client):
                clients_correspondants.append((client_original, client_norm))
                break

    if len(clients_correspondants) == 1:
        return clients_correspondants[0][0], "exact"
    elif len(clients_correspondants) > 1:
        return [c[0] for c in clients_correspondants], "ambigu"

    return None, "aucun"


def question_fait_reference(question: str) -> bool:
    if est_question_generale(question):
        return False

    # ── Questions courtes sur les stats globales ──
    q_norm = normaliser(question)
    _questions_globales = [
        "nbr client", "nb client", "nbre client",
        "nombre client", "nombre de client",
        "nbr clients", "nb clients",
        "client eau", "client elec",
        "client electricite", "clients eau",
        "clients elec", "nbr facture",
        "nb facture", "nombre facture",
        "top consommation", "top conso",
        "max conso", "conso max",
        "qui consomme", "qui consome",
        "quel client consomme", "quel client a",
        "client max", "client min",
        "consomme le plus", "consomme le moins",
    ]
    if any(t in q_norm for t in _questions_globales):
        return False

    question_lower = question.lower()
    for mot in MOTS_REFERENCE_IMPLICITE:
        if mot in question_lower:
            return True

    mots = question_lower.split()
    if len(mots) <= 8:
        mots_norm = [normaliser(m) for m in mots]
        tous_fonctionnels = all(m in MOTS_FONCTIONNELS or len(m) <= 3 for m in mots_norm)
        if tous_fonctionnels:
            return True

    return False

def _extraire_client_depuis_historique(historique: list, liste_clients: list) -> str | None:
    for msg in reversed(historique):
        contenu = msg.get("content", "")
        if msg.get("role") == "user":
            res, st = detecter_client(contenu, liste_clients)
            if st == "exact":
                print(f"  [CONTEXTE] Client trouvé dans historique user : {res}")
                return res
        if msg.get("role") == "assistant":
            noms_gras = re.findall(r'\*\*([^*]+)\*\*', contenu)
            for nom in noms_gras:
                for client in liste_clients:
                    if normaliser(client) == normaliser(nom):
                        print(f"  [CONTEXTE] Client trouvé dans réponse assistant : {client}")
                        return client
            res, st = detecter_client(contenu, liste_clients)
            if st == "exact":
                print(f"  [CONTEXTE] Client trouvé dans texte assistant : {res}")
                return res
    return None


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
    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    liste_clients = resume["clients"]

    resultat, statut = detecter_client(question, liste_clients)

    if statut == "ambigu":
        noms_formates = "\n".join(f"- {c}" for c in resultat)
        return (
            "⚠️ Plusieurs clients correspondent à votre recherche. "
            "Pouvez-vous préciser le nom complet ?\n\n"
            + noms_formates
        )

    client_trouve = resultat if statut == "exact" else None

    if not client_trouve and question_fait_reference(question):
        client_trouve = _extraire_client_depuis_historique(historique, liste_clients)
        if client_trouve:
            print(f"  [CONTEXTE] Réutilisation client depuis historique : {client_trouve}")

    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    if client_trouve:
        return repondre_question_client(question, client_trouve, historique_texte)

    return repondre_question_generale(question, historique_texte)