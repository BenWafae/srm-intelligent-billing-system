import pandas as pd

ONGLET_A_IGNORER = "Résumé"

# Renommage : nom exact dans Excel → nom propre pour la BD
RENOMMAGE_COLONNES = {
    "Agence": "agence",
    "Editée le": "date_edition",
    "Période début": "periode_debut",
    "Période fin": "periode_fin",
    "N° Contrat": "numero_contrat",
    "N° Client": "numero_client",
    "N° Compteur": "numero_compteur",
    "Usage": "usage",
    "Client": "nom_client",
    "Adresse": "adresse",
    "Type service": "type_service",
    "Consommation": "consommation",
    "Unité": "unite",
    "Montant TTC (Dhs)": "montant_ttc",
    "Date limite paiement": "date_limite_paiement",
    "Alerte": "alerte"
}

def lire_excel(chemin_excel: str) -> list[dict]:

    xl = pd.ExcelFile(chemin_excel)
    tous_les_mois = []

    for nom_onglet in xl.sheet_names:

        if nom_onglet == ONGLET_A_IGNORER:
            print(f"  ⏭️  Onglet '{nom_onglet}' ignoré.")
            continue

        df = pd.read_excel(chemin_excel, sheet_name=nom_onglet)

        # Renommer avec les noms propres AVANT de nettoyer
        df = df.rename(columns=RENOMMAGE_COLONNES)

        df = df.fillna("")
        df["mois_source"] = nom_onglet

        tous_les_mois.append(df)
        print(f"  ✅ '{nom_onglet}' : {len(df)} lignes lues.")

    df_final = pd.concat(tous_les_mois, ignore_index=True)
    print(f"\nTotal : {len(df_final)} lignes combinées.")

    return df_final.to_dict(orient="records")


# -------- TEST --------
if __name__ == "__main__":
    import json
    lignes = lire_excel("data/factures_srm.xlsx")
    print("\nColonnes finales :")
    for col in lignes[0].keys():
        print(f"  - {col}")
    print("\nPremière ligne :")
    print(json.dumps(lignes[0], indent=2, ensure_ascii=False, default=str))