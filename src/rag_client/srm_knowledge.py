# ════════════════════════════════════════════
# BASE DE CONNAISSANCE SRM — DONNÉES OFFICIELLES
# Source : site officiel SRM Souss-Massa
# NE PAS MODIFIER sans vérification officielle
# ════════════════════════════════════════════

SRM_KNOWLEDGE = """
## QUI EST SRM ?
La Société Régionale Multiservices Souss-Massa SA (SRM SM) a été créée le 15 octobre 2024.
C'est l'opérateur unique qui assure la distribution de l'eau potable, de l'électricité,
et de l'assainissement liquide dans la région Souss-Massa.
Son territoire couvre : les préfectures d'Agadir Ida-Outanane et d'Inezgane Ait Melloul,
ainsi que les provinces de Chtouka Ait Baha, Tata, Tiznit et Taroudant —
soit 175 communes et environ 3,06 millions d'habitants.

## CONTACT SRM
- Siège : Rue 18 Novembre, Quartier Industriel, AGADIR
- Centre d'appels : 08 02 03 12 12
- Téléphone siège : 05 28 82 96 00 (de 8h00 à 16h30)
- Email : Contact@srm-sm.ma

## ABONNEMENT — PERSONNES PHYSIQUES (particuliers)
Documents à fournir :
1. Formulaire de demande d'abonnement signé (disponible en agence ou sur e-agence)
2. Photocopie pièce d'identité : CIN, Carte de séjour ou passeport
3. Justificatif du droit de jouissance :
   - Propriétaire : copie du titre de propriété (titre foncier, Moulkia, attestation notaire)
   - Locataire : contrat de bail, certificat de résidence, ou autorisation du propriétaire légalisée
4. Procuration légalisée si : héritiers indivisaires, absence du propriétaire, copropriétaires, colocataires

En plus, pour un branchement ÉLECTRICITÉ uniquement :
- Copie du permis d'habiter ou certificat de conformité
- Certificat de garantie du disjoncteur différentiel (conforme aux normes)

## ABONNEMENT — PERSONNES MORALES (sociétés)
Documents à fournir :
1. Formulaire de demande signé par le gérant ou représentant
2. Copie CIN du gérant (ou passeport/carte de séjour)
3. Autorisation d'exercer délivrée par les Autorités Compétentes
4. Extrait du registre du commerce, statuts sociaux, attestation ICE
5. Acte de propriété OU contrat de bail du local

En plus, pour un branchement ÉLECTRICITÉ :
- Certificat de conformité
- Certificat de garantie du disjoncteur différentiel

## ABONNEMENT — ASSOCIATIONS, SYNDICS, COOPÉRATIVES
Documents à fournir :
1. Formulaire signé par le président ou représentant
2. Copie CIN du président
3. PV de l'assemblée générale
4. Statuts de l'association / règlement de copropriété
5. Reçu du dossier déposé aux Autorités Compétentes
6. Acte de propriété OU contrat de bail

En plus, pour un branchement ÉLECTRICITÉ :
- Permis d'habiter ou certificat de conformité
- Certificat de garantie du disjoncteur différentiel

## BRANCHEMENT — PIÈCES COMMUNES (eau + électricité)
Pour toute demande de branchement :
1. Formulaire de demande de branchement (en agence ou sur e-agence)
2. Photocopie pièce d'identité (CIN, carte de séjour, passeport)
3. Copie du titre de propriété
4. Plans de construction approuvés : plan de distribution, plan de masse, plan de façades
5. Attestation d'architecte ou topographe agréé (surfaces planchers, niveaux, consistance)
6. Copie de l'autorisation de construction
7. Autorisation spéciale si pas d'autorisation de construction
8. Engagement de paiement de participation au réseau d'assainissement si zone non desservie

Note : En cas de demande simultanée eau + électricité + assainissement,
un seul exemplaire des documents est requis.

## DISPOSITIONS PARTICULIÈRES
- Fonctions libérales : autorisations d'exercice selon la fonction (Autorités Compétentes)
- Logements de fonction : l'attestation administrative remplace le titre de propriété et le permis d'habiter

## RECRUTEMENT — TRAVAILLER À SRM (EMPLOI PERMANENT)
Tu veux travailler à SRM SM en tant qu'employé permanent ?
SRM SM recrute dans deux catégories :

Cadres et Ingénieurs (Bac+5) — domaines : Finance, Comptabilité, RH,
Génie électrique, Génie Civil, Hydraulique, Génie logiciel, Réseaux,
Sécurité informatique, Commerce/Marketing, SIG, Génie Industriel.
Candidature en ligne : https://www.mafoamanagement.com/e-concours/srm-sm-2025/

Agents de Maîtrise (Bac+2) — domaines : Développement informatique,
Gestion/Comptabilité, Hydraulique/Génie Civil, Électricité/Électromécanique, RH.
Candidature en ligne : https://econcours.brainman.ma/cmp/SRM_SM_2025

IMPORTANT : Les candidatures emploi se font UNIQUEMENT en ligne via les liens ci-dessus.
Ne pas envoyer de CV par email ni se présenter en agence pour un emploi.

## STAGE À SRM (ÉTUDIANTS UNIQUEMENT)
Tu es étudiant et tu cherches un stage académique dans le cadre de tes études ?
C'est différent d'un emploi permanent.
Documents à envoyer UNIQUEMENT par email à stages@srm-sm.ma :
1. Copie CNI
2. CV avec téléphone et email
3. Convention de stage signée et cachetée par l'école
4. Demande de stage sur en-tête de l'école avec période précisée
5. Attestation d'assurance

IMPORTANT : Aucune demande de stage ne sera acceptée sur place.
Le stage est réservé aux étudiants avec convention d'école.
Ne pas confondre stage étudiant et offre d'emploi permanent.

## SENSIBILISATION — ÉCONOMISER L'EAU
- Réparer immédiatement les fuites (un robinet qui goutte peut gaspiller énormément)
- Prendre des douches courtes plutôt que des bains
- Fermer le robinet pendant le brossage des dents
- Arroser les plantes le soir ou tôt le matin pour éviter l'évaporation
- Utiliser des équipements économiseurs d'eau
- Signaler les fuites sur le réseau public à la SRM

## SENSIBILISATION — ÉCONOMISER L'ÉLECTRICITÉ
- Éteindre les appareils plutôt que de les laisser en veille
- Utiliser des ampoules LED (consomment beaucoup moins)
- Éviter de faire tourner les gros appareils aux heures de pointe (18h-22h)
- Bien isoler son logement (évite de chauffer ou climatiser excessivement)
- Utiliser un chauffe-eau solaire si possible
- Débrancher les chargeurs de téléphone quand ils ne servent pas
"""

# ════════════════════════════════════════════
# TOKENS — détection questions générales SRM
# ════════════════════════════════════════════

TOKENS_GENERAL_SRM = [
    # Identité SRM
    "srm", "c est quoi srm", "que veut dire srm", "qui est srm",
    "historique srm", "srm souss massa", "societe srm",
    "srm sm", "srm agadir", "société regionale",
    "multiservices", "souss massa", "srm souss massa ",

    # Abonnement général
    "abonnement", "s abonner", "comment s abonner","commencer un abonnement ",
    "je veux m abonner", "je veux abonner",
    "new abonnement", "nouvel abonnement",
    "ouvrir un compte", "creer un abonnement",
    "comment faire un abonnement ","comment ouvrir abonnement","abonement",

    # Documents abonnement / branchement
    "documents", "document demande", "papiers",
    "pièces a fournir", "pieces a fournir",
    "les documents", "quels documents",
    "wach khasso", "chno ndiro","qui sont les document que je dois utulise","les document pour sabonner"
    "dossier abonnement", "dossier branchement","mon dossier quoi contenir pour sabonner","pieces a donner pour faire mon abonnemnt "

    # Branchement
    "branchement", "nouveau branchement",
    "branchement eau", "branchement electricite",
    "branchement électricité", "raccordement",
    "comment brancher", "kif n9dir nfot",

    # Procédure / démarche
    "procedure", "procédure", "demarche","procedur"
    "comment faire", 
    "etapes", "étapes",

    # Contact / agence
    "contact srm", "telephone srm", "appeler srm",
    "email srm", "adresse srm", "agence srm",
    "numero srm", "joindre srm",
    "centre appels", "centre d appels",
    "contacter srm numero ou email"
     "numero srm", "joindre",       
    "comment contacter", "contact"

    # Recrutement / emploi
    "recrutement", "recruter", "emploi srm",
    "travail srm", "offre emploi", "offre d emploi",
    "poste srm", "ingenieur srm", "cadre srm",
    "technicien srm", "bghit nkhdem srm",       # darija

    # Stage
    "stage", "stage srm", "stagiaire",
    "demande stage", "comment faire stage",
    "stages srm", "bghit ndir stage",

    # Économies / sensibilisation
    "economiser", "economise", "gaspiller", "gaspillage",
    "ne pas gaspiller", "sensibilisation",
    "conseils eau", "conseils electricite",
    "reduire facture", "comment payer moins",
    "trop cher", "ne pas gaspiller","comment faire"
    "consommer moins", "astuce",

    # Contrat abonnement
    "contrat abonnement", "contrat srm",
    "contenu contrat", "que contient contrat",
]


def repondre_general(question: str, appeler_llm_func) -> str:
    from rag_client.srm_rag import rechercher_chunks

    contexte = rechercher_chunks(question, top_k=2)

    prompt = f"""Tu es l'assistant officiel de SRM Souss-Massa (distributeur d'eau,
d'électricité et d'assainissement à Agadir, Maroc).

CONTEXTE PERTINENT :
{contexte}

Question du client : {question}

RÈGLES STRICTES :
- Réponds UNIQUEMENT à partir du contexte ci-dessus
- Si la réponse n'est pas dans le contexte, dis exactement :
  "Pour cette information, je vous invite à contacter directement votre agence SRM
   ou appeler le 08 02 03 12 12."
- Réponds en français simple et clair, maximum 6 lignes
- Ne jamais inventer de chiffres, documents ou délais non mentionnés
- IMPORTANT distinction abonnement vs branchement :
  "s'abonner" = logement déjà raccordé → section abonnement uniquement
  "nouveau branchement" = construction neuve → section branchement
- Filtre par service : question eau uniquement → ne pas mentionner exigences électricité, et vice versa
- Numérotation continue (1, 2, 3...) sans redémarrer
- Stage ≠ emploi permanent, ne pas mélanger les deux
- Si la question contient "travail", "emploi", "recrutement", "poste", "travailler" : réponds uniquement emploi permanent, pas de stage
- Si la question contient "stage", "stagiaire", "étudiant" : réponds uniquement stage, pas d'emploi permanent
- "S'abonner" n'a rien à voir avec le nettoyage, lavage ou lessive. Réponds uniquement avec les informations sur l'abonnement
- Ne réponds jamais aux questions sur le nettoyage, lavage, plomberie ou réparation → utilise le message par défaut
- Vérifie que le contexte contient une réponse avant de répondre : si ce n'est pas le cas, n'invente rien
- Maximum 6 lignes, va droit au but

"""
    return appeler_llm_func(prompt)