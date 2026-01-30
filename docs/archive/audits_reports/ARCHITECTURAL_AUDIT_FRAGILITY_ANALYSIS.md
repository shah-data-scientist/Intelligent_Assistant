# Architectural Audit: Root Cause Analysis of System Fragility

**Date:** 2026-01-24
**Status:** CRITICAL - System architecture is causing whac-a-mole regressions
**Auditor:** Senior Software Architect
**Scope:** Complete RAG system architecture review

---

## Executive Summary

The RAG system exhibits **severe architectural fragility** caused by:

1. **Massive logic duplication** across 4+ layers (prompts, chain, manager, vector_store)
2. **Conflicting responsibilities** where fixes in one component break others
3. **No clear separation of concerns** between data retrieval, filtering, and presentation
4. **LLM instructions fighting with Python logic**, creating unpredictable behavior
5. **Multiple serial LLM calls** creating unnecessary latency and complexity

**Impact:** Every fix creates 2-3 new bugs because the same logic is duplicated and decentralized across multiple files. The system is **unmaintainable** in its current state.

---

## Component Interaction Map

```
User Query
    │
    ↓
┌─────────────────────────────────────────────────┐
│  RAGChain (chain.py)                            │
│  - Manages chat history & summarization         │
│  - Orchestrates 4-stage pipeline                │
│  - Formats final output                         │
└─────────────────────────────────────────────────┘
    │
    ├→ Stage 1: Query Reformulation (LLM Call #1)
    │   └→ CONTEXTUALIZE_Q_PROMPT
    │      └→ MistralLLM.invoke()
    │
    ├→ Stage 2: Query Refinement (LLM Call #2)
    │   └→ QUERY_REFINEMENT_PROMPT
    │      └→ MistralLLM.invoke()
    │         └→ Fixes typos, expands demonyms
    │
    ├→ Stage 3: Intent Extraction (LLM Call #3)
    │   └→ METADATA_EXTRACTION_PROMPT
    │      └→ MistralLLM.invoke() → JSON filters
    │         ├→ Extracts: city, month, day, year, category, is_free, age
    │         └→ **PROBLEM:** Complex date logic in prompt (lines 114-126)
    │
    ├→ Stage 4: Retrieval
    │   └→ RetrievalManager.execute_search()
    │      ├→ parse_intent() - Normalizes filters
    │      │  └→ **PROBLEM:** Duplicates date logic from prompt
    │      │
    │      ├→ _search_exact() → calls vector_store.search()
    │      │  └→ **PROBLEM:** vector_store re-applies filters
    │      │
    │      ├→ _search_nearby_locations() → calls vector_store.search()
    │      │  └→ **PROBLEM:** Removes city but keeps date strict
    │      │
    │      └→ _count_alt_dates() → calls vector_store.search()
    │         └→ **PROBLEM:** Changes date to +/-7 day window
    │
    └→ Stage 5: Generation (LLM Call #4)
        └→ RAG_SYSTEM_PROMPT
           └→ MistralLLM.invoke() → JSON response
              └→ **PROBLEM:** More date/filter instructions (lines 72-80)
```

### EventVectorStore Internal Flow

```
vector_store.search(query, k, metadata_filter)
    │
    ├→ 1. Vector Search (FAISS)
    │   └→ Retrieves top 200*k candidates
    │
    ├→ 2. BM25 Search (Keyword)
    │   └→ Retrieves top 200*k candidates
    │
    ├→ 3. Reciprocal Rank Fusion (RRF)
    │   └→ Combines vector + BM25 scores
    │
    ├→ 4. Keyword Boosting
    │   └→ **PROBLEM:** Applied AFTER fusion (line 202-215)
    │      └→ Can distort RRF scores unpredictably
    │
    ├→ 5. Filtering (_matches_filter)
    │   └→ **MASSIVE DUPLICATION:**
    │      ├→ City filtering (lines 318-353)
    │      ├→ Date filtering (lines 365-412)
    │      │  ├→ year filter (lines 365-368)
    │      │  ├→ month filter (lines 369-372)
    │      │  ├→ day filter (lines 373-376)
    │      │  ├→ date_min filter (lines 378-395)
    │      │  └→ date_max filter (lines 397-412)
    │      ├→ Category filtering (lines 362-364)
    │      ├→ is_free filtering (lines 355-356)
    │      └→ age filtering (lines 358-360)
    │
    └→ 6. Geo Priority (_apply_geo_priority)
        └→ **PROBLEM:** Re-sorts by distance AFTER filtering
           └→ Conflicts with manager's distance calculations
```

---

## Critical Issues Identified

### 1. MASSIVE LOGIC DUPLICATION (Severity: CRITICAL)

#### Date Filtering Logic Appears in 4 Places:

**Location 1:** `prompts.py` - METADATA_EXTRACTION_PROMPT (lines 114-126)
```python
"""
**STRICT RULES:**
1. **DATE EXTRACTION:** ONLY extract "month" or "day" if the user EXPLICITLY mentions a time
   - **CRITICAL:** Do NOT default to the current month (January) if the user asks a broad question
2. **YEAR:** Default to 2026 for the year if a month is mentioned, otherwise leave null.
3. **NO DEFAULT DATES:** Do NOT default to the current date if the user is asking about a specific event
4. **CURRENT INTENT PRIORITY:** The current user question is the most important.
   - If the user asks for "today" (Jan 24, 2026), output "day": 24, "month": 1.
   - If the user asks for "tomorrow" (Jan 25, 2026), output "day": 25, "month": 1.
"""
```

**Location 2:** `manager.py` - parse_intent() (lines 38-71)
```python
def parse_intent(self, filters: Dict[str, Any]) -> SearchIntent:
    intent = SearchIntent(
        city=filters.get("city"),
        month=filters.get("month"),
        year=filters.get("year", 2026),  # Defaults to 2026
        category=filters.get("category")
    )

    # Handle Days (single or list)
    days = filters.get("day")
    if isinstance(days, list):
        intent.days = days
    elif isinstance(days, int):
        intent.days = [days]

    # Handle Date Range
    if "date_min" in filters:
        val = filters["date_min"]
        intent.date_min = val if isinstance(val, date) else date.fromisoformat(val)
    # ... more date logic
```

**Location 3:** `vector_store.py` - _matches_filter() (lines 365-412)
```python
elif key == "year" and event.start_date:
    if isinstance(value, list):
        if event.start_date.year not in value: return False
    elif event.start_date.year != value: return False

elif key == "month" and event.start_date:
    if isinstance(value, list):
        if event.start_date.month not in value: return False
    elif event.start_date.month != value: return False

elif key == "day" and event.start_date:
    if isinstance(value, list):
        if event.start_date.day not in value: return False
    elif event.start_date.day != value: return False

# Date Range Filtering
elif key == "date_min" and event.start_date:
    # Value should be a datetime.date object or string ISO format
    if isinstance(value, str):
        from datetime import date
        try:
            value = date.fromisoformat(value)
        # ... 15 more lines of date handling
```

**Location 4:** `prompts.py` - RAG_SYSTEM_PROMPT (lines 72-74)
```python
"""
1. **GROUNDING (CRITICAL):**
   - If a source does not match the user's requested CATEGORY or DATE, EXCLUDE it.
"""
```

**Why This Is a Problem:**
- Changing date logic requires updating 4 files
- Each location has different edge cases and validation
- LLM prompt instructions can contradict Python logic
- No single source of truth

---

### 2. CONFLICTING RESPONSIBILITIES (Severity: CRITICAL)

#### City/Location Filtering Done in 3 Places:

**RetrievalManager (manager.py)**
- Lines 91-128: Implements nearby location fallback
- Calculates distances using haversine_distance
- Sorts by distance
- Keeps date filters strict when doing nearby search

**EventVectorStore (vector_store.py)**
- Lines 318-353: Implements 50km radius filtering in _matches_filter
- Lines 277-311: Re-applies geo priority in _apply_geo_priority
- Sorts by distance AGAIN after manager already sorted

**METADATA_EXTRACTION_PROMPT (prompts.py)**
- Lines 123-125: Instructions about location inheritance
- "CRITICAL: If the user changes location (e.g. 'how about in nearby towns?'), KEEP the existing date filters"

**Consequence:**
- Manager says "nearby locations" but keeps dates strict
- Vector store applies 50km radius
- Then vector store re-sorts by distance
- **Result:** Sorting happens twice with different criteria, causing unpredictable ordering

---

### 3. LLM INSTRUCTIONS FIGHTING WITH PYTHON LOGIC (Severity: HIGH)

#### Example: Category Filtering

**Prompt Says (METADATA_EXTRACTION_PROMPT, line 108):**
```python
"category": Cultural category (e.g., "classical", "jazz", "theater"). If none, null.
```

**Python Does (vector_store.py, lines 362-364):**
```python
elif key == "category" and event.category:
    if value.lower() not in event.category.lower() and event.category.lower() not in value.lower():
        return False
```

**Problem:** Bidirectional substring matching (`A in B or B in A`) is not explained to the LLM. The LLM might extract "jazz concert" while the user asked "jazz", but the Python does substring matching. This creates confusion when debugging mismatches.

---

### 4. OVER-ENGINEERING: TOO MANY SERIAL LLM CALLS (Severity: MEDIUM)

Every query triggers **4 LLM API calls:**

1. **Query Reformulation** (if chat history exists)
   - Purpose: Convert follow-up to standalone question
   - Cost: ~1-2 seconds

2. **Query Refinement**
   - Purpose: Fix typos, expand demonyms
   - Cost: ~1-2 seconds

3. **Metadata Extraction**
   - Purpose: Extract filters (city, date, category)
   - Cost: ~1-2 seconds

4. **Final Generation**
   - Purpose: Generate answer from context
   - Cost: ~2-3 seconds

**Total Latency:** 5-9 seconds JUST for LLM calls (not including retrieval)

**Why This Is a Problem:**
- Expensive (4x API costs)
- Slow (5-9 second latency floor)
- Fragile (4 points of failure)
- Hard to debug (which LLM call introduced the error?)

---

### 5. RETRIEVER CLASS IS UNUSED (Severity: LOW)

**retriever.py** defines `EventRetriever(BaseRetriever)`:
- Has its own cache
- Has `search_with_filters()` method
- Wraps `vector_store.search()`

**BUT:** `chain.py` creates an `EventRetriever` instance (line 96) but **never uses its methods**. All retrieval goes through `RetrievalManager.execute_search()` instead.

**Why This Exists:**
- Legacy code from earlier architecture
- Creates confusion about which retrieval path is active

---

### 6. KEYWORD BOOSTING APPLIED AFTER RRF FUSION (Severity: MEDIUM)

**vector_store.py, lines 202-215:**
```python
# 3. Fusion (RRF)
fused_scores_list = self._reciprocal_rank_fusion(vector_results, bm25_results)
fused_scores = dict(fused_scores_list)

# --- KEYWORD BOOSTING ---
# If the query contains specific keywords, boost documents that contain them
boost_keywords = [w for w in query.lower().split() if len(w) > 3]
if boost_keywords:
    for event_id in fused_scores:
        event = self.storage.get_event(event_id)
        if event:
            text = f"{event.title} {event.description or ''}".lower()
            if any(kw in text for kw in boost_keywords):
                # Apply a significant boost to the RRF score
                fused_scores[event_id] *= 2.0  # 2x boost
```

**Problems:**
1. **Applied AFTER fusion:** RRF creates normalized scores, then boosting doubles them. This breaks the RRF score distribution.
2. **Too aggressive:** 2x multiplier can completely override semantic relevance.
3. **Wrong layer:** Boosting should happen BEFORE fusion (boost vector/BM25 scores separately, then fuse).
4. **Naive keyword matching:** Matches any 4+ char word, even common ones like "dans", "pour", "avec".

---

### 7. NO CLEAR SEPARATION OF CONCERNS (Severity: CRITICAL)

**When you need to change date filtering behavior:**

| Layer | File | Lines | What You Must Update |
|-------|------|-------|----------------------|
| **LLM Extraction** | prompts.py | 114-126 | Date extraction rules in METADATA_EXTRACTION_PROMPT |
| **Intent Parsing** | manager.py | 38-71 | parse_intent() date normalization logic |
| **Exact Search** | manager.py | 158-169 | _search_exact() filter assembly |
| **Nearby Search** | manager.py | 171-182 | _search_nearby_locations() filter assembly |
| **Alt Date Search** | manager.py | 184-201 | _count_alt_dates() date window logic |
| **Vector Store Filtering** | vector_store.py | 365-412 | _matches_filter() date comparison logic |
| **LLM Generation** | prompts.py | 72-74 | RAG_SYSTEM_PROMPT grounding rules |

**Result:** One conceptual change (e.g., "support date ranges instead of exact dates") requires modifying **7 different locations** across **3 files**, with no guarantee they'll stay in sync.

---

## Root Cause Analysis: Why Regressions Keep Happening

### Architectural Anti-Pattern: "Distributed Validation"

The system has **no single source of truth** for:
- What filters are valid
- How filters are applied
- What filters mean semantically

Instead, validation and filtering logic is **distributed** across:
1. LLM prompts (natural language rules)
2. Python data classes (SearchIntent)
3. Manager search logic (filter assembly)
4. Vector store filtering (filter application)

**Consequence:** When you fix a bug in one layer, the other 3 layers don't automatically update, causing:
- **Regression Type 1:** Prompt change breaks Python assumptions
- **Regression Type 2:** Python change creates results LLM can't handle
- **Regression Type 3:** Fixes conflict between manager's multi-stage logic and vector store's single-stage filtering

### Example Regression Scenario

**User reports:** "Events for 'this weekend' returns events from next month"

**You investigate and find:**
1. METADATA_EXTRACTION_PROMPT extracts `day: [24, 25], month: 1`
2. manager.parse_intent() creates `SearchIntent(days=[24,25], month=1, year=2026)`
3. manager._search_exact() passes `{"day": [24,25], "month": 1, "year": 2026}` to vector_store
4. vector_store._matches_filter() checks `event.start_date.day in [24,25]` AND `event.start_date.month == 1`
5. Works correctly!

**You fix it by updating the prompt to be more specific.**

**NEW BUG APPEARS:** "Events in Paris returns no results"

**Why?** Your prompt change accidentally modified the city extraction logic because:
- The prompt has 300+ lines of instructions
- Date and city logic are in the same prompt
- Changing one affects the other

**You fix the city extraction.**

**ANOTHER BUG:** "Nearby locations fallback broken"

**Why?** Your city fix changed how the LLM outputs city names (e.g., "Paris" vs "paris" vs "Paris, France"). Now manager's string comparison on line 320 fails:
```python
if value.lower() not in event.location.city.lower(): return False
```

---

## Recommended Refactoring Plan

### Phase 1: Centralize Filter Definition (Priority: CRITICAL)

**Goal:** Single source of truth for what filters exist and how they're validated.

**Create:** `src/retrieval/filters.py`

```python
"""Centralized filter definitions and validation."""

from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Dict, Any
from enum import Enum

class FilterType(Enum):
    CITY = "city"
    DATE_RANGE = "date_range"  # Replaces month/day/year
    CATEGORY = "category"
    IS_FREE = "is_free"
    AGE = "age"

@dataclass
class SearchFilters:
    """Validated search filters - single source of truth."""
    city: Optional[str] = None
    date_min: Optional[date] = None
    date_max: Optional[date] = None
    category: Optional[str] = None
    is_free: Optional[bool] = None
    age: Optional[int] = None

    @classmethod
    def from_llm_output(cls, raw: Dict[str, Any]) -> "SearchFilters":
        """Parse and validate LLM extraction output."""
        # Single place to handle: month/day/year → date_min/date_max conversion
        # Single place to normalize city names
        # Single place to validate categories
        pass

    def to_vector_store_filter(self) -> Dict[str, Any]:
        """Convert to format expected by vector_store._matches_filter()."""
        pass

    def matches(self, event: Event) -> bool:
        """Check if event matches these filters."""
        # Replaces vector_store._matches_filter() logic
        pass
```

**Impact:**
- ✅ Date logic centralized to one file
- ✅ Filter validation in one place
- ✅ Easy to test in isolation
- ✅ Changes don't cascade across 7 locations

---

### Phase 2: Simplify Retrieval Pipeline (Priority: CRITICAL)

**Current:**
```
Query → RetrievalManager.execute_search()
    ├→ _search_exact(filters)      → vector_store.search(filters)
    ├→ _search_nearby(filters)     → vector_store.search(modified_filters)
    └→ _count_alt_dates(filters)   → vector_store.search(window_filters)
```

**Problem:** Manager modifies filters for each stage, then vector_store re-applies them differently.

**Refactor to:**
```
Query → RetrievalOrchestrator.search(query, filters)
    ├→ Stage 1: vector_store.search_exact(query, filters)
    │   └→ Returns: List[Event], no post-processing
    │
    ├→ Stage 2: vector_store.search_nearby(query, filters.remove_city())
    │   └→ Returns: List[Event], no post-processing
    │
    └→ Stage 3: Merge & Deduplicate
        └→ Returns: List[Event] with match_type metadata
```

**Key Changes:**
1. **vector_store becomes dumb:** Just does search + filtering, no geo-sorting
2. **Orchestrator handles multi-stage logic:** Decides when to fallback
3. **Filtering happens once:** In SearchFilters.matches()
4. **Geo-sorting happens once:** In orchestrator after all stages complete

---

### Phase 3: Eliminate Redundant LLM Calls (Priority: HIGH)

**Combine 3 LLM calls into 1:**

**Current:**
```
Query → Query Refinement LLM → Query Reformulation LLM → Metadata Extraction LLM → Search
```

**Refactored:**
```
Query → Single "Query Understanding" LLM → Search
```

**New Prompt: QUERY_UNDERSTANDING_PROMPT**
```python
"""You are a search query analyzer for cultural events.

Input: User query (may be a follow-up question)
Chat History: Previous conversation context

Output JSON:
{
  "refined_query": "Typo-corrected, standalone search query",
  "filters": {
    "city": "Paris" or null,
    "date_min": "2026-01-24" or null,
    "date_max": "2026-01-31" or null,
    "category": "jazz" or null,
    "is_free": true or null,
    "age": 5 or null
  }
}

Rules:
1. Fix typos in the query
2. If follow-up question, resolve references from chat history
3. Extract filters from the refined query
4. Output valid JSON only
"""
```

**Benefits:**
- ⚡ 3x faster (1 LLM call instead of 3)
- 💰 3x cheaper
- 🐛 1 failure point instead of 3
- 🧪 Easier to test

---

### Phase 4: Extract Filtering from Vector Store (Priority: MEDIUM)

**Current:**
```python
# vector_store.py
def search(query, k, metadata_filter):
    # 1. Vector search
    # 2. BM25 search
    # 3. RRF fusion
    # 4. Keyword boosting
    # 5. Filtering  ← Problem: Too late
    # 6. Geo sorting ← Problem: Too late
```

**Refactor:**
```python
# vector_store.py
def search(query, k):
    # 1. Vector search (large candidate pool)
    # 2. BM25 search (large candidate pool)
    # 3. RRF fusion
    # 4. Return top candidates
    # → No filtering, no sorting, just raw similarity results

# orchestrator.py
def search_with_filters(query, filters):
    # 1. Get raw candidates from vector_store
    candidates = vector_store.search(query, k=100)

    # 2. Apply filters
    filtered = [e for e in candidates if filters.matches(e)]

    # 3. Apply geo sorting if city filter exists
    if filters.city:
        sorted_results = geo_sorter.sort(filtered, filters.city)

    # 4. Return top k
    return sorted_results[:k]
```

**Benefits:**
- ✅ Vector store does one thing: semantic search
- ✅ Filtering logic in SearchFilters.matches()
- ✅ Orchestrator controls the flow
- ✅ Easy to test each stage independently

---

### Phase 5: Fix Keyword Boosting (Priority: LOW)

**Move boosting BEFORE fusion:**

```python
def search(query, k):
    # 1. Vector search
    vector_results = self.index.search(query_array, k)

    # 2. BM25 search
    bm25_results = self.bm25.get_scores(tokenized_query)

    # 3. Keyword boosting (BEFORE fusion)
    boost_keywords = extract_significant_keywords(query)
    if boost_keywords:
        vector_results = apply_keyword_boost(vector_results, boost_keywords)
        bm25_results = apply_keyword_boost(bm25_results, boost_keywords)

    # 4. RRF fusion (on boosted scores)
    fused_scores = self._reciprocal_rank_fusion(vector_results, bm25_results)

    return fused_scores
```

---

## Summary: Architecture vs. Requirements

| Requirement | Current Architecture | Problems | Recommended |
|-------------|---------------------|----------|-------------|
| **Date Filtering** | Duplicated across 4 locations (prompts, manager, vector_store, RAG prompt) | Impossible to maintain consistency | Centralize in SearchFilters |
| **Location Filtering** | 3 conflicting implementations (manager geo-calc, vector_store radius, vector_store geo-sort) | Sorting happens twice, unpredictable results | Single geo module with clear responsibility |
| **Multi-Stage Retrieval** | Manager modifies filters, vector_store re-filters | Conflicts between layers | Orchestrator controls flow, vector_store is dumb |
| **Query Understanding** | 3 serial LLM calls (reformulate, refine, extract) | Slow, expensive, fragile | 1 unified LLM call |
| **Category Matching** | Substring matching hidden in Python, not documented in prompt | LLM and Python disagree | Explicit matching rules in SearchFilters |

---

## Next Steps

### Immediate Action (This Week)

1. **Create `src/retrieval/filters.py`** with `SearchFilters` class
2. **Update `manager.py`** to use `SearchFilters.from_llm_output()`
3. **Test isolation:** Verify filters work independently of vector_store

### Short-Term (Next 2 Weeks)

4. **Refactor retrieval pipeline** to separate concerns
5. **Combine LLM calls** into single "query understanding" step
6. **Move keyword boosting** before RRF fusion

### Long-Term (Next Month)

7. **Remove legacy `retriever.py`** (unused code)
8. **Add integration tests** for each refactored component
9. **Document** the new architecture with clear diagrams

---

## Testing Strategy for Refactoring

### Test Suite Structure

```python
# tests/test_filters.py
def test_date_extraction_from_llm():
    """Verify LLM output → SearchFilters conversion"""
    raw = {"month": 1, "day": [24, 25], "year": 2026}
    filters = SearchFilters.from_llm_output(raw)
    assert filters.date_min == date(2026, 1, 24)
    assert filters.date_max == date(2026, 1, 25)

def test_filter_matching():
    """Verify event matches filters"""
    filters = SearchFilters(city="Paris", date_min=date(2026, 1, 24))
    event = Event(location=EventLocation(city="Paris"), start_date=datetime(2026, 1, 24))
    assert filters.matches(event) == True

# tests/test_orchestrator.py
def test_exact_then_nearby_fallback():
    """Verify multi-stage retrieval logic"""
    # Mock vector_store to return 0 exact matches
    # Verify orchestrator calls search_nearby()
    # Verify results are sorted by distance

# tests/test_regression.py
def test_weekend_query_date_filtering():
    """Regression test: 'this weekend' should not return next month events"""
    result = chain.query("events this weekend")
    # Verify all events are within Jan 24-25, 2026

def test_paris_city_filtering():
    """Regression test: 'events in Paris' should return Paris events"""
    result = chain.query("events in Paris")
    # Verify all events are in Paris
```

---

## Risk Assessment

| Refactoring Phase | Risk Level | Mitigation |
|-------------------|------------|------------|
| Phase 1 (Filters) | **LOW** | New module, doesn't touch existing code until tested |
| Phase 2 (Retrieval) | **MEDIUM** | Replace piece by piece, run regression tests after each change |
| Phase 3 (LLM Calls) | **HIGH** | A/B test new prompt vs old pipeline, compare results |
| Phase 4 (Vector Store) | **MEDIUM** | Existing tests will catch breaking changes |
| Phase 5 (Boosting) | **LOW** | Performance optimization, doesn't affect correctness |

---

## Conclusion

The current architecture suffers from **distributed responsibilities** and **duplicated logic**. Every fix cascades through 4-7 locations, making the system unmaintainable.

**The solution is NOT to be more careful when making changes.** The solution is to **refactor the architecture** so that each concern has ONE authoritative implementation.

**Recommended Priority:**
1. ✅ **Phase 1:** Centralize filters (1 week, low risk)
2. ✅ **Phase 3:** Combine LLM calls (1 week, high impact)
3. ✅ **Phase 2:** Refactor retrieval pipeline (2 weeks, critical)
4. ⏸️ **Phase 4-5:** Optimizations (defer until core stable)

**Expected Outcome:**
- ✅ Fixes stop creating regressions
- ✅ Changes localized to single files
- ✅ 3x faster response time (fewer LLM calls)
- ✅ 3x cheaper (fewer API calls)
- ✅ Testable in isolation
- ✅ Maintainable long-term
