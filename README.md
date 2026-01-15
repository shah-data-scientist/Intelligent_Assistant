# Cultural Events Recommendation Assistant

## Overview

A Retrieval-Augmented Generation (RAG) system that recommends cultural events in Paris using real-time data from OpenAgenda. This POC combines semantic search, metadata filtering, and LLM-powered generation to answer user queries about upcoming events.

**Key Features:**
- Real-time event data from OpenAgenda API
- Semantic search with FAISS vector store
- Metadata-based filtering (date, location)
- Multi-language support (French/English auto-detection)
- Mistral LLM for natural language responses
- REST API for easy integration
- <2 second response time target

## Setup

### Prerequisites

- Python 3.11+
- Poetry
- Mistral API key ([Get one here](https://console.mistral.ai/))

### Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Set up environment variables
cp .env.example .env
# Edit .env and add your MISTRAL_API_KEY
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Mistral API
MISTRAL_API_KEY=your_mistral_api_key_here

# OpenAgenda API
OPENAGENDA_BASE_URL=https://api.openagenda.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records

# Vector Store
FAISS_INDEX_PATH=./data/faiss_index
VECTOR_DIMENSION=1024

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
```

## Project Structure

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
├── docs/                  # Documentation
├── notebooks/             # Experimentation & analysis
├── data/                  # Cached event data & FAISS index
├── docker/                # Dockerfile & compose
└── scripts/               # Utility scripts
```

## Usage

### Data Ingestion

```bash
# Fetch and process events from OpenAgenda
poetry run python -m src.data.api_client

# Build FAISS index
poetry run python -m src.models.vector_store build
```

### Running the API

```bash
# Start the FastAPI server
poetry run uvicorn src.api.endpoints:app --reload

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Query Examples

```bash
# Using curl
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Quels concerts ont lieu ce week-end à Paris?"}'

# Response will include recommended events with descriptions
```

### Docker Deployment

```bash
# Build and run with Docker
docker-compose up --build

# API available at http://localhost:8000
```

## Development

### Running Tests

```bash
poetry run pytest tests/
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/
```

## Evaluation

The system includes comprehensive evaluation metrics:

```bash
# Run full evaluation suite
poetry run python -m src.evaluation.evaluate

# Metrics include:
# - Retrieval: Precision, Recall, MRR
# - Generation: ROUGE, BLEU
# - End-to-end: LLM-as-judge scores
# - Performance: Latency, throughput
```

## Architecture

The system follows a modular RAG architecture:
1. **Data Pipeline**: Fetches events from OpenAgenda API
2. **Vector Store**: FAISS index with Mistral embeddings
3. **Retrieval**: Semantic search + metadata filtering
4. **Generation**: Mistral LLM with domain-specific prompts
5. **API**: FastAPI REST endpoint

See [PROJECT_MEMORY.md](PROJECT_MEMORY.md) for detailed architecture diagrams.

## Documentation

- [PROJECT_MEMORY.md](PROJECT_MEMORY.md) - Requirements, architecture, and implementation notes
- [DOCUMENTATION_POLICY.md](DOCUMENTATION_POLICY.md) - Documentation standards
- API docs available at `/docs` endpoint when server is running

## License

[License to be added]
