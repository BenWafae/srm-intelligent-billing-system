# ════════════════════════════════════════════════════════════
# EMAIL TEMPLATES — Cas 1 : template fixe, zéro LLM
# ════════════════════════════════════════════════════════════

def generer_email_html(client: dict, analyse_ia: str = None) -> str:

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

    if variation >= 80:
        couleur_badge = "#dc2626"
        niveau        = "critique"
    elif variation >= 50:
        couleur_badge = "#f97316"
        niveau        = "élevée"
    else:
        couleur_badge = "#eab308"
        niveau        = "modérée"

    bloc_analyse = ""
    if analyse_ia:
        bloc_analyse = f"""
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="background:#f0fdf4; border-radius:8px;
                                          border:1px solid #bbf7d0; margin-bottom:24px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <p style="margin:0 0 6px; font-size:12px; font-weight:bold;
                                                  color:#15803d; text-transform:uppercase;
                                                  letter-spacing:0.5px;">
                                            💡 Analyse personnalisée
                                        </p>
                                        <p style="margin:0; font-size:14px; color:#166534;
                                                  line-height:1.7;">
                                            {analyse_ia}
                                        </p>
                                    </td>
                                </tr>
                            </table>"""

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
                            <h1 style="margin:0; color:#ffffff; font-size:20px;">SRM Souss-Massa</h1>
                            <p style="margin:4px 0 0; color:#a0b4c8; font-size:13px;">
                                Société Régionale Multiservices
                            </p>
                        </td>
                    </tr>

                    <!-- BADGE ALERTE -->
                    <tr>
                        <td style="padding: 28px 32px 0;">
                            <span style="background:{couleur_badge}; color:#ffffff;
                                         padding: 5px 14px; border-radius: 20px;
                                         font-size: 12px; font-weight: bold;
                                         text-transform: uppercase; letter-spacing: 0.5px;">
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
                                               font-weight:bold; color:#475569;">Période</td>
                                    <td style="padding:10px 16px; font-size:13px;
                                               font-weight:bold; color:#475569;
                                               text-align:right;">Consommation</td>
                                </tr>
                                <tr>
                                    <td style="padding:12px 16px; font-size:14px;
                                               color:#334155;">{mois_prec}</td>
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
                                               color:#c2410c; font-weight:bold;
                                               text-align:right;">{conso_act} {unite}</td>
                                </tr>
                                <tr style="background:#fef2f2; border-top:1px solid #fecaca;">
                                    <td style="padding:10px 16px; font-size:13px;
                                               color:#991b1b;">Augmentation détectée</td>
                                    <td style="padding:10px 16px; font-size:13px;
                                               color:#991b1b; text-align:right;
                                               font-weight:bold;">+{variation}%</td>
                                </tr>
                            </table>

                            <!-- MONTANT -->
                            <table width="100%" cellpadding="0" cellspacing="0"
                                   style="background:#eff6ff; border-radius:8px;
                                          border:1px solid #bfdbfe; margin-bottom:24px;">
                                <tr>
                                    <td style="padding:14px 16px; font-size:14px;
                                               color:#1e40af;">
                                        💳 Montant de votre dernière facture
                                    </td>
                                    <td style="padding:14px 16px; font-size:16px;
                                               color:#1e40af; font-weight:bold;
                                               text-align:right;">{montant} MAD</td>
                                </tr>
                            </table>

                            {bloc_analyse}

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
</html>"""
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
# ════════════════════════════════════════════════════════════
# ENRICHISSEMENT IA — Analyse contextuelle par Mistral (Ollama)
# ════════════════════════════════════════════════════════════

def generer_analyse_llm(client: dict) -> str:
    """
    Génère 2 phrases d'analyse contextuelle via Mistral local (Ollama).
    Le LLM reçoit uniquement les données déjà calculées par Python.
    Il n'intervient PAS dans les chiffres — uniquement l'interprétation.

    Retourne : str (2 phrases, texte brut)
    Fallback  : "" si erreur — l'email part quand même sans analyse
    """
    from rag.intent import _appeler_llm

    nom          = client.get("nom_client", "le client")
    usage        = client.get("usage", "")
    mois_actuel  = client.get("mois_actuel", "")
    variation    = client.get("variation_pct", 0)
    unite        = client.get("unite", "")
    conso_act    = client.get("conso_actuelle", 0)
    conso_prec   = client.get("conso_precedente", 0)
    mois_prec    = client.get("mois_precedent", "")
    agence       = client.get("agence", "")
    type_service = client.get("type_service", "")

    # Déterminer le type de service si non fourni
    if not type_service:
        type_service = "eau" if unite == "m³" else "électricité"

    # Adapter les exemples selon l'usage réel
    if "PROFESSIONNEL" in usage.upper() or "COMMERCIAL" in usage.upper():
        conseil_exemple = """Exemple pour usage PROFESSIONNEL :
"Cette augmentation de votre consommation peut s'expliquer par une activité accrue de votre établissement pendant cette période. Nous vous recommandons de vérifier l'état de vos équipements et d'optimiser vos plages horaires d'utilisation." """
    elif "AGRICOLE" in usage.upper():
        conseil_exemple = """Exemple pour usage AGRICOLE :
"Cette hausse est cohérente avec les besoins d'irrigation pendant la saison estivale dans la région Souss-Massa. Nous vous conseillons de programmer votre pompage pendant les heures creuses et de vérifier l'étanchéité de votre réseau." """
    elif "DOMESTIQUE" in usage.upper():
        conseil_exemple = """Exemple pour usage DOMESTIQUE :
"Cette augmentation peut être liée à l'utilisation de la climatisation ou du chauffage selon la saison. Pensez à vérifier vos appareils électriques et à adopter des gestes simples pour réduire votre consommation." """
    else:
        conseil_exemple = ""

    prompt = f"""Tu es un assistant expert en efficacité énergétique pour SRM Souss-Massa (région d'Agadir, Maroc).

⚠️ RÈGLES ABSOLUMENT STRICTES À RESPECTER ⚠️
1. NE JAMAIS inventer ou modifier l'USAGE du client
2. L'usage EXACT du client est : "{usage}"
3. Le type de service EXACT est : "{type_service}"
4. Si usage = PROFESSIONNEL → ne JAMAIS parler d'agriculture, de ferme, d'irrigation
5. Si usage = PROFESSIONNEL → parler de son activité commerciale/professionnelle
6. Si type_service = eau → parler de consommation D'EAU, pas d'électricité
7. Si type_service = électricité → parler de consommation ÉLECTRIQUE, pas d'eau
8. NE PAS mentionner les chiffres exacts (ils sont déjà dans le tableau)

DONNÉES RÉELLES DU CLIENT (à utiliser pour le contexte UNIQUEMENT) :
- Nom : {nom}
- Usage RÉEL : {usage}
- Type service RÉEL : {type_service}
- Mois concerné : {mois_actuel}
- Saison approximative : {"été" if mois_actuel in ["Juin", "Juillet", "Août", "Septembre"] else ("hiver" if mois_actuel in ["Décembre", "Janvier", "Février"] else "printemps/automne")}
- Augmentation : +{variation}%
- Agence : {agence}

{conseil_exemple}

Ta mission : rédige EXACTEMENT 2 phrases en français, SANS introduire d'erreur.

Phrase 1 : Une explication plausible de cette hausse, adaptée STRICTEMENT à :
   - L'usage réel : "{usage}"
   - Le type service réel : "{type_service}"
   - La saison du mois concerné

Phrase 2 : Un conseil pratique et bienveillant adapté à ce type de client.

Contraintes FINALES IMPORTANTES :
- Rédige les 2 phrases à la suite, SÉPARÉES PAR UN ESPACE, sans les préfixer par "Phrase 1 :" ou "Phrase 2 :"
- Ne mets aucun numéro, aucun tiret, aucun marqueur avant les phrases
- Commence directement par la première phrase
- Termine la première phrase par un point, puis espace, puis la deuxième phrase
- EXACTEMENT 2 phrases
- Pas de "Bonjour", pas de "Cordialement", pas de signature
- Pas de markdown, pas d'émoticônes
- Ton professionnel, précis et bienveillant
- Soigne l'orthographe : les apostrophes doivent être correctement placées (l'activité, d'eau, l'eau, d'énergie)

RÉPONDS UNIQUEMENT AVEC LES 2 PHRASES, RIEN D'AUTRE."""

    try:
        analyse = _appeler_llm(prompt)
        
        # Nettoyage renforcé
        analyse = analyse.replace("1.", "").replace("2.", "")
        analyse = analyse.replace("Phrase 1 :", "").replace("Phrase 2 :", "")
        analyse = analyse.replace("Phrase 1", "").replace("Phrase 2", "")
        analyse = analyse.replace("phrase 1 :", "").replace("phrase 2 :", "")
        analyse = analyse.replace("Première phrase :", "").replace("Deuxième phrase :", "")
        analyse = analyse.strip()
        
        # Supprimer les guillemets superflus
        analyse = analyse.strip('"').strip("'")
        
        # Correction automatique des apostrophes mal placées
        corrections = {
            "lactivité": "l'activité",
            "lactivite": "l'activité",
            "deau": "d'eau",
            "leau": "l'eau",
            "denergie": "d'énergie",
            "denergie": "d'énergie",
            "lenergie": "l'énergie",
            "lentreprise": "l'entreprise",
            "lefficacite": "l'efficacité",
            "lefficacité": "l'efficacité",
            "dun": "d'un",
            "une eau": "d'eau",
        }
        
        for mauvais, bon in corrections.items():
            analyse = analyse.replace(mauvais, bon)
        
        # Nettoyer les espaces multiples
        analyse = " ".join(analyse.split())
        
        # Validation simple : si l'analyse contient "agricole" mais usage != AGRICOLE → rejeter
        if "agricole" in analyse.lower() and "AGRICOLE" not in usage.upper():
            print(f"[LLM] ⚠️ Hallucination détectée (agricole vs {usage}) - analyse ignorée")
            return ""
        
        if ("électrique" in analyse.lower() or "electricite" in analyse.lower()) and type_service == "eau":
            print(f"[LLM] ⚠️ Hallucination détectée (électrique vs eau) - analyse ignorée")
            return ""
        
        if ("eau" in analyse.lower() or "hydrique" in analyse.lower()) and type_service == "électricité":
            print(f"[LLM] ⚠️ Hallucination détectée (eau vs électricité) - analyse ignorée")
            return ""
        
        # Vérifier qu'il y a bien 2 phrases (au moins 2 points ou points d'exclamation)
        nb_phrases = analyse.count('.') + analyse.count('!')
        if nb_phrases < 2:
            print(f"[LLM] ⚠️ Moins de 2 phrases détectées ({nb_phrases}) - analyse ignorée")
            return ""
        
        # Capitaliser la première lettre
        if analyse and len(analyse) > 0:
            analyse = analyse[0].upper() + analyse[1:]
        
        return analyse
        
    except Exception as e:
        print(f"[LLM] Erreur génération analyse : {e}")
        return ""