# src/normalisation.py
# ─────────────────────────────────────────────────────────
# Normalisation floue — tolère fautes, anglais, abréviations
# ─────────────────────────────────────────────────────────

# Dictionnaire de synonymes / variantes → forme canonique
SYNONYMES = {
    # ── Mois français ──
    "jan": "Janvier", "janv": "Janvier", "january": "Janvier",
    "fev": "Février", "fevr": "Février", "février": "Février",
    "février": "Février", "february": "Février", "feb": "Février",
    "mar": "Mars", "mars": "Mars", "march": "Mars",
    "avr": "Avril", "april": "Avril", "apr": "Avril",
    "mai": "Mai", "may": "Mai",
    "jun": "Juin", "june": "Juin", "juin": "Juin",
    "jul": "Juillet", "july": "Juillet", "juillet": "Juillet",
    "aou": "Août", "aout": "Août", "août": "Août", "august": "Août", "aug": "Août",
    "sep": "Septembre", "sept": "Septembre", "september": "Septembre",
    "oct": "Octobre", "october": "Octobre",
    "nov": "Novembre", "november": "Novembre",
    "dec": "Décembre", "déc": "Décembre", "december": "Décembre",

    # ── Termes métier ──
    "conso": "consommation", "consom": "consommation",
    "consomation": "consommation", "consomasion": "consommation",
    "consommassion": "consommation", "consumption": "consommation",
    "montant": "montant", "amount": "montant", "prix": "montant",
    "facture": "facture", "invoice": "facture", "bill": "facture",
    "client": "client", "customer": "client",
    "agence": "agence", "agency": "agence",
    "alerte": "alerte", "alert": "alerte", "warning": "alerte",
    "eau": "eau", "water": "eau",
    "elec": "electricite", "elecricite": "electricite",
    "electricité": "electricite", "electricity": "electricite",
    "electrcite": "electricite", "electicite": "electricite",
}

# Formes canoniques reconnues (pour Levenshtein)
FORMES_CANONIQUES_MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

FORMES_CANONIQUES_METIER = [
    "consommation", "montant", "facture", "client",
    "agence", "alerte", "eau", "electricite", "usage", "service"
]


def _levenshtein(a: str, b: str) -> int:
    """Distance d'édition entre deux chaînes (insensible à la casse)."""
    a, b = a.lower(), b.lower()
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,   # suppression
                curr[j] + 1,       # insertion
                prev[j] + (ca != cb)  # substitution
            ))
        prev = curr
    return prev[-1]


def normaliser_mot(mot: str, formes_canoniques: list, seuil: int = 2) -> str | None:
    """
    Retourne la forme canonique la plus proche si distance ≤ seuil.
    Retourne None si aucun match acceptable.
    """
    mot_lower = mot.lower().strip()

    # Étape 1 : synonyme direct
    if mot_lower in SYNONYMES:
        return SYNONYMES[mot_lower]

    # Étape 2 : Levenshtein sur les formes canoniques
    meilleur, dist_min = None, float("inf")
    for forme in formes_canoniques:
        d = _levenshtein(mot_lower, forme.lower())
        if d < dist_min:
            meilleur, dist_min = forme, d

    return meilleur if dist_min <= seuil else None


def normaliser_mois(mois: str) -> str:
    """
    Normalise un mois saisi librement.
    'maars' → 'Mars', 'decembr' → 'Décembre', 'january' → 'Janvier'
    Retourne le mot original si aucun match.
    """
    if not mois:
        return mois
    # Prendre seulement le premier mot (ex: "octobre 2025" → "octobre")
    mot = mois.strip().split()[0]
    resultat = normaliser_mot(mot, FORMES_CANONIQUES_MOIS, seuil=3)
    return resultat if resultat else mois.strip()


def normaliser_terme_metier(terme: str) -> str:
    """
    Normalise un terme métier.
    'consomasion' → 'consommation', 'electricity' → 'electricite'
    Retourne le mot original si aucun match.
    """
    if not terme:
        return terme
    mot = terme.strip().lower()
    resultat = normaliser_mot(mot, FORMES_CANONIQUES_METIER, seuil=3)
    return resultat if resultat else terme.strip()