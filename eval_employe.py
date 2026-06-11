#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_employe_v2.py
══════════════════════════════════════════════════════════════
Évaluation pipeline Employé — Stratégie par oracles SQL
Auteur : BEN ZHIR Wafa — SRM Souss-Massa 2025-2026

PRINCIPE :
  N0  / Ambiguïtés → keyword matching (messages fixes attendus)
  N1              → oracle SQL : on interroge la BDD directement
                    et on vérifie que la valeur réelle apparaît
                    dans la réponse du système
  N2 / N3         → évaluation structurelle : la réponse contient-elle
                    des données réelles (noms, chiffres, unités) ?
══════════════════════════════════════════════════════════════
"""

import sys, os, time, json, sqlite3, re
from datetime import datetime

# ── chemins ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR  = os.path.join(BASE_DIR, "src")
RAG_DIR  = os.path.join(BASE_DIR, "src", "rag")
DB_PATH  = os.path.join(BASE_DIR, "data", "srm.db")

for p in [BASE_DIR, SRC_DIR, RAG_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── import dispatcher ─────────────────────────────────────────
repondre_question_generale = None
valider_colonnes_sql = None
try:
    from rag.dispatcher import repondre_question_generale, valider_colonnes_sql
    print("✅ Import dispatcher OK")
except ImportError as e:
    print(f"❌ Import impossible : {e}")
    print(f"   Lancez depuis la racine du projet : python eval_employe_v2.py")


# ══════════════════════════════════════════════════════════════
# HELPERS BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════

def _db(sql: str, params=()) -> list:
    """Exécute une requête sur srm.db et retourne les lignes."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def _val(sql: str, params=()) -> str:
    """Retourne la première valeur de la première ligne."""
    rows = _db(sql, params)
    if rows and rows[0][0] is not None:
        v = rows[0][0]
        # Arrondi à 2 décimales si float
        if isinstance(v, float):
            return str(round(v, 2))
        return str(v)
    return ""


def _norm(s: str) -> str:
    """Normalise accents + casse + virgules de milliers pour comparaison."""
    s = s.lower()
    s = s.replace(",", "")  # Supprime les séparateurs de milliers
    for a, b in [("é","e"),("è","e"),("ê","e"),("à","a"),("â","a"),
                 ("ô","o"),("î","i"),("ù","u"),("û","u"),("ç","c")]:
        s = s.replace(a, b)
    return s


def _contient(reponse: str, valeur: str) -> bool:
    """Vérifie si valeur est contenue dans la réponse (normalisée)."""
    return _norm(valeur) in _norm(reponse)


def _contient_tous(reponse: str, valeurs: list) -> bool:
    """Vérifie si TOUTES les valeurs sont dans la réponse."""
    return all(_contient(reponse, v) for v in valeurs)


def _contient_un(reponse: str, valeurs: list) -> bool:
    """Vérifie si AU MOINS UNE valeur est dans la réponse."""
    return any(_contient(reponse, v) for v in valeurs)


# ══════════════════════════════════════════════════════════════
# ORACLES SQL — CALCULS DE RÉFÉRENCE
# Chaque oracle retourne la valeur attendue depuis la vraie BDD.
# Si la BDD est vide ou le client n'existe pas, retourne "".
# ══════════════════════════════════════════════════════════════

def oracle_top_consommateur():
    """Client avec la plus grande consommation totale."""
    rows = _db("""
        SELECT nom_client, ROUND(SUM(consommation),2), unite
        FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(consommation) DESC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_min_consommateur():
    rows = _db("""
        SELECT nom_client FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(consommation) ASC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_top_montant():
    rows = _db("""
        SELECT nom_client FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(montant_ttc) DESC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_min_montant():
    rows = _db("""
        SELECT nom_client FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(montant_ttc) ASC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_nb_clients():
    return _val("SELECT COUNT(DISTINCT nom_client) FROM factures_excel")


def oracle_nb_agences():
    return _val("SELECT COUNT(DISTINCT agence) FROM factures_excel")


def oracle_clients_usage(usage_like: str) -> list:
    rows = _db("""
        SELECT DISTINCT nom_client FROM factures_excel
        WHERE LOWER(usage) LIKE ?
    """, [f"%{usage_like.lower()}%"])
    return [r[0] for r in rows]


def oracle_clients_service(service: str) -> list:
    rows = _db("""
        SELECT DISTINCT nom_client FROM factures_excel
        WHERE LOWER(type_service) = ?
    """, [service.lower()])
    return [r[0] for r in rows]


def oracle_top5() -> list:
    rows = _db("""
        SELECT nom_client FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(consommation) DESC
        LIMIT 5
    """)
    return [r[0] for r in rows]


def oracle_top3_montant() -> list:
    rows = _db("""
        SELECT nom_client FROM factures_excel
        GROUP BY nom_client
        ORDER BY SUM(montant_ttc) DESC
        LIMIT 3
    """)
    return [r[0] for r in rows]


def oracle_somme_conso_mois(mois: str) -> str:
    return _val("""
        SELECT ROUND(SUM(consommation),2) FROM factures_excel
        WHERE mois_source LIKE ?
    """, [f"%{mois}%"])


def oracle_somme_conso_mois_par_service(mois: str) -> dict:
    """Retourne la somme de consommation par service pour un mois donné."""
    eau = _val("""
        SELECT ROUND(SUM(consommation),2) FROM factures_excel
        WHERE mois_source LIKE ? AND LOWER(type_service)='eau'
    """, [f"%{mois}%"])
    elec = _val("""
        SELECT ROUND(SUM(consommation),2) FROM factures_excel
        WHERE mois_source LIKE ? AND LOWER(type_service)='electricite'
    """, [f"%{mois}%"])
    return {"eau": eau, "electricite": elec}


def oracle_somme_montant_mois(mois: str) -> str:
    return _val("""
        SELECT ROUND(SUM(montant_ttc),2) FROM factures_excel
        WHERE mois_source LIKE ?
    """, [f"%{mois}%"])


def oracle_nb_alertes() -> str:
    return _val("""
        SELECT COUNT(*) FROM factures_excel
        WHERE alerte IS NOT NULL AND alerte != '' AND alerte != 'None'
    """)


def oracle_adresse_client(nom: str) -> str:
    return _val("""
        SELECT adresse FROM factures_excel
        WHERE nom_client LIKE ? LIMIT 1
    """, [f"%{nom}%"])


def oracle_usage_client(nom: str) -> str:
    return _val("""
        SELECT usage FROM factures_excel
        WHERE nom_client LIKE ? LIMIT 1
    """, [f"%{nom}%"])


def oracle_infos_client(nom: str) -> dict:
    rows = _db("""
        SELECT nom_client, numero_client, numero_contrat,
               numero_compteur, adresse, agence, usage, type_service
        FROM factures_excel
        WHERE nom_client LIKE ? LIMIT 1
    """, [f"%{nom}%"])
    if not rows:
        return {}
    r = rows[0]
    return {
        "nom": r[0], "numero_client": r[1], "numero_contrat": r[2],
        "numero_compteur": r[3], "adresse": r[4], "agence": r[5],
        "usage": r[6], "service": r[7]
    }


def oracle_somme_conso_client(nom: str) -> str:
    return _val("""
        SELECT ROUND(SUM(consommation),2) FROM factures_excel
        WHERE nom_client LIKE ?
    """, [f"%{nom}%"])


def oracle_clients_agence(agence_like: str) -> list:
    rows = _db("""
        SELECT DISTINCT nom_client FROM factures_excel
        WHERE LOWER(agence) LIKE ?
    """, [f"%{agence_like.lower()}%"])
    return [r[0] for r in rows]


def oracle_top_conso_elec() -> str:
    rows = _db("""
        SELECT nom_client FROM factures_excel
        WHERE LOWER(type_service) = 'electricite'
        GROUP BY nom_client
        ORDER BY SUM(consommation) DESC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_min_conso_eau() -> str:
    rows = _db("""
        SELECT nom_client FROM factures_excel
        WHERE LOWER(type_service) = 'eau'
        GROUP BY nom_client
        ORDER BY SUM(consommation) ASC
        LIMIT 1
    """)
    return rows[0][0] if rows else ""


def oracle_numero_compteur(nom: str) -> str:
    return _val("""
        SELECT DISTINCT numero_compteur FROM factures_excel
        WHERE nom_client LIKE ? LIMIT 1
    """, [f"%{nom}%"])


def oracle_numero_contrat(nom: str) -> str:
    return _val("""
        SELECT DISTINCT numero_contrat FROM factures_excel
        WHERE nom_client LIKE ? LIMIT 1
    """, [f"%{nom}%"])


def oracle_moyenne_conso_par_client() -> list:
    """Retourne la liste des noms de clients (pour vérifier qu'ils apparaissent)."""
    rows = _db("""
        SELECT DISTINCT nom_client FROM factures_excel
        ORDER BY nom_client
    """)
    return [r[0] for r in rows]


# ══════════════════════════════════════════════════════════════
# FONCTION D'ÉVALUATION STRUCTURELLE (N2/N3)
# Pour les questions qui passent par LLM ou fallback SQL :
# on vérifie que la réponse n'est pas un message d'erreur
# et qu'elle contient au moins une donnée réelle.
# ══════════════════════════════════════════════════════════════

def _eval_structurelle(reponse: str) -> bool:
    """
    Retourne True si la réponse semble contenir des données réelles.
    Critères : contient un chiffre OU une unité OU un nom de client connu.
    """
    r = _norm(reponse)
    
    # Échec si message d'erreur ou réponse vide
    erreurs = [
        "je n'ai pas pu", "erreur", "impossible", "aucun resultat",
        "aucune donnee", "reformuler", "pas compris"
    ]
    if any(e in r for e in erreurs):
        return False
    
    # Succès si contient un chiffre (données numériques)
    if re.search(r'\d+', reponse):
        return True
    
    # Succès si contient une unité de mesure
    if any(u in r for u in ["kwh", "m3", "dhs", "dirham", "%"]):
        return True
    
    return False


# ══════════════════════════════════════════════════════════════
# DATASET — Questions avec évaluateurs
#
# Chaque entrée = (question, categorie, niveau_attendu, evaluateur)
# evaluateur : fonction lambda(reponse) → bool
# ══════════════════════════════════════════════════════════════

def _build_dataset():
    """
    Construit le dataset APRÈS avoir interrogé la BDD.
    Ainsi les valeurs attendues sont tirées des vraies données.
    """

    # Pré-calcul des valeurs réelles
    top_conso      = oracle_top_consommateur()
    min_conso      = oracle_min_consommateur()
    top_montant    = oracle_top_montant()
    min_montant    = oracle_min_montant()
    nb_clients     = oracle_nb_clients()
    nb_agences     = oracle_nb_agences()
    clients_dom    = oracle_clients_usage("domestique")
    clients_agri   = oracle_clients_usage("agricole")
    clients_pro    = oracle_clients_usage("professionnel")
    clients_eau    = oracle_clients_service("eau")
    clients_elec   = oracle_clients_service("electricite")
    top5_conso     = oracle_top5()
    top3_montant   = oracle_top3_montant()
    top_conso_elec = oracle_top_conso_elec()
    min_conso_eau  = oracle_min_conso_eau()
    somme_fev_serv = oracle_somme_conso_mois_par_service("Fevrier")  # MODIFICATION 3
    somme_nov_ttc  = oracle_somme_montant_mois("Novembre")
    nb_alertes     = oracle_nb_alertes()
    
    # Clients spécifiques — à adapter selon vos données
    # Si "Tariq" n'existe pas dans votre BDD, ces tests seront "pas de données"
    adresse_tariq  = oracle_adresse_client("Tariq")
    usage_tariq    = oracle_usage_client("Tariq")
    infos_wissam   = oracle_infos_client("Wissam")
    infos_tariq    = oracle_infos_client("Tariq")
    conso_tariq    = oracle_somme_conso_client("Tariq")
    compteur_anas  = oracle_numero_compteur("Anas Naji")  # MODIFICATION 2 : nom complet
    contrat_tariq  = oracle_numero_contrat("Tariq")
    clients_agadir = oracle_clients_agence("Agadir")
    moyenne_clients = oracle_moyenne_conso_par_client()
    
    # ─────────────────────────────────────────────────────────
    # FORMAT : (question, categorie, niveau_attendu, evaluateur)
    # evaluateur = lambda reponse: bool
    # ─────────────────────────────────────────────────────────
    dataset = [

        # ══════════════════════════════════════════════════════
        # NIVEAU 0 — Portail validation (champs inexistants)
        # Évaluation : keyword matching sur message d'indispo
        # ══════════════════════════════════════════════════════
        (
            "donne moi le telephone des clients",
            "N0_TELEPHONE", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible", "pas disponible"])
        ),
        (
            "quel est lemail de tariq",
            "N0_EMAIL", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),
        (
            "quel est l age de chaque client",
            "N0_AGE", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),
        (
            "code postal des clients svp",
            "N0_CODE_POSTAL", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),
        (
            "cin de fatima",
            "N0_CIN", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),
        (
            "clients ayant le salaire depasse 5000",
            "N0_SALAIRE", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),
        (
            "clients avec une note superieure a 8",
            "N0_NOTE", "niveau0",
            lambda r: _contient_un(r, ["information", "disponible"])
        ),

        # ══════════════════════════════════════════════════════
        # AMBIGUÏTÉS — questions trop vagues
        # Évaluation : message de demande de précision
        # ══════════════════════════════════════════════════════
        (
            "somme",
            "AMB_SOMME", "ambigu",
            lambda r: _contient_un(r, ["quoi", "preciser", "precisez", "clarifier"])
        ),
        (
            "total",
            "AMB_TOTAL", "ambigu",
            lambda r: _contient_un(r, ["quoi", "preciser", "precisez"])
        ),
        (
            "donne moi",
            "AMB_VIDE", "ambigu",
            lambda r: _contient_un(r, ["preciser", "precisez", "compris", "souhaitez"])
        ),
        (
            "liste",
            "AMB_LISTE", "ambigu",
            lambda r: _contient_un(r, ["quoi", "preciser", "precisez"])
        ),
        (
            "montant",
            "AMB_MONTANT", "ambigu",
            lambda r: _contient_un(r, ["qui", "mois", "preciser", "precisez"])
        ),
        (
            "donne moi le bilan de facturation",
            "AMB_BILAN", "ambigu",
            lambda r: _contient_un(r, ["preciser", "precisez", "compris", "souhaitez"])
        ),
        (
            "donne moi un recap mentuelle",
            "AMB_RECAP", "ambigu",
            lambda r: _contient_un(r, ["preciser", "precisez", "compris", "souhaitez"])
        ),

        # ══════════════════════════════════════════════════════
        # NIVEAU 1 — Règles Python
        # Évaluation ORACLE : valeur extraite directement de la BDD
        # ══════════════════════════════════════════════════════

        # Comptages
        (
            "liste clients svp",
            "N1_LISTE_CLIENTS", "niveau1",
            lambda r: _contient(r, nb_clients) and re.search(r'\d', r) is not None
        ),
        (
            "ca fait combien de clients au total",
            "N1_COUNT_CLIENTS", "niveau1",
            lambda r: _contient(r, nb_clients)
        ),
        (
            "nbr agence existant",
            "N1_COUNT_AGENCES", "niveau1",
            lambda r: _contient(r, nb_agences)
        ),

        # Agence par client
        (
            "montre moi l agence de chaque client",
            "N1_AGENCE_PAR_CLIENT", "niveau1",
            lambda r: _eval_structurelle(r) and
                      _contient_un(r, ["agence", "Agadir", "Inezgane", "Tiznit"])
        ),
        (
            "les clients de l agence Agadir Nord",
            "N1_AGENCE_FILTRE", "niveau1",
            lambda r: (
                _contient(r, clients_agadir[0]) if clients_agadir else _eval_structurelle(r)
            )
        ),
        (
            "lister les clients par agence",
            "N1_LISTE_PAR_AGENCE", "niveau1",
            lambda r: _eval_structurelle(r) and
                      _contient_un(r, ["agence", "clients"])
        ),

        # Usages
        (
            "lister les clients ayant usage domestique",
            "N1_USAGE_DOM", "niveau1",
            lambda r: (
                _contient(r, clients_dom[0]) if clients_dom else _eval_structurelle(r)
            )
        ),
        (
            "quels clients ont un usage agricole",
            "N1_USAGE_AGRI", "niveau1",
            lambda r: (
                _contient(r, clients_agri[0]) if clients_agri else _eval_structurelle(r)
            )
        ),
        (
            "clients usage professionnel",
            "N1_USAGE_PRO", "niveau1",
            lambda r: (
                _contient(r, clients_pro[0]) if clients_pro else _eval_structurelle(r)
            )
        ),

        # Consommation élevée / faible
        (
            "c est qui le plus gros consommateur",
            "N1_TOP_CONSO", "niveau1",
            lambda r: _contient(r, top_conso) if top_conso else _eval_structurelle(r)
        ),
        (
            "et le plus petit consommateur",
            "N1_MIN_CONSO", "niveau1",
            lambda r: _contient(r, min_conso) if min_conso else _eval_structurelle(r)
        ),
        (
            "donne moi le top 5 des consommateurs",
            "N1_TOP5_CONSO", "niveau1",
            lambda r: sum(1 for c in top5_conso if _contient(r, c)) >= 3
            # Au moins 3 des 5 noms présents (tolérance)
        ),
        (
            "clients qui consomment beaucoup en electricite",
            "N1_TOP_CONSO_ELEC", "niveau1",
            lambda r: _contient(r, top_conso_elec) if top_conso_elec else _eval_structurelle(r)
        ),
        (
            "qui consomme le moins en eau",
            "N1_MIN_CONSO_EAU", "niveau1",
            lambda r: _contient(r, min_conso_eau) if min_conso_eau else _eval_structurelle(r)
        ),

        # Montants
        (
            "qui est ce qui paye le plus",
            "N1_TOP_MONTANT", "niveau1",
            lambda r: _contient(r, top_montant) if top_montant else _eval_structurelle(r)
        ),
        (
            "la facture la moins chere",
            "N1_MIN_MONTANT", "niveau1",
            lambda r: _contient(r, min_montant) if min_montant else _eval_structurelle(r)
        ),
        (
            "top 3 montant les plus eleves",
            "N1_TOP3_MONTANT", "niveau1",
            lambda r: sum(1 for c in top3_montant if _contient(r, c)) >= 2
        ),

        # Services
        (
            "client eau",
            "N1_SERVICE_EAU", "niveau1",
            lambda r: (
                _contient(r, clients_eau[0]) if clients_eau else _eval_structurelle(r)
            )
        ),
        (
            "les clients qui ont de l electricite",
            "N1_SERVICE_ELEC", "niveau1",
            lambda r: (
                _contient(r, clients_elec[0]) if clients_elec else _eval_structurelle(r)
            )
        ),

        # Évolution et alertes
        (
            "affiche moi l evolution mois par mois",
            "N1_EVOLUTION", "niveau1",
            lambda r: _eval_structurelle(r) and
                      _contient_un(r, ["janvier", "fevrier", "mars", "mois"])
        ),
        (
            "y a des alertes",
            "N1_ALERTES_LIST", "niveau1",
            lambda r: _eval_structurelle(r) or
                      _contient(r, "aucune alerte")
        ),
        (
            "combien d alerte existant",
            "N1_COUNT_ALERTES", "niveau1",
            lambda r: _contient(r, nb_alertes) if nb_alertes else _eval_structurelle(r)
        ),

        # Sommes par mois — ORACLE avec séparation par service (MODIFICATION 3)
        (
            "donner moi la somme de consomation en fev",
            "N1_SOMME_CONSO_FEV", "niveau1",
            lambda r: (
                _contient(r, somme_fev_serv["eau"]) and _contient(r, somme_fev_serv["electricite"])
                if somme_fev_serv["eau"] and somme_fev_serv["electricite"]
                else _eval_structurelle(r)
            )
        ),
        (
            "quel est la somme de montant en nov",
            "N1_SOMME_MONTANT_NOV", "niveau1",
            lambda r: _contient(r, somme_nov_ttc) if somme_nov_ttc else _eval_structurelle(r)
        ),

        # Fautes d'orthographe — robustesse lexicale
        (
            "consomation eleve",
            "N1_FAUTE_CONSO", "niveau1",
            lambda r: _contient(r, top_conso) if top_conso else _eval_structurelle(r)
        ),
        # CORRECTION 2 : N1_FAUTE_AGENCE - plus stricte (exige mappings)
        (
            "agennce de chaque client",
            "N1_FAUTE_AGENCE", "niveau1",
            lambda r: (
                _eval_structurelle(r) and
                _contient_un(r, ["agence", "client"]) and
                (r.count("→") >= 3 or r.count(":") >= 10)
            )
        ),
        (
            "grand consomateur eau",
            "N1_FAUTE_CONSOMATEUR", "niveau1",
            lambda r: _contient(r, top_conso_elec) or _eval_structurelle(r)
        ),

        # Infos client spécifique — ORACLE : valeur dans la BDD
        (
            "donner moi adresse de tariq",
            "N1_ADRESSE_TARIQ", "niveau1",
            lambda r: (
                _contient(r, adresse_tariq) if adresse_tariq
                else _contient_un(r, ["adresse", "tariq", "aucune"])
            )
        ),
        (
            "donner moi usage de tariq",
            "N1_USAGE_TARIQ", "niveau1",
            lambda r: (
                _contient(r, usage_tariq) if usage_tariq
                else _contient_un(r, ["usage", "tariq", "aucune"])
            )
        ),
        # CORRECTION 1 : N1_INFOS_WISSAM - plus spécifique (exige numéro contrat/compteur)
        (
            "donner moi infos de wissam",
            "N1_INFOS_WISSAM", "niveau1",
            lambda r: (
                _contient(r, infos_wissam.get("nom", "Wissam")) and
                (
                    _contient_un(r, ["numero_contrat", "numero_compteur", "n° contrat", "n° compteur"]) or
                    _contient(r, "informations du client")
                )
                if infos_wissam else _eval_structurelle(r)
            )
        ),
        (
            "quels sont info de tariq",
            "N1_INFOS_TARIQ", "niveau1",
            lambda r: (
                _contient(r, infos_tariq.get("nom", "Tariq")) and
                _contient_un(r, ["contrat", "compteur", "agence", "usage"])
                if infos_tariq else _eval_structurelle(r)
            )
        ),
        (
            "quel est la somme de conso de tariq",
            "N1_SOMME_CONSO_TARIQ", "niveau1",
            lambda r: (
                _contient(r, conso_tariq) if conso_tariq
                else _eval_structurelle(r)
            )
        ),

        # ══════════════════════════════════════════════════════
        # NIVEAU 2 — LLM Router (classificateur d'intention)
        # Évaluation structurelle : réponse non vide avec données
        # ══════════════════════════════════════════════════════
        (
            "statistiques generales de la base",
            "N2_STATS_GENERALES", "niveau2",
            lambda r: _eval_structurelle(r) and
                      _contient_un(r, ["client", "facture", "montant"])
        ),
        (
            "fais moi un classement des clients par consommation",
            "N2_CLASSEMENT", "niveau2",
            lambda r: _eval_structurelle(r) and
                      re.search(r'\d', r) is not None
        ),
        (
            "comment ont evolue les factures au fil des mois",
            "N2_EVOLUTION", "niveau2",
            lambda r: _eval_structurelle(r) and
                      _contient_un(r, ["mois", "janvier", "fevrier", "evolution"])
        ),

        # ══════════════════════════════════════════════════════
        # NIVEAU 3 — Fallback Text-to-SQL
        # Évaluation : valeur exacte ou structurelle selon le cas
        # ══════════════════════════════════════════════════════
        (
            "clients avec usage domestique et qui sont a Agadir Sud",
            "N3_MULTI_FILTRE", "niveau3",
            lambda r: _eval_structurelle(r)
            # Résultat dépend des données — on vérifie juste que la réponse est structurée
        ),
        (
            "ceux qui prennent de l eau et habitent a Inezgane",
            "N3_EAU_INEZGANE", "niveau3",
            lambda r: _eval_structurelle(r) or _contient(r, "aucun resultat")
        ),
        (
            "les clients electricite avec un usage professionnel",
            "N3_ELEC_PRO", "niveau3",
            lambda r: _eval_structurelle(r) or _contient(r, "aucun resultat")
        ),
        (
            "numero de compteur de Anas Naji",
            "N3_COMPTEUR_ANAS", "niveau3",
            lambda r: (
                _contient(r, compteur_anas) if compteur_anas
                else _contient_un(r, ["compteur", "anas", "aucune"])
            )
        ),
        (
            "quel est le numero de contrat de tariq",
            "N3_CONTRAT_TARIQ", "niveau3",
            lambda r: (
                _contient(r, contrat_tariq) if contrat_tariq
                else _contient_un(r, ["contrat", "tariq", "aucune"])
            )
        ),
        (
            "donner moi la moyenne generale de chaque client",
            "N3_MOYENNE_GENERALE", "niveau3",
            lambda r: (
                _eval_structurelle(r) and
                sum(1 for c in moyenne_clients[:3] if _contient(r, c)) >= 1
            )
        ),
    ]

    return dataset


# ══════════════════════════════════════════════════════════════
# EXÉCUTION ET COMPTEURS
# ══════════════════════════════════════════════════════════════

_llm_count = 0
_sql_count = 0

def _repondre_employe(question: str) -> str:
    global _llm_count, _sql_count
    if repondre_question_generale is None:
        return "ERREUR: dispatcher non chargé"

    # Patch LLM counter
    original_llm = None
    try:
        import rag.intent as _intent
        original_llm = _intent._appeler_llm
        def _llm_patch(prompt):
            global _llm_count
            _llm_count += 1
            return original_llm(prompt)
        _intent._appeler_llm = _llm_patch
    except Exception:
        pass

    # Patch SQL counter
    original_sql = None
    try:
        import rag.dispatcher as _disp
        original_sql = _disp.repondre_fallback_sql
        def _sql_patch(*a, **kw):
            global _sql_count
            _sql_count += 1
            return original_sql(*a, **kw)
        _disp.repondre_fallback_sql = _sql_patch
    except Exception:
        pass

    try:
        reponse = repondre_question_generale(question, "", "")
    except Exception as e:
        reponse = f"ERREUR: {e}"

    # Restore
    try:
        if original_llm:
            import rag.intent as _intent
            _intent._appeler_llm = original_llm
        if original_sql:
            import rag.dispatcher as _disp
            _disp.repondre_fallback_sql = original_sql
    except Exception:
        pass

    return reponse


def _detecter_niveau_reel(reponse: str) -> str:
    r = _norm(reponse)
    if "information" in r and "disponible" in r:
        return "niveau0"
    if any(t in r for t in ["quoi", "precisez", "preciser", "pas compris", "souhaitez"]):
        return "ambigu"
    return "detect_auto"  # on ne peut pas distinguer N1/N2/N3 depuis la réponse seule


# ══════════════════════════════════════════════════════════════
# TESTS UNITAIRES SCHÉMA SQL
# ══════════════════════════════════════════════════════════════

CAS_SCHEMA = [
    ("colonne score inexistante",
     "SELECT nom_client, score FROM factures_excel ORDER BY score DESC",
     True),
    ("colonne coefficient inexistante",
     "SELECT nom_client, coefficient FROM factures_excel WHERE coefficient > 5",
     True),
    ("colonnes valides — SUM(consommation)",
     "SELECT nom_client, SUM(consommation) FROM factures_excel GROUP BY nom_client",
     False),
    ("colonnes valides — montant_ttc WHERE mois",
     "SELECT nom_client, montant_ttc FROM factures_excel WHERE mois_source LIKE '%Janvier%'",
     False),
    ("colonnes valides — agence LIKE",
     "SELECT nom_client, agence FROM factures_excel WHERE agence LIKE '%Agadir%'",
     False),
    ("colonne rang_client inexistante",
     "SELECT nom_client, rang_client FROM factures_excel ORDER BY rang_client",
     True),
    ("colonnes valides — numero_compteur",
     "SELECT DISTINCT nom_client, numero_compteur FROM factures_excel WHERE nom_client LIKE '%Anas%'",
     False),
]

VERT   = "\033[92m"
ROUGE  = "\033[91m"
JAUNE  = "\033[93m"
RESET  = "\033[0m"
GRAS   = "\033[1m"


def _tester_schema() -> list:
    if valider_colonnes_sql is None:
        print(f"  {JAUNE}⚠️  valider_colonnes_sql non disponible{RESET}")
        return []
    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  TESTS UNITAIRES — VALIDATION SCHÉMA SQL{RESET}")
    print(f"{'═'*60}{RESET}\n")
    resultats = []
    for desc, sql, doit_echouer in CAS_SCHEMA:
        try:
            est_valide = valider_colonnes_sql(sql)
            succes = (est_valide != doit_echouer)
        except Exception as e:
            succes = False
            est_valide = False
        icone = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"  {icone} {desc}")
        resultats.append({
            "description": desc, "sql": sql,
            "doit_echouer": doit_echouer,
            "est_valide": bool(est_valide),
            "succes": succes
        })
    nb = sum(1 for t in resultats if t["succes"])
    print(f"\n  Schéma : {nb}/{len(resultats)} ({nb/len(resultats)*100:.0f}%)\n")
    return resultats


# ══════════════════════════════════════════════════════════════
# GÉNÉRATION HTML
# ══════════════════════════════════════════════════════════════

def _generer_html(resultats, tests_schema, date_exec, llm_count, sql_count):
    nb_ok  = sum(1 for r in resultats if r["succes"])
    total  = len(resultats)
    score  = nb_ok / total if total else 0
    couleur = "#2ecc71" if score >= 0.85 else ("#f39c12" if score >= 0.65 else "#e74c3c")

    # Stats par niveau
    par_niv = {}
    for r in resultats:
        n = r["niveau_attendu"]
        par_niv.setdefault(n, {"ok": 0, "total": 0, "temps": []})
        par_niv[n]["total"] += 1
        par_niv[n]["temps"].append(r["duree_ms"])
        if r["succes"]:
            par_niv[n]["ok"] += 1

    total_sans_llm = sum(1 for r in resultats
                         if r["niveau_attendu"] in ("niveau0", "niveau1", "ambigu"))
    pct_sans_llm = total_sans_llm / total * 100 if total else 0

    # Blocs niveau
    NIVEAUX_META = {
        "niveau0": ("🚪 N0 — Portail validation", "#58a6ff"),
        "niveau1": ("⚡ N1 — Règles Python (oracle SQL)", "#58a6ff"),
        "niveau2": ("🤖 N2 — LLM Router", "#c792ea"),
        "niveau3": ("📊 N3 — Fallback Text-to-SQL", "#2ecc71"),
        "ambigu":  ("❓ Ambiguïtés", "#f39c12"),
    }
    blocs_niveau = ""
    for niv, (label, txt) in NIVEAUX_META.items():
        if niv not in par_niv:
            continue
        v = par_niv[niv]
        taux = v["ok"] / v["total"]
        bar_c = "#2ecc71" if taux >= 0.85 else ("#f39c12" if taux >= 0.65 else "#e74c3c")
        tps_m = sum(v["temps"]) / len(v["temps"])
        blocs_niveau += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
                    padding:16px;flex:1;min-width:190px">
          <div style="font-size:12px;font-weight:bold;color:{txt}">{label}</div>
          <div style="font-size:22px;font-weight:bold;margin:6px 0">{v['ok']}/{v['total']}</div>
          <div style="color:{bar_c};font-size:13px">{taux*100:.0f}%</div>
          <div style="font-size:10px;color:#8b949e">⏱️ {tps_m:.0f} ms moy.</div>
          <div style="background:#21262d;border-radius:4px;height:5px;margin-top:8px">
            <div style="background:{bar_c};width:{int(taux*100)}%;height:5px;border-radius:4px"></div>
          </div>
        </div>"""

    # Lignes schéma
    nb_schema_ok = sum(1 for t in tests_schema if t["succes"])
    lignes_schema = ""
    for t in tests_schema:
        bg    = "#1a2e1a" if t["succes"] else "#2e1a1a"
        icone = "✅" if t["succes"] else "❌"
        attendu = "Rejetée" if t["doit_echouer"] else "Acceptée"
        obtenu  = ("✅ Rejetée" if not t["est_valide"] else "❌ Acceptée") if t["doit_echouer"] else \
                  ("✅ Acceptée" if t["est_valide"] else "❌ Rejetée")
        lignes_schema += f"""
        <tr style="background:{bg}">
          <td style="text-align:center">{icone}</td>
          <td>{t['description']}</td>
          <td><code style="font-size:10px">{t['sql'][:60]}...</code></td>
          <td>{attendu}</td><td>{obtenu}</td>
        </tr>"""

    # Lignes détail
    echecs = [r for r in resultats if not r["succes"]]
    lignes_detail = ""
    for i, r in enumerate(resultats, 1):
        bg    = "#1a2e1a" if r["succes"] else "#2e1a1a"
        icone = "✅" if r["succes"] else "❌"
        niv   = r["niveau_attendu"]
        BADGE = {"niveau0": ("#0d2137","🚪N0"), "niveau1": ("#0d2137","⚡N1"),
                 "niveau2": ("#1e0d37","🤖N2"), "niveau3": ("#0d2e1a","📊N3"),
                 "ambigu":  ("#2e2a0d","❓AMB")}
        bg_b, lbl_b = BADGE.get(niv, ("#161b22", niv))
        rep_html = (r["reponse"]
                    .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                    .replace("\n","<br>"))
        tps_c = "#2ecc71" if r["duree_ms"] < 500 else ("#f39c12" if r["duree_ms"] < 20000 else "#e74c3c")
        
        methode = r.get("methode_eval", "keyword")
        badge_m = ("🔬 oracle" if methode == "oracle"
                   else "🏗️ struct." if methode == "structurelle"
                   else "🔑 keyword")
        lignes_detail += f"""
        <tr style="background:{bg}">
          <td style="text-align:center">{i}</td>
          <td style="text-align:center">{icone}</td>
          <td><span style="background:{bg_b};border:1px solid #374151;border-radius:4px;
                           padding:2px 6px;font-size:11px">{lbl_b}</span></td>
          <td style="font-size:12px">{r['question']}</td>
          <td><div style="max-height:120px;overflow-y:auto;font-size:11px;
                          background:#0d1117;border-radius:4px;padding:6px">{rep_html}</div></td>
          <td style="font-size:10px;color:#8b949e">{badge_m}</td>
          <td style="color:{tps_c};font-size:12px">{r['duree_ms']:.0f}ms</td>
        </tr>"""

    # Lignes échecs
    lignes_echecs = ""
    for r in echecs:
        methode = r.get("methode_eval", "keyword")
        lignes_echecs += f"""
        <tr style="background:#2e1a1a">
          <td>❌</td>
          <td>{r['categorie']}</td>
          <td style="font-size:12px">{r['question']}</td>
          <td style="font-size:11px">{r['methode_eval']}</td>
          <td style="font-size:11px">{r['reponse'][:100].replace(chr(10),' ')}</td>
        </tr>"""
    if not echecs:
        lignes_echecs = '<tr><td colspan="5" style="text-align:center;color:#2ecc71">🎉 Aucun échec !</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <title>Rapport Évaluation v2 — Employé SRM</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:28px;font-size:13px}}
    h1{{color:#58a6ff;margin-bottom:4px}}h2{{color:#79c0ff;margin:28px 0 10px;border-bottom:1px solid #30363d;padding-bottom:6px}}
    .meta{{color:#8b949e;font-size:11px;margin-bottom:22px}}
    .cards{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}}
    .card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;min-width:110px;text-align:center}}
    .card .val{{font-size:26px;font-weight:bold}}
    .pbar{{background:#21262d;border-radius:5px;height:16px;margin-bottom:18px}}
    .pfill{{height:16px;border-radius:5px;background:{couleur};width:{score*100:.1f}%}}
    .niv-grid{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px}}
    table{{width:100%;border-collapse:collapse;margin-bottom:8px}}
    th{{background:#161b22;padding:8px;text-align:left;border-bottom:2px solid #30363d;font-size:12px}}
    td{{padding:7px 10px;border-bottom:1px solid #21262d;vertical-align:middle}}
    tr:hover td{{background:#161b22}}
    .note{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;
            margin-bottom:16px;font-size:11px;color:#8b949e;line-height:1.6}}
    code{{background:#21262d;padding:1px 4px;border-radius:3px;font-size:10px}}
    footer{{text-align:center;margin-top:32px;padding-top:12px;border-top:1px solid #21262d;font-size:10px;color:#8b949e}}
  </style>
</head>
<body>
<h1>📊 Rapport d'Évaluation v2 — Assistant Employé SRM</h1>
<div class="meta">Généré le <strong>{date_exec}</strong> | <strong>{total}</strong> questions | Évaluation par oracles SQL</div>

<div class="pbar"><div class="pfill"></div></div>

<div class="cards">
  <div class="card"><div class="val" style="color:{couleur}">{score*100:.1f}%</div><div>Taux global</div></div>
  <div class="card"><div class="val">{nb_ok}/{total}</div><div>Réussies</div></div>
  <div class="card"><div class="val">{llm_count}</div><div>Appels LLM</div></div>
  <div class="card"><div class="val">{sql_count}</div><div>Appels SQL</div></div>
  <div class="card"><div class="val">{pct_sans_llm:.0f}%</div><div>Sans LLM</div></div>
  <div class="card"><div class="val">{nb_schema_ok}/{len(tests_schema)}</div><div>Schéma SQL</div></div>
</div>

<div class="note">
  <strong>🔬 Méthode d'évaluation :</strong><br>
  🔑 <strong>Keyword</strong> — messages fixes attendus (N0, ambiguïtés)<br>
  🔬 <strong>Oracle SQL</strong> — valeur extraite directement de srm.db puis cherchée dans la réponse (N1)<br>
  🏗️ <strong>Structurelle</strong> — la réponse contient des données réelles (chiffres, unités, noms) (N2/N3)<br>
  <strong>Avantage</strong> : une réponse reformulée différemment mais correcte sera quand même évaluée ✅
</div>

<h2>Performance par niveau</h2>
<div class="niv-grid">{blocs_niveau}</div>

<h2>Tests unitaires — Validation schéma SQL ({nb_schema_ok}/{len(tests_schema)})</h2>
<table><thead><tr><th>État</th><th>Description</th><th>SQL</th><th>Attendu</th><th>Obtenu</th></tr></thead>
<tbody>{lignes_schema}</tbody></table>

<h2>Échecs ({len(echecs)})</h2>
<table><thead><tr><th>État</th><th>Cat.</th><th>Question</th><th>Méthode</th><th>Réponse obtenue</th></tr></thead>
<tbody>{lignes_echecs}</tbody></table>

<h2>Détail des {total} questions</h2>
<table><thead><tr><th>#</th><th>✅/❌</th><th>Niveau</th><th>Question</th><th>Réponse</th><th>Méthode</th><th>Durée</th></tr></thead>
<tbody>{lignes_detail}</tbody></table>

<footer>SRM Souss-Massa — BEN ZHIR Wafa — EST Guelmim SDSI 2025–2026</footer>
</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    global _llm_count, _sql_count
    _llm_count = 0
    _sql_count = 0

    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  ÉVALUATION V2 — ASSISTANT EMPLOYÉ SRM{RESET}")
    print(f"{'═'*60}{RESET}\n")

    # ── Vérification BDD ──
    if not os.path.exists(DB_PATH):
        print(f"{ROUGE}❌ Base de données introuvable : {DB_PATH}{RESET}")
        print("   Ajustez DB_PATH en haut du script.")
        return

    # ── Construction dataset avec oracles ──
    print("  📊 Calcul des oracles depuis srm.db...")
    dataset = _build_dataset()
    print(f"  ✅ {len(dataset)} questions chargées\n")

    tests_schema = _tester_schema()

    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  ÉVALUATION PIPELINE{RESET}")
    print(f"{'═'*60}{RESET}\n")

    resultats = []
    for i, (q, cat, niv, evaluateur) in enumerate(dataset, 1):
        print(f"  [{i:2d}/{len(dataset)}] {cat:<28} {q[:45]}...")
        debut  = time.time()
        reponse = _repondre_employe(q)
        duree  = (time.time() - debut) * 1000

        # Déterminer méthode d'évaluation pour le rapport
        methode = ("keyword" if niv in ("niveau0", "ambigu")
                   else "oracle" if niv == "niveau1"
                   else "structurelle")

        succes = bool(evaluateur(reponse))
        icone  = f"{VERT}✅{RESET}" if succes else f"{ROUGE}❌{RESET}"
        print(f"       {icone}  [{methode}]  {duree:.0f}ms")
        if not succes:
            print(f"       {ROUGE}Réponse : {reponse[:80]}{RESET}")

        resultats.append({
            "question":      q,
            "categorie":     cat,
            "niveau_attendu": niv,
            "succes":        succes,
            "duree_ms":      duree,
            "reponse":       reponse,
            "methode_eval":  methode,
        })

    total  = len(resultats)
    nb_ok  = sum(1 for r in resultats if r["succes"])
    score  = nb_ok / total if total else 0

    # Stats par niveau
    par_niv = {}
    for r in resultats:
        n = r["niveau_attendu"]
        par_niv.setdefault(n, {"ok": 0, "total": 0})
        par_niv[n]["total"] += 1
        if r["succes"]:
            par_niv[n]["ok"] += 1

    total_sans_llm = sum(1 for r in resultats
                         if r["niveau_attendu"] in ("niveau0", "niveau1", "ambigu"))

    print(f"\n{GRAS}{'═'*60}{RESET}")
    print(f"{GRAS}  RÉSULTATS{RESET}")
    print(f"{'═'*60}{RESET}")
    print(f"\n  Score global    : {nb_ok}/{total}  ({score*100:.1f}%)")
    print(f"  Appels LLM (N2) : {_llm_count}")
    print(f"  Appels SQL (N3) : {_sql_count}")
    print(f"  Sans LLM        : {total_sans_llm}/{total} ({total_sans_llm/total*100:.0f}%)")
    print(f"\n  Détail par niveau :")
    for niv in ["niveau0", "niveau1", "niveau2", "niveau3", "ambigu"]:
        if niv in par_niv:
            v = par_niv[niv]
            t = v["ok"] / v["total"] * 100
            bar = ("█" * round(t/5)) + ("░" * (20 - round(t/5)))
            print(f"    {niv:10} : {v['ok']:2}/{v['total']:2}  {bar}  {t:.0f}%")

    date_exec = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    os.makedirs("eval_results", exist_ok=True)

    json_path = os.path.join("eval_results", "rapport_eval_employe.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_exec,
            "total": total,
            "reussis": nb_ok,
            "score": round(score, 4),
            "methode": "oracle_sql_v2",
            "llm_calls": _llm_count,
            "sql_calls": _sql_count,
            "couverture_sans_llm": round(total_sans_llm / total, 4) if total else 0,
            "par_niveau": {k: {"reussis": v["ok"], "total": v["total"],
                               "taux": round(v["ok"]/v["total"], 4)}
                           for k, v in par_niv.items()},
            "tests_schema": tests_schema,
            "resultats": [{
                "question": r["question"], "categorie": r["categorie"],
                "niveau": r["niveau_attendu"], "succes": r["succes"],
                "duree_ms": round(r["duree_ms"], 1),
                "methode_eval": r["methode_eval"],
                "reponse": r["reponse"][:200]
            } for r in resultats],
        }, f, ensure_ascii=False, indent=2)

    html_path = os.path.join("eval_results", "rapport_eval_employe.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_generer_html(resultats, tests_schema, date_exec, _llm_count, _sql_count))

    print(f"\n{GRAS}  FICHIERS GÉNÉRÉS :{RESET}")
    print(f"  📄 {html_path}")
    print(f"  📊 {json_path}")
    print(f"\n{'═'*60}\n")


if __name__ == "__main__":
    main()