# Evaluation Issues Identified (2026-01-26)

## Executive Summary

After running the first 20 queries from the golden dataset, I identified 3 critical issues that need to be fixed before full evaluation:

1. **Golden Dataset Out of Sync** (CRITICAL)
2. **Île-de-France Region Filter Bug** (HIGH PRIORITY)
3. **Database Coverage Gaps** (INFORMATIONAL)

---

## Issue 1: Golden Dataset Out of Sync (CRITICAL)

### Description
The golden dataset's `relevance_ground_truth` contains event IDs that **do not exist** in the current database.

### Evidence
- Q001 expects events: `14551589`, `89710664`, `44104225`
- None of these IDs exist in current database
- Current database has 53 Paris jazz events in February with different IDs (e.g., `30745065_0`, `48478814_0`)

### Root Cause
The golden dataset was created with an older version of the database. Event IDs have changed due to:
- Database rebuilds
- New data ingestion
- ID schema changes (e.g., `_0`, `_1` suffixes added for recurring events)

### Impact
- **Cannot use exact event ID matching** for evaluation
- Traditional precision/recall metrics are meaningless
- Ground truth validation is impossible

### Solution
**Switch to semantic evaluation** instead of exact ID matching:
- Check if chatbot returns results when database has matching events
- Validate returned results match query filters (city, date, category, keywords)
- Evaluate transparency messaging correctness
- Check for errors and failures

**Script Created**: `scripts/semantic_evaluation.py`

---

## Issue 2: Île-de-France Region Filter Bug (HIGH PRIORITY)

### Description
When users ask for "events in Île-de-France" (a region), the LLM extracts `city="Île-de-France"`, which matches **0 events** since it's not a city name in our database.

### Evidence
**Failing Queries:**
- Q002: "Tell me about Finnish artists and exhibitions" → extracted `city="Île-de-France"`
- Q007: "Japanese art exhibitions in Île-de-France" → extracted `city="Île-de-France"`
- Q016: "Sports et loisirs en Île-de-France" → extracted `city="Île-de-France"`

**Expected Behavior:**
- Database has NO events with `city="Île-de-France"`
- Database has events in cities within Île-de-France: Paris (444 events), Versailles (14 events), Montreuil, etc.

**Actual Result:**
- Filter: `SearchFilters(city="Île-de-France", category="Art / Exposition")`
- Matches: **0 exact matches**
- Chatbot returns: "I found 0 events"

### Root Cause
The metadata extraction prompt treats "Île-de-France" as a city name, but it's actually a **region** encompassing multiple cities.

### Solution
**Option A (Recommended)**: Modify metadata extraction prompt to handle regions:
```python
# In METADATA_EXTRACTION_SYSTEM_PROMPT:
- "city": City name (e.g., "Paris", "Versailles").
  * **CRITICAL**: If the user mentions "Île-de-France" or "Ile-de-France" (the region),
    set city to null instead. The region encompasses all cities in our database.
  * If none specified, null.
```

**Option B**: Add post-processing to detect region names and clear city filter:
```python
# In chain.py after metadata extraction:
if extracted_city in ['Île-de-France', 'Ile-de-France']:
    filters.city = None
```

**Option C**: Map regions to multiple cities:
```python
REGION_MAP = {
    'Île-de-France': ['Paris', 'Versailles', 'Montreuil', 'Saint-Denis', ...]
}
```

**Recommended**: **Option A** - fix at the source (prompt engineering) to prevent extraction error

### Implementation

**File**: `src/generation/prompts.py` (Line ~158-162)

**Change**:
```python
# BEFORE:
- "city": Target city (e.g., "Paris"). If none, null.

# AFTER:
- "city": Target city (e.g., "Paris"). **CRITICAL: If user mentions "Île-de-France" or
  "Ile-de-France" (the region, not a city), set to null.** If none, null.
```

---

## Issue 3: Database Coverage Gaps (INFORMATIONAL)

### Description
Database lacks events for certain time periods and categories, causing some queries to legitimately return 0 results.

### Evidence

**Date Range Coverage:**
```
Database date range: 2026-01-24 to 2027-01-23
Events by month:
  January:   125 events
  February:  333 events (BEST COVERAGE)
  March:     186 events
  April:     206 events
  May:        97 events
  June:       43 events
  July:        6 events
  October:     2 events
  November:    2 events
  December:    0 events (NO EVENTS!)
```

**Failing Queries Due to Missing Data:**
- Q009: "Spectacles pour enfants pendant les vacances de Noël" (December) → DB has **0 December events**
- Q019: "Free outdoor events in Paris during June for families" → DB has only **43 June events total**
- Q020: "Concerts de musique jazz en plein air à Paris en juin" → Same issue

### Root Cause
Database primarily covers January-June 2026, with very sparse coverage for July-November and **zero** December events.

### Impact
- **NOT a bug** - database accurately reflects data availability
- Chatbot correctly returns 0 results when no matching events exist
- Transparency rules correctly state "I found no events"

### Solution
**No code fix needed.** This is expected behavior when database lacks coverage.

**Documentation Update:** Update README to clarify database date range coverage.

---

## Summary of Required Fixes

### Priority 1 (Blocking Full Evaluation):
- [x] Create semantic evaluation script (DONE - `scripts/semantic_evaluation.py`)
- [ ] Fix Île-de-France region filter bug (modify metadata extraction prompt)

### Priority 2 (Documentation):
- [ ] Update README with database date range coverage
- [ ] Document that golden dataset ground truth is outdated

### Testing Plan:
1. Apply Île-de-France fix
2. Re-run semantic evaluation on first 20 queries
3. Verify Q002, Q007, Q016 now return results
4. Run full 135-query evaluation
5. Present results

---

## Next Steps

1. **Apply Île-de-France Fix** (2 minutes)
2. **Test on failing queries** (5 minutes)
3. **Run full 135-query semantic evaluation** (30-60 minutes)
4. **Present comprehensive results** to user

---

**Evaluation Approach:**
- Semantic relevance validation (not exact ID matching)
- Transparency rule verification
- Error rate measurement
- Query success rate by category

**Target Metrics:**
- Query Success Rate: >85% (returns results when database has results)
- Error Rate: <5%
- Transparency Compliance: 100%
