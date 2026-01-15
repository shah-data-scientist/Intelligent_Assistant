# Project Memory

**Last Updated:** 2026-01-15
**Status:** Requirements Defined
**Project:** RAG-based Cultural Events Recommendation Assistant

## 📋 Project Requirements

**Last Audit:** Never
**Requirements Status:** Requirements Defined - Implementation Pending

### Project Overview

Design, implement, and demonstrate a Retrieval-Augmented Generation (RAG) system for recommending cultural events in Paris. The system is a Proof of Concept (POC) aimed at both technical evaluators and business stakeholders.

### Functional Requirements

1. **Data Retrieval**
   - Fetch cultural event data from OpenAgenda API
   - API Endpoint: `/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records?limit=20`
   - Focus: Events in Paris within 1-year time window
   - Support continuous data ingestion and index rebuilding

2. **Data Processing**
   - Clean and normalize event data
   - Structure data for semantic search
   - Extract and maintain metadata (dates, locations, categories)

3. **Query Processing**
   - Accept user questions about cultural events
   - Auto-detect query language (French/English)
   - Respond in the same language as the query

4. **Information Retrieval**
   - Semantic vector search using FAISS
   - Metadata-based filtering (location, date)
   - Optional reranking for improved relevance

5. **Response Generation**
   - Generate coherent, accurate, context-aware responses
   - Use Mistral LLM via API
   - Domain-specific prompts for cultural events

6. **API Exposure**
   - REST API for business experimentation
   - Suitable for future integration

### Technical Requirements

**Core Technologies:**
- **LLM:** Mistral (API key required - request when needed)
- **Embeddings:** Mistral embeddings
- **Vector Store:** FAISS
- **Orchestration:** LangChain
- **Language Support:** Multi-language (auto-detect French/English)
- **Deployment:** Docker containerized

**Performance Requirements:**
- Response time: <2 seconds (target SLA)
- Handle real-time API data fetching
- Support index rebuilding without downtime

**Architecture Components:**
1. Data ingestion pipeline (OpenAgenda API → processing)
2. Vector indexing system (embeddings → FAISS)
3. Retrieval system (query → relevant events)
4. Generation system (context → LLM → response)
5. REST API layer (external interface)

### Evaluation Requirements

**All metrics required:**
1. **Retrieval Metrics:** Precision, recall, relevance of retrieved events
2. **Generation Quality:** ROUGE, BLEU scores against reference answers
3. **End-to-End Evaluation:** User satisfaction, LLM-as-judge for answer quality
4. **Performance Metrics:** Latency, throughput, system capacity

### Security/Compliance Requirements

- Security Standard: OWASP Top 10
- Compliance: None (POC)
- Input Validation: Required for all user queries
- API Key Management: Mistral API key in .env file
- Data Handling: Public event data, no PII
- Secrets: Never commit API keys (use .env + .gitignore)

### Audit History

**2026-01-15:** Repository initialized

## 🏗️ Architecture

### Technology Stack

**Core:**
- **Language:** Python 3.11+
- **Package Manager:** Poetry
- **LLM:** Mistral API
- **Embeddings:** Mistral embeddings
- **Vector Store:** FAISS
- **Orchestration:** LangChain
- **API Framework:** FastAPI (REST API)
- **Containerization:** Docker

**Development:**
- **Testing:** pytest
- **Code Quality:** ruff, black, mypy
- **Visualization:** plotly

### System Architecture

```
┌─────────────────┐
│   REST API      │  ← FastAPI endpoint
│   (FastAPI)     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│     RAG Orchestration Layer         │
│         (LangChain)                 │
├─────────────────────────────────────┤
│  Query Processing → Retrieval →    │
│  Context Building → Generation      │
└──┬────────────────────────────────┬─┘
   │                                │
   ↓                                ↓
┌──────────────────┐    ┌──────────────────┐
│  Vector Store    │    │   LLM Service    │
│   (FAISS)        │    │   (Mistral)      │
│                  │    │                  │
│ - Embeddings     │    │ - Generation     │
│ - Metadata       │    │ - Prompts        │
│ - Filtering      │    └──────────────────┘
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│  Data Pipeline   │
│                  │
│ - API Fetching   │  ← OpenAgenda API
│ - Processing     │
│ - Indexing       │
└──────────────────┘
```

### Project Structure

```
intelligent-assistant/
├── src/
│   ├── data/              # Data ingestion & processing
│   │   ├── api_client.py  # OpenAgenda API client
│   │   └── processor.py   # Data cleaning/normalization
│   ├── models/            # Vector store & embeddings
│   │   ├── embeddings.py  # Mistral embeddings
│   │   └── vector_store.py# FAISS operations
│   ├── retrieval/         # RAG retrieval logic
│   │   ├── retriever.py   # Semantic + metadata search
│   │   └── reranker.py    # Optional reranking
│   ├── generation/        # LLM generation
│   │   ├── llm.py         # Mistral LLM client
│   │   └── prompts.py     # Domain-specific prompts
│   ├── api/               # REST API
│   │   └── endpoints.py   # FastAPI routes
│   └── evaluation/        # Evaluation metrics
├── tests/                 # Unit & integration tests
├── notebooks/             # Experimentation & analysis
├── data/                  # Cached event data
├── docker/                # Dockerfile & compose
└── scripts/               # Utility scripts
```

## 📝 Implementation Notes

### Recent Changes

**2026-01-15:**
- Initialized repository
- Set up Poetry with dev dependencies
- Created standard project structure
- Added documentation templates
- Defined project requirements (RAG system for Paris cultural events)
- **Phase 1 Complete: Data Pipeline**
  - Installed core dependencies (httpx, langchain, fastapi, faiss-cpu)
  - Implemented configuration management ([src/config.py](src/config.py))
  - Created Event and EventLocation models ([src/data/models.py](src/data/models.py))
  - Implemented OpenAgendaClient for API fetching ([src/data/api_client.py](src/data/api_client.py))
  - Implemented EventProcessor for data normalization ([src/data/processor.py](src/data/processor.py))
  - Added comprehensive test suite (22 tests passing)

### Known Issues

None

### Next Steps

**Phase 1: Data Pipeline** ✓ COMPLETE

**Phase 2: Vector Store & Embeddings (Priority 1)** ← CURRENT
1. Set up Mistral embeddings
2. Implement FAISS indexing
3. Add metadata filtering capabilities

**Phase 3: RAG System (Priority 2)**
1. Implement retrieval logic
2. Set up Mistral LLM integration
3. Create domain-specific prompts
4. Build LangChain orchestration

**Phase 4: API Layer (Priority 2)**
1. Implement FastAPI endpoints
2. Add query validation & error handling
3. Implement language detection

**Phase 5: Evaluation (Priority 3)**
1. Build retrieval metrics
2. Implement generation quality evaluation
3. Add performance monitoring
4. Create end-to-end evaluation suite

**Phase 6: Deployment (Priority 3)**
1. Create Dockerfile
2. Set up docker-compose
3. Add deployment documentation

## 🔒 Security Notes

- All user inputs must be validated
- Sensitive data should be encrypted
- Use parameterized queries for databases
- No secrets in code (use .env)

## 📚 Documentation

- Global Policy: `C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md`
- Documentation Policy: [DOCUMENTATION_POLICY.md](DOCUMENTATION_POLICY.md)
- README: [README.md](README.md)
