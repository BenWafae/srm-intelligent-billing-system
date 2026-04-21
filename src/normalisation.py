# src/normalisation.py
# ─────────────────────────────────────────────────────────
# Normalisation floue — tolère fautes, anglais, abréviations
# ─────────────────────────────────────────────────────────

SYNONYMES = {
    # ── Mois français ──
    # ✅ FIX BUG DÉCEMBRE (et Février, Août) :
    #    Les valeurs retournées DOIVENT être sans accents pour matcher
    #    exactement ce qui est stocké en base SQLite ("Decembre", "Fevrier", "Aout").
    #    Avant : "dec" → "Décembre" → LIKE '%Décembre%' → 0 résultat.
    #    Après : "dec" → "Decembre" → LIKE '%Decembre%' → ✅ match.
    "jan": "Janvier",   "janv": "Janvier",    "january": "Janvier",
    "fev": "Fevrier",   "fevr": "Fevrier",    "février": "Fevrier",
    "fevrier": "Fevrier", "february": "Fevrier", "feb": "Fevrier",
    "mar": "Mars",      "mars": "Mars",        "march": "Mars",
    "avr": "Avril",     "april": "Avril",      "apr": "Avril",
    "mai": "Mai",       "may": "Mai",
    "jun": "Juin",      "june": "Juin",        "juin": "Juin",
    "jul": "Juillet",   "july": "Juillet",     "juillet": "Juillet",
    "aou": "Aout",      "aout": "Aout",        "aout": "Aout",
    "august": "Aout",   "aug": "Aout",
    "sep": "Septembre", "sept": "Septembre",   "september": "Septembre",
    "oct": "Octobre",   "october": "Octobre",
    "nov": "Novembre",  "november": "Novembre",
    "dec": "Decembre",  "dec": "Decembre",     "december": "Decembre",
    "decembre": "Decembre",

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
    "electricite": "electricite", "electricity": "electricite",
    "electrcite": "electricite", "electicite": "electricite",

    # ── Usages ──
    "dom": "USAGE DOMESTIQUE",
    "domes": "USAGE DOMESTIQUE",
    "domest": "USAGE DOMESTIQUE",
    "domestique": "USAGE DOMESTIQUE",
    "domestic": "USAGE DOMESTIQUE",
    "maison": "USAGE DOMESTIQUE",
    "residentiel": "USAGE DOMESTIQUE",
    "habitation": "USAGE DOMESTIQUE",
    "usage domestique": "USAGE DOMESTIQUE",

    "pro": "USAGE PROFESSIONNEL",
    "prof": "USAGE PROFESSIONNEL",
    "profes": "USAGE PROFESSIONNEL",
    "profet": "USAGE PROFESSIONNEL",
    "profetionel": "USAGE PROFESSIONNEL",
    "profetionnel": "USAGE PROFESSIONNEL",
    "profetionnelle": "USAGE PROFESSIONNEL",
    "profesionel": "USAGE PROFESSIONNEL",
    "profesionnel": "USAGE PROFESSIONNEL",
    "professionel": "USAGE PROFESSIONNEL",
    "professionnel": "USAGE PROFESSIONNEL",
    "professionnelle": "USAGE PROFESSIONNEL",
    "professional": "USAGE PROFESSIONNEL",
    "professionnal": "USAGE PROFESSIONNEL",
    "profesional": "USAGE PROFESSIONNEL",
    "bureau": "USAGE PROFESSIONNEL",
    "commercial": "USAGE PROFESSIONNEL",
    "commerce": "USAGE PROFESSIONNEL",
    "entreprise": "USAGE PROFESSIONNEL",
    "usage professionnel": "USAGE PROFESSIONNEL",

    "agri": "USAGE AGRICOLE",
    "agric": "USAGE AGRICOLE",
    "agricol": "USAGE AGRICOLE",
    "agricole": "USAGE AGRICOLE",
    "agricolee": "USAGE AGRICOLE",
    "agricolle": "USAGE AGRICOLE",
    "agricultural": "USAGE AGRICOLE",
    "agriculture": "USAGE AGRICOLE",
    "farm": "USAGE AGRICOLE",
    "ferme": "USAGE AGRICOLE",
    "irrigation": "USAGE AGRICOLE",
    "usage agricole": "USAGE AGRICOLE",
}

# ✅ Formes canoniques SANS accents — doivent correspondre exactement à la base
FORMES_CANONIQUES_MOIS = [
    "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"
]

FORMES_CANONIQUES_METIER = [
    "consommation", "montant", "facture", "client",
    "agence", "alerte", "eau", "electricite", "usage", "service"
]

USAGES_EXACTS = [
    "USAGE DOMESTIQUE",
    "USAGE PROFESSIONNEL",
    "USAGE AGRICOLE",
]

USAGE_KEYWORDS = {
    "USAGE DOMESTIQUE":    ["dom", "domes", "domest", "domestiq", "maison", "resid", "habita"],
    "USAGE PROFESSIONNEL": ["pro", "prof", "profes", "profet", "profess", "bureau", "commerc", "entrepr"],
    "USAGE AGRICOLE":      ["agri", "agric", "agricol", "farm", "ferme", "irrigat"],
}


def _levenshtein(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j+1]+1, curr[j]+1, prev[j]+(ca != cb)))
        prev = curr
    return prev[-1]


def _sans_accent(texte: str) -> str:
    import unicodedata
    texte = unicodedata.normalize("NFD", texte)
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def normaliser_mot(mot: str, formes_canoniques: list, seuil: int = 2) -> str | None:
    mot_lower = _sans_accent(mot.lower().strip())

    if mot_lower in SYNONYMES:
        return SYNONYMES[mot_lower]

    meilleur, dist_min = None, float("inf")
    for forme in formes_canoniques:
        d = _levenshtein(mot_lower, _sans_accent(forme.lower()))
        if d < dist_min:
            meilleur, dist_min = forme, d

    return meilleur if dist_min <= seuil else None


def normaliser_mois(mois: str) -> str:
    """
    Normalise un mois saisi librement vers le libellé EXACT stocké en base.

    La base stocke SANS accents : "Janvier", "Fevrier", ..., "Decembre"

    Exemples :
      "décembre"     → "Decembre"   ✅
      "Décembre"     → "Decembre"   ✅
      "dec"          → "Decembre"   ✅
      "december"     → "Decembre"   ✅
      "decembr"      → "Decembre"   ✅ via Levenshtein
      "février"      → "Fevrier"    ✅
      "août"         → "Aout"       ✅
      "Octobre 2025" → "Octobre"    ✅ (l'année est ignorée)
    """
    if not mois:
        return mois

    # Supprimer accents + minuscules + prendre le premier mot (ignore l'année)
    mot = _sans_accent(mois.strip().split()[0].lower())

    # Lookup direct dans SYNONYMES
    if mot in SYNONYMES:
        return SYNONYMES[mot]

    # Levenshtein sur les formes canoniques sans accents
    resultat = normaliser_mot(mot, FORMES_CANONIQUES_MOIS, seuil=3)
    return resultat if resultat else mois.strip().capitalize()


def normaliser_terme_metier(terme: str) -> str:
    if not terme:
        return terme
    mot = _sans_accent(terme.strip().lower())
    resultat = normaliser_mot(mot, FORMES_CANONIQUES_METIER, seuil=3)
    return resultat if resultat else terme.strip()


def normaliser_usage(texte: str) -> str | None:
    """
    Normalise n'importe quelle saisie vers un libellé exact de la base.
    Retourne None si aucun usage reconnu (ex: "service", "client").
    """
    if not texte:
        return None

    texte_norm = _sans_accent(texte.strip().lower())

    # Étape 1 : synonyme direct (phrase complète)
    if texte_norm in SYNONYMES:
        val = SYNONYMES[texte_norm]
        if val in USAGES_EXACTS:
            return val

    # Étape 2 : matching par mots-clés partiels
    for usage_exact, keywords in USAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in texte_norm:
                return usage_exact

    # Étape 3 : chaque mot du texte via synonymes
    for mot in texte_norm.split():
        if mot in SYNONYMES and SYNONYMES[mot] in USAGES_EXACTS:
            return SYNONYMES[mot]

    # Étape 4 : Levenshtein sur les libellés complets
    meilleur, dist_min = None, float("inf")
    for usage_exact in USAGES_EXACTS:
        d = _levenshtein(texte_norm, _sans_accent(usage_exact.lower()))
        if d < dist_min:
            meilleur, dist_min = usage_exact, d
    if dist_min <= 6:
        return meilleur

    # Étape 5 : Levenshtein mot par mot sur la partie après "USAGE "
    parties = [u.replace("USAGE ", "") for u in USAGES_EXACTS]
    for mot in texte_norm.split():
        for i, partie in enumerate(parties):
            d = _levenshtein(mot, _sans_accent(partie.lower()))
            if d <= 4:
                return USAGES_EXACTS[i]

    return None