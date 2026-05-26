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
    "meme", "aussi", "encore", "somme", "sommes",
    "janv", "fevr", "juil", "aout", "sept", "oct", "nov", "dec",
    "jan", "fev", "mar", "avr", "jun", "jul", "aug", "sep",
    "lusage", "lagence", "ladresse", "linfos",
    "lhistorique", "levolution", "lidentifiant",
    "lagence", "lusages", "lagences", "give",
    "grande", "grand", "grands", "grandes",
    "gros", "grosse", "grosses",
    "petit", "petite", "petits", "petites",
    "haut", "haute", "hauts", "hautes",
    "bas", "basse", "basses",
    "fort", "forte", "forts", "fortes",
    "important", "importante", "importants", "importantes",
    "cest", "c est", "cest qui", "c est qui",
    "ya", "y a", "yaa",
    "montre", "montrez",
    "cherche", "chercher",
    "trouve", "trouver",
    "indique", "indiquer",
    "precise", "preciser",
    "rappelle", "rappeler",
    "explique", "expliquer",
    "calcule", "calculer",
    "retourne", "retourner",
    "beaucoup", "peu", "trop", "assez",
    "enormement", "vraiment", "tres",
    "maximum", "maximal", "maximale",
    "minimum", "minimal", "minimale",
    "optimal", "optimale",
    "record", "recordman", "recordwoman",
    "top", "premier", "premiere",
    "dernier", "derniere",
    "meilleur", "meilleure", "pire",
    "unique", "seul", "seule", "seuls", "seules",
    "donc", "alors", "ainsi", "car", "parce",
    "mais", "cependant", "pourtant", "toutefois",
    "selon", "apres", "avant", "pendant", "lors",
    "grace", "cause", "raison",
    "bcp", "agadir",
    "affiche", "affichez", "afficher", "consommateur", "consomateur"
}

PATTERNS_QUESTION_GENERALE = [
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
    r"\busage\b(?!\s+de\b)",
    r"\bclassement\b",
    r"\bevolution\b",
    r"\balerte",
    r"\bservice\b(?!\s+de\b)",
    r"\bquel\s+client\b",
    r"\bqui\s+consomme\b",
    r"\bqui\s+paie\b",
    r"\bqui\s+paye\b",
    r"\bqui\s+a\s+(la|le|les|une)\b",
    r"\bclient\s+(avec|qui|a\s+une|ayant)\b",
    r"\bquel\s+est\s+le\s+client\b",
    r"\bconsomme\s+(le\s+plus|le\s+moins|eleve|elevee|faible|max|min)\b(?!\s+de\b)",
    r"\bconsomme\s+la\s+plus\b",
    r"\bquel\w*\s+usage\b",
    r"\busages?\s+exist",
    r"\bclients?\s+par\s+usage",
    r"\bpar\s+usage\b",
    r"\bquel\s+mois\b.*\b(consomme|paye|paie)\b",
]

MOTS_REFERENCE_IMPLICITE = [
    "son ", "sa ", "ses ",
    " il ", " elle ", "lui ",
    "ce client", "ce meme client", "le meme", "la meme",
    "pour lui", "pour elle", "de lui", "d elle",
    "quelle est sa", "quel est son",
    "et sa ", "et son ", "et ses ",
    "son usage", "son service", "son agence",
    "son adresse", "son contrat", "son compteur",
]

def est_question_generale(question: str) -> bool:
    q = normaliser(question)
    _refs_explicites = [
        "son usage", "son service", "son agence",
        "son adresse", "son contrat", "son compteur",
        "agence de", "usage de", "service de",
        "adresse de", "contrat de", "compteur de",
        "consomation de", "consommation de",
        "montant de", "facture de", "informations de", "infos de", "info de",
        "historique de", "evolution de", "factures de", "information de",
        "a consomme le plus", "a consomme le moins",
        "a paye le plus", "a paye le moins",
        "mois fatima", "mois bilal", "quel mois",
    ]
    if any(t in q for t in _refs_explicites):
        return False
    for pattern in PATTERNS_QUESTION_GENERALE:
        if re.search(pattern, q):
            return True
    return False


def normaliser(texte: str) -> str:
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte


MOTS_METIER = {
    "consomation", "consommation", "consomme", "conso",
    "consomateur", "consommateur", "consommatrice",
    "montant", "mantant", "monton", "montan",
    "facture", "factures",
    "eleve", "elevee", "eleves", "elevees",
    "faible", "faibles",
    "plus", "moins", "max", "min",
    "total", "somme", "cumul",
    "alerte", "alertes",
    "agence", "service", "usage",
    "evolution", "historique",
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
    "janv", "fevr", "juil", "sept",
    "eau", "electricite", "elec",
    "periode", "debut", "fin",
    "grand", "grande", "gros", "grosse",
    "beaucoup", "bcp", "bzaf",
    "client", "clients",
    "agadir", "inezgane", "tiznit", "taroudant",
    "ait melloul", "melloul",
    "agadir nord", "agadir sud",
    "lagence", "lagences",
    "code", "postal", "postale",
    "numero", "numeros",
    "adresse", "contrat", "compteur",
    "liste", "information", "informations", "infos",
    "facturee", "facturation", "factur",
}

_CONCEPTS_METIER_FUZZY = MOTS_METIER


def _est_mot_fonctionnel_approx(mot: str, distance_max: int = 2) -> bool:
    if mot in MOTS_FONCTIONNELS:
        return True
    if mot in MOTS_METIER:
        return True
    if len(mot) < 4:
        return False

    def levenshtein(a: str, b: str) -> int:
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for ca in a:
            curr = [prev[0] + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
            prev = curr
        return prev[-1]

    for fonc in MOTS_FONCTIONNELS:
        if abs(len(mot) - len(fonc)) > distance_max:
            continue
        if levenshtein(mot, fonc) <= distance_max:
            return True
    for metier in MOTS_METIER:
        if " " in metier:
            continue
        if abs(len(mot) - len(metier)) > distance_max:
            continue
        if levenshtein(mot, metier) <= distance_max:
            return True
    return False


def extraire_mots_nom(question: str) -> list[str]:
    mots = [normaliser(m) for m in re.findall(r'\b\w+\b', question)]
    return [m for m in mots if len(m) > 2 and m not in MOTS_FONCTIONNELS]


def _detecter_nom_inconnu(question: str, liste_clients: list) -> str | None:
    if est_question_generale(question):
        return None

    _indicateurs = [
        "infos de", "info de", "informations de", "information de",
        "usage de", "agence de", "service de", "adresse de",
        "contrat de", "compteur de", "consommation de", "consomation de",
        "montant de", "facture de", "evolution de", "historique de",
        "moyenne de", "factures de",
    ]

    q_lower = normaliser(question)
    if not any(t in q_lower for t in _indicateurs):
        return None

    prenoms_reels = set()
    noms_reels = set()
    for client in liste_clients:
        parties = normaliser(client).split()
        if len(parties) >= 1:
            prenoms_reels.add(parties[0])
        if len(parties) >= 2:
            noms_reels.add(parties[1])

    tous_noms_reels = prenoms_reels | noms_reels

    def levenshtein(a: str, b: str) -> int:
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for ca in a:
            curr = [prev[0] + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(ca != cb)))
            prev = curr
        return prev[-1]

    def verifier_mot(mot: str) -> str:
        if mot in tous_noms_reels:
            return "exact"
        if len(mot) <= 3:
            seuil = 0
        elif len(mot) <= 5:
            seuil = 1
        else:
            seuil = 2
        for nom in tous_noms_reels:
            if abs(len(mot) - len(nom)) <= seuil:
                if levenshtein(mot, nom) <= seuil:
                    return "suggestion"
        return "inconnu"

    for indicateur in sorted(_indicateurs, key=len, reverse=True):
        if indicateur in q_lower:
            apres = q_lower.split(indicateur, 1)[1].strip()
            mots_apres = [m for m in apres.split() if len(m) >= 3]
            if not mots_apres:
                continue
            candidat = mots_apres[0]
            if candidat in MOTS_FONCTIONNELS or candidat in MOTS_METIER:
                continue
            resultat = verifier_mot(candidat)
            if resultat == "exact":
                return None
            if resultat == "suggestion":
                return candidat
            if resultat == "inconnu":
                return candidat

    return None


def detecter_client(question: str, liste_clients: list) -> tuple[str | list | None, str]:
    if est_question_generale(question):
        return None, "aucun"

    q_norm = normaliser(question)
    clients_norm = [(c, normaliser(c)) for c in liste_clients]

    for client_original, client_norm in clients_norm:
        if client_norm in q_norm:
            return client_original, "exact"

    mots_nom_question = extraire_mots_nom(question)
    if not mots_nom_question:
        return None, "aucun"

    mots_dans_base = [m for m in mots_nom_question
                      if any(m in cn for (_, cn) in clients_norm)]
    if not mots_dans_base:
        mots_question_norm = [normaliser(m) for m in re.findall(r'\b\w+\b', question)]
        mots_metier_presents = [m for m in mots_question_norm
                                 if m in _CONCEPTS_METIER_FUZZY]
        mots_candidats_prenom = [m for m in mots_nom_question
                                  if m not in _CONCEPTS_METIER_FUZZY
                                  and not _est_mot_fonctionnel_approx(m)
                                  and len(m) >= 4]

        if mots_metier_presents and not mots_candidats_prenom:
            return None, "aucun"

        from difflib import get_close_matches
        for mot in mots_candidats_prenom:
            noms_norm = [cn for (_, cn) in clients_norm]
            prenoms = [cn.split()[0] for cn in noms_norm]
            matches = get_close_matches(mot, prenoms, n=1, cutoff=0.65)
            if matches:
                idx = prenoms.index(matches[0])
                client_suggere = clients_norm[idx][0]
                return None, f"suggestion:{client_suggere}"

        return None, "aucun"

    mots_plausibles = [m for m in mots_dans_base if len(m) >= 4]
    if not mots_plausibles:
        return None, "aucun"

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

    q_norm = normaliser(question)
    _questions_globales = [
        "nbr client", "nb client", "nbre client", "nombre client", "nombre de client",
        "client eau", "client elec", "client electricite", "clients eau", "clients elec",
        "nbr facture", "nb facture", "nombre facture",
        "top consommation", "top conso", "max conso", "conso max",
        "qui consomme", "qui consome", "quel client consomme", "quel client a",
        "client max", "client min", "consomme le plus", "consomme le moins",
        "consomation total", "consommation total", "total consommation",
        "total consomation", "total de consommation", "total de consomation",
        "consommation en janvier", "consomation en janvier",
        "total en janvier", "total en fevrier", "total en mars", "total en avril",
        "total en mai", "total en juin", "total en juillet", "total en aout",
        "total en septembre", "total en octobre", "total en novembre", "total en decembre",
        "montant maximum", "montant minimum", "montant moyen",
        "montant max", "montant min", "montant moy",
        "montant total en janvier", "montant total en fevrier", "montant total en mars",
        "montant total en avril", "montant total en mai", "montant total en juin",
        "montant total en juillet", "montant total en aout", "montant total en septembre",
        "montant total en octobre", "montant total en novembre", "montant total en decembre",
        "somme de montant en", "somme montant en",
        "montant en janvier", "montant en fevrier", "montant en mars",
        "montant en avril", "montant en mai", "montant en juin",
        "montant en juillet", "montant en aout", "montant en septembre",
        "montant en octobre", "montant en novembre", "montant en decembre",
        "somme de consomation en", "somme consomation en",
        "agence agadir", "agence inezgane", "agence tiznit", "agence taroudant",
        "agence ait melloul", "agence agadir nord", "agence agadir sud",
        "lagence agadir", "lagence inezgane", "lagence tiznit", "lagence taroudant",
        "lagence ait melloul", "utulise lagence", "utilise lagence",
        "de lagence", "de l agence", "clients agence", "client agence",
    ]
    if any(t in q_norm for t in _questions_globales):
        return False

    question_lower = question.lower()
    mots = question_lower.split()
    if len(mots) <= 1:
        return False

    for mot in MOTS_REFERENCE_IMPLICITE:
        if mot in question_lower:
            return True

    # if len(mots) <= 8:
    #     mots_norm = [normaliser(m) for m in mots]
    #     tous_fonctionnels = all(m in MOTS_FONCTIONNELS or len(m) <= 3 for m in mots_norm)
    #     if tous_fonctionnels:
    #         return True

    return False


def _extraire_client_depuis_historique(historique: list, liste_clients: list) -> str | None:
    for msg in reversed(historique):
        contenu = msg.get("content", "")
        if msg.get("role") == "user":
            res, st = detecter_client(contenu, liste_clients)
            if st == "exact":
                return res
        if msg.get("role") == "assistant":
            noms_gras = re.findall(r'\*\*([^*]+)\*\*', contenu)
            for nom in noms_gras:
                for client in liste_clients:
                    if normaliser(client) == normaliser(nom):
                        return client
            res, st = detecter_client(contenu, liste_clients)
            if st == "exact":
                return res
    return None


def poser_question(texte_facture: str, question: str, historique: list = []) -> str:
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un assistant intelligent spécialisé dans l'analyse de factures SRM.

Voici le contenu de la facture :
{texte_facture}

Historique :
{historique_texte}

Question : {question}

Réponds en français de façon claire et précise.
"""
    import os
    OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


# ══════════════════════════════════════════════════════════════
# SEUL CHANGEMENT : ajout du paramètre nom_fichier
# qui est propagé jusqu'au dispatcher via
# repondre_question_generale et repondre_question_client
# ══════════════════════════════════════════════════════════════
def poser_question_excel(question: str, historique: list = [], nom_fichier: str = "", nom_client_force: str = "") -> str:
    resume = get_resume_excel()

    if resume["total"] == 0:
        return "Aucune donnée disponible. Veuillez d'abord importer un fichier Excel."

    liste_clients = resume["clients"]
     # ── CAS SPÉCIAL : client forcé via numéro de contrat ──
    if nom_client_force:
        historique_texte = ""
        for msg in historique[:-1]:
            role = "Client" if msg["role"] == "user" else "Assistant"
            historique_texte += f"{role}: {msg['content']}\n"
        return repondre_question_client(
            question, nom_client_force, historique_texte, nom_fichier=nom_fichier
        )

    # ── ÉTAPE 0 — VÉRIFICATION NOM INCONNU ──
    nom_inconnu = _detecter_nom_inconnu(question, liste_clients)
    if nom_inconnu:
        _, statut_check = detecter_client(question, liste_clients)
        if statut_check.startswith("suggestion:"):
            nom_suggere = statut_check.replace("suggestion:", "")
            return f"⚠️ Aucun client trouvé.\nVouliez-vous dire **{nom_suggere}** ?"
        return f"⚠️ Aucun client nommé **'{nom_inconnu}'** trouvé dans la base."

    # ── ÉTAPE 1 — DÉTECTION CLIENT ──
    resultat, statut = detecter_client(question, liste_clients)

    if statut == "ambigu":
        noms_formates = "\n".join(f"- {c}" for c in resultat)
        return (
            "⚠️ Plusieurs clients correspondent à votre recherche. "
            "Pouvez-vous préciser le nom complet ?\n\n"
            + noms_formates
        )

    if statut.startswith("suggestion:"):
        nom_suggere = statut.replace("suggestion:", "")
        return f"⚠️ Aucun client trouvé.\nVouliez-vous dire **{nom_suggere}** ?"

    client_trouve = resultat if statut == "exact" else None

    # ── ÉTAPE 2 — RÉFÉRENCE IMPLICITE → HISTORIQUE ──
    if not client_trouve and question_fait_reference(question):
        client_trouve = _extraire_client_depuis_historique(historique, liste_clients)
        if client_trouve:
            print(f"  [CONTEXTE] Réutilisation client : {client_trouve}")

    # ── ÉTAPE 3 — CLIENT INTROUVABLE RÉSIDUEL ──
    if not client_trouve and statut == "aucun":
        mots = extraire_mots_nom(question)
        noms_suspects = [
            m for m in mots
            if len(m) >= 4
            and not _est_mot_fonctionnel_approx(m)
            and not m.isdigit()
        ]
        _indicateurs_client = [
            "de ", "du client", "pour ", "infos de", "informations de",
            "consomation de", "montant de", "facture de"
        ]
        q_lower = question.lower()
        if noms_suspects and not est_question_generale(question) and any(
            t in q_lower for t in _indicateurs_client
        ):
            return f"⚠️ Aucun client nommé **'{noms_suspects[0]}'** trouvé dans la base."

    # ── ÉTAPE 4 — RÉPONDRE ──
    historique_texte = ""
    for msg in historique[:-1]:
        role = "Client" if msg["role"] == "user" else "Assistant"
        historique_texte += f"{role}: {msg['content']}\n"

    if client_trouve:
        # ← nom_fichier propagé au dispatcher
        return repondre_question_client(question, client_trouve, historique_texte, nom_fichier=nom_fichier)

    # ← nom_fichier propagé au dispatcher
    return repondre_question_generale(question, historique_texte, nom_fichier=nom_fichier)