# Complete RAG Pipeline Data Flow (Production - January 2026)

## Overview

This document describes the complete data flow from user query to response, including all validation, retrieval, and generation steps. **All optimizations are ACTIVE in production code.**

**Key Optimizations (ALL ACTIVE):**
- Pre-compiled regex patterns (~10% faster matching)
- **Early broad query detection BEFORE LLM calls** (saves ~5-8s for vague queries)
- **Early city validation with fuzzy matching BEFORE LLM calls**
- **Statistical query handling merged into fast path** (no LLM)
- **Async database writes** (fire-and-forget for user messages)
- Strict 3-criteria requirement (city + event_type + date)
- Fuzzy city matching for typo tolerance (Levenshtein distance)
- Centralized clarification templates
- Unified query understanding (1 LLM call instead of 3)
- **Database-backed keyword detection** (333 event keywords, 78 date keywords with fuzzy matching)
- **Lazy FAISS index loading** (delay load until first query)
- **Eliminated redundant function calls** (is_broad_query, language detection reuse)
- **Pre-computed display labels** (`price_label`, `age_label` in database - no runtime enrichment)
- **Database deduplication** (no runtime consolidation needed)

---

## 1. Entry Point: API Endpoint

**File:** `src/api/endpoints.py` → `chat()` function

```
User Query (ChatRequest)
    │
    ├── session_id: str
    ├── question: str
    └── language: Optional[str]
```

**Checks performed:**
- API key validation (middleware)
- Rate limiting (slowapi)
- Request validation (Pydantic schema)

---

## 2. RAG Chain Entry: `query_with_metadata()`

**File:** `src/retrieval/chain.py` → `RAGChain.query_with_metadata()` (line 908)

### Step 2.1: Safety Check
```
question → check_safety(question)
```
**File:** `src/security/guardrails.py` (line 153)

**Checks (PRE-COMPILED patterns for ~10% speedup):**
| Check | Patterns | Method |
|-------|----------|--------|
| Prompt Injection | 20+ patterns (MALICIOUS_PATTERNS) | Pre-compiled regex |
| Profanity | Word-boundary phrases (PROFANITY_PHRASES) | Pre-compiled + Unicode normalization |

**Unicode Normalization:**
- Homoglyph detection: `fuсk` (Cyrillic с) → `fuck`
- Leetspeak: `f4ck` → `fack`
- Accented chars: `fück` → `fuck`

**Result:** Raises `SecurityException` if unsafe, otherwise continues.

---

### Step 2.2: Language Detection
```
language → detect_language_from_query(question)
```
**File:** `src/retrieval/chain.py` (line 234)

**Logic:**
- Checks for French indicator words
- Returns "fr" if ≥1 French word found, else "en"

---

### Step 2.3: Special Query Detection (FAST PATH - No LLM)
```
question + language → check_special_query()
```
**File:** `src/retrieval/chain.py` (line 573)

**OPTIMIZATIONS MERGED HERE:**
1. **Statistical query detection** - Previously separate, now integrated
2. **Early fuzzy city matching** - Typo correction before marking out-of-scope

**Checks (in order, ALL PRE-COMPILED):**

| Check | Response | LLM Used? | Query Type |
|-------|----------|-----------|------------|
| Greeting | Welcome message | **NO** | `greeting` |
| Capability | Help description | **NO** | `capability` |
| Off-topic | Polite decline | **NO** | `off_topic` |
| **Statistical** | Polite redirect | **NO** | `statistical` |
| City typo (fuzzy match) | Suggestion message | **NO** | `city_typo_suggestion` |
| Out-of-scope city | Coverage message | **NO** | `out_of_scope_city` |

**Early City Validation with Fuzzy Matching:**
`detect_out_of_scope_city()` now returns `(city, suggested_city)` tuple:
- `("Possy", "Poissy")` → Typo detected, suggest correction
- `("Delhi", None)` → Out of scope, no suggestion
- `(None, None)` → City is valid or no city mentioned

---

### Step 2.4: Cache Check
```
(question, session_id) → cache.get()
```
**File:** `src/retrieval/cache.py`

**Result:** If cached → Return cached response with re-enrichment.

---

## 3. EARLY BROAD QUERY CHECK (OPTIMIZATION - BEFORE LLM)

**File:** `src/retrieval/chain.py` (line 957-986)

```python
# OPTIMIZATION: EARLY BROAD QUERY CHECK
# Check if query is missing required criteria BEFORE calling LLM
# This saves ~5-8s and API costs for vague queries
is_broad, broad_reason = is_broad_query(question, chat_history)
if is_broad:
    # Return clarification immediately - NO LLM CALL
    return clarification_response
```

### Database-Backed Keyword Detection (KeywordLocator)

**File:** `src/utils/keywords.py` → `KeywordLocator` class

**Database Table:** `search_keywords` (404 total entries)
| Keyword Type | Count | Examples |
|--------------|-------|----------|
| Date keywords | 78 | janvier, février, today, weekend, prochain |
| Event keywords | 333 | concert, jazz, exposition, vernissage, ballet |

**Detection Methods:**
1. **Exact match** - keyword in database
2. **Known typo match** - from pre-defined typo lists in `typos` column
3. **Fuzzy match** - Levenshtein distance (SequenceMatcher, threshold 0.80)
4. **Date format patterns** - Regex for DD/MM/YYYY, "15 janvier", etc.

**Typo Examples Handled:**
- `wekend` → `weekend` (fuzzy match, 0.95 confidence)
- `febrier` → `février` (typo match, 0.95 confidence)
- `expostion` → `exposition` (fuzzy match, 0.91 confidence)

**Event Keywords → Category Mapping:**
- `jazz`, `rock`, `classical` → `Musique`
- `exposition`, `vernissage` → `Art`
- `ballet`, `chorégraphie` → `Danse`
- `atelier`, `workshop` → `Atelier`

---

**STRICT 3-CRITERIA CHECK:**
| Criterion | Detection Method | Examples |
|-----------|------------------|----------|
| City | CityLocator (geo.py) | Paris, Versailles, île-de-france |
| Event Type | **KeywordLocator** (keywords.py) | concerts, jazz, expositions + 330 more |
| Date/Timeframe | **KeywordLocator** (keywords.py) | ce week-end, février, today + patterns |

**If ANY criterion missing → Return clarification from `clarifications.py` (NO LLM)**

**Possible reasons (from query OR conversation history):**
- `missing_city`
- `missing_event_type`
- `missing_date`
- `missing_city+event_type`
- `missing_city+date`
- `missing_event_type+date`
- `missing_city+event_type+date`

**EXCEPTION:** Explicit broad intent words bypass check:
`all, everything, anything, tous, tout, toutes, n'importe, whatever, any`

---

## 4. RAG Chain Invocation (Only if query is complete)

**File:** `src/retrieval/chain.py` → `self.rag_chain.invoke()` (line 988)

### Step 4.1: Unified Query Understanding (1 LLM Call)

```
question + chat_history → unified_understanding_chain.invoke()
```
**File:** `src/generation/prompts.py` → `get_query_understanding_prompt()`

**OPTIMIZATION:** Previously 3 LLM calls (~15-24s), now 1 call (~5-8s)

**LLM extracts:**
```json
{
  "refined_query": "corrected and expanded query",
  "filters": {
    "city": "Paris",
    "month": 2,
    "category": "Musique"
  },
  "needs_clarification": false,
  "clarifying_questions": []
}
```

---

### Step 4.2: Intent Parsing
```
raw_filters → retrieval_manager.parse_intent()
```
**File:** `src/retrieval/manager.py` (line 38)

**Note:** `manager.py` IS the active production code (no orchestrator.py exists).

---

### Step 4.3: Multi-Stage Retrieval
```
refined_query + intent → retrieval_manager.execute_search()
```
**File:** `src/retrieval/manager.py` (line 85)

**Stages:**

#### Stage 1: Exact Match Search
```
FAISS semantic search + BM25 keyword search → RRF fusion
Apply all filters: city, month, day, year, date_min, date_max, category, period
```

#### Stage 2: Nearby Location Fallback
If results < k AND city specified:
```
Keep date strict, remove city filter
Search all Île-de-France, sort by haversine distance from target city
```

#### Stage 3: Alternative Dates Check (Metadata Only)
If city specified AND date filter present:
```
Count events in same city within ±7 days window
Add SYSTEM_NOTE to inform user of alternatives
```

---

### Step 4.4: LLM Response Generation (1 LLM Call)
```
context + question + chat_history → RAG prompt → LLM
```
**File:** `src/generation/prompts.py` → `get_rag_prompt(language)`

**LLM generates:**
```json
{
  "answer_text": "Human-readable response",
  "events": [...],
  "needs_clarification": false,
  "clarifying_questions": []
}
```

---

## 5. Post-Processing (Minimal)

### Step 5.1: LLM Clarification Check
If LLM flagged `needs_clarification=True` with questions → Show only questions, no events.

### Step 5.2: Response Sanitization
Remove emojis and problematic Unicode characters (optional for modern systems).

**REMOVED (Phase 15/16):**
- ~~Event Limit~~ → Now enforced in `manager.py` (single source of truth)
- ~~Backup Broad Query~~ → Dead code (early check always returns if broad)
- ~~Metadata Enrichment~~ → Pre-computed in database (`price_label`, `age_label`)
- ~~Deduplication~~ → Database already deduplicated (Phase 14)

---

## 6. Persistence (OPTIMIZED - Async Writes)

**File:** `src/retrieval/chain.py`

### OPTIMIZATION: Async Database Writes
```python
def _async_db_write(func, *args, **kwargs):
    """Execute database write in background thread (fire-and-forget)."""
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
```

**Implementation:**
- **User messages:** Written async (fire-and-forget) - reduces latency
- **Assistant messages:** Written sync (need message_id for feedback)

```python
# User message - async (don't wait)
_async_db_write(self.chat_storage.add_chat_message, session_id, "user", question)

# Assistant message - sync (need message_id)
message_id = self.chat_storage.add_chat_message(session_id, "assistant", answer_text)
```

---

## 7. Response Assembly

```python
{
    "answer": str,              # Human-readable text
    "structured_events": [...], # List of event objects (max 8)
    "message_id": int,          # For feedback
    "sources": [...],           # Source documents
    "retrieval_stats": {...},   # Counts and match types
    "needs_clarification": bool,
    "clarifying_questions": []
}
```

---

## Optimized Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. API LAYER                                                                 │
│    ├── API Key Validation                                                   │
│    ├── Rate Limiting                                                        │
│    └── Request Validation                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. SAFETY CHECK (Pre-compiled patterns)                                     │
│    ├── Prompt injection (20+ patterns)                                      │
│    └── Profanity (Unicode normalized)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. ★ SPECIAL QUERY FAST PATH (No LLM) ★ [ALL PRE-COMPILED]                  │
│    ├── Greeting → Welcome response                                          │
│    ├── Capability → Help response                                           │
│    ├── Off-topic → Decline response                                         │
│    ├── ★ Statistical → Redirect response [MERGED HERE]                      │
│    ├── ★ City typo → Suggestion with fuzzy match [EARLY FUZZY]              │
│    └── Out-of-scope city → Coverage message                                 │
│                                                                              │
│    ALL handled WITHOUT LLM call (~100ms response time)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. CACHE CHECK → If hit, return cached (No LLM)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. ★ EARLY BROAD QUERY CHECK ★ [OPTIMIZATION - BEFORE LLM]                  │
│    ├── Check 3-criteria (city + event_type + date)                          │
│    │   ├── City: CityLocator (database-backed, fuzzy)                       │
│    │   ├── Event Type: ★ KeywordLocator (333 keywords, fuzzy) ★             │
│    │   └── Date: ★ KeywordLocator (78 keywords + patterns) ★                │
│    ├── Check conversation history context                                   │
│    └── If ANY missing → Return clarification (NO LLM CALL!)                 │
│        └── Saves ~5-8s and API costs for vague queries                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                         [Only if query is COMPLETE]
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. QUERY UNDERSTANDING (1 LLM Call) [Was 3 calls]                           │
│    ├── Reformulate query                                                    │
│    ├── Extract filters                                                      │
│    └── Detect clarification needs                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. MULTI-STAGE RETRIEVAL                                                    │
│    ├── Stage 1: Exact match (FAISS + BM25 + RRF + period filter)            │
│    ├── Stage 2: Nearby location fallback (keep date, remove city)           │
│    └── Stage 3: Alternative dates check (metadata only, ±7 days)            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. RESPONSE GENERATION (1 LLM Call)                                         │
│    ├── Language-aware prompt selection                                      │
│    ├── Generate answer_text                                                 │
│    └── Structure events list                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 9. POST-PROCESSING                                                          │
│    ├── Enrich metadata (price, age, times)                                  │
│    ├── Deduplicate & consolidate                                            │
│    ├── Enforce event limit (max 8)                                          │
│    ├── Backup broad query check (if LLM missed)                             │
│    └── Response sanitization                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 10. PERSISTENCE [OPTIMIZED - Async Writes]                                  │
│    ├── User message → ASYNC (fire-and-forget, ~50ms saved)                  │
│    └── Assistant message → Sync (need message_id)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RESPONSE                                        │
│    {answer, structured_events, message_id, sources, ...}                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files Summary

| File | Responsibility |
|------|----------------|
| `src/api/endpoints.py` | API entry point |
| `src/retrieval/chain.py` | Main orchestration, early checks, async writes |
| `src/retrieval/manager.py` | Multi-stage retrieval (ACTIVE production code) |
| `src/retrieval/clarifications.py` | Centralized clarification templates |
| `src/models/vector_store.py` | FAISS + BM25 hybrid search |
| `src/generation/prompts.py` | LLM prompt templates |
| `src/security/guardrails.py` | Safety checks (pre-compiled) |
| `src/utils/geo.py` | City validation, fuzzy matching |
| `src/utils/keywords.py` | **Database-backed keyword detection (dates, event types)** |
| `src/data/chat_storage.py` | Persistent chat history |
| `scripts/migrate_search_keywords.py` | Database migration for search_keywords table |

---

## Active Optimizations Summary

| Optimization | Status | Impact | Location |
|--------------|--------|--------|----------|
| Pre-compiled regex | ACTIVE | ~10% faster matching | guardrails.py, chain.py |
| Early broad query check | ACTIVE | Saves ~5-8s for vague queries | chain.py:957 |
| **Early city validation + fuzzy** | ACTIVE | Fast rejection OR correction | chain.py:573 |
| **Statistical query merged** | ACTIVE | No separate check needed | chain.py:573 |
| Async DB writes | ACTIVE | ~50ms latency reduction | chain.py:37 |
| Unified query understanding | ACTIVE | 3 LLM calls → 1 | chain.py:764 |
| Fuzzy city matching | ACTIVE | Better typo tolerance | geo.py:113 |
| Enhanced skip_words | ACTIVE | Fewer false city detections | chain.py:270 |
| **Database-backed keywords** | ACTIVE | 333 event + 78 date keywords with fuzzy | keywords.py |
| **Lazy FAISS loading** | ACTIVE | Faster chain init, load on first query | chain.py:717, 848 |
| **Redundant call elimination** | ACTIVE | is_broad_query called once, result reused | chain.py:905, 1005 |

---

## Validation Points Summary

| Stage | What's Checked | Action on Failure | LLM Used? |
|-------|---------------|-------------------|-----------|
| API | API key, rate limit | 401/429 error | NO |
| Safety | Profanity, injection | SecurityException | NO |
| Special | Greeting, capability, off-topic | Custom response | **NO** |
| **Special** | **Statistical queries** | **Redirect response** | **NO** |
| **Special** | **City typo (fuzzy match)** | **Suggestion response** | **NO** |
| Special | Out-of-scope city | Coverage message | **NO** |
| Cache | Previous response | Return cached | **NO** |
| **Early Broad** | **3-criteria check** | **Clarification** | **NO** |
| Post-proc | Backup broad check | Clarification | After LLM |

---

## Performance Characteristics

| Scenario | LLM Calls | Estimated Latency |
|----------|-----------|-------------------|
| Greeting/Capability/Off-topic | 0 | ~100ms |
| **Statistical query** | **0** | **~100ms** |
| **City typo (fuzzy suggestion)** | **0** | **~100ms** |
| Out-of-scope city (early) | 0 | ~100ms |
| Broad query (early detection) | 0 | ~100ms |
| Cache hit | 0 | ~50ms |
| Complete query | 2 | ~6-10s |
| Complete query (no results) | 2 | ~5-8s |

---

## Fast Path Query Types (No LLM)

| Query Type | Pattern/Detection | Response |
|------------|-------------------|----------|
| `greeting` | "bonjour", "hello", etc. | Welcome message |
| `capability` | "what can you do", "aide" | Help description |
| `off_topic` | Weather, translate, recipe | Polite decline |
| `statistical` | "how many events", "combien" | Redirect to search |
| `city_typo_suggestion` | "Possy" → "Poissy" (fuzzy) | Correction suggestion |
| `out_of_scope_city` | "Delhi", "London" | Coverage message |
| `broad_query` | Missing 3-criteria | Clarification questions |

---

*Last updated: January 27, 2026*
*Version: 7.1 (k limit in manager.py, removed dead backup broad query code)*
