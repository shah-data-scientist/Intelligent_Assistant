# RAG Pipeline Data Flow (January 2026)

This document describes the complete data flow from user query to response.

---

## Overview Diagram

```
USER QUERY
    │
    ▼
┌─────────────────────────────────────────┐
│ 1. API ENDPOINT (endpoints.py)          │
│    - API key validation                 │
│    - Rate limiting (20/min)             │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 2. SECURITY CHECK (guardrails.py)       │
│    - Prompt injection detection         │
│    - Profanity filtering                │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 3. UNIFIED ANALYSIS (LLM Call #1)       │
│    - Language detection (fr/en)         │
│    - Intent classification              │
│    - Multi-dimensional analysis         │
│    - Entity extraction                  │
│    - Filter extraction                  │
│    - Completeness check                 │
└─────────────────────────────────────────┘
    │
    ├── [Special Query] → Early Response
    │
    ▼
┌─────────────────────────────────────────┐
│ 4. SESSION FILTER MERGE (chain.py)      │
│    - Merge with previous turn filters   │
│    - Accumulate search terms            │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 5. MULTI-STAGE RETRIEVAL (manager.py)   │
│    - Stage 1: Exact match (FAISS+BM25)  │
│    - Stage 2: Nearby locations fallback │
│    - Stage 3: Alternative dates check   │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 6. RESPONSE GENERATION (LLM Call #2)    │
│    - Language-aware prompt (fr/en)      │
│    - Grounded on retrieved sources      │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 7. PERSISTENCE (chat_storage.py)        │
│    - User message (async)               │
│    - Assistant message (sync)           │
└─────────────────────────────────────────┘
    │
    ▼
RESPONSE
```

---

## Step-by-Step Details

### 1. API Entry Point

**File:** `src/api/endpoints.py` → `chat()`

```python
@router.post("/chat")
def chat(request: Request, chat_request: ChatRequest):
    # Input: session_id, question, language (optional)
    # Calls: chain.query_with_metadata()
```

**Checks:**
- API key validation via `X-API-Key` header
- Rate limiting: 20 requests/minute per IP

---

### 2. Security Check

**File:** `src/security/guardrails.py` → `check_safety()`

**Detections:**
- Prompt injection patterns (20+ patterns)
- Profanity (with Unicode normalization for evasion attempts)

**Result:** Raises `SecurityException` if unsafe.

---

### 3. Unified Analysis (LLM Call #1)

**File:** `src/retrieval/unified_analyzer.py` → `unified_analyze()`

This is a single LLM call that extracts everything including language:

**Input:**
- User query
- Chat history (for context carryover)
- Known cities list (for normalization)

**Output (`UnifiedAnalysisResult`):**
```python
@dataclass
class UnifiedAnalysisResult:
    intent: QueryIntent              # event_search, greeting, chitchat, etc.
    intent_confidence: float         # 0.0 - 1.0
    dimensions: Dict[str, QueryDimension]  # greeting, typo, statistical, scope
    detected_language: str           # "fr" or "en" (LLM-detected)
    city: str                        # Raw city from user
    city_normalized: str             # Normalized to official name
    event_type: str                  # concert, exhibition, etc.
    timeframe: str                   # "this weekend", "February", etc.
    is_complete: bool                # Has 2 of 3 criteria?
    missing_criteria: List[str]      # What's missing
    filters: Dict[str, Any]          # city, month, day, year, category, etc.
    refined_query: str               # Typo-corrected query
```

**Language Detection:**
The LLM detects language by analyzing:
- French articles/prepositions: de, à, en, la, le, les, du, des, pour, dans, avec
- French greetings: bonjour, salut, bonsoir
- French question words: où, quand, combien, qu'est-ce
- Accented characters: é, è, ê, à, ù, ç, œ

Example:
- "Concerts de jazz à Paris" → `detected_language: "fr"`
- "Jazz concerts in Paris" → `detected_language: "en"`

**Multi-Dimensional Analysis:**
| Dimension | Description |
|-----------|-------------|
| greeting | Query starts with hello/bonjour |
| typo | Spelling correction applied |
| statistical | Asking "how many" or "combien" |
| scope | All events vs specific type |

**Completeness Rule (2 out of 3):**
A query is complete if it has at least 2 of:
- city
- timeframe
- event_type

**Category Mapping:**
```python
CATEGORY_MAPPING = {
    "concert": "Musique",
    "jazz": "Musique",
    "exposition": "Art / Exposition",
    "theatre": "Théâtre / Spectacle",
    ...
}
```

**Early Responses (no RAG needed):**
| Intent | Response |
|--------|----------|
| greeting | Welcome message |
| chitchat | Friendly redirect |
| capability | Help description |
| abuse | Polite response |
| off_topic | Decline with suggestion |
| out_of_scope_city | Coverage message |
| incomplete query | Clarification questions |

---

### 4. Session Filter Merge

**File:** `src/retrieval/chain.py` → `_merge_with_previous_filters()`

For multi-turn conversations, preserves context:
- Filters not explicitly changed are carried over
- Search terms accumulate across turns

**Example:**
```
Turn 1: "Concerts de jazz à Paris"
  → Stored: {city: "Paris", category: "Musique"}

Turn 2: "En février plutôt"
  → Previous: {city: "Paris", category: "Musique"}
  → New: {month: 2}
  → Merged: {city: "Paris", category: "Musique", month: 2}
```

---

### 5. Multi-Stage Retrieval

**File:** `src/retrieval/manager.py` → `RetrievalManager.execute_search()`

**Stage 1: Exact Match**
```
FAISS semantic search + BM25 keyword search → RRF fusion
Apply filters: city, month, day, year, category, is_free, audience
```

**Stage 2: Nearby Locations (if < k results)**
```
Remove city filter, keep date strict
Search all Île-de-France
Sort by haversine distance from target city
```

**Stage 3: Alternative Dates Check**
```
Count events in same city within ±7 days
Add SYSTEM_NOTE if alternatives exist
```

**SearchIntent Structure:**
```python
@dataclass
class SearchIntent:
    city: Optional[str]
    month: Optional[int]
    day: List[int]
    year: int = 2026
    date_min: Optional[date]
    date_max: Optional[date]
    category: Optional[str]
    is_free: Optional[bool]
    audience: Optional[str]
```

---

### 6. Response Generation (LLM Call #2)

**File:** `src/generation/prompts.py` → `get_rag_prompt()`

**Prompt Structure:**
- System message: Grounding rules, today's date, output format
- Chat history: Previous messages
- Human message: Question + SOURCES (retrieved events)

**Language-Aware Prompts:**
The system prompt is selected based on `detected_language`:
- `detected_language: "fr"` → French prompt (RAG_SYSTEM_PROMPT_FR)
- `detected_language: "en"` → English prompt (RAG_SYSTEM_PROMPT_EN)

**Grounding Rules:**
1. List ONLY events from SOURCES
2. NEVER fabricate titles, dates, cities, prices, URLs
3. OMIT fields if not in SOURCE
4. Verify EVERY detail comes from a SOURCE

**Output Format:**
```json
{
  "answer_text": "Human-readable response",
  "events": [
    {
      "title": "Event Title",
      "date": "2026-02-15",
      "city": "Paris",
      "location": "Venue Name",
      "url": "https://...",
      "match_type": "Exact Match"
    }
  ]
}
```

---

### 7. Persistence

**File:** `src/data/chat_storage.py`

- **User message:** Written async (fire-and-forget)
- **Assistant message:** Written sync (need message_id for feedback)

```python
_async_db_write(chat_storage.add_chat_message, session_id, "user", question)
message_id = chat_storage.add_chat_message(session_id, "assistant", answer_text)
```

---

## Response Structure

```python
{
    "answer": str,                    # Human-readable text with filters/hints
    "structured_events": [...],       # Parsed event objects (max 8)
    "message_id": int,                # For feedback submission
    "sources": [...],                 # Source documents with metadata
    "retrieval_stats": {
        "total_count": int,
        "exact_count": int,
        "nearby_count": int
    },
    "needs_clarification": bool,
    "clarifying_questions": [...]
}
```

---

## Key Files

| File | Responsibility |
|------|----------------|
| `src/api/endpoints.py` | API entry point, rate limiting |
| `src/retrieval/chain.py` | Main orchestration, session management |
| `src/retrieval/unified_analyzer.py` | LLM-based query analysis + language detection |
| `src/retrieval/manager.py` | Multi-stage retrieval |
| `src/generation/prompts.py` | LLM prompt templates (FR/EN) |
| `src/security/guardrails.py` | Safety checks |
| `src/data/chat_storage.py` | Conversation persistence |
| `src/models/vector_store.py` | FAISS + BM25 hybrid search |

---

## LLM Calls Summary

| Call | Purpose | Includes | Latency |
|------|---------|----------|---------|
| #1 Unified Analysis | Intent + entities + filters | Language detection | ~2-3s |
| #2 Response Generation | Grounded answer | Language-aware prompt | ~3-5s |

**Total typical latency:** 5-10s for complete queries.

---

*Last updated: January 29, 2026*
