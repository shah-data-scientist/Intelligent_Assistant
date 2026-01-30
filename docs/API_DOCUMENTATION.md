# API Documentation - Cultural Events RAG Assistant

## Overview

The Cultural Events RAG Assistant exposes a RESTful API built with FastAPI that provides access to the RAG system for cultural event discovery in Île-de-France.

**Base URL**: `http://localhost:8000` (local deployment)

**Authentication**: API Key via `X-API-Key` header

**API Documentation (Swagger)**: http://localhost:8000/docs

**Alternative Docs (ReDoc)**: http://localhost:8000/redoc

---

## Authentication

All endpoints (except `/health` and `/metrics`) require authentication via API key.

**Header Format**:
```
X-API-Key: your-api-key-here
```

**Configuration**:
- API key is set in `.env` file: `APP_API_KEY=your-secret-key`
- Default for development: Check `.env.example`

**Example Request**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "jazz concerts in Paris?"}'
```

**Authentication Errors**:
- `403 Forbidden`: Invalid or missing API key

---

## Rate Limiting

Rate limits are enforced per IP address:

| Endpoint | Rate Limit |
|----------|------------|
| `/chat` | 20 requests/minute |
| `/feedback` | 100 requests/minute |
| `/health` | Unlimited |
| `/metrics` | Unlimited |

**Rate Limit Headers** (included in response):
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 19
X-RateLimit-Reset: 1706724120
```

**Rate Limit Errors**:
- `429 Too Many Requests`: Rate limit exceeded

---

## Endpoints

### 1. Health Check

**GET /health**

Check if the API and RAG system are running properly.

**Authentication**: None required

**Request**:
```bash
curl http://localhost:8000/health
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "rag_system": "initialized",
  "service": "Intelligent Assistant API"
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| status | string | "ok" if system is healthy, "error" otherwise |
| rag_system | string | "initialized" or "not_initialized" |
| service | string | Service name |

**Use Cases**:
- Health check for monitoring systems
- Verify system initialization before making chat requests
- Load balancer health probe

---

### 2. Chat Query

**POST /chat**

Submit a natural language question about cultural events and receive an AI-generated response with event recommendations.

**Authentication**: Required (API Key)

**Rate Limit**: 20 requests/minute

**Request Body**:
```json
{
  "question": "jazz concerts in Paris this weekend?",
  "session_id": "user-123-session-456",
  "language": "en"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question | string | ✅ Yes | User's natural language query |
| session_id | string | ❌ No | Session ID for conversation tracking (default: auto-generated) |
| language | string | ❌ No | Preferred language: "fr" or "en" (default: auto-detected) |

**Example Request**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Concerts de jazz à Paris ce week-end?",
    "session_id": "session-001",
    "language": "fr"
  }'
```

**Response** (200 OK):
```json
{
  "answer": "Voici 5 concerts de jazz à Paris ce week-end:\n\n1. **Jazz au Sunset**\n   📍 Paris, Sunset Sunside\n   📅 2026-02-01 20:00\n   🎭 Musique\n\n2. **Trio Vocal**...",
  "sources": [
    {
      "event_id": "12345",
      "title": "Jazz au Sunset",
      "start_date": "2026-02-01T20:00:00",
      "city": "Paris",
      "venue": "Sunset Sunside",
      "category": "Musique",
      "url": "https://example.com/event/12345"
    }
  ],
  "structured_events": [
    {
      "title": "Jazz au Sunset",
      "location": "Paris",
      "date": "2026-02-01",
      "category": "Musique",
      "event_id": "12345"
    }
  ],
  "message_id": 42,
  "needs_clarification": false,
  "clarifying_questions": []
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| answer | string | Natural language response with event details |
| sources | array | List of event objects with full metadata |
| structured_events | array | Simplified event list for programmatic use |
| message_id | integer | Unique ID for this response (for feedback) |
| needs_clarification | boolean | True if query is ambiguous |
| clarifying_questions | array | Suggested questions to refine the query |

**Source Object Fields**:
| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Unique event identifier |
| title | string | Event title |
| start_date | string | ISO 8601 datetime |
| city | string | Event city |
| venue | string | Venue name |
| category | string | Event category (Musique, Exposition, etc.) |
| url | string | Event URL for more info |
| description | string | Event description (optional) |
| organizer | string | Organizer name (optional) |
| image_url | string | Event image (optional) |

**Error Responses**:

**400 Bad Request** (Security Violation):
```json
{
  "detail": "Inappropriate content detected in query"
}
```

**403 Forbidden** (Blocked Session):
```json
{
  "detail": "Session blocked due to repeated policy violations"
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Error message"
}
```

**Use Cases**:
- Chatbot integration: Multi-turn conversations with context
- Event search: Simple keyword queries
- Bilingual support: French or English queries
- Follow-up questions: "show me more", "for kids", "free events"

**Notes**:
- Session tracking enables conversation memory (filters carry over)
- Language auto-detection if not specified
- Security guardrails check for profanity, prompt injection, PII
- PII in responses is automatically redacted

---

### 3. Feedback Submission

**POST /feedback**

Submit user feedback (thumbs up/down) for a specific assistant response.

**Authentication**: Required (API Key)

**Rate Limit**: 100 requests/minute

**Request Body**:
```json
{
  "message_id": 42,
  "is_positive": true,
  "comment": "Great recommendations!"
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | integer | ✅ Yes | Message ID from chat response |
| is_positive | boolean | ✅ Yes | true = thumbs up, false = thumbs down |
| comment | string | ❌ No | Optional feedback comment |

**Example Request**:
```bash
curl -X POST http://localhost:8000/feedback \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": 42,
    "is_positive": true,
    "comment": "Excellent recommendations, very relevant!"
  }'
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Feedback submitted"
}
```

**Error Responses**:

**500 Internal Server Error**:
```json
{
  "detail": "Failed to submit feedback"
}
```

**Use Cases**:
- Collect user satisfaction metrics
- Identify problematic responses
- Train future versions of the model
- Quality assurance

---

### 4. System Metrics

**GET /metrics**

Get system metrics including circuit breaker state and health information.

**Authentication**: None required

**Response** (200 OK):
```json
{
  "circuit_breaker": {
    "name": "llm_circuit_breaker",
    "state": "closed",
    "failure_count": 0,
    "failure_threshold": 3,
    "reset_timeout": 60,
    "last_failure": null
  },
  "uptime_seconds": 3600,
  "total_requests": 1523
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| circuit_breaker.state | string | "closed", "open", or "half_open" |
| circuit_breaker.failure_count | integer | Current consecutive failures |
| circuit_breaker.failure_threshold | integer | Max failures before opening |
| circuit_breaker.reset_timeout | integer | Seconds before half-open attempt |
| uptime_seconds | integer | API uptime in seconds |
| total_requests | integer | Total requests processed |

**Circuit Breaker States**:
- **closed**: Normal operation, requests pass through
- **open**: Too many failures, all requests rejected
- **half_open**: Testing if service recovered

**Use Cases**:
- Monitoring dashboards (Grafana, Datadog)
- Alerting on circuit breaker open state
- Performance tracking

---

## Error Codes Summary

| HTTP Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Security violation, malformed input |
| 403 | Forbidden | Invalid API key, blocked session |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | System error, LLM failure |
| 503 | Service Unavailable | RAG system not initialized |

---

## Integration Examples

### Python (requests)

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-api-key"

def ask_question(question: str, session_id: str = None, language: str = None):
    """Query the RAG system."""
    response = requests.post(
        f"{API_URL}/chat",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "question": question,
            "session_id": session_id or "default-session",
            "language": language
        }
    )
    response.raise_for_status()
    return response.json()

def submit_feedback(message_id: int, is_positive: bool, comment: str = None):
    """Submit feedback for a response."""
    response = requests.post(
        f"{API_URL}/feedback",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "message_id": message_id,
            "is_positive": is_positive,
            "comment": comment
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
result = ask_question("jazz concerts in Paris?", language="en")
print(result["answer"])

for event in result["sources"]:
    print(f"- {event['title']} at {event['venue']}")

# Submit positive feedback
submit_feedback(result["message_id"], is_positive=True)
```

### JavaScript (fetch)

```javascript
const API_URL = "http://localhost:8000";
const API_KEY = "your-api-key";

async function askQuestion(question, sessionId = null, language = null) {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      session_id: sessionId || "default-session",
      language
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

async function submitFeedback(messageId, isPositive, comment = null) {
  const response = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message_id: messageId,
      is_positive: isPositive,
      comment
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

// Usage
(async () => {
  const result = await askQuestion("jazz concerts in Paris?", null, "en");
  console.log(result.answer);

  result.sources.forEach(event => {
    console.log(`- ${event.title} at ${event.venue}`);
  });

  // Submit positive feedback
  await submitFeedback(result.message_id, true);
})();
```

### cURL

```bash
# Ask a question
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "jazz concerts in Paris?",
    "session_id": "session-001",
    "language": "en"
  }' | jq

# Submit feedback
curl -X POST http://localhost:8000/feedback \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": 42,
    "is_positive": true,
    "comment": "Great!"
  }'

# Check health
curl http://localhost:8000/health | jq

# Get metrics
curl http://localhost:8000/metrics | jq
```

---

## Security Features

### Input Validation
- **Profanity Detection**: Unicode-aware pattern matching
- **Prompt Injection Prevention**: 20+ attack pattern detection
- **PII Sanitization**: Automatic redaction of emails, phone numbers

### Session Blocking
- Repeated security violations result in session blocking
- Blocked sessions receive `403 Forbidden` for subsequent requests
- Block duration: 1 hour (configurable)

### Output Safety
- **PII Redaction**: Sensitive data removed from responses
- **LLM Grounding**: Responses constrained to source documents
- **Content Filtering**: Mistral's built-in safety features

---

## Performance Considerations

### Latency
- **Median**: 2-3 seconds per query
- **P95**: 4-6 seconds
- **Breakdown**:
  - Query analysis: ~200ms
  - Retrieval: ~50ms
  - LLM generation: ~1.8s

### Throughput
- **Max**: ~30 queries/second (single instance)
- **Rate limit**: 20 requests/minute per IP (chat endpoint)

### Caching
- LLM responses are NOT cached (each query is unique)
- FAISS index is memory-resident (fast lookups)

---

## Troubleshooting

### Common Issues

**403 Forbidden**:
- Check `X-API-Key` header is set correctly
- Verify API key matches `.env` configuration
- Check if session is blocked (use new session_id)

**500 Internal Server Error**:
- Check API logs for stack trace
- Verify Mistral API key is valid
- Check FAISS index exists at `data/faiss_index/`

**Empty Results**:
- Query too specific (no matching events)
- Try broader search terms
- Check database has events (`data/events.db`)

**Slow Responses**:
- LLM generation takes 1-2 seconds (normal)
- Network latency to Mistral API
- Large conversation history (>10 messages)

### Debugging

**Enable Debug Logging**:
```bash
export LOG_LEVEL=DEBUG
poetry run uvicorn src.api.main:app --reload
```

**Check Circuit Breaker**:
```bash
curl http://localhost:8000/metrics | jq '.circuit_breaker'
```

**Inspect Database**:
```bash
sqlite3 data/events.db "SELECT COUNT(*) FROM events;"
sqlite3 data/chat_history.db "SELECT * FROM conversations ORDER BY id DESC LIMIT 10;"
```

---

## API Versioning

**Current Version**: v1 (implicit)

Future versions will use URL prefix: `/v2/chat`

Breaking changes will be communicated via:
- Release notes
- Deprecation warnings (3-month notice)
- Migration guides

---

## Support

**Documentation**:
- [System Architecture](SYSTEM_ARCHITECTURE.md)
- [Technical Report](../TECHNICAL_REPORT.md)
- [Deployment Guide](../README.md)

**Interactive API Docs**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Contact**:
- GitHub Issues: [Report bugs or request features]
- Email: [Your contact email]

---

**Last Updated**: 2026-01-30
