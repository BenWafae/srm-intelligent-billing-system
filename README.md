<div align="center">

<img src="https://img.shields.io/badge/Python-3.10.9-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Streamlit-Interface-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
<img src="https://img.shields.io/badge/Ollama-Mistral_Local-000000?style=for-the-badge"/>
<img src="https://img.shields.io/badge/SQLite-Base_de_données-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
<img src="https://img.shields.io/badge/RAG-Architecture_Hybride-7B68EE?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Status-En_cours-orange?style=for-the-badge"/>

# 🧾 SRM Intelligent Billing System
> Système Intelligent de Gestion des Factures — SRM Souss-Massa

Réalisé par : **BEN ZHIR Wafa**
Encadrant entreprise : **ZEROUALI Hassan** · Encadrant académique : **AIT BAHA Tarek**

</div>

---

##  Description

Système de gestion intelligente des factures développé pour la **SRM Souss-Massa**, composé de trois interfaces dédiées et d'un assistant conversationnel basé sur une architecture RAG hybride avec LLM local.

- **Interface Admin** — import Excel/PDF, gestion base de données & comptes utilisateurs
- **Interface Employé** — assistant intelligent : analyse PDF (RAG classique) + interrogation multi-clients Excel (détection d'intents → fetchers Python → fallback Text-to-SQL)
- **Interface Client** — authentification sécurisée, chatbot filtré par contrat, téléchargement de factures PDF personnalisées

---

##  Tech Stack

| Couche | Technologie |
|---|---|
| Langage | Python 3.10.9 |
| Interface | Streamlit |
| LLM | Mistral via Ollama (local) |
| Extraction PDF | pdfplumber |
| Génération PDF | ReportLab |
| Base de données | SQLite |
| Traitement Excel | pandas / openpyxl |
| Similarité texte | fuzzywuzzy / python-levenshtein |

---

##  Prérequis

Avant de lancer le projet, assurez-vous d'avoir installé :

- **Python 3.10.9** — [python.org](https://www.python.org/downloads/release/python-3109/)
- **Ollama** — [ollama.com](https://ollama.com/)
- **Git**

---

##  Quick Start

```bash
pip install -r requirements.txt
ollama pull mistral
streamlit run app.py
```

---

##  Lancer le projet

### 1. Cloner le dépôt

```bash
git clone https://github.com/<username>/srm-intelligent-billing-system.git
cd srm-intelligent-billing-system
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Télécharger le modèle Mistral

```bash
ollama pull mistral
```

> Ollama tourne en arrière-plan automatiquement après installation. Vérifiable sur `http://localhost:11434`

### 4. Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur sur `http://localhost:8501`

---

## 🗂️ Structure du projet

```
srm-intelligent-billing-system/
│
├── app.py                            # Point d'entrée : authentification & routage par rôle
│
├── pages/
│   ├── admin.py                      # Interface administrateur
│   ├── employe.py                    # Interface employé (assistant complet)
│   └── client.py                     # Interface client (filtrage par contrat)
│
├── src/
│   ├── pdf_reader.py                 # Extraction texte PDF
│   ├── excel_reader.py               # Traitement Excel multi-clients
│   ├── extractor.py                  # Structuration des données via LLM
│   ├── database.py                   # Gestion SQLite (factures, users)
│   ├── llm.py                        # Interactions avec le modèle LLM
│   ├── normalisation.py              # Normalisation des questions
│   ├── rag_general.py                # RAG classique pour factures PDF
│   │
│   ├── rag/
│   │   ├── dispatcher.py             # Routage vers le bon fetcher
│   │   ├── intent.py                 # Détection d'intention (règles → LLM fallback)
│   │   ├── mode.py                   # Mode de réponse (count / list / detail)
│   │   ├── fetchers_generaux.py      # Fetchers multi-clients
│   │   └── fetchers_client.py        # Fetchers spécifiques client
│   │
│   └── rag_client/
│       ├── dispatcher.py             # Pipeline client : filtrage par contrat
│       ├── intent.py                 # Détection d'intention (contexte client)
│       ├── fetchers.py               # Données filtrées par contrat
│       ├── tokens.py                 # Mots-clés pour la détection d'intents
│       └── pdf_facture.py            # Génération factures PDF (ReportLab)
│
├── assets/
│   └── srm_logo.png
│
├── data/                             # Fichiers Excel/PDF importés
├── requirements.txt
└── README.md
```

---

## 👥 Rôles & accès

| Rôle | Accès |
|---|---|
| **Admin** | Import données, gestion utilisateurs, supervision base de données |
| **Employé** | Assistant complet : analyse PDF + interrogation multi-clients Excel |
| **Client** | Espace personnel : ses factures uniquement + téléchargement PDF |

> Les comptes utilisateurs sont créés et gérés par l'Admin depuis son interface.

---

##  Sécurité

- Hashage des mots de passe **SHA-256**
- Isolation totale des données client par numéro de contrat
- Validation du schéma SQL avant toute exécution (fallback Text-to-SQL)
- Rejet de toute requête non-SELECT

---

##  Notes

- Le LLM tourne **entièrement en local** via Ollama — aucune donnée ne quitte la machine
- La base SQLite est stockée localement dans le répertoire du projet
- Le premier lancement peut être lent le temps qu'Ollama charge le modèle Mistral en mémoire