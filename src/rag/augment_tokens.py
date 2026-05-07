# src/rag/augment_tokens.py
# ════════════════════════════════════════════════════════════
# Script offline — à lancer UNE SEULE FOIS depuis le terminal
# pour générer des variantes de tokens via le LLM local (Mistral).
#
# Usage :
#   cd votre_projet
#   python src/rag/augment_tokens.py
#
# Le script écrit directement dans tokens_extra.py.
# Vérifiez le résultat avant de committer.
# Ce fichier n'est JAMAIS importé par l'application.
# ════════════════════════════════════════════════════════════

import requests
import json
import re
import os

TOKENS_EXTRA_PATH = os.path.join(os.path.dirname(__file__), "tokens_extra.py")


# ════════════════════════════════════════════════════════════
# LLM
# ════════════════════════════════════════════════════════════

def _appeler_llm(prompt: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return response.json()["response"].strip()


def generer_variantes(nom_liste: str, tokens_existants: list, description: str, nb: int = 40) -> list:
    exemples = "\n".join(f'  "{t}"' for t in tokens_existants[:15])

    prompt = f"""Tu es un expert en traitement du langage naturel pour un système de facturation SRM (eau et électricité au Maroc).

Je travaille sur une liste de tokens Python nommée `{nom_liste}`.
Cette liste sert à détecter quand un utilisateur pose une question sur : **{description}**

Voici des exemples de tokens déjà présents :
{exemples}

Ta tâche : générer exactement {nb} nouvelles variantes supplémentaires absentes de la liste.

RÈGLES :
1. Uniquement en français — pas de darija, pas d'arabe
2. Couvrir : fautes d'orthographe courantes, formulations familières,
   abréviations, tournures inversées, synonymes courants
3. Style naturel qu'un employé marocain francophone pourrait taper
4. Variantes courtes (2 à 7 mots) — pas de phrases complètes longues
5. Aucun doublon avec les exemples existants
6. Retourner UNIQUEMENT un tableau JSON valide de strings
   sans explication, sans markdown, sans backticks

JSON uniquement :
["variante1", "variante2", ...]"""

    texte = _appeler_llm(prompt)
    match = re.search(r'\[.*\]', texte, re.DOTALL)
    if match:
        try:
            variantes = json.loads(match.group())
            tokens_set = set(tokens_existants)
            return [v for v in variantes if v not in tokens_set and isinstance(v, str) and len(v) >= 4]
        except Exception as e:
            print(f"  ⚠️ Erreur parsing JSON pour {nom_liste} : {e}")
            print(f"  Réponse brute : {texte[:300]}")
            return []
    print(f"  ⚠️ Aucun JSON trouvé pour {nom_liste}")
    return []


# ════════════════════════════════════════════════════════════
# TOKENS EXISTANTS (référence pour éviter les doublons)
# ════════════════════════════════════════════════════════════

_EXISTANTS = {

    "EXTRA_CONSO_ELEVEE": {
        "description": "détecter quand l'utilisateur demande qui consomme le plus / consommation élevée / maximum",
        "tokens": [
            "consomme le plus", "le plus consomme", "consomme eleve", "consomme elevee",
            "consomme la plus eleve", "la plus eleve", "la plus elevee",
            "consomme haute", "consomme max", "consomme maximum",
            "consomme grand", "consomme grande", "grand consommateur",
            "grand consomateur", "gros consomateur", "consomme beaucoup",
            "consomme bcp", "conso bcp", "top consomme", "top consommateur",
            "max conso", "conso max", "ayant conso eleve", "ayant consomation eleve",
            "grosse consomation", "grande consomation", "grande consommateur",
        ]
    },

    "EXTRA_CONSO_FAIBLE": {
        "description": "détecter quand l'utilisateur demande qui consomme le moins / consommation faible / minimum",
        "tokens": [
            "consomme le moins", "le moins consomme", "consomme faible",
            "consomme la plus faible", "la plus faible", "le plus faible",
            "consomme basse", "consomme bas", "consomme min", "consomme minimum",
            "faible consomme", "basse consomme", "petit consommateur",
            "petit consomme", "moins consomme", "consomme moins",
            "ayant conso faible", "ayant consomation faible",
            "consomme reduite", "consomme legere",
        ]
    },

    "EXTRA_MONTANT_ELEVE": {
        "description": "détecter quand l'utilisateur demande le montant le plus élevé / facture la plus chère / qui paie le plus",
        "tokens": [
            "montant le plus eleve", "montant le plus haut", "montant le plus grand",
            "montant eleve", "montant elevee", "montant maximum", "montant max",
            "facture la plus chere", "facture la plus elevee",
            "paie le plus", "paye le plus", "qui paie le plus", "qui paye le plus",
            "client le plus cher", "client qui paie le plus", "montant fort",
            "plus grand montant", "plus haut montant",
        ]
    },

    "EXTRA_MONTANT_FAIBLE": {
        "description": "détecter quand l'utilisateur demande le montant le plus faible / facture la moins chère / qui paie le moins",
        "tokens": [
            "montant le plus faible", "montant le plus bas", "montant le plus petit",
            "montant faible", "montant minimum", "montant min", "montant minimal",
            "facture la moins chere", "facture la plus faible",
            "paie le moins", "paye le moins", "qui paie le moins", "qui paye le moins",
            "client le moins cher", "client avec le moins",
            "plus faible montant", "plus bas montant",
        ]
    },

    "EXTRA_SOMME_MOIS": {
        "description": "détecter quand l'utilisateur demande la somme ou total de consommation pour un mois précis",
        "tokens": [
            "somme de consomme", "somme des consomme", "somme de conso", "somme conso",
            "total consomme", "total de consomme", "consomme total", "consomme totale",
            "combien a-t-on consomme", "combien consomme",
            "somme de consommation", "somme consommation", "somme consomation",
            "total consommation", "total de consommation",
            "quelle est la consommation", "quel est la consommation",
            "consomation global", "consomation generale",
        ]
    },

    "EXTRA_SOMME_MONTANT": {
        "description": "détecter quand l'utilisateur demande la somme ou total des montants pour un mois précis",
        "tokens": [
            "somme des montant", "somme de montant", "somme montant",
            "total montant", "total des montant", "montant total",
            "montant global", "montant cumule",
            "combien a-t-on paye", "combien ont paye",
            "mantant total", "total mantant", "somme mantant",
        ]
    },

    "EXTRA_MAX_CONSO_CLIENT": {
        "description": "détecter pour un client spécifique : le mois où il a le plus consommé / consommation maximale",
        "tokens": [
            "le plus consomme", "consomme le plus", "consomme maximale",
            "consomme la plus elevee", "pic de consomme",
            "mois ou il a le plus consomme", "mois ou le client a le plus consomme",
            "quel mois a le plus", "mois maximum", "mois max",
            "plus elevee", "plus eleve", "le plus grand",
        ]
    },

    "EXTRA_MIN_CONSO_CLIENT": {
        "description": "détecter pour un client spécifique : le mois où il a le moins consommé / consommation minimale",
        "tokens": [
            "le moins consomme", "consomme le moins", "consomme minimale",
            "consomme la plus faible", "mois ou il a le moins consomme",
            "mois ou le client a le moins consomme",
            "quel mois a le moins", "mois minimum", "mois min",
            "plus faible consomme", "faible consomme",
        ]
    },

    "EXTRA_SOMME_CONSO_CLIENT": {
        "description": "détecter pour un client : somme totale de consommation sur tous les mois",
        "tokens": [
            "somme totale", "somme de consomme", "total consomme",
            "en tout", "cumul", "cumulee", "sur tous les mois",
            "global", "globale", "combien a consomme en tout",
            "consomme total", "consomme globale",
        ]
    },

    "EXTRA_SOMME_MONTANT_CLIENT": {
        "description": "détecter pour un client : somme totale des montants payés sur tous les mois",
        "tokens": [
            "somme totale montant", "somme montant", "total paye",
            "total montant", "montant total", "combien a-t-il paye",
            "combien a paye", "combien depense", "montant en tout",
            "paye en tout", "depense en tout", "total des factures",
            "montant global", "montant cumule sur",
        ]
    },
}


# ════════════════════════════════════════════════════════════
# ÉCRITURE DANS tokens_extra.py
# ════════════════════════════════════════════════════════════

def ecrire_tokens_extra(resultats: dict):
    dispatcher_keys = [
        "EXTRA_CONSO_ELEVEE", "EXTRA_CONSO_FAIBLE",
        "EXTRA_MONTANT_ELEVE", "EXTRA_MONTANT_FAIBLE",
        "EXTRA_SOMME_MOIS", "EXTRA_SOMME_MONTANT",
    ]
    intent_keys = [
        "EXTRA_MAX_CONSO_CLIENT", "EXTRA_MIN_CONSO_CLIENT",
        "EXTRA_SOMME_CONSO_CLIENT", "EXTRA_SOMME_MONTANT_CLIENT",
    ]

    def formater_liste(nom, variantes):
        lignes = [f"{nom} = ["]
        for v in variantes:
            v_safe = v.replace('"', '\\"')
            lignes.append(f'    "{v_safe}",')
        lignes.append("]\n")
        return "\n".join(lignes)

    contenu = '''# src/rag/tokens_extra.py
# ════════════════════════════════════════════════════════════
# Variantes supplémentaires générées par augment_tokens.py
# Ce fichier est importé par dispatcher.py et intent.py
# Pour régénérer : python src/rag/augment_tokens.py
# ════════════════════════════════════════════════════════════


# ── dispatcher.py ────────────────────────────────────────────
'''
    for key in dispatcher_keys:
        variantes = resultats.get(key, [])
        contenu += formater_liste(key, variantes)

    contenu += "\n# ── intent.py (client) ─────────────────────────────────────\n\n"
    for key in intent_keys:
        variantes = resultats.get(key, [])
        contenu += formater_liste(key, variantes)

    with open(TOKENS_EXTRA_PATH, "w", encoding="utf-8") as f:
        f.write(contenu)

    print(f"\n✅ tokens_extra.py écrit : {TOKENS_EXTRA_PATH}")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("🚀 Démarrage de l'augmentation de tokens...")
    print("⚠️  Appels au LLM local (Mistral via Ollama) en cours...\n")

    resultats = {}

    for nom_var, config in _EXISTANTS.items():
        print(f"⏳ Génération pour {nom_var}...")
        variantes = generer_variantes(
            nom_liste=nom_var,
            tokens_existants=config["tokens"],
            description=config["description"],
            nb=40
        )
        resultats[nom_var] = variantes
        print(f"  ✓ {len(variantes)} variantes générées")
        for v in variantes[:5]:
            print(f'    → "{v}"')
        if len(variantes) > 5:
            print(f"    ... et {len(variantes)-5} autres")

    ecrire_tokens_extra(resultats)

    print("\n⚠️  Vérifiez tokens_extra.py avant de committer !")
    print("⚠️  Supprimez les variantes trop génériques ou incorrectes.")
    print("✅  Ensuite ajoutez les imports dans dispatcher.py et intent.py.")