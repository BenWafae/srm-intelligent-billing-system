# ════════════════════════════════════════════
# CHUNKS RAG — BASE DE CONNAISSANCE SRM
# Découpée par thème pour retrieval sémantique
# ════════════════════════════════════════════

SRM_CHUNKS = [
    {
        "id": "identite_srm",
        "theme": "Qui est SRM, historique, territoire, creation",
        "texte": """SRM Souss-Massa SA créée le 15 octobre 2024.
Opérateur unique distribution eau potable, électricité, assainissement liquide région Souss-Massa.
Territoire : préfectures Agadir Ida-Outanane, Inezgane Ait Melloul, provinces Chtouka Ait Baha, Tata, Tiznit, Taroudant.
175 communes, 3,06 millions habitants."""
    },
    {
        "id": "contact_srm",
        "theme": "Contact SRM, telephone, email, adresse, agence, joindre",
        "texte": """Contact SRM Souss-Massa :
Siège : Rue 18 Novembre, Quartier Industriel, AGADIR
Centre d'appels : 08 02 03 12 12
Téléphone siège : 05 28 82 96 00 (8h00 à 16h30)
Email : Contact@srm-sm.ma"""
    },
    {
        "id": "abonnement_particulier",
        "theme": "Abonnement eau electricite particulier personne physique documents s abonner sabonner inscription contrat devenir client ouvrir compte que faire comment abonnement",
        "texte": """ABONNEMENT EAU ET ELECTRICITE (particulier) :
Variantes : s abonner, sabonner, devenir client SRM, ouvrir un abonnement, comment faire un abonnement, que faire pour abonnement, documents abonnement eau, documents abonnement electricite.

Pour vous ABONNER à l'EAU ou à l'ÉLECTRICITÉ (logement déjà raccordé) :
1. Formulaire de demande d'abonnement signé (disponible en agence ou sur e-agence)
2. Photocopie pièce d'identité : CIN, carte de séjour ou passeport
3. Justificatif droit de jouissance :
   - Propriétaire : titre de propriété (titre foncier, Moulkia, attestation notaire)
   - Locataire : contrat de bail, certificat de résidence, ou autorisation propriétaire légalisée
4. Procuration légalisée si héritiers, absence propriétaire, copropriétaires, colocataires

Ceci concerne un LOGEMENT DEJA RACCORDE au réseau (pas un nouveau branchement).
Pour électricité uniquement : ajouter permis d'habiter + certificat de garantie disjoncteur différentiel."""
    },
    {
        "id": "abonnement_societe",
        "theme": "Abonnement societe entreprise personne morale documents",
        "texte": """Abonnement personne morale (société) :
1. Formulaire signé par gérant ou représentant
2. Copie CIN du gérant
3. Autorisation d'exercer délivrée par Autorités Compétentes
4. Extrait registre du commerce, statuts sociaux, attestation ICE
5. Acte de propriété OU contrat de bail
Pour électricité : certificat de conformité + certificat de garantie disjoncteur différentiel."""
    },
    {
        "id": "abonnement_association",
        "theme": "Abonnement association syndic cooperative documents",
        "texte": """Abonnement associations, syndics, coopératives :
1. Formulaire signé par président ou représentant
2. Copie CIN du président
3. PV de l'assemblée générale
4. Statuts de l'association ou règlement de copropriété
5. Reçu du dossier déposé aux Autorités Compétentes
6. Acte de propriété OU contrat de bail
Pour électricité : permis d'habiter ou certificat de conformité + certificat de garantie disjoncteur différentiel."""
    },
    {
        "id": "branchement",
        "theme": "Branchement nouveau raccordement eau electricite construction documents pieces",
        "texte": """BRANCHEMENT NOUVEAU (construction neuve non encore raccordee) :
Ceci concerne une CONSTRUCTION NEUVE qui n'est pas encore raccordée au réseau.
Pour un NOUVEAU BRANCHEMENT électricité ou eau :
1. Formulaire de demande de branchement
2. Photocopie pièce d'identité
3. Copie titre de propriété
4. Plans de construction approuvés : distribution, masse, façades
5. Attestation architecte ou topographe agréé
6. Copie autorisation de construction
7. Autorisation spéciale si pas d'autorisation de construction
8. Engagement paiement participation réseau assainissement si zone non desservie
Demande simultanée eau + électricité + assainissement : un seul exemplaire des documents."""
    },
    {
        "id": "recrutement",
        "theme": "Recrutement emploi travail poste offre ingenieur cadre technicien",
        "texte": """RECRUTEMENT SRM SM — EMPLOI PERMANENT :
Pour commencer un TRAVAIL à SRM, candidatures UNIQUEMENT en ligne :
Cadres et Ingénieurs (Bac+5) : https://www.mafoamanagement.com/e-concours/srm-sm-2025/
Agents de Maîtrise (Bac+2) : https://econcours.brainman.ma/cmp/SRM_SM_2025
Ne pas envoyer CV par email ni se présenter en agence pour un emploi."""
    },
    {
        "id": "stage",
        "theme": "Stage stagiaire etudiant convention demande stage academique",
        "texte": """STAGE ACADEMIQUE SRM (étudiants uniquement) :
Pour commencer un STAGE à SRM, envoyer par email à stages@srm-sm.ma :
1. Copie CNI
2. CV avec téléphone et email
3. Convention de stage signée et cachetée par l'école
4. Demande de stage sur en-tête de l'école avec période précisée
5. Attestation d'assurance
Aucune demande acceptée sur place. Stage réservé aux étudiants avec convention d'école."""
    },
    {
        "id": "economie_conseils",
        "theme": "Economiser eau electricite conseils reduire consommation gaspillage astuces",
        "texte": """CONSEILS POUR ECONOMISER L'EAU (ne concerne pas l'abonnement) :
- Réparer immédiatement les fuites
- Douches courtes plutôt que bains
- Fermer robinet pendant brossage dents
- Arroser plantes le soir ou tôt le matin
- Utiliser équipements économiseurs d'eau
- Signaler fuites réseau public à SRM

CONSEILS POUR ECONOMISER L'ELECTRICITE :
- Éteindre appareils plutôt que laisser en veille
- Utiliser ampoules LED
- Éviter gros appareils aux heures de pointe (18h-22h)
- Bien isoler logement
- Utiliser chauffe-eau solaire si possible
- Débrancher chargeurs quand inutilisés"""
    },
]