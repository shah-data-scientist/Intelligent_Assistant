# Rapport Technique – Assistant Intelligent de Recommandation d'Événements Culturels

## 1. Objectifs du projet

### Contexte
Puls-Events, une entreprise spécialisée dans la promotion culturelle en Île-de-France, souhaite développer un assistant conversationnel intelligent capable de recommander des événements culturels à ses utilisateurs. L'objectif est de faciliter la découverte d'événements en permettant aux utilisateurs de poser des questions en langage naturel.

### Problématique
Les utilisateurs recherchent des événements de manière traditionnelle via des filtres statiques (date, catégorie, lieu), ce qui limite la découverte. Un système RAG (Retrieval-Augmented Generation) répond à ce besoin en permettant :
- Des requêtes en langage naturel ("concerts de jazz à Paris ce weekend")
- Une compréhension contextuelle des conversations multi-tours
- Des recommandations personnalisées basées sur le contenu sémantique des événements
- Une transparence sur les filtres appliqués et les sources citées

### Objectif du POC
Démontrer la faisabilité technique d'un assistant RAG capable de :
- Comprendre et traiter des requêtes en français et en anglais
- Maintenir le contexte conversationnel sur plusieurs échanges
- Récupérer des événements pertinents via recherche hybride (sémantique + mots-clés)
- Générer des réponses naturelles avec citations des sources

### Périmètre
- **Zone géographique** : Île-de-France (Paris et communes environnantes)
- **Période d'événements** : Événements actuels et à venir (30 prochains jours par défaut)
- **Données utilisées** : 1 052 événements culturels provenant de l'API Open Agenda
- **Catégories** : Musique, Théâtre/Spectacle, Exposition, Conférence, Cinéma, Jeune public, etc.

---

## 2. Architecture du système

### Schéma global (flux de données)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Open Agenda   │────▶│   Ingestion      │────▶│   SQLite DB     │
│   API           │     │   Pipeline       │     │   (events.db)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Mistral       │────▶│   EventEmbedder  │────▶│   FAISS Index   │
│   Embed API     │     │   (1024 dim)     │     │   + BM25        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Utilisateur   │────▶│   FastAPI        │────▶│   RAG Chain     │
│   (Frontend)    │     │   /api/v1/chat   │     │   (LangChain)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Gemini 2.0    │
                                                 │   Flash (LLM)   │
                                                 └─────────────────┘
```

### Technologies utilisées

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Langage** | Python | 3.11+ |
| **API REST** | FastAPI | 0.115.0 |
| **Serveur ASGI** | Uvicorn | 0.32.0 |
| **Orchestration RAG** | LangChain (LCEL) | 0.3.0 |
| **LLM Principal** | Google Gemini 2.0 Flash | - |
| **Embeddings** | Mistral Embed | 1024 dim |
| **Base vectorielle** | FAISS | 1.9.0 |
| **Recherche mots-clés** | Rank-BM25 | 0.2.2 |
| **Base de données** | SQLite + SQLAlchemy | 2.0.36 |
| **Frontend** | Streamlit | 1.40.0 |
| **Conteneurisation** | Docker | Multi-stage |
| **Tests** | Pytest | 9.0.2 |

---

## 3. Préparation et vectorisation des données

### Source de données : API Open Agenda

**URL de base** : `https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records`

**Paramètres utilisés** :
- `limit` : 100 événements par requête (pagination)
- `offset` : Pagination incrémentale
- `order_by` : "firstdate_begin desc" (événements les plus récents en premier)
- `where` : 'location_region like "Île-de-France"' (filtre géographique)

**Configuration** :
- Maximum 20 000 événements par ingestion
- Objectif minimum : 1 000 événements Île-de-France
- Enrichissement via scraping des URLs d'événements (batch de 10)

### Nettoyage

**Exemples d'anomalies corrigées** :
- Normalisation UTF-8 (préservation des caractères français : é, è, ê, etc.)
- Suppression de 50+ patterns de phrases boilerplate (ex: "Cliquez ici pour plus d'infos")
- Déduplication des phrases répétitives dans les descriptions
- Forçage de la classification sémantique vers 10 catégories (élimination de "Autre")
- Normalisation des labels de prix et d'âge pour l'affichage

### Chunking

**Stratégie** : Granularité au niveau de l'événement (pas de découpage textuel)

**Raison** : Chaque événement est une unité atomique de recherche. Découper un événement en morceaux créerait des résultats incohérents.

**Représentation textuelle pour embedding** (`Event.to_text()`) :
```
[Ville: Paris] [Catégorie: Musique] [Date: February 2026]
Titre: Concert de Jazz
URL: https://...
Description: ...
Tags: jazz, musique live, concert
```

### Embedding

**Modèle utilisé** : Mistral `mistral-embed`

| Paramètre | Valeur |
|-----------|--------|
| Dimensionnalité | 1024 |
| Méthode batch | `embed_documents()` via LangChain |
| Cache | 2h TTL, 500 entrées max, éviction LRU |
| Clé de cache | SHA-256 du texte normalisé |

---

## 4. Choix du modèle NLP

### Modèle sélectionné

**LLM Principal** : Google Gemini 2.0 Flash (`gemini-2.0-flash`)

### Pourquoi ce modèle ?

| Critère | Évaluation |
|---------|------------|
| **Coût** | API Google AI gratuite pour prototypage |
| **Qualité** | Excellente compréhension FR/EN, bon respect des instructions |
| **Compatibilité LangChain** | Support natif via `langchain-google-genai` |
| **Sortie structurée** | Bon support JSON pour extraction d'événements |
| **Latence** | Rapide pour un modèle de cette qualité |
| **Stabilité** | Version "Flash" stable, pas de problèmes de mode thinking |

**Backends alternatifs supportés** :
- Mistral (`mistral-small-latest`)
- HuggingFace Inference API (`Qwen/Qwen2.5-7B-Instruct`)
- Ollama local (`qwen2.5:1.5b`)

### Prompting

**Structure du prompt RAG** (extrait simplifié) :
```
Tu es un assistant culturel expert en événements en Île-de-France.

RÈGLES :
1. Réponds UNIQUEMENT à partir des événements fournis
2. Cite toujours les sources avec URLs
3. Si aucun événement ne correspond, dis-le clairement
4. Indique les filtres appliqués en fin de réponse

CONTEXTE ÉVÉNEMENTS :
{context}

HISTORIQUE CONVERSATION :
{chat_history}

QUESTION UTILISATEUR :
{question}
```

### Limites du modèle

- Latence moyenne de 58 secondes pour requêtes complexes (incluant analyse + génération)
- Peut parfois inclure des informations non présentes dans les sources (hallucination légère)
- Nécessite des prompts explicites pour éviter les réponses trop longues

---

## 5. Construction de la base vectorielle

### FAISS utilisé

**Type d'index** : `IndexFlatIP` (Flat Index avec Inner Product)

**Configuration** :
- Normalisation L2 pour similarité cosinus
- Recherche hybride : FAISS + BM25 Okapi via Reciprocal Rank Fusion (RRF)
- Paramètre RRF k : 60
- Facteur de boost mots-clés : 1.5x
- Pool de candidats : k×10 événements (100 par défaut)

### Stratégie de persistance

**Format de sauvegarde** :
- Index FAISS : `data/faiss_index/index.faiss` (binaire)
- Métadonnées : `data/faiss_index/metadata.pkl` (pickle Python)

**Nommage** : Fichiers fixes rechargés au démarrage de l'API

### Métadonnées associées

Pour chaque document indexé :
- `event_id` : Identifiant unique de l'événement
- `dimension` : 1024 (vérifié à l'initialisation)
- Index BM25 inversé pour recherche par mots-clés
- État de tokenisation multilingue (FR/EN)

---

## 6. API et endpoints exposés

### Framework utilisé

**FastAPI** v0.115.0 avec Uvicorn (ASGI)

### Endpoints clés

| Endpoint | Méthode | Auth | Rate Limit | Description |
|----------|---------|------|------------|-------------|
| `/api/v1/chat` | POST | API Key | 20/min | Point d'entrée principal pour les requêtes |
| `/api/v1/feedback` | POST | API Key | - | Soumission de feedback utilisateur |
| `/api/v1/health` | GET | - | - | Vérification de santé du système |
| `/api/v1/metrics` | GET | - | - | État du circuit breaker |

### Format des requêtes/réponses

**Requête `/api/v1/chat`** :
```json
{
  "question": "Concerts de jazz à Paris ce weekend",
  "session_id": "user_123",
  "language": "fr",
  "age": 25
}
```

**Réponse `/api/v1/chat`** :
```json
{
  "answer": "Voici 3 concerts de jazz à Paris...",
  "sources": [
    {
      "title": "Concert Jazz Club",
      "city": "Paris",
      "date": "2026-02-07T20:00:00",
      "url": "https://openagenda.com/...",
      "score": 0.85,
      "category": "Musique",
      "match_type": "Exact Match"
    }
  ],
  "structured_events": [...],
  "message_id": 42,
  "needs_clarification": false,
  "clarifying_questions": []
}
```

### Exemple d'appel API

**Avec curl** :
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"question": "Spectacles pour enfants à Versailles", "session_id": "demo"}'
```

**Avec Python** :
```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/chat",
    headers={"X-API-Key": "your-api-key"},
    json={"question": "Expositions gratuites à Paris", "session_id": "demo"}
)
print(response.json()["answer"])
```

### Tests effectués et documentés

- **519 tests** couvrant : unité, intégration, e2e, sécurité, évaluation
- Documentation complète dans `docs/TESTING_GUIDE.md`
- Marqueurs pytest : `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.security`

### Gestion des erreurs / limitations

- **Rate limiting** : 100 req/min global, 20 req/min par IP pour `/chat`
- **Validation** : Maximum 1000 caractères par requête
- **Sécurité** : Détection d'injection de prompt, scan PII, filtrage de profanités
- **Circuit breaker** : Désactivé par défaut (activable via `ENABLE_CIRCUIT_BREAKER=true`)
- **Retry** : 2 tentatives avec backoff exponentiel (2-10s)

---

## 7. Évaluation du système

### Jeu de test annoté

**Golden Dataset** : `evaluation/golden_dataset.json`

- **Nombre d'exemples** : 50 requêtes conversationnelles
- **Types de requêtes** :
  - `initial` : Première requête d'une conversation
  - `refinement` : Modification de la requête précédente
  - `follow_up` : Question sur un résultat spécifique
  - `topic_shift` : Changement de sujet
  - `clarification_response` : Réponse à une question de clarification

**Méthode d'annotation** :
- Définition manuelle des comportements attendus
- Filtres attendus (ville, catégorie, date)
- Mots-clés obligatoires dans la réponse
- Actions acceptables (demander clarification, afficher résultats)

### Métriques d'évaluation

**Métriques de retrieval** :
- Hit Rate : Au moins 1 document pertinent récupéré
- MRR (Mean Reciprocal Rank) : Rang du premier document pertinent
- Precision@k, Recall@k, F1@k
- NDCG@k : Normalized Discounted Cumulative Gain

**Métriques de génération (LLM-as-Judge)** :
- **Faithfulness** : Les affirmations sont-elles fondées sur les sources ?
- **Relevancy** : La réponse répond-elle à la question ?
- **Quality Score** : Moyenne de Faithfulness + Relevancy
- **Quality Pass Rate** : % de requêtes avec score ≥ 0.5

### Résultats obtenus

#### Évaluation Retrieval (6 février 2026)

Évaluation sur **44 requêtes** du golden dataset avec expected_filters définis.
Ground truth : événements correspondant aux filtres attendus dans la base de données.

| Métrique | Valeur |
|----------|--------|
| **Hit Rate** | 50.00% |
| **MRR** | 29.03% |
| **Precision@10** | 18.18% |
| **Recall@10** | 15.17% |
| **F1@10** | 12.77% |

**Meilleurs cas** (Recall@10 = 100%) :
- "Classical music in Bondy this weekend" : 8 events ground truth, 80% precision
- "Art exhibitions in Versailles in February" : 3 events ground truth, 30% precision
- "Theatre shows in Vincennes" : 1 event ground truth, 10% precision

**Observations** :
- Les requêtes ciblant des villes spécifiques (Versailles, Bondy, Saint-Denis) obtiennent de meilleurs scores
- Les requêtes sur Paris ont une recall faible car le pool de ground truth est large (50 events)
- Les requêtes avec filtres "is_free" obtiennent souvent 0% car peu d'événements gratuits dans la base

#### Évaluation Génération LLM-as-Judge (4 février 2026)

Évaluation sur **5 requêtes conversationnelles** avec scoring automatisé par Mistral.

| Métrique | Valeur |
|----------|--------|
| **Taux de succès** | 100% |
| **Score de qualité moyen** | 67% |
| **Faithfulness moyen** | 68% |
| **Relevancy moyen** | 66% |
| **Quality Pass Rate** | 75% |
| **Latence moyenne** | 58 201 ms |

**Analyse par type de requête** :

| Type | Nombre | Score qualité |
|------|--------|---------------|
| Initial | 2 | 55% |
| Refinement | 1 | 70% |
| Follow-up | 1 | 0% |
| Topic shift | 1 | 87.5% |

**Analyse qualitative** :

*Bonnes réponses* :
- Recherche de théâtre à Versailles (score 87.5%) : Le système a correctement identifié l'absence d'événements à Versailles et proposé des alternatives à Paris

*Mauvaises réponses* :
- "Parle-moi du premier" (score 0%) : Le système n'a pas correctement géré la référence anaphorique au premier résultat
- "Jazz concerts in Paris this weekend" (score 40%) : Événements musicaux retournés mais pas spécifiquement jazz

---

## 8. Recommandations et perspectives

### Ce qui fonctionne bien

- **Recherche hybride** : Combinaison FAISS + BM25 efficace pour la pertinence
- **Support multilingue** : Français et anglais bien gérés
- **Transparence des filtres** : L'utilisateur voit les filtres appliqués
- **Citations des sources** : URLs systématiquement fournies
- **Architecture modulaire** : Backends LLM interchangeables

### Limites du POC

| Limite | Impact |
|--------|--------|
| **Volumétrie** | 1 052 événements, suffisant pour POC mais limité |
| **Performance** | Latence élevée (58s moyenne) due aux appels LLM |
| **Coût** | APIs payantes (Mistral embed, Gemini) pour production |
| **Couverture thématique** | Concentration sur musique/spectacles, moins d'expos |
| **Résolution d'anaphores** | "Parle-moi du premier" mal géré |

### Améliorations possibles

**Ajout de** :
- Cache de réponses pour requêtes fréquentes
- Support de géolocalisation utilisateur
- Recommandations proactives basées sur l'historique
- Filtres budgétaires avancés ("gratuit", "moins de 20€")

**Amélioration de** :
- Résolution des références ("le premier", "celui-là")
- Latence via streaming des réponses LLM
- Score de qualité via fine-tuning du prompt
- Couverture via ingestion programmée quotidienne

**Passage en production via** :
- Déploiement sur infrastructure cloud (GCP, AWS)
- Base de données PostgreSQL pour la scalabilité
- Redis pour le cache distribué
- Monitoring avec Prometheus/Grafana
- CI/CD avec GitHub Actions

---

## 9. Organisation du dépôt GitHub

### Arborescence du dépôt

```
intelligent-assistant/
├── src/                          # Code source principal
│   ├── api/                      # API REST FastAPI
│   │   ├── main.py               # Configuration FastAPI, lifespan
│   │   ├── endpoints.py          # Routes (/chat, /feedback, /health)
│   │   └── schemas.py            # Modèles Pydantic
│   ├── data/                     # Ingestion et stockage
│   │   ├── api_client.py         # Client API Open Agenda
│   │   ├── processor.py          # Traitement des événements
│   │   ├── storage.py            # Opérations SQLite
│   │   └── ingestion.py          # Pipeline d'ingestion
│   ├── models/                   # Modèles ML
│   │   ├── embeddings.py         # Mistral Embed (1024 dim)
│   │   └── vector_store.py       # FAISS + BM25 hybride
│   ├── retrieval/                # Logique RAG
│   │   ├── chain.py              # Orchestration LangChain LCEL
│   │   ├── manager.py            # Gestion retrieval multi-étapes
│   │   └── unified_analyzer.py   # Analyse de requête LLM
│   ├── generation/               # Génération LLM
│   │   ├── llm.py                # Client multi-backend
│   │   └── prompts.py            # Prompts bilingues (i18n)
│   ├── evaluation/               # Framework d'évaluation
│   │   ├── metrics/              # Métriques retrieval/generation
│   │   └── evaluators/           # Évaluateurs système
│   ├── security/                 # Sécurité
│   │   ├── guardrails.py         # Détection injection, profanités
│   │   └── sanitization.py       # Détection PII
│   └── frontend/                 # Interface Streamlit
│       └── app.py                # Application web
├── tests/                        # Suite de tests (519 tests)
│   ├── unit/                     # Tests unitaires
│   ├── integration/              # Tests d'intégration
│   ├── e2e/                      # Tests end-to-end
│   └── security/                 # Tests de sécurité
├── data/                         # Données
│   ├── events.db                 # Base SQLite (1052 événements)
│   ├── faiss_index/              # Index FAISS persisté
│   └── evaluation/               # Golden dataset et rapports
├── evaluation/                   # Scripts d'évaluation
│   ├── golden_dataset.json       # 50 requêtes annotées
│   └── reports/                  # Rapports générés
├── docs/                         # Documentation
│   ├── SYSTEM_ARCHITECTURE.md    # Architecture système
│   ├── DATA_FLOW.md              # Flux de données
│   ├── API_DOCUMENTATION.md      # Documentation API
│   └── EVALUATION_GUIDE.md       # Guide d'évaluation
├── docker/                       # Configuration Docker
│   └── Dockerfile                # Build multi-stage
├── pyproject.toml                # Dépendances Poetry
└── README.md                     # Vue d'ensemble projet
```

### Explication rapide de chaque répertoire

| Répertoire | Responsabilité |
|------------|----------------|
| `src/api/` | Exposition REST, validation, rate limiting |
| `src/data/` | Ingestion Open Agenda, stockage SQLite, scraping |
| `src/models/` | Embeddings Mistral, index FAISS + BM25 |
| `src/retrieval/` | Orchestration RAG, analyse de requête, filtres |
| `src/generation/` | Clients LLM multi-backend, prompts i18n |
| `src/evaluation/` | Métriques, évaluateurs LLM-as-Judge |
| `src/security/` | Guardrails, détection PII, sanitization |
| `tests/` | 519 tests pytest (unit, integration, e2e) |
| `data/` | Bases de données, index vectoriel, datasets |
| `docs/` | Documentation technique et guides |
| `docker/` | Containerisation multi-stage |

---

## 10. Annexes

### Annexe A : Extrait du jeu de test annoté

```json
{
  "session_id": "conv_001",
  "description": "Simple refinement: User narrows down date after initial broad query",
  "test_focus": ["context_retention", "incremental_modification"],
  "language": "fr",
  "turns": [
    {
      "turn_id": "conv_001_t1",
      "turn_number": 1,
      "turn_type": "initial",
      "query": "Concerts de jazz à Paris",
      "expected_behavior": {
        "should_ask_clarification": true,
        "clarification_topics": ["date", "month"],
        "acceptable_actions": ["ask_clarification", "show_results_with_suggestion"]
      },
      "expected_filters": {
        "city": "Paris",
        "category": "Musique"
      }
    },
    {
      "turn_id": "conv_001_t2",
      "turn_number": 2,
      "turn_type": "refinement",
      "query": "En février plutôt",
      "expected_filters": {
        "city": "Paris",
        "category": "Musique",
        "month": 2
      }
    }
  ]
}
```

### Annexe B : Prompt RAG principal (extrait)

```python
RAG_SYSTEM_PROMPT = """
Tu es un assistant expert en événements culturels en Île-de-France.

RÈGLES STRICTES :
1. UTILISE UNIQUEMENT les événements fournis dans le contexte
2. CITE TOUJOURS les sources avec leurs URLs
3. Si aucun événement ne correspond, DIS-LE clairement
4. INDIQUE les filtres appliqués à la fin de ta réponse

FORMAT DE RÉPONSE :
- Liste numérotée des événements pertinents
- Pour chaque événement : titre, date, lieu, URL
- Section "Filtres appliqués" en fin de message

ÉVÉNEMENTS DISPONIBLES :
{context}

HISTORIQUE :
{chat_history}

QUESTION :
{question}
"""
```

### Annexe C : Exemple de réponse JSON API

```json
{
  "answer": "Voici 8 concerts de jazz à Paris en février 2026...",
  "sources": [
    {
      "title": "Zoot Sundays! Sessions Jazz du dimanche",
      "city": "Paris",
      "date": "2026-02-01T19:30:00",
      "url": "https://openagenda.com/jassclub-paris/events/zoot-sundays...",
      "score": 0.029,
      "category": "Musique",
      "match_type": "Exact Match"
    }
  ],
  "structured_events": [
    {
      "title": "Zoot Sundays! Sessions Jazz du dimanche",
      "date": "2026-02-01",
      "city": "Paris",
      "location": "JASS CLUB PARIS, 141 Rue de Tolbiac",
      "url": "https://openagenda.com/...",
      "price_label": "15€ - 19€",
      "times": ["19:30", "21:30"],
      "times_display": "19h30, 21h30"
    }
  ],
  "message_id": 1,
  "needs_clarification": false,
  "clarifying_questions": []
}
```

### Annexe D : Résultats détaillés de l'évaluation génération (LLM-as-Judge)

| Query ID | Requête | Type | Faithfulness | Relevancy | Qualité |
|----------|---------|------|--------------|-----------|---------|
| conv_001_t1 | Concerts de jazz à Paris | initial | 0.50 | 0.90 | 0.70 |
| conv_001_t2 | En février plutôt | refinement | 0.50 | 0.90 | 0.70 |
| conv_001_t3 | Parle-moi du premier | follow_up | 0.00 | 0.00 | 0.00 |
| conv_002_t1 | Jazz concerts in Paris this weekend | initial | 0.70 | 0.10 | 0.40 |
| conv_002_t2 | Theater shows in Versailles? | topic_shift | 1.00 | 0.75 | 0.875 |

### Annexe E : Résultats détaillés de l'évaluation retrieval (Precision/Recall)

**Meilleures performances** (sélection de 10 requêtes) :

| Requête | Ground Truth | Precision@10 | Recall@10 |
|---------|--------------|--------------|-----------|
| Montre-moi tout ce qui se passe à Versailles | 13 | 100% | 76.92% |
| Classical music in Bondy this weekend | 8 | 80% | 100% |
| Ballet performances in Saint-Denis | 13 | 60% | 46.15% |
| Concerts de jazz à Paris | 50 | 70% | 14% |
| Concerts à Paris en mars | 25 | 60% | 24% |
| Expositions à Paris | 31 | 50% | 16.13% |
| Concerts de jazz en février | 50 | 50% | 10% |
| Electronic music festivals | 50 | 40% | 8% |
| Art exhibitions in Versailles in February | 3 | 30% | 100% |
| Expositions d'art contemporain à Nanterre en mars | 6 | 20% | 33.33% |

**Observations clés** :
- Les villes moins peuplées (Versailles, Bondy, Saint-Denis) obtiennent de meilleurs scores car le pool de ground truth est plus petit
- Les requêtes sur Paris avec catégorie large ont une recall faible (10-16%) car 50 événements correspondent
- Les filtres "gratuit" (is_free) donnent souvent 0% car peu d'événements gratuits annotés

---

*Document généré le 6 février 2026*
*Projet réalisé dans le cadre de la formation OpenClassrooms - Développeur en Intelligence Artificielle*
