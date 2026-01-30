# API Usage Guide

## Overview

The Intelligent Cultural Assistant API is a REST API powered by FastAPI that provides AI-powered recommendations for cultural events in Île-de-France using Retrieval-Augmented Generation (RAG).

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API service is running.

**Response:**
```json
{
  "status": "ok",
  "service": "Intelligent Assistant API"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/health
```

### Chat - Ask About Events

**Endpoint:** `POST /chat`

**Description:** Ask natural language questions about cultural events and receive AI-generated recommendations with source events.

**Request Body:**
```json
{
  "question": "string"
}
```

**Response:**
```json
{
  "answer": "string",
  "sources": [
    {
      "event_id": "string",
      "title": "string",
      "description": "string",
      "category": "string",
      "location": {
        "city": "string",
        "postal_code": "string",
        "address": "string"
      },
      "start_date": "2026-01-15T20:00:00",
      "end_date": "2026-01-15T23:00:00",
      "url": "string",
      "similarity_score": 0.85
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels concerts de jazz sont disponibles ce mois-ci?"
  }'
```

**Example Response:**
```json
{
  "answer": "Voici quelques concerts de jazz disponibles ce mois-ci en Île-de-France:\n\n1. **Fred Nardin Quintet** - Le 6 mars 2026 à Paris. Un concert de jazz contemporain avec des influences modernes.\n\n2. **William Mendelbaum - Piano Solo Session** - Le 4 mars 2026 à Paris. Une performance intimiste de piano jazz.\n\nPour plus d'informations et pour réserver vos places, consultez les liens fournis dans les événements.",
  "sources": [
    {
      "event_id": "jazz-concert-001",
      "title": "Fred Nardin Quintet",
      "description": "Concert de jazz contemporain",
      "category": "Music",
      "location": {
        "city": "Paris",
        "postal_code": "75001"
      },
      "start_date": "2026-03-06T20:00:00",
      "similarity_score": 0.83
    }
  ]
}
```

## Multi-Language Support

The API automatically detects the language of your question and responds in the same language:

**French Query:**
```json
{
  "question": "Quels sont les événements pour enfants ce weekend?"
}
```

**English Query:**
```json
{
  "question": "What cultural events are happening this weekend?"
}
```

## Query Examples

### Finding Specific Event Types

```json
{"question": "Trouve-moi des expositions d'art contemporain"}
{"question": "Show me theater performances for children"}
{"question": "Quels festivals de musique ont lieu en juillet?"}
```

### Location-Based Queries

```json
{"question": "What events are happening in Paris this month?"}
{"question": "Y a-t-il des événements gratuits à Versailles?"}
```

### Date-Specific Queries

```json
{"question": "What's happening this weekend?"}
{"question": "Quels événements sont prévus en mars?"}
{"question": "Show me spring festivals"}
```

### Category-Based Queries

```json
{"question": "Je cherche des concerts de musique classique"}
{"question": "Are there any sports events?"}
{"question": "Expositions et galeries d'art"}
```

## Technical Details

### Response Time

- **Health Check:** < 100ms
- **Chat Queries:** 2-7 seconds (includes embedding generation, vector search, and LLM generation)

### Rate Limiting

Currently no rate limiting (POC). In production, consider:
- Rate limiting per IP
- API key authentication
- Request quotas

### Error Responses

**503 Service Unavailable:**
```json
{
  "detail": "RAG system not initialized"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error message describing the issue"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "question"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Starting the Server

### Development Mode

```bash
# With auto-reload
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the module directly
poetry run python -m src.api.main
```

### Production Mode

```bash
# Single worker
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1

# Multiple workers (for higher throughput)
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Note:** The RAG chain loads during startup and takes approximately 7 seconds to initialize. Wait for the "Application startup complete" log message before making requests.

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Architecture

```
┌──────────────┐
│  HTTP Client │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────┐
│      FastAPI Endpoints       │
│  - /health (GET)             │
│  - /chat (POST)              │
└──────────┬───────────────────┘
           │
           ↓
┌──────────────────────────────┐
│       RAG Chain              │
│  1. Embed query (Mistral)    │
│  2. Search FAISS (1000 events)│
│  3. Retrieve top-k events    │
│  4. Generate answer (Mistral)│
└──────────────────────────────┘
```

## Python Client Example

```python
import requests

API_BASE = "http://localhost:8000/api/v1"

def ask_about_events(question: str) -> dict:
    """Query the cultural events API."""
    response = requests.post(
        f"{API_BASE}/chat",
        json={"question": question},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Example usage
result = ask_about_events("What jazz concerts are happening this month?")
print(f"Answer: {result['answer']}")
print(f"\nFound {len(result['sources'])} relevant events:")
for event in result['sources']:
    print(f"- {event['title']} ({event['location']['city']})")
```

## Testing

```bash
# Run API tests
poetry run pytest tests/test_api.py -v

# Test with curl
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Test query"}'
```

## Troubleshooting

### Server Not Responding

1. **Check if server is running:** `netstat -ano | findstr :8000`
2. **Check logs:** Look for "Application startup complete" message
3. **Wait for initialization:** RAG chain takes ~7 seconds to load
4. **Kill zombie processes:** `taskkill /F /PID <pid>`

### Slow Responses

- Normal: 2-7 seconds per query
- If slower: Check Mistral API rate limits or network latency

### 503 Service Unavailable

- RAG chain failed to initialize
- Check that FAISS index exists at `data/faiss_index/index.faiss`
- Rebuild index: `poetry run python -m src.models.vector_store`

## Data Pipeline

To refresh the event data:

```bash
# Re-ingest events (clears existing data)
poetry run python -m src.data.ingestion --force

# Rebuild FAISS index
poetry run python -m src.models.vector_store
```

## Security Considerations (Production)

1. **API Keys:** Implement authentication
2. **Rate Limiting:** Prevent abuse
3. **CORS:** Restrict allowed origins
4. **Input Validation:** Sanitize user queries
5. **HTTPS:** Use TLS in production
6. **Secrets:** Never expose Mistral API key

## Support

For issues or questions:
- GitHub: [Repository URL]
- Documentation: [docs/](../docs/)
