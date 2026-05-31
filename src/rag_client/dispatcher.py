import re
import json

from rag.mode import _normaliser_q
from rag.intent import _appeler_llm, _extraire_mois, _contient_mois
from rag_client.intent import _detecter_champ_infos
from src.database import get_statut_paiements_client
from rag_client.srm_knowledge import TOKENS_GENERAL_SRM, repondre_general


from rag_client.fetchers import (
    get_infos, get_mois_specifique,
    get_max_consommation, get_min_consommation,
    get_max_montant, get_min_montant,
    get_somme_montant, get_somme_conso, get_moyenne,
    get_evolution, get_par_annee,
    get_top_n_conso, get_top_n_montant,
    get_derniers_n_mois, get_premiers_n_mois,
    get_comparaison
)

from rag_client.tokens import (
    _TOKENS_MONTANT_MAX, _TOKENS_MONTANT_MIN,
    _TOKENS_CONSO_MAX, _TOKENS_CONSO_MIN,
    _TOKENS_SOMME_MONTANT, _TOKENS_SOMME_CONSO,
    _TOKENS_EVOLUTION, _TOKENS_MOYENNE,
    _TOKENS_INFOS, _TOKENS_MOIS,
    _TOKENS_CHAMP_MONTANT, _TOKENS_CHAMP_CONSO,
    INTENTS_CLIENT_CONNECTE,
    _TOKENS_COMPARAISON,
    _TOKENS_RETARD_PAIEMENT,
)

# ════════════════════════════════════════════
# MOTS ANGLAIS
# ════════════════════════════════════════════
_MOTS_ANGLAIS = [
    "last", "year", "month", "show", "give",
    "what", "when", "how", "much", "my",
    "consumption", "amount", "invoice", "bill"
]

# ════════════════════════════════════════════
# EXTRACTION NOMBRE (pour top N)
# ════════════════════════════════════════════
def _extraire_nombre(q: str) -> int:
    _MOTS_NOMBRES = {
        "un": 1, "une": 1, "deux": 2, "trois": 3,
        "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
        "huit": 8, "neuf": 9, "dix": 10
    }
    match = re.search(r'\b(\d+)\b', q)
    if match:
        return int(match.group(1))
    for mot, val in _MOTS_NOMBRES.items():
        if mot in q:
            return val
    return 3

# ════════════════════════════════════════════
# EXTRACTION TOUS LES MOIS
# ════════════════════════════════════════════
def _extraire_tous_les_mois(q: str) -> list:
    from rag.intent import _MAP_MOIS
    mois_trouves = []
    tokens_tries = sorted(_MAP_MOIS.keys(), key=len, reverse=True)
    for token in tokens_tries:
        if re.search(r'\b' + re.escape(token) + r'\b', q):
            mois_canon = _MAP_MOIS[token]
            if mois_canon not in mois_trouves:
                mois_trouves.append(mois_canon)
    return mois_trouves

# ════════════════════════════════════════════
# EXTRACTION ANNÉE
# ════════════════════════════════════════════
def _extraire_annee(q: str) -> str:
    match = re.search(r'\b(202[0-9])\b', q)
    if match:
        return match.group(1)
    if any(t in q for t in ["annee derniere", "l annee derniere", "an passe", "annee passee", "last year"]):
        return "2025"
    if any(t in q for t in ["cette annee", "annee actuelle", "annee en cours", "this year"]):
        return "2026"
    return ""

# ════════════════════════════════════════════
# TOKENS TOP N
# ════════════════════════════════════════════
_TOKENS_TOP_N_CONSO = [
    "mois les plus consomme", "mois les moins consomme",
    "plus consomme", "moins consomme",
    "consomme le plus", "consomme le moins",
    "top conso", "pic conso",
]

_TOKENS_TOP_N_MONTANT = [
    "mois les plus chers", "mois les moins chers",
    "mois les plus eleves", "mois les moins eleves",
    "factures les plus cheres", "factures les moins cheres",
    "plus cher", "moins cher", "plus eleve",
]

_TOKENS_DERNIERS = [
    "derniers mois", "dernier mois", "les derniers",
    "recents", "recent", "derniere periode",
]

_TOKENS_PREMIERS = [
    "premiers mois", "premier mois", "les premiers",
    "debut", "premiere periode",
]

# ════════════════════════════════════════════
# FALLBACK LLM
# ════════════════════════════════════════════
def _fallback_llm(question: str, numero_contrat: str) -> str:
    prompt = f"""Tu es un assistant pour un client SRM (eau et électricité au Maroc).
Les données couvrent : Octobre 2025 à Septembre 2026.
"last year" ou "année dernière" = 2025.
"this year" ou "cette année" = 2026.

Intents disponibles :
MAX_MONTANT       : mois où j'ai payé le plus
MIN_MONTANT       : mois où j'ai payé le moins
MAX_CONSOMMATION  : mois où j'ai le plus consommé
MIN_CONSOMMATION  : mois où j'ai le moins consommé
SOMME_MONTANT     : total de ce que j'ai payé
SOMME_CONSO       : total de ce que j'ai consommé
EVOLUTION         : historique complet, toutes les factures
MOYENNE           : moyenne mensuelle
INFOS             : informations du compte
MOIS_SPECIFIQUE   : facture d'un mois précis
PAR_ANNEE         : factures d'une année précise
TOP_N_CONSO       : les N mois les plus/moins consommés
TOP_N_MONTANT     : les N mois les plus/moins chers
DERNIERS_N        : les N derniers mois
PREMIERS_N        : les N premiers mois
ANALYSE           : question sur normalité, comparaison, conseil, explication personnalisée
HORS_SUJET        : question sans rapport avec les factures

EXEMPLES :
"le mois que je consomme beaucoup" → MAX_CONSOMMATION
"quand est ce que j ai beaucoup depense" → MAX_MONTANT
"donne moi tout" → EVOLUTION
"c est quoi ma moyenne" → MOYENNE
"resume moi mes factures" → EVOLUTION
"je veux voir mes 3 premiers mois" → PREMIERS_N avec n=3
"les mois ou j ai peu consomme" → MIN_CONSOMMATION
"montre moi les 5 factures les plus cheres" → TOP_N_MONTANT avec n=5, ordre=DESC
"factures recentes" → DERNIERS_N avec n=3
"bonjour", "merci", "aide moi" → HORS_SUJET
"quel temps fait il" → HORS_SUJET

EXEMPLES ANALYSE :
"est ce que ma consommation est normale" → ANALYSE
"je consomme trop ?" → ANALYSE
"pourquoi je paie autant" → ANALYSE
"ma facture est elle elevee" → ANALYSE
"c est normal comme montant" → ANALYSE
"comment reduire ma consommation" → ANALYSE
"des conseils pour payer moins" → ANALYSE
"ma conso est bizarre" → ANALYSE
"c est beaucoup ou pas" → ANALYSE
"je comprends pas ma facture" → ANALYSE
"est ce que ce mois est normal par rapport au mois dernier" → ANALYSE
"pourquoi ma conso a augmente" → ANALYSE
"quelle est la raison de cette hausse" → ANALYSE

RÈGLES IMPORTANTES :
- "normal", "bizarre", "conseil", "pourquoi", "comment reduire", "expliquer", "raison", "augmente", "diminue" → ANALYSE
- "infos", "profil", "compte", "numero" → INFOS
- Ne jamais retourner INFOS pour une question sur consommation ou montant
- Ne jamais retourner INFOS si la question contient "normal", "conseil", "pourquoi"
- HORS_SUJET uniquement si aucun rapport avec factures, eau, electricite, consommation

Question : {question}

Réponds UNIQUEMENT avec un JSON valide :
{{"intent": "NOM_INTENT", "params": {{}}}}
Ajoute selon l'intent :
- mois précis : {{"mois": "Janvier"}}
- année : {{"annee": "2025"}}
- nombre N : {{"n": 3}}
- ordre : {{"ordre": "DESC"}} pour plus/élevé, {{"ordre": "ASC"}} pour moins/faible
"""
    texte = _appeler_llm(prompt)
    match = re.search(r'\{.*\}', texte, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            intent = result.get("intent", "")
            params = result.get("params", {})

            # ── HORS SUJET ──
            if intent == "HORS_SUJET":
                return (
                    "Je suis votre assistant SRM 😊\n\n"
                    "Je peux vous aider sur :\n"
                    "• Vos consommations et montants par mois\n"
                    "• Vos factures par année\n"
                    "• L'analyse et comparaison de votre consommation\n"
                    "• Des conseils adaptés à votre situation\n\n"
                    "Posez-moi une question sur vos factures !"
                )

            # ── ANALYSE PERSONNALISÉE ──
            if intent == "ANALYSE":
                from datetime import datetime
                from dateutil.relativedelta import relativedelta

                _MOIS_FR = {
                    "January": "Janvier", "February": "Fevrier", "March": "Mars",
                    "April": "Avril", "May": "Mai", "June": "Juin",
                    "July": "Juillet", "August": "Aout", "September": "Septembre",
                    "October": "Octobre", "November": "Novembre", "December": "Decembre"
                }
                now            = datetime.now()
                mois_actuel    = _MOIS_FR[now.strftime("%B")]
                mois_precedent = _MOIS_FR[(now - relativedelta(months=1)).strftime("%B")]

                infos     = get_infos(numero_contrat)
                evolution = get_evolution(numero_contrat)
                moyenne   = get_moyenne(numero_contrat)

                donnees_mois_cles = (
                    f"Mois actuel ({mois_actuel}) :\n"
                    + get_mois_specifique(numero_contrat, mois_actuel)
                    + f"\n\nMois précédent ({mois_precedent}) :\n"
                    + get_mois_specifique(numero_contrat, mois_precedent)
                )

                from src.database import get_nom_client_par_contrat
                nom_complet = get_nom_client_par_contrat(numero_contrat) or ""
                prenom = nom_complet.split()[0] if nom_complet else "client"

                mois_mentionnes = _extraire_tous_les_mois(question)
                donnees_mois = ""
                if mois_mentionnes:
                    for m in mois_mentionnes:
                        donnees_mois += get_mois_specifique(numero_contrat, m) + "\n"

                prompt_analyse = f"""Tu es un assistant SRM pour un client au Maroc (eau et électricité).

Le prénom du client est : {prenom}
Commence TOUJOURS ta réponse par "Bonjour {prenom},"

Voici le profil réel de ce client :
{infos}

Voici son historique complet de consommation :
{evolution}

Voici ses statistiques :
{moyenne}

CONTEXTE TEMPOREL IMPORTANT :
- Mois actuel : {mois_actuel}
- Mois précédent : {mois_precedent}
- Quand le client dit "ce mois" → il parle de {mois_actuel}
- Quand le client dit "mois dernier" → il parle de {mois_precedent}
- Comparer TOUJOURS {mois_actuel} vs {mois_precedent} pour les questions de hausse/baisse

Données réelles des deux mois clés :
{donnees_mois_cles}

{"Données des mois mentionnés explicitement :" + chr(10) + donnees_mois if donnees_mois else ""}

Question du client : {question}

RÈGLES STRICTES :
- Ne jamais dire "heureuse de vous rencontrer", "ravi de vous aider" ou toute formule de politesse inutile
- Commence TOUJOURS par "Bonjour {prenom},"
- Va directement à l'explication après "Bonjour {prenom},"
- Cite obligatoirement les chiffres réels de {mois_actuel} ET {mois_precedent}
- Cite la moyenne réelle du client pour comparer
- Utilise UNIQUEMENT les chiffres présents ci-dessus, ne jamais inventer
- Si un mois n'est pas dans l'historique, dis-le clairement sans inventer
- Explique en tenant compte du type d'usage réel (agricole, domestique, professionnel)
- Adapte à la saisonnalité marocaine (été = irrigation/climatisation, hiver = chauffage)
- Ne jamais dire "je suppose" ou "probablement" sur des chiffres
- Donne des conseils uniquement si le client le demande explicitement
- Réponds en français, clair et bienveillant, maximum 5-6 lignes
- Le client est au MAROC, jamais mentionner la Tunisie ou un autre pays
-IMPORTANT : appelle toujours les mois par leur NOM EXACT — {mois_actuel} est le mois actuel, {mois_precedent} est le mois précédent. Ne jamais appeler {mois_precedent} "mois dernier" ni {mois_actuel} "ce mois" dans les chiffres, utilise toujours le nom du mois (ex: "Avril", "Mai"
- Ne jamais ajouter de formules comme "je t apprécie", "je suis heureux", "ravi de vous aider" ou toute expression de bienvenue — commence directement par "Bonjour {prenom}," suivi de l explication
- Saisonnalité STRICTE au Maroc : Mai/Juin/Juillet/Août = été = chaleur/irrigation. Septembre/Octobre/Novembre = automne. Décembre/Janvier/Février = hiver = froid/chauffage. Mars/Avril = printemps. Ne jamais inverser les saisons
"""
                return _appeler_llm(prompt_analyse)

            mois  = params.get("mois", "")
            annee = params.get("annee", "")
            n     = int(params.get("n", 3))
            ordre = params.get("ordre", "DESC")

            if intent == "MAX_MONTANT":
                return get_max_montant(numero_contrat)
            elif intent == "MIN_MONTANT":
                return get_min_montant(numero_contrat)
            elif intent == "MAX_CONSOMMATION":
                return get_max_consommation(numero_contrat)
            elif intent == "MIN_CONSOMMATION":
                return get_min_consommation(numero_contrat)
            elif intent == "SOMME_MONTANT":
                return get_somme_montant(numero_contrat)
            elif intent == "SOMME_CONSO":
                return get_somme_conso(numero_contrat)
            elif intent == "EVOLUTION":
                return get_evolution(numero_contrat)
            elif intent == "MOYENNE":
                return get_moyenne(numero_contrat)
            elif intent == "INFOS":
                return get_infos(numero_contrat)
            elif intent == "MOIS_SPECIFIQUE" and mois:
                return get_mois_specifique(numero_contrat, mois)
            elif intent == "PAR_ANNEE" and annee:
                return get_par_annee(numero_contrat, annee)
            elif intent == "TOP_N_CONSO":
                return get_top_n_conso(numero_contrat, n, ordre)
            elif intent == "TOP_N_MONTANT":
                return get_top_n_montant(numero_contrat, n, ordre)
            elif intent == "DERNIERS_N":
                return get_derniers_n_mois(numero_contrat, n)
            elif intent == "PREMIERS_N":
                return get_premiers_n_mois(numero_contrat, n)

        except Exception:
            pass

    return (
        "Je n'ai pas bien compris votre question. "
        "Vous pouvez me demander par exemple :\n"
        "• Le mois où j'ai le plus consommé\n"
        "• Les 3 mois les plus chers\n"
        "• Mes factures de 2025\n"
        "• Mon historique complet"
    )
# ════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════
def repondre_client_connecte(question: str, numero_contrat: str, historique: str = "") -> str:

    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    _MOIS_FR = {
        "January": "Janvier", "February": "Fevrier", "March": "Mars",
        "April": "Avril", "May": "Mai", "June": "Juin",
        "July": "Juillet", "August": "Aout", "September": "Septembre",
        "October": "Octobre", "November": "Novembre", "December": "Decembre"
    }
    _TOKENS_CE_MOIS        = ["ce mois", "ce mois ci", "mois actuel", "mois en cours", "mois courant"]
    _TOKENS_MOIS_PRECEDENT = ["mois dernier", "mois precedent", "mois passe", "le mois d avant", "moi dernier",    "mois denier", "mois dernir",     ]
    _TOKENS_MOIS_PROCHAIN  = ["mois prochain", "mois suivant", "mois d apres"]
    
    # ── Tokens comparaison (définis ici pour être disponibles partout dans la fonction) ──
    _TOKENS_COMPARAISON = [
        "compare", "comparer", "comparaison",
        "difference entre", "diff entre",
        "diffirence entre",
        "quelle est la difference", "quel est la difference",
        "quelle est la diffirence", "quel est la diffirence",
        "plus que", "moins que",
        "par rapport a", "par rapport au",
        "vs", "versus",
    ]
    _TOKENS_ANALYSE = [
        "pourquoi", "comment", "normal", "bizarre",
        "beaucoup", "trop", "eleve", "expliquer",
        "raison", "cause", "augmente", "diminue",
        "comprends pas", "je comprends", "conseil",
        "reduire", "economiser", "c est normal",
    ]
   

    now = datetime.now()

    def _detecter_champ(q):
        if any(t in q for t in _TOKENS_CHAMP_MONTANT) and \
           not any(t in q for t in _TOKENS_CHAMP_CONSO):
            return "montant"
        elif any(t in q for t in _TOKENS_CHAMP_CONSO) and \
             not any(t in q for t in _TOKENS_CHAMP_MONTANT):
            return "consommation"
        return None
    # ══════════════════════════════════════════
    # ÉTAPE -1 — QUESTION GÉNÉRALE SRM
    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    # ÉTAPE -1 — ROUTEUR LLM : GÉNÉRAL SRM ou PERSONNEL ?
    # ══════════════════════════════════════════
    q_brut = _normaliser_q(question)
    

    # Court-circuit : si la question contient un mot personnel
    # évident → on saute directement à la logique existante
    _MOTS_PERSO_EVIDENTS = [# Possessifs — étapes 0, 3, 4
        "mon ", "ma ", "mes ",
        # Retard — étape retard
        "j ai", "suis je", "je suis",
        "en retard", "impaye", "pas paye",
        # Consommation personnelle — étape 4
        "je consomme", "je paie", "je paye",
        "jai paye", "jai consomme",
        # Max/Min/Somme — étape 4
        "montant le plus", "montant max", "montant min",
        "montant eleve", "montant haut", "montant faible",
        "consomme le plus", "consomme le moins",
        "consommation max", "consommation min",
        "consommation eleve", "consommation faible",
        "somme", "total", "combien",
        # Historique/Moyenne — étape 4
        "historique", "evolution", "moyenne",
        "toutes mes", "tout afficher", "voir tout",
        "mois par mois",
        # Mois relatifs — étape 3.5
        "ce mois", "mois dernier", "mois prochain",
        "mois precedent", "mois actuel",
        # Comparaison — étape 2.5
        "compare", "comparer", "difference entre",
        "par rapport", "vs ", "versus",
        # Mois explicites — étape 3
        "janvier", "fevrier", "mars", "avril", "mai", "juin",
        "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
        # Années — étape 1
        "2025", "2026",
        # Top N — étape 2
        "derniers mois", "premiers mois", "dernier mois",
        "plus cher", "moins cher", "plus eleve",
        "plus consomme", "moins consomme",]
    print(f"DEBUG q_brut: '{q_brut}'")
    print(f"DEBUG perso match: {[t for t in _MOTS_PERSO_EVIDENTS if t in q_brut]}")
    
    if not any(t in q_brut for t in _MOTS_PERSO_EVIDENTS):
        intent_route = _appeler_llm(
            f"""Réponds UNIQUEMENT par GENERAL ou PERSONNEL.
GENERAL = question sur SRM (abonnement, branchement, documents, stage, recrutement, contact, économies, c'est quoi SRM)
PERSONNEL = question sur ses propres factures, consommation, montants, retard, historique

Question : {question}"""
        ).strip().upper()

        if "GENERAL" in intent_route:
            return repondre_general(question, _appeler_llm)
    
    # ── Détection anglais sur question brute ──
    question_lower = question.lower()
    mots_bruts = question_lower.split()
    if any(m in mots_bruts for m in _MOTS_ANGLAIS):
        return _fallback_llm(question, numero_contrat)

    q = _normaliser_q(question)
    q = re.sub(r'^(et|mais|aussi|donc|alors|puis)\s+', '', q)
    
    if any(t in q for t in _TOKENS_RETARD_PAIEMENT):
        factures = get_statut_paiements_client(numero_contrat)

        # ── Filtrer uniquement les mois déjà arrivés (jusqu'à aujourd'hui) ──
        mois_actuel = now.strftime("%Y%m")
        factures_passees = []
        for f in factures:
            try:
                # periode_debut format : "01/10/2025"
               
                date_lim = datetime.strptime(f["date_limite"], "%d/%m/%Y")
                # On garde uniquement si la date limite est <= aujourd'hui + 1 mois
                # c'est-à-dire les factures déjà émises et dont l'échéance est passée ou ce mois
                if date_lim <= datetime(now.year, now.month, 28):
                    factures_passees.append(f)
            except:
                factures_passees.append(f)

        # ── Cas mois explicite dans la question ──
        mois_cible = None
        mois_explicites = _extraire_tous_les_mois(q)

        if any(t in q for t in _TOKENS_CE_MOIS):
            mois_cible = _MOIS_FR[now.strftime("%B")]
        elif any(t in q for t in _TOKENS_MOIS_PRECEDENT):
            mois_cible = _MOIS_FR[(now - relativedelta(months=1)).strftime("%B")]
        elif mois_explicites:
            mois_cible = mois_explicites[0]

        if mois_cible:
            # Chercher dans TOUTES les factures (pas seulement passées)
            facture_mois = next(
                (f for f in factures if mois_cible in f["mois"]), None
            )
            if not facture_mois:
                return f"Aucune facture trouvée pour **{mois_cible}**."

            try:
                date_lim = datetime.strptime(facture_mois["date_limite"], "%d/%m/%Y")
                jours = (date_lim - now).days
                if date_lim < now:
                    msg_date = f"⚠️ Date limite dépassée depuis le {facture_mois['date_limite']} ({abs(jours)} jours de retard)"
                    return (
                        f"⚠️ Votre facture de **{facture_mois['mois']}** n'a pas été réglée dans les délais.\n"
                        f"• Montant : {facture_mois['montant_ttc']:,.2f} Dhs\n"
                        f"• {msg_date}\n\n"
                        f"Contactez votre agence SRM pour régulariser."
                    )
                else:
                    return (
                        f"📅 Votre facture de **{facture_mois['mois']}** n'est pas encore dépassée.\n"

                        f"• Montant : {facture_mois['montant_ttc']:,.2f} Dhs\n"
                        f"• Vous avez jusqu'au **{facture_mois['date_limite']}** pour payer\n"
                        f"• Il vous reste **{jours} jours**"
                    )
            except:
                return f"Facture {facture_mois['mois']} — {facture_mois['montant_ttc']:,.2f} Dhs"

        # ── Cas général : uniquement les factures déjà échues ──
        if not factures_passees:
            return "✅ Aucune facture échue pour le moment. Vous êtes à jour !"

        lignes = []
        for f in factures_passees:
            try:
                date_lim = datetime.strptime(f["date_limite"], "%d/%m/%Y")
                jours = abs((date_lim - now).days)
                if f["en_retard"]:
                    statut = f"⚠️ En retard ({jours}j)"
                else:
                    statut = "✅ Dans les délais"
            except:
                statut = "⚠️ En retard" if f["en_retard"] else "✅ OK"

            lignes.append(
                f"{statut} | {f['mois']} — {f['montant_ttc']:,.2f} Dhs "
                f"(date limite : {f['date_limite']})"
            )

        nb_retard = sum(1 for f in factures_passees if f["en_retard"])
        if nb_retard == 0:
            entete = f"✅ Toutes vos factures échues sont dans les délais.\n\n"
        else:
            entete = f"⚠️ {nb_retard} facture(s) non réglée(s) dans les délais :\n\n"

        return entete + "\n\n".join(lignes)
    # ══════════════════════════════════════════
    # ÉTAPE 0 — CHAMP PRÉCIS (infos compte)
    # ══════════════════════════════════════════
    champ = _detecter_champ_infos(q)
    if champ:
        return get_infos(numero_contrat, champ)

    # ══════════════════════════════════════════
    # ÉTAPE 1 — ANNÉE PRÉCISE (sans mois)
    # ══════════════════════════════════════════
    annee = _extraire_annee(q)
    if annee and not _contient_mois(q):
        return get_par_annee(numero_contrat, annee)

    # ══════════════════════════════════════════
    # ÉTAPE 2 — TOP N
    # ══════════════════════════════════════════
    _detect_nombre = re.search(r'\b(\d+|deux|trois|quatre|cinq)\b', q)
    if _detect_nombre:
        n = _extraire_nombre(q)
        has_top_token = (
            any(t in q for t in _TOKENS_DERNIERS) or
            any(t in q for t in _TOKENS_PREMIERS) or
            any(t in q for t in _TOKENS_TOP_N_MONTANT) or
            any(t in q for t in _TOKENS_TOP_N_CONSO)
        )
        if has_top_token:
            if any(t in q for t in _TOKENS_DERNIERS):
                return get_derniers_n_mois(numero_contrat, n)
            if any(t in q for t in _TOKENS_PREMIERS):
                return get_premiers_n_mois(numero_contrat, n)
            if any(t in q for t in _TOKENS_TOP_N_MONTANT):
                ordre = "ASC" if any(t in q for t in ["moins", "faible", "bas", "petit"]) else "DESC"
                return get_top_n_montant(numero_contrat, n, ordre)
            if any(t in q for t in _TOKENS_TOP_N_CONSO):
                ordre = "ASC" if any(t in q for t in ["moins", "faible", "bas", "petit"]) else "DESC"
                return get_top_n_conso(numero_contrat, n, ordre)

    # ══════════════════════════════════════════
    # ÉTAPE 2.5 — COMPARAISON (AVANT mois spécifique)
    # ══════════════════════════════════════════
    if any(t in q for t in _TOKENS_COMPARAISON):
        mois_resolus = []

        # Résoudre références relatives
        if any(t in q for t in _TOKENS_CE_MOIS):
            mois_resolus.append(_MOIS_FR[now.strftime("%B")])
        if any(t in q for t in _TOKENS_MOIS_PRECEDENT):
            mois_resolus.append(_MOIS_FR[(now - relativedelta(months=1)).strftime("%B")])

        # Ajouter mois explicites
        mois_explicites = _extraire_tous_les_mois(q)
        for m in mois_explicites:
            if m not in mois_resolus:
                mois_resolus.append(m)

        if len(mois_resolus) >= 2:
            # Analytique → LLM
            if any(t in q for t in _TOKENS_ANALYSE):
                return _fallback_llm(question, numero_contrat)
            # Factuelle → données directes
            return get_comparaison(numero_contrat, mois_resolus[0], mois_resolus[1])

    # ══════════════════════════════════════════
    # ÉTAPE 2.8 — ANALYSE AVEC MOIS (LLM)
    # ══════════════════════════════════════════
    if _contient_mois(q) and any(t in q for t in _TOKENS_ANALYSE):
        return _fallback_llm(question, numero_contrat)

    # ══════════════════════════════════════════
    # ÉTAPE 3 — MOIS SPÉCIFIQUE
    # ══════════════════════════════════════════
    if _contient_mois(q):
        mois = _extraire_mois(q)
        if mois:
            annee_mois = annee
            champ_mois = None
            if any(t in q for t in _TOKENS_CHAMP_MONTANT) and \
               not any(t in q for t in _TOKENS_CHAMP_CONSO):
                champ_mois = "montant"
            elif any(t in q for t in _TOKENS_CHAMP_CONSO) and \
                 not any(t in q for t in _TOKENS_CHAMP_MONTANT):
                champ_mois = "consommation"
            return get_mois_specifique(numero_contrat, mois, champ_mois, annee_mois)

    # ══════════════════════════════════════════
    # ÉTAPE 3.5 — CE MOIS / MOIS PRÉCÉDENT / PROCHAIN
    # ══════════════════════════════════════════
    if any(t in q for t in _TOKENS_CE_MOIS):
        if any(t in q for t in _TOKENS_ANALYSE):
            return _fallback_llm(question, numero_contrat)
        mois_fr  = _MOIS_FR[now.strftime("%B")]
        annee_fr = now.strftime("%Y")
        return get_mois_specifique(numero_contrat, mois_fr, _detecter_champ(q), annee_fr)

    if any(t in q for t in _TOKENS_MOIS_PRECEDENT):
        if any(t in q for t in _TOKENS_ANALYSE):
            return _fallback_llm(question, numero_contrat)
        date_prec = now - relativedelta(months=1)
        mois_fr   = _MOIS_FR[date_prec.strftime("%B")]
        annee_fr  = date_prec.strftime("%Y")
        return get_mois_specifique(numero_contrat, mois_fr, _detecter_champ(q), annee_fr)

    if any(t in q for t in _TOKENS_MOIS_PROCHAIN):
        date_suiv = now + relativedelta(months=1)
        mois_fr   = _MOIS_FR[date_suiv.strftime("%B")]
        annee_fr  = date_suiv.strftime("%Y")
        return get_mois_specifique(numero_contrat, mois_fr, _detecter_champ(q), annee_fr)
    # ══════════════════════════════════════════
    # ÉTAPE 4 — RÈGLES EXACTES
    # ══════════════════════════════════════════
    if any(t in q for t in _TOKENS_MONTANT_MAX):
        return get_max_montant(numero_contrat)
    if any(t in q for t in _TOKENS_MONTANT_MIN):
        return get_min_montant(numero_contrat)
    if any(t in q for t in _TOKENS_CONSO_MAX):
        return get_max_consommation(numero_contrat)
    if any(t in q for t in _TOKENS_CONSO_MIN):
        return get_min_consommation(numero_contrat)
    if any(t in q for t in _TOKENS_SOMME_MONTANT):
        return get_somme_montant(numero_contrat)
    if any(t in q for t in _TOKENS_SOMME_CONSO):
        return get_somme_conso(numero_contrat)
    if any(t in q for t in _TOKENS_EVOLUTION):
        return get_evolution(numero_contrat)
    if any(t in q for t in _TOKENS_MOYENNE):
        return get_moyenne(numero_contrat)
    if any(t in q for t in _TOKENS_INFOS):
        return get_infos(numero_contrat)

    # ══════════════════════════════════════════
    # ÉTAPE 5 — LLM FALLBACK
    # ══════════════════════════════════════════
    return _fallback_llm(question, numero_contrat)