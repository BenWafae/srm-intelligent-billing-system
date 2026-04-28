# ════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════

from rag_client.tokens import (
    _TOKENS_CHAMP_USAGE,
    _TOKENS_CHAMP_SERVICE,
    _TOKENS_CHAMP_AGENCE,
    _TOKENS_CHAMP_ADRESSE,
    _TOKENS_CHAMP_COMPTEUR,
    _TOKENS_CHAMP_CONTRAT,
    _TOKENS_CHAMP_CLIENT,
)


# ════════════════════════════════════════════
# DÉTECTION CHAMP PRÉCIS — pour INFOS
# ════════════════════════════════════════════

def _detecter_champ_infos(q: str):
    """
    Retourne le nom du champ précis si le client demande
    une info spécifique (usage, agence, adresse...).
    Retourne None si c'est une demande de profil complet.
    """
    # Ordre important : du plus spécifique au plus général
    if any(t in q for t in _TOKENS_CHAMP_USAGE):
        return "usage"
    if any(t in q for t in _TOKENS_CHAMP_SERVICE):
        return "service"
    if any(t in q for t in _TOKENS_CHAMP_AGENCE):
        return "agence"
    if any(t in q for t in _TOKENS_CHAMP_ADRESSE):
        return "adresse"
    if any(t in q for t in _TOKENS_CHAMP_COMPTEUR):
        return "compteur"
    if any(t in q for t in _TOKENS_CHAMP_CONTRAT):
        return "contrat"
    if any(t in q for t in _TOKENS_CHAMP_CLIENT):
        return "client"
    return None  # profil complet