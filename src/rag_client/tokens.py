# ════════════════════════════════════════════
# TOKENS — langage personnel du client
# ════════════════════════════════════════════

# INFOS : uniquement les questions générales sur le profil complet
_TOKENS_INFOS = [
    "mes infos", "mon profil", "mes informations", "mes info", "mes information",
    "qui suis je", "mon compte", "infos", "mon identite",
    "donner moi mes infos", "voir mon profil",
]

# Champs précis — détectés AVANT l'intent INFOS général
_TOKENS_CHAMP_USAGE    = ["usage", "mon usage", "quel usage", "type usage", "quel est mon usage"]
_TOKENS_CHAMP_AGENCE   = ["agence", "mon agence", "quelle agence", "quel agence"]
_TOKENS_CHAMP_ADRESSE  = ["adresse", "mon adresse", "ou j habite", "ou je suis", "habite"]
_TOKENS_CHAMP_SERVICE  = ["service", "mon service", "quel service", "type service", "quel est mon service"]
_TOKENS_CHAMP_CONTRAT  = ["contrat", "mon contrat", "numero contrat", "n contrat"]
_TOKENS_CHAMP_COMPTEUR = ["compteur", "mon compteur", "numero compteur", "n compteur", "n compt"]
_TOKENS_CHAMP_CLIENT   = ["numero client", "mon numero", "n client", "identifiant"]

_TOKENS_MONTANT_MAX = [
    "mon montant le plus eleve", "mon montant max",
    "ma facture la plus chere", "j ai le plus paye",
    "mois ou j ai le plus paye", "mon maximum",
    "mon mois le plus cher", "montant max", "montant eleve",
    "montant le plus eleve", "montant le plus haut",
    "facture chere", "facture elevee", "facture max",
    "j ai paye beaucoup", "j ai beaucoup paye",
    "mois ou j ai paye le plus", "mois cher",
    "mois couteux", "mois le plus cher",
    "mon montant eleve", "mon montant haut",
    "paye le plus", "plus paye", "max montant",
    "montant maximum", "montant maximal",
    "mantant max", "mantant eleve", "monton max",
    "facture la plus grande", "ma plus grande facture",
    "mon pic montant", "pic facture",
]

_TOKENS_MONTANT_MIN = [
    "mon montant le plus faible", "mon montant min",
    "ma facture la moins chere", "j ai le moins paye",
    "mois ou j ai le moins paye", "mon minimum",
    "mon mois le moins cher", "montant min", "montant faible",
    "montant le plus faible", "montant le plus bas",
    "facture pas chere", "facture faible", "facture min",
    "j ai paye peu", "j ai peu paye",
    "mois ou j ai paye le moins", "mois pas cher",
    "mois le moins cher", "mois le plus bas",
    "mon montant faible", "mon montant bas",
    "paye le moins", "moins paye", "min montant",
    "montant minimum", "montant minimal",
    "mantant min", "mantant faible", "monton min",
    "facture la plus petite", "ma plus petite facture",
    "mon minimum facture",
]

_TOKENS_CONSO_MAX = [
    "ma consommation la plus elevee", "ma conso max",
    "mois ou j ai le plus consomme", "j ai le plus consomme",
    "ma consommation maximale", "mon pic de consommation",
    "mois ou j ai consomme le plus",
    "ma conso eleve", "ma conso elevee",
    "ma consommation eleve", "ma consommation elevee",
    "mois ou j ai plus consomme", "mois ou j ai consomme plus",
    "j ai plus consomme", "conso eleve", "conso elevee",
    "consomme le plus", "plus consomme", "mois max conso",
    "conso max", "mon max conso", "max consommation",
    "consommation max", "consommation elevee", "consommation eleve",
    "consomme beaucoup", "forte consommation", "grande consommation",
    "mois fort", "mois eleve", "pic conso", "sommet conso",
    "consomation eleve", "consomation max", "consomation elevee",
    "consome le plus", "consome beaucoup", "consome eleve",
    "kwh eleve", "kwh max", "m3 eleve", "m3 max",
]

_TOKENS_CONSO_MIN = [
    "ma consommation la plus faible", "ma conso min",
    "mois ou j ai le moins consomme", "j ai le moins consomme",
    "ma consommation minimale", "mois ou j ai consomme le moins",
    "ma conso faible", "ma conso basse",
    "ma consommation faible", "ma consommation basse",
    "mois ou j ai moins consomme", "mois ou j ai consomme moins",
    "j ai moins consomme", "conso faible", "conso basse",
    "consomme le moins", "moins consomme", "mois min conso",
    "conso min", "mon min conso", "min consommation",
    "consommation min", "consommation faible", "consommation basse",
    "consomme peu", "faible consommation", "petite consommation",
    "mois faible", "mois bas", "mois minimum",
    "consomation faible", "consomation min", "consomation basse",
    "consome le moins", "consome peu", "consome faible",
    "kwh faible", "kwh min", "m3 faible", "m3 min",
]

_TOKENS_SOMME_MONTANT = [
    "combien j ai paye en tout", "total de mes paiements",
    "somme de mes montants", "total mes montants",
    "combien j ai depense", "mon total paye",
    "mes paiements totaux", "total factures",
]

_TOKENS_SOMME_CONSO = [
    "combien j ai consomme en tout", "ma consommation totale",
    "somme de mes consommations", "total ma consommation",
    "cumul de ma consommation", "ma conso totale",
]

_TOKENS_EVOLUTION = [
    "mon historique", "mes factures", "toutes mes factures",
    "mon evolution", "mois par mois", "ma progression",
    "voir tout", "tout afficher", "historique complet", "donner moi tous mes",
]

_TOKENS_MOYENNE = [
    "ma moyenne", "mon montant moyen", "ma consommation moyenne",
    "en moyenne", "montant moyen", "conso moyenne",
]

_TOKENS_MOIS = [
    "mon montant", "ma consommation", "ma facture",
    "combien j ai", "combien ai je", "en janvier", "en janv",
    "en fevrier", "en fev", "en mars",
    "en avril", "en avr", "en mai",
    "en juin", "en juillet", "en juil",
    "en aout", "en aou", "en septembre", "en sept", "en sep",
    "en octobre", "en oct", "en novembre", "en nov",
    "en decembre", "en dec",
]

_TOKENS_CHAMP_MONTANT = ["montant", "mantant", "monton", "paye", "facture", "prix", "cout", "dhs"]
_TOKENS_CHAMP_CONSO   = ["consomme", "conso", "consommation", "consomation", "kwh", "m3"]

INTENTS_CLIENT_CONNECTE = """
MAX_MONTANT       : mois où j'ai payé le plus, ma facture la plus chère
MIN_MONTANT       : mois où j'ai payé le moins, ma facture la moins chère
MAX_CONSOMMATION  : mois où j'ai le plus consommé, ma consommation maximale
MIN_CONSOMMATION  : mois où j'ai le moins consommé, ma consommation minimale
SOMME_MONTANT     : total de ce que j'ai payé, combien j'ai dépensé en tout
SOMME_CONSO       : total de ce que j'ai consommé, ma consommation totale
EVOLUTION         : mon historique, toutes mes factures, mois par mois
MOYENNE           : ma moyenne, montant moyen, consommation moyenne
INFOS             : mes infos, mon profil, mes informations générales
INFOS_CHAMP       : mon usage, mon agence, mon adresse, mon service, mon contrat
MOIS_SPECIFIQUE   : mon montant en janvier, ma consommation en mars
"""

# ════════════════════════════════════════════
# MOTS VIDES — ignorés dans le scoring
# ════════════════════════════════════════════

_MOTS_VIDES = {
    "le", "la", "les", "de", "du", "des", "un", "une",
    "je", "j", "ai", "et", "en", "ou", "est", "ce",
    "que", "qui", "il", "elle", "on", "nous", "vous",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa",
    "ses", "par", "sur", "pour", "dans", "avec", "plus",
    "moi", "toi", "lui", "suis", "quel", "quelle", "quels", "quelles",
    "donner", "donne", "voir", "afficher", "montrer",
}