# ════════════════════════════════════════════════════════════
# EMAIL TEMPLATES — Cas 1 : template fixe, zéro LLM
# ════════════════════════════════════════════════════════════

def generer_email_html(client: dict) -> str:
    """
    Génère un email HTML personnalisé à partir des données du client.
    Zéro LLM — uniquement des variables injectées dans un template fixe.

    Paramètre :
        client : dict retourné par detecter_surconsommations()
        {
            nom_client, mois_actuel, conso_actuelle,
            mois_precedent, conso_precedente,
            variation_pct, unite, montant_ttc, usage, agence
        }

    Retourne : str (HTML complet de l'email)
    """

    nom          = client.get("nom_client", "Client")
    mois_actuel  = client.get("mois_actuel", "")
    mois_prec    = client.get("mois_precedent", "")
    conso_act    = client.get("conso_actuelle", 0)
    conso_prec   = client.get("conso_precedente", 0)
    variation    = client.get("variation_pct", 0)
    unite        = client.get("unite", "")
    montant      = client.get("montant_ttc", 0)
    usage        = client.get("usage", "")
    agence       = client.get("agence", "")

    # Couleur selon niveau de variation
    if variation >= 80:
        couleur_badge = "#dc2626"   # rouge — critique
        niveau        = "critique"
    elif variation >= 50:
        couleur_badge = "#f97316"   # orange — élevée
        niveau        = "élevée"
    else:
        couleur_badge = "#eab308"   # jaune — modérée
        niveau        = "modérée"

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alerte Surconsommation — SRM Souss-Massa</title>
</head>
<body style="margin:0; padding:0; background:#f4f4f4; font-family: Arial, sans-serif;">

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4; padding: 30px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0"
                       style="background:#ffffff; border-radius:8px;
                              box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow:hidden;">

                    <!-- EN-TÊTE -->
                    <tr>
                        <td style="background:#1e3a5f; padding: 24px 32px;">
                            <h1 style="margin:0; color:#ffffff; font-size:20px;">
                                SRM Souss-Massa
                            </h1>
                            <p style="margin:4px 0 0; color:#a0b4c8; font-size:13px;">
                                Société Régionale Multiservices
                            </p>
                        </td>
                    </tr>

                    <!-- BADGE ALERTE -->
                    <tr>
                        <td style="padding: 28px 32px 0;">
                            <span style="
                                background:{couleur_badge};
                                color:#ffffff;
                                padding: 5px 14px;
                                border-radius: 20px;
                                font-size: 12px;
                                font-weight: bold;
                                text-transform: uppercase;
                                letter-spacing: 0.5px;">
                                ⚠ Alerte surconsommation — niveau {niveau}
                            </span>
                        </td>
                    </tr>

                    <!-- CORPS -->
                    <tr>
                        <td style="padding: 24px 32px;">
                            <p style="font-size:15px; color:#333; margin:0 0 16px;">
                                Bonjour <strong>{nom}</strong>,
                            </p>
                            <p style="font-size:15px; color:#333; line-height:1.6; margin:0 0 24px;">
                                Nous avons détecté une augmentation inhabituelle de votre consommation
                                <strong>{usage.lower()}</strong> sur votre compte géré par
                                l'agence <strong>{agence}</strong>.
                            </p>

                            <!-- TABLEAU COMPARATIF -->
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="background:#f8fafc; border-radius:8px;
                                          border:1px solid #e2e8f0; margin-bottom:24px;">
                                <tr style="background:#e2e8f0;">
                                    <td style="padding:10px 16px; font-size:13px;
                                               font-weight:bold; color:#475569;">
                                        Période
                                    </td>
                                    <td style="padding:10px 16px; font-size:13px;
                                               font-weight:bold; color:#475569; text-align:right;">
                                        Consommation
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:12px 16px; font-size:14px; color:#334155;">
                                        {mois_prec}
                                    </td>
                                    <td style="padding:12px 16px; font-size:14px;
                                               color:#334155; text-align:right;">
                                        {conso_prec} {unite}
                                    </td>
                                </tr>
                                <tr style="background:#fff7ed; border-top:1px solid #fed7aa;">
                                    <td style="padding:12px 16px; font-size:14px;
                                               color:#c2410c; font-weight:bold;">
                                        {mois_actuel} ← mois actuel
                                    </td>
                                    <td style="padding:12px 16px; font-size:14px;
                                               color:#c2410c; font-weight:bold; text-align:right;">
                                        {conso_act} {unite}
                                    </td>
                                </tr>
                                <tr style="background:#fef2f2; border-top:1px solid #fecaca;">
                                    <td style="padding:10px 16px; font-size:13px; color:#991b1b;">
                                        Augmentation détectée
                                    </td>
                                    <td style="padding:10px 16px; font-size:13px;
                                               color:#991b1b; text-align:right; font-weight:bold;">
                                        +{variation}%
                                    </td>
                                </tr>
                            </table>

                            <!-- MONTANT -->
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="background:#eff6ff; border-radius:8px;
                                          border:1px solid #bfdbfe; margin-bottom:24px;">
                                <tr>
                                    <td style="padding:14px 16px; font-size:14px; color:#1e40af;">
                                        💳 Montant de votre dernière facture
                                    </td>
                                    <td style="padding:14px 16px; font-size:16px;
                                               color:#1e40af; font-weight:bold; text-align:right;">
                                        {montant} MAD
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size:14px; color:#555; line-height:1.7; margin:0 0 16px;">
                                Nous vous invitons à vérifier vos installations et à contacter
                                votre agence SRM si vous constatez une anomalie.
                            </p>
                            <p style="font-size:14px; color:#555; line-height:1.7; margin:0;">
                                Pour toute question, vous pouvez nous contacter directement
                                ou consulter votre espace client.
                            </p>
                        </td>
                    </tr>

                    <!-- PIED DE PAGE -->
                    <tr>
                        <td style="background:#f1f5f9; padding:20px 32px;
                                   border-top:1px solid #e2e8f0;">
                            <p style="margin:0; font-size:12px; color:#94a3b8; text-align:center;">
                                SRM Souss-Massa — Ce message est envoyé automatiquement,
                                merci de ne pas y répondre directement.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>

</body>
</html>
"""
    return html


def generer_sujet_email(client: dict) -> str:
    """
    Génère le sujet de l'email selon le niveau de variation.
    """
    variation = client.get("variation_pct", 0)
    mois      = client.get("mois_actuel", "")

    if variation >= 80:
        return f"⚠ Alerte critique : surconsommation détectée — {mois}"
    elif variation >= 50:
        return f"⚠ Alerte : augmentation élevée de votre consommation — {mois}"
    else:
        return f"Information : augmentation de votre consommation — {mois}"