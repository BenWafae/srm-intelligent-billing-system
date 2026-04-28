# ════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════

from rag_client.tokens import _MOTS_VIDES


# ════════════════════════════════════════════
# LEVENSHTEIN — distance entre deux mots
# ════════════════════════════════════════════

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j+1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


# ════════════════════════════════════════════
# SCORE INTENT
# ════════════════════════════════════════════

def _score_intent(question_normalisee: str, tokens: list) -> float:
    mots_question = question_normalisee.split()
    meilleur_score = 0.0

    for token in tokens:
        if token in question_normalisee:
            return 1.0

        mots_token = [m for m in token.split() if m not in _MOTS_VIDES]
        if not mots_token:
            continue

        mots_importants_q = set(mots_question)
        if all(m in mots_importants_q for m in mots_token):
            meilleur_score = max(meilleur_score, 0.9)
            continue

        correspondances = 0
        for mot_token in mots_token:
            if len(mot_token) < 4:
                if mot_token in mots_importants_q:
                    correspondances += 1
                continue

            seuil = 2 if len(mot_token) >= 8 else 1

            for mot_q in mots_question:
                if len(mot_q) < 3:
                    continue
                dist = _levenshtein(mot_token, mot_q)
                if dist <= seuil:
                    correspondances += 1
                    break

        ratio = correspondances / len(mots_token)
        score_flou = ratio * 0.75
        meilleur_score = max(meilleur_score, score_flou)

    return meilleur_score