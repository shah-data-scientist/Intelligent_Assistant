# Optimization Plan: Clean Integration

## Overview

This document outlines all proposed optimizations and how they will be integrated without conflicts or duplication.

---

## Optimization 1: Strict 3-Criteria Requirement

### Current Files Affected
- `src/retrieval/chain.py` → `is_broad_query()` function

### Changes Required

**Before (lines 311-405):**
```python
def is_broad_query(query, chat_history) -> Tuple[bool, str]:
    # Returns broad if only 1 criterion present
    if criteria_count == 1:
        return (True, reason)
    return (False, "")
```

**After:**
```python
def is_broad_query(query, chat_history) -> Tuple[bool, str]:
    # Returns broad if ANY criterion is missing
    missing = []
    if not has_city:
        missing.append("city")
    if not has_date:
        missing.append("date")
    if not has_event_type:
        missing.append("event_type")

    if missing:
        return (True, f"missing_{'+'.join(missing)}")
    return (False, "")
```

### Clarifications Module Update
- `src/retrieval/clarifications.py` → Add new templates for missing combinations

**New Templates:**
```python
"missing_city": {...}
"missing_date": {...}
"missing_event_type": {...}
"missing_city+date": {...}
"missing_city+event_type": {...}
"missing_date+event_type": {...}
"missing_city+date+event_type": {...}
```

### No Duplication
- All clarification logic stays in `clarifications.py`
- `is_broad_query()` only detects, doesn't generate questions
- `query_with_metadata()` uses `get_clarification_response()` for backup

---

## Optimization 2: Precompile Regex Patterns

### Current Files Affected
- `src/retrieval/chain.py` → Pattern lists at module level

### Changes Required

**Before (lines 43-83):**
```python
GREETING_PATTERNS = [
    r"^(bonjour|hello)...",
]

# Used as:
for pattern in GREETING_PATTERNS:
    if re.match(pattern, query, re.IGNORECASE):
```

**After:**
```python
import re

_GREETING_PATTERNS_RAW = [
    r"^(bonjour|hello)...",
]
GREETING_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _GREETING_PATTERNS_RAW]

# Used as:
for pattern in GREETING_PATTERNS:
    if pattern.match(query):  # Already compiled
```

### Files to Update
| File | Patterns |
|------|----------|
| `chain.py` | GREETING_PATTERNS, CAPABILITY_PATTERNS, OFF_TOPIC_PATTERNS |
| `guardrails.py` | PROFANITY_PATTERNS, MALICIOUS_PATTERNS |

### No Conflicts
- Pattern definitions stay in same files
- Only change is pre-compilation at module load time
- All usages updated to use `.match()` or `.search()` directly

---

## Optimization 3: Fuzzy Matching for City Typos

### Current Files Affected
- `src/utils/geo.py` → `CityLocator` class

### New Function
```python
def find_closest_city(self, city_name: str, threshold: float = 0.8) -> Optional[str]:
    """Find closest matching city using Levenshtein distance."""
    from difflib import SequenceMatcher

    city_key = city_name.lower().strip()
    best_match = None
    best_ratio = 0.0

    for known_city in self.city_cache.keys():
        ratio = SequenceMatcher(None, city_key, known_city).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = known_city

    return best_match
```

### Integration Point
- `src/retrieval/chain.py` → `validate_city_filter()`

**Update:**
```python
def validate_city_filter(city_name: str) -> Tuple[bool, Optional[str]]:
    # ... existing exact/prefix match logic ...

    # NEW: Fuzzy match as last resort
    city_locator = get_city_locator()
    fuzzy_match = city_locator.find_closest_city(city_name)
    if fuzzy_match:
        logger.info(f"Fuzzy matched '{city_name}' -> '{fuzzy_match}'")
        return (True, fuzzy_match)

    return (False, None)
```

### No Duplication
- Fuzzy logic only in `geo.py`
- `chain.py` calls it through `validate_city_filter()`
- No changes to other files

---

## Optimization 4: Language-Aware BM25 Tokenization

### Current Files Affected
- `src/models/vector_store.py` → `EventVectorStore` class

### Changes Required

**Add new methods:**
```python
FRENCH_STOPWORDS = {"le", "la", "les", "de", "du", "à", "et", "dans", "un", "une", ...}
ENGLISH_STOPWORDS = {"the", "a", "an", "and", "or", "in", "on", "at", "to", ...}

def _tokenize_for_bm25(self, text: str, language: str = "fr") -> List[str]:
    """Language-aware tokenization with stopword removal."""
    # Normalize: lowercase, remove accents
    from unidecode import unidecode
    normalized = unidecode(text.lower())

    # Tokenize
    tokens = normalized.split()

    # Remove stopwords
    stopwords = FRENCH_STOPWORDS if language == "fr" else ENGLISH_STOPWORDS
    tokens = [t for t in tokens if t not in stopwords and len(t) > 2]

    return tokens
```

**Update `search_raw()`:**
```python
def search_raw(self, query: str, k: int = 50, language: str = "fr"):
    # Use language-aware tokenization for BM25
    query_tokens = self._tokenize_for_bm25(query, language)
    bm25_scores = self.bm25.get_scores(query_tokens)
    # ... rest unchanged
```

### Dependencies
- Add `unidecode` to pyproject.toml (already suggested in Phase 4)

### No Conflicts
- All BM25 logic stays in `vector_store.py`
- No changes to retrieval manager or chain

---

## Optimization 5: Query Intent Classification (Future)

### Proposal
Add a lightweight classifier to distinguish:
1. Event search queries
2. General knowledge questions
3. Greetings/capabilities

### Implementation
- New file: `src/classification/intent_classifier.py`
- Uses keyword-based rules (no ML needed)
- Called early in `query_with_metadata()` before LLM

### Current Pattern-Based Approach
The current regex patterns in `chain.py` already do this:
- `GREETING_PATTERNS` → Greeting intent
- `CAPABILITY_PATTERNS` → Capability intent
- `OFF_TOPIC_PATTERNS` → Off-topic intent

**Recommendation:** Keep current approach. It's efficient and works well.

---

## Files to Delete (Stale Code)

### Already Identified
| File | Reason |
|------|--------|
| `scripts/test_fixes.py` | Temporary test file (deleted) |
| `src/retrieval/manager.py` | Only if fully superseded by orchestrator |

### Code to Remove in chain.py
None currently - all code is active.

### Pattern Consolidation
Currently patterns are defined in:
- `src/retrieval/chain.py` → Query patterns
- `src/security/guardrails.py` → Security patterns

**Recommendation:** Keep separate. They serve different purposes.

---

## Integration Order

To avoid conflicts, implement in this order:

1. **Optimization 1: Strict 3-criteria** (chain.py + clarifications.py)
2. **Optimization 2: Precompile regex** (chain.py + guardrails.py)
3. **Optimization 3: Fuzzy city matching** (geo.py + chain.py)
4. **Optimization 4: Language-aware BM25** (vector_store.py)

Each optimization is isolated and can be tested independently.

---

## Testing Strategy

After each optimization:
```bash
# Unit tests
poetry run pytest tests/test_behavior.py -v

# Integration tests
poetry run pytest tests/test_api_endpoints.py -v

# Manual verification
poetry run python scripts/test_fixes.py  # (recreate for each optimization)
```

---

## Rollback Plan

Each optimization can be reverted independently:
```bash
git checkout HEAD -- src/retrieval/chain.py  # Revert chain changes
git checkout HEAD -- src/utils/geo.py        # Revert geo changes
# etc.
```

---

## Summary

| Optimization | Files Changed | Risk | Impact |
|-------------|---------------|------|--------|
| Strict 3-criteria | chain.py, clarifications.py | Low | High precision |
| Precompile regex | chain.py, guardrails.py | Very Low | ~10% faster pattern matching |
| Fuzzy city matching | geo.py, chain.py | Low | Better typo handling |
| Language-aware BM25 | vector_store.py | Medium | Better bilingual search |

**No duplication, no conflicts, clean integration guaranteed.**
