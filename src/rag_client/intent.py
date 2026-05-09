from rag_client.tokens import (
    _TOKENS_CHAMP_USAGE,
    _TOKENS_CHAMP_SERVICE,
    _TOKENS_CHAMP_AGENCE,
    _TOKENS_CHAMP_ADRESSE,
    _TOKENS_CHAMP_COMPTEUR,
    _TOKENS_CHAMP_CONTRAT,
    _TOKENS_CHAMP_CLIENT,
    _TOKENS_CHAMP_DATE_LIMITE,
)
from rag_client.normalisation_client import _levenshtein


def _detecter_champ_infos(q: str):

    _CHAMPS = {
        "compteur" : _TOKENS_CHAMP_COMPTEUR,
        "contrat"  : _TOKENS_CHAMP_CONTRAT,
        "client"   : _TOKENS_CHAMP_CLIENT,
        "adresse"  : _TOKENS_CHAMP_ADRESSE,
        "service"  : _TOKENS_CHAMP_SERVICE,
        "agence"   : _TOKENS_CHAMP_AGENCE,
        "usage"    : _TOKENS_CHAMP_USAGE,
        "date_limite" : _TOKENS_CHAMP_DATE_LIMITE,
    }

    # ── Matching exact d'abord ──
    for champ, tokens in _CHAMPS.items():
        if any(t in q for t in tokens):
            return champ

    # ── Matching fuzzy — uniquement mots longs ──
    mots_q = q.split()
    for champ, tokens in _CHAMPS.items():
        for token in tokens:
            mots_token = token.split()
            for mot_token in mots_token:
                if len(mot_token) < 7:
                    continue
                seuil = 3 if len(mot_token) >= 10 else 2
                for mot_q in mots_q:
                    if len(mot_q) < 5:
                        continue
                    if _levenshtein(mot_token, mot_q) <= seuil:
                        return champ

    return None