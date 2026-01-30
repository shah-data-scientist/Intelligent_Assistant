# Chatbot Transparency Rules Implementation

## Overview

This document describes the transparency rules implemented in the cultural events chatbot to ensure users always understand where results come from and whether criteria were modified.

## Core Principles

1. **Target 8 Results**: The system aims to return exactly 8 events when possible
2. **Strict Filter Respect**: Primary filters (city, date, category) are strictly respected in initial search
3. **Transparent Fallback**: When insufficient exact matches exist, nearby cities may be included BUT this is EXPLICITLY communicated
4. **Never Fabricate**: No events are ever invented or hallucinated
5. **Never Silent Changes**: Criteria are never changed without informing the user

## Implementation Architecture

### Three-Tier Search Strategy

The `RetrievalOrchestrator` implements a three-stage search:

1. **Stage 1: Exact Match**
   - Search with strict filters (city, date, category)
   - If ≥8 matches found → Return first 8, DONE
   - If <8 matches found → Continue to Stage 2

2. **Stage 2: Nearby Location Fallback**
   - Expand city filter to include nearby towns (within 10-20 km)
   - Keep all other filters strict (date, category)
   - Sort by distance from target city
   - Combine with exact matches to reach 8 total

3. **Stage 3: Alternative Date Detection** (metadata only)
   - If city + category match but date doesn't → Add note
   - Does NOT include these events in results
   - Just informs user they exist

### Metadata Enrichment

Every retrieved event includes:
- `match_type`: "Exact Match" or "Nearby Location"
- `distance_km`: Distance from requested city (for nearby matches)
- `score`: Similarity score from FAISS + BM25 hybrid search

## Transparency Messaging Rules

### French Prompt Rules (`RAG_SYSTEM_PROMPT_FR`)

**ÉTAPE 1:** Count sources with `match_type`: "Exact Match"
**ÉTAPE 2:** Count sources with `match_type`: "Nearby Location"

**Required Response Formats:**

| Scenario | Message Template |
|----------|------------------|
| Only exact matches | "J'ai trouvé [X] événements correspondant à vos critères à [Ville]." |
| Zero exact, only nearby | "Je n'ai pas trouvé d'événements à [Ville]. Cependant, j'ai trouvé [Y] événements dans des villes voisines (à moins de 10-20 km)." |
| Mix of exact + nearby | "J'ai trouvé [X] événements correspondant à vos critères à [Ville]. Pour compléter, j'ai trouvé [Y] événements supplémentaires dans des villes voisines." |

### English Prompt Rules (`RAG_SYSTEM_PROMPT_EN`)

**STEP 1:** Count sources with `match_type`: "Exact Match"
**STEP 2:** Count sources with `match_type`: "Nearby Location"

**Required Response Formats:**

| Scenario | Message Template |
|----------|------------------|
| Only exact matches | "I found [X] events that match your criteria in [City]." |
| Zero exact, only nearby | "I found no events in [City]. However, I found [Y] events in nearby towns (within 10-20 km)." |
| Mix of exact + nearby | "I found [X] events that match your criteria in [City]. To help, I also found [Y] additional events in nearby towns." |

### Critical Rules

- **NEVER** say an event is in the requested city if it has `match_type`: "Nearby Location"
- **ALWAYS** mention nearby town names if events come from them (e.g., "Paris, Montreuil")
- **ALWAYS** distinguish exact vs nearby counts explicitly

## Code References

### Modified Files

1. **src/generation/prompts.py** (Lines 67-132)
   - Added ÉTAPE 1/2 counting instructions
   - Added three-scenario messaging templates
   - Added strict warnings about match_type field

2. **src/retrieval/chain.py** (Lines 170-194, 222-231)
   - Added dynamic language-aware prompt selection
   - Pass language parameter through invoke()
   - Default language: French

3. **src/retrieval/orchestrator.py** (Lines 158-188)
   - Already implements three-stage search logic
   - Already adds match_type and distance_km metadata

## Testing

### Manual Tests Performed

**Test 1: All Exact Matches (Paris Jazz)**
```
Query: "Concerts de jazz à Paris en février"
Language: fr
Result: "I found 8 events that match your criteria in Paris."
Breakdown: 24 exact, 0 nearby
✓ PASS
```

**Test 2: Zero Exact, Only Nearby (Versailles Weekend)**
```
Query: "Concerts à Versailles ce week-end"
Language: fr
Result: "Je n'ai pas trouvé d'événements à Versailles. Cependant, j'ai trouvé 3 événements dans des villes voisines (à moins de 10-20 km)."
Breakdown: 0 exact, 3 nearby (all from Paris)
✓ PASS
```

**Test 3: All Exact (Paris Classical)**
```
Query: "Concerts de musique classique à Paris"
Language: fr
Result: "J'ai trouvé 8 événements correspondant à vos critères à Paris."
Breakdown: 24 exact, 0 nearby
✓ PASS
```

### Automated Tests

All 14 tests in `tests/test_retrieval_orchestrator.py` pass:
- Exact match filtering
- Nearby fallback triggering
- Distance-based sorting
- Date filter respect in nearby search
- Alternative date metadata
- Deduplication
- Metadata enrichment

## Usage Examples

### Python API

```python
from src.retrieval.chain import RAGChain

chain = RAGChain()

# French query
result = chain.query_with_metadata(
    "Concerts à Versailles ce week-end",
    session_id="user_123",
    language="fr"
)

print(result["answer"])
# Output: "Je n'ai pas trouvé d'événements à Versailles. Cependant, j'ai trouvé 3 événements dans des villes voisines."

print(f"Exact matches: {result['retrieval_stats']['exact_count']}")
print(f"Total returned: {result['retrieval_stats']['total_count']}")
```

### REST API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "question": "Concerts à Versailles ce week-end",
    "session_id": "user_123",
    "language": "fr"
  }'
```

## Benefits

1. **User Trust**: Users always know whether results exactly match their criteria
2. **No Confusion**: Clear distinction between exact matches and nearby alternatives
3. **Informed Decisions**: Users can decide whether nearby events are acceptable
4. **No Silent Failures**: When no exact matches exist, users are informed explicitly
5. **Bilingual Support**: Transparency works in both French and English

## Future Enhancements

- Add distance ranges in messaging (e.g., "within 5 km", "within 15 km")
- Show specific nearby city names in the answer text
- Add option to exclude nearby cities entirely (strict mode)
- Track transparency metrics (% queries using fallback)

## Changelog

### 2026-01-26
- **Added**: Dynamic language-aware prompt selection in RAG chain
- **Added**: Three-scenario transparency messaging templates
- **Added**: ÉTAPE 1/2 counting instructions for exact vs nearby
- **Fixed**: Language parameter now properly passed to prompts
- **Verified**: All 14 orchestrator tests pass
- **Verified**: Manual testing confirms correct transparency messaging
