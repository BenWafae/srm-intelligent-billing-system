# test_validation_sql.py
# ════════════════════════════════════════════════════════════
# Tests unitaires — validation du schéma SQL
# Vérifie que valider_colonnes_sql() accepte les colonnes
# réelles de la base et rejette les colonnes inexistantes.
# ════════════════════════════════════════════════════════════

from src.rag.dispatcher import valider_colonnes_sql

print("=" * 55)
print("Tests de validation du schéma SQL — factures_excel")
print("=" * 55)

# ════════════════════════════════════════════════════════════
# CAS ACCEPTÉS — colonnes réelles de la base
# ════════════════════════════════════════════════════════════

cas_acceptes = [
    (
        "SELECT nom_client, SUM(consommation) FROM factures_excel GROUP BY nom_client",
        "colonnes réelles : nom_client, consommation"
    ),
    (
        "SELECT nom_client, agence FROM factures_excel WHERE LOWER(agence) LIKE '%agadir%'",
        "filtre sur agence"
    ),
    (
        "SELECT nom_client, montant_ttc FROM factures_excel ORDER BY montant_ttc DESC",
        "tri sur montant_ttc"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE mois_source LIKE '%Janvier%'",
        "filtre sur mois_source"
    ),
    (
        "SELECT nom_client, numero_compteur FROM factures_excel WHERE nom_client LIKE '%Fatima%'",
        "filtre sur nom_client"
    ),
]

print("\n✅ CAS ACCEPTÉS (colonnes réelles) :")
for sql, description in cas_acceptes:
    resultat = valider_colonnes_sql(sql)
    statut = "PASS ✅" if resultat == True else "FAIL ❌"
    print(f"  {statut} — {description}")
    assert resultat == True, f"ÉCHEC : colonnes réelles rejetées — {description}"

# ════════════════════════════════════════════════════════════
# CAS REJETÉS — colonnes inexistantes dans la base
# ════════════════════════════════════════════════════════════

cas_rejetes = [
    (
        "SELECT nom_client FROM factures_excel WHERE score = 100",
        "colonne inexistante : score"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE telephone = '0600000000'",
        "colonne inexistante : telephone"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE email = 'test@test.com'",
        "colonne inexistante : email"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE code_postal = '80000'",
        "colonne inexistante : code_postal"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE cin = 'AB123456'",
        "colonne inexistante : cin"
    ),
    (
        "SELECT nom_client FROM factures_excel ORDER BY rang DESC",
        "colonne inexistante : rang"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE statut = 'actif'",
        "colonne inexistante : statut"
    ),
    (
        "SELECT nom_client FROM factures_excel WHERE solde > 0",
        "colonne inexistante : solde"
    ),
]

print("\n❌ CAS REJETÉS (colonnes inexistantes) :")
for sql, description in cas_rejetes:
    resultat = valider_colonnes_sql(sql)
    statut = "PASS ✅" if resultat == False else "FAIL ❌"
    print(f"  {statut} — {description}")
    assert resultat == False, f"ÉCHEC : colonne inexistante acceptée — {description}"

# ════════════════════════════════════════════════════════════
# RÉSULTAT FINAL
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 55)
print("✅ Tous les tests de validation schéma passent.")
print("   La fonction valider_colonnes_sql() fonctionne")
print("   correctement pour protéger le système contre")
print("   les colonnes SQL hallucInées par le LLM.")
print("=" * 55)