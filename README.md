<div align="center">

<img src="https://img.shields.io/badge/Python-3.10.9-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/TailwindCSS-Frontend-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white"/>
<img src="https://img.shields.io/badge/Ollama-Mistral_Local-000000?style=for-the-badge"/>
<img src="https://img.shields.io/badge/SQLite-Base_de_données-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
<img src="https://img.shields.io/badge/Architecture-LLM_as_a_Router-7B68EE?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Agent_IA-Autonome_+_Génératif-FF6B35?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Docker-Conteneurisé-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
<img src="https://img.shields.io/badge/Status-En_cours-orange?style=for-the-badge"/>

# 🧾 SRM Intelligent Billing System

> Système Intelligent de Gestion des Factures — SRM Souss-Massa

**Réalisé par : BEN ZHIR Wafa**
Encadrant entreprise : **ZEROUALI Hassan** · Encadrant académique : **AIT BAHA Tarek**
*Stage de fin d'études — EST Guelmim, Filière SDSI 2025–2026*

</div>

---

## Vue d'ensemble

Ce projet est un système complet de gestion intelligente des factures développé pour la **SRM Souss-Massa** dans le cadre d'un stage de fin d'études. Il repose sur une **architecture hybride LLM as a Router** qui garantit des réponses déterministes et fiables en confiant au LLM uniquement la compréhension du langage naturel, tandis que Python et SQL assurent l'intégralité des calculs et du traitement des données.

Le système évolue en trois phases :

| Phase | Statut | Description |
|---|---|---|
| **Tâche 1** | ✅ Terminée | Système complet de gestion et d'analyse des factures avec 3 interfaces dédiées |
| **Tâche 2** | ✅ Terminée | Agent autonome de détection des surconsommations avec alertes email enrichies par IA |
| **Tâche 3** | ✅ Terminée | Conteneurisation Docker complète — déploiement en une seule commande |

---

## Démonstration

### 🎬 Login — Authentification & thème

![Demo Login](screenshots/demo_login.gif)

---

### 👨‍💼 Interface Employé — Assistant multi-clients

![Demo Employé](screenshots/demo_employe.gif)

---

### 👤 Interface Client — Espace personnel

![Demo Client](screenshots/demo_client.gif)

---

### 🔔 Agent Alertes — Détection & envoi email

![Demo Alertes](screenshots/demo_alertes.gif)

---

## Architecture IA — Pipeline Employé SRM

Le pipeline employé repose sur un mécanisme de décision hiérarchique à 4 niveaux. Le LLM joue **uniquement le rôle de routeur sémantique** — il n'intervient jamais dans le calcul ou la génération des réponses finales sur les données.

> Ce paradigme s'inscrit dans le cadre des *LLM augmentés par des outils* (Mialon et al., 2023 ; Schick et al., 2023 — Toolformer).

```
Question utilisateur (Interface Employé)
        │
        ▼
┌─────────────────────────────────────────┐
│  Niveau 0 — Portail de validation       │
│  Champ inexistant dans la base ?        │──→ Message d'indisponibilité immédiat
└─────────────────────────────────────────┘
        │ Non
        ▼
┌─────────────────────────────────────────┐
│  Niveau 1 — Règles Python               │
│  Mot-clé / intent reconnu ?             │──→ Réponse déterministe (sans LLM)
└─────────────────────────────────────────┘
        │ Non
        ▼
┌─────────────────────────────────────────┐
│  Niveau 2 — LLM Router (Mistral)        │
│  Classificateur d'intention uniquement  │──→ Validation en 3 couches avant routage
└─────────────────────────────────────────┘
        │ Intent non reconnu
        ▼
┌─────────────────────────────────────────┐
│  Niveau 3 — Fallback Text-to-SQL        │
│  Génération SQL contrainte              │──→ Whitelist SELECT + Validation schéma
└─────────────────────────────────────────┘
```

---

## Architecture IA — Pipeline Client Connecté

Le pipeline client est distinct du pipeline employé. Il intègre deux mécanismes absents chez l'employé : un **routeur amont General/Personnel** qui distingue les questions sur les factures des questions générales sur la SRM, et un **intent ANALYSE** qui permet des réponses narratives personnalisées combinant données réelles et génération LLM.

```
Question utilisateur (Interface Client)
        │
        ▼
┌─────────────────────────────────────────┐
│  Niveau 0 — Routeur General / Personnel │
│  Détection automatique du contexte      │
│                                         │
│  Question générale SRM ?                │──→ Base de connaissance SRM
│  (abonnement, branchement, stage,       │    (abonnement, contact, recrutement,
│   recrutement, contact...)              │     sensibilisation eau/électricité)
│                                         │
│  Question personnelle sur factures ?    │──→ Pipeline personnel (suite)
└─────────────────────────────────────────┘
        │ Personnelle
        ▼
┌─────────────────────────────────────────┐
│  Niveau 1 — Champ précis du profil      │
│  Usage, agence, compteur, contrat ?     │──→ Réponse ciblée (champ unique)
└─────────────────────────────────────────┘
        │ Non
        ▼
┌─────────────────────────────────────────┐
│  Niveau 2 — Règles Python déterministes │
│  Année / Top N / Comparaison /          │──→ Réponse déterministe filtrée
│  Mois spécifique / Mois relatifs /      │    par numéro de contrat (sans LLM)
│  Max / Min / Somme / Évolution...       │
└─────────────────────────────────────────┘
        │ Non couvert
        ▼
┌─────────────────────────────────────────┐
│  Niveau 3 — Fallback LLM                │
│  • Questions hors règles → LLM Router   │──→ Réponse guidée avec exemples
│  • Intent ANALYSE → LLM narratif        │──→ Réponse personnalisée avec données
│    (données réelles injectées,          │    réelles, comparaison mois actuel
│     zéro hallucination sur les chiffres)│    vs précédent, saisonnalité marocaine
└─────────────────────────────────────────┘
```

---

## Différences entre les deux pipelines

| | Pipeline Employé | Pipeline Client |
|---|---|---|
| **Données accessibles** | Tous les clients (multi-contrats) | Uniquement son contrat (isolation totale) |
| **Routeur amont** | Portail de validation (champs inexistants) | Routeur General / Personnel |
| **Niveau LLM** | Classificateur d'intention strict + validation 3 couches | Classificateur + intent ANALYSE narratif |
| **Fallback final** | Text-to-SQL sécurisé (whitelist + schéma) | LLM narratif avec données réelles injectées |
| **Base de connaissance** | Non | Oui — questions générales SRM (abonnement, contact, stage...) |
| **Analyse personnalisée** | Non | Oui — explication des variations, conseils adaptés à l'usage et à la saisonnalité |

---

## Interfaces & Fonctionnalités

### Interface Administrateur
- Import de fichiers Excel multi-clients / multi-périodes et factures PDF
- Gestion de la base de données SQLite
- Gestion des comptes utilisateurs (création, suppression, rôles)
- **Agent Alertes** : détection des surconsommations, envoi ciblé ou en masse, historique complet

### Interface Employé SRM
- **Assistant conversationnel PDF** : analyse de factures individuelles via RAG classique
- **Assistant Excel multi-clients** : interrogation via l'architecture hybride LLM as a Router
- Filtre par fichier Excel source pour des analyses ciblées
- **Persistance des conversations** : historique sauvegardé en base, consultable et renommable depuis la sidebar
- **Multilinguisme** : interface disponible en français, anglais et arabe

### Interface Client Connecté
- Authentification sécurisée par email
- Chatbot personnalisé filtré automatiquement par numéro de contrat (isolation totale des données)
- Mini-dashboard : dernière facture, prochain paiement, graphique de consommation
- Téléchargement de factures PDF personnalisées (ReportLab)
- Base de connaissance institutionnelle SRM (abonnement, branchement, contacts)
- **Persistance des conversations** : historique sauvegardé par client, accessible après reconnexion
- **Multilinguisme** : interface disponible en français, anglais et arabe

---

## Agent Alertes — Tâche 2

### Mode Manuel (Admin)

L'admin peut déclencher la détection depuis l'interface et choisir entre deux modes :

| Mode | Méthode | Avantage |
|---|---|---|
| **Mode 1** | Comparaison mois précédent | Détection immédiate des hausses soudaines |
| **Mode 2** | Moyenne historique 6 mois | Élimine les fausses alertes dues à un mois anormalement bas |

Envoi individuel, par sélection, ou en masse. Historique des alertes avec export CSV, déduplication anti-doublons.

### Mode Automatique (APScheduler)

L'agent tourne **sans intervention humaine** — planifié automatiquement via APScheduler. Par défaut il utilise le **Mode 2 (moyenne historique)** pour réduire les fausses alertes.

Fonctionnalités communes : seuil configurable, template email HTML avec niveaux de criticité (modéré / élevé / critique), distinction source manuel / automatique dans l'historique.

### Mode IA (Mistral)

En complément des deux modes de détection, l'agent peut enrichir les emails d'alerte avec une **analyse contextuelle personnalisée générée par Mistral**. Le LLM reçoit le profil réel du client (usage, agence, type de service, saisonnalité marocaine) et génère une explication narrative de 2 phrases. Les calculs et chiffres restent entièrement déterministes — Mistral intervient uniquement pour le texte d'analyse, garantissant zéro hallucination sur les données.

---

## Tech Stack

| Couche | Technologie | Rôle |
|---|---|---|
| Langage | Python 3.10.9 | Développement principal |
| Backend | FastAPI + Jinja2 | Routes HTTP, sessions par cookies, routage par rôle |
| Frontend | Tailwind CSS | Design des interfaces |
| LLM | Mistral via Ollama | Classificateur d'intention + génération d'analyse email (local) |
| Extraction PDF | pdfplumber | Lecture des factures PDF |
| Génération PDF | ReportLab | Factures personnalisées téléchargeables |
| Base de données | SQLite | Persistance des données et conversations |
| Traitement Excel | pandas / openpyxl | Lecture multi-clients / multi-périodes |
| Similarité texte | fuzzywuzzy | Détection des noms mal orthographiés |
| Sécurité | hashlib SHA-256 | Hashage des mots de passe |
| Planification | APScheduler | Agent autonome planifié |
| Email | smtplib + SMTP Gmail | Envoi automatique des alertes |
| Conteneurisation | Docker + Docker Compose | Déploiement isolé et reproductible |

> **Note sur la migration UI :** Le prototype initial a été développé sous Streamlit, puis migré vers FastAPI + Jinja2 + Tailwind CSS pour lever les contraintes de personnalisation UI. La migration a été réalisée sans aucune régression fonctionnelle, confirmant la solidité de l'architecture modulaire adoptée dès le départ.

---

## Sécurité

- Authentification par email avec hashage **SHA-256**
- Système de rôles : **Admin / Employé / Client**
- **Isolation totale** des données client par numéro de contrat
- Validation du schéma SQL avant toute exécution (rejet des colonnes inexistantes)
- Whitelist SELECT : rejet de toute instruction de modification (INSERT, UPDATE, DELETE, DROP...)
- Le LLM tourne **entièrement en local** via Ollama — aucune donnée ne quitte la machine

---

## 🐳 Déploiement Docker (Recommandé)

La méthode recommandée pour déployer ce projet est via Docker. Elle ne nécessite **aucune installation manuelle** de Python, Ollama ou Mistral — tout est automatisé.

### Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- 8 Go de RAM minimum (requis pour Mistral)
- Connexion internet (premier lancement uniquement)

### Lancement en 3 étapes

**Étape 1 — Cloner le dépôt**

```bash
git clone https://github.com/BenWafae/srm-intelligent-billing-system.git
cd srm-intelligent-billing-system
```

**Étape 2 — Configurer les variables d'environnement**

```bash
cp .env.example .env
```

Ouvrir le fichier `.env` et remplir `EMAIL_SENDER` et `EMAIL_PASSWORD`.

**Étape 3 — Démarrer l'application**

```bash
docker compose up -d
```

L'application est accessible sur **`http://localhost:8000`**

### Ce qui se passe automatiquement au démarrage

| Étape | Description |
|---|---|
|  Construction de l'image | Python 3.10.9 + toutes les dépendances installées automatiquement |
|  Démarrage Ollama | Serveur LLM local démarré sur le port 11434 |
|  Téléchargement Mistral | Modèle téléchargé **automatiquement** au premier lancement (~4 GB) |
|  Démarrage FastAPI | Application accessible sur `http://localhost:8000` |

> **Aucune commande supplémentaire n'est requise.** Mistral est téléchargé et configuré automatiquement au premier démarrage grâce à l'`entrypoint` du `docker-compose.yml`.

### Premier lancement vs suivants

**Premier lancement** (nouveau PC) :
- Mistral se télécharge automatiquement (~4 GB) — environ 30 à 60 minutes selon la connexion
- Aucune intervention manuelle requise

**Lancements suivants** :
- Mistral déjà sauvegardé dans le volume Docker persistant `ollama_data`
- Démarrage complet en **moins de 30 secondes**

### Commandes utiles

**Démarrer en arrière-plan**

```bash
docker compose up -d
```

**Voir les logs en temps réel**

```bash
docker compose logs -f
```

**Voir les logs d'Ollama uniquement**

```bash
docker compose logs -f ollama
```

**Arrêter les conteneurs**

```bash
docker compose down
```

**Reconstruire après modification du code**

```bash
docker compose up -d --build
```

> **Note :** Le modèle Mistral est sauvegardé dans le volume Docker `ollama_data`. Il n'est téléchargé qu'une seule fois — même après `docker compose down` ou reconstruction des conteneurs, Mistral reste disponible.

---

## ⚡ Lancement sans Docker (mode développement local)

Pour tester ou modifier le code sans Docker :

### Prérequis

- **Python 3.10.9** : [python.org](https://www.python.org/downloads/release/python-3109/)
- **Ollama** : [ollama.com](https://ollama.com/)
- **Git**

### Installation

**Étape 1 — Cloner le dépôt**

```bash
git clone https://github.com/BenWafae/srm-intelligent-billing-system.git
cd srm-intelligent-billing-system
```

**Étape 2 — Installer les dépendances**

```bash
pip install -r requirements.txt
```

**Étape 3 — Configurer les variables d'environnement**

```bash
cp .env.example .env
```

Ouvrir le fichier `.env` et remplir `EMAIL_SENDER` et `EMAIL_PASSWORD`.

**Étape 4 — Télécharger le modèle Mistral**

```bash
ollama pull mistral
```

**Étape 5 — Lancer l'application**

```bash
uvicorn main:app --reload
```

L'application est accessible sur `http://localhost:8000`

> Au premier lancement, Ollama peut prendre quelques secondes pour charger le modèle Mistral en mémoire.

---

## Rôles & Accès

| Rôle | Accès |
|---|---|
| **Admin** | Import données, gestion utilisateurs, agent alertes, historique |
| **Employé** | Assistant complet : analyse PDF + interrogation multi-clients Excel |
| **Client** | Espace personnel : ses factures uniquement + téléchargement PDF |

> Les comptes sont créés et gérés par l'Admin depuis son interface.