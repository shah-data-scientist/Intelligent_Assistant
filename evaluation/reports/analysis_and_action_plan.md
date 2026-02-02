# RAG System Evaluation Analysis & Action Plan

**Date:** 2026-02-01
**Evaluated By:** Mistral LLM Judge
**Dataset:** Golden Dataset v3.3 (15 queries)

---

## Executive Summary

The production API evaluation revealed **significant quality issues** that require immediate attention. The system achieved a **57% quality score** against a target of 70%, with particular weakness in **initial queries (37% quality)** and **faithfulness scoring (66%)**.

### Key Metrics Summary

| Metric | Actual | Target | Status |
|--------|--------|--------|--------|
| Quality Score | 0.57 | >= 0.70 | FAIL |
| Faithfulness | 0.66 | >= 0.70 | FAIL |
| Relevancy | 0.68 | >= 0.70 | FAIL |
| Latency (avg) | 3894ms | < 5000ms | PASS |
| Success Rate | 100% | >= 95% | PASS |

---

## Root Cause Analysis

### Issue 1: Empty Response Bodies (Critical)

**Symptom:** Faithfulness score of 0.0 on multiple queries

**Affected Queries:**
- `conv_002_t1`: "Jazz concerts in Paris this weekend" (faithfulness=0.0)
- `conv_003_t1`: "events" (faithfulness=0.0)

**Root Cause:** The system returns summary statements like "Here are 8 events in Paris" without actually listing the events. The LLM judge correctly penalizes this as the response makes claims not supported by visible content.

**Example Response:**
```
"Here are 8 music events in Paris this weekend:
*Just a heads-up, I also found 14 events on alternative dates.*
Applied filters: Paris | February | Musique"
```

The response claims 8 events but **lists none of them**.

**Evidence from JSON:**
```json
{
  "query": "Jazz concerts in Paris this weekend",
  "faithfulness_score": 0.0,
  "judge_reasoning": "The answer claims there are 8 music events in Paris this weekend, but it does not list any of them..."
}
```

---

### Issue 2: Context Loss in Follow-up Queries

**Symptom:** Follow-up queries return unrelated events

**Affected Query:**
- `conv_001_t3`: "Parle-moi du premier" (quality=0.55)

**Root Cause:** When user asks "Tell me about the first one" after a jazz search, the system:
1. Loses the jazz/music context
2. Returns random events (PUNK.E.S in Guyancourt instead of jazz in Paris)
3. Mixes multiple categories (Music, Formation/Emploi, Theatre)

**Evidence:**
- Previous query: Jazz concerts in Paris (February)
- Follow-up: "Parle-moi du premier"
- Response shows: PUNK.E.S in Guyancourt, Forum des metiers, Les Femmes Savantes

The session context is not properly maintained for "first event" references.

---

### Issue 3: Vague Queries Return Low-Quality Results

**Symptom:** Extremely vague queries receive poor treatment

**Affected Query:**
- `conv_003_t1`: "events" (quality=0.2, faithfulness=0.0)

**Root Cause:** The system should either:
1. Ask for clarification (city/category/date), OR
2. Provide a helpful default response

Instead, it returns a minimal response claiming events exist without showing them.

---

### Issue 4: No Events Found Scenario Handling

**Symptom:** Zero quality score when no events match

**Affected Query:**
- `conv_004_t4`: "Non, plutot a Versailles finalement" (quality=0.0)

**Root Cause:** When switching from Paris expositions to Versailles, no matching events were found. The system did not gracefully handle this scenario or suggest alternatives.

---

### Issue 5: Follow-up Detail Requests Not Supported

**Symptom:** Questions about specific event details fail

**Affected Query:**
- `conv_005_t2`: "What's the price for the second one?" (quality=0.0)

**Root Cause:** The system cannot reference previously listed events. When user asks about "the second one", the system has no memory of which events were shown and in what order.

---

## Performance by Query Type

| Query Type | Count | Avg Quality | Assessment |
|------------|-------|-------------|------------|
| **initial** | 5 | 0.37 | CRITICAL - First impressions matter most |
| follow_up | 3 | 0.50 | Poor - Context not maintained |
| refinement | 4 | 0.53 | Moderate - Filter additions work partially |
| clarification_response | 2 | 0.58 | Acceptable |
| topic_shift | 1 | 0.78 | Good - Fresh context works best |

**Key Insight:** Initial queries have the **worst performance** at 37%, which is problematic because:
1. First query sets user expectations
2. Poor initial response leads to conversation abandonment
3. Topic shifts (fresh starts) perform best, suggesting context handling is the issue

---

## Detailed Failure Analysis

### 6 Low-Quality Queries (<0.5 score)

| Query ID | Query | Score | Primary Issue |
|----------|-------|-------|---------------|
| conv_002_t1 | Jazz concerts in Paris this weekend | 0.30 | Empty response body |
| conv_003_t1 | events | 0.20 | Too vague, no events listed |
| conv_004_t1 | Expositions a Paris | 0.30 | Events not listed in response |
| conv_004_t4 | Non, plutot a Versailles | 0.00 | No events found, poor fallback |
| conv_005_t1 | Classical music concerts February Paris | 0.30 | Events claimed but not shown |
| conv_005_t2 | What's the price for the second one? | 0.00 | Cannot reference previous events |

---

## Action Plan

### Priority 1: Fix Empty Response Bodies (Critical - 1 day)

**Problem:** Responses claim "Here are N events" but don't list them.

**Files to Modify:**
- [src/retrieval/chain.py](src/retrieval/chain.py) - Response composition logic
- [src/retrieval/response_builder.py](src/retrieval/response_builder.py) - Response templates

**Actions:**
1. Ensure `build_response()` always includes event details when events exist
2. If response would be truncated, include at least 3 events with full details
3. Never return a summary count without corresponding event listing

**Acceptance Criteria:**
- All responses with events must list at least the first event with title, date, location
- Faithfulness score >= 0.7 on initial queries

---

### Priority 2: Improve Session Context for Follow-ups (High - 2 days)

**Problem:** Follow-up queries lose context of what was previously shown.

**Files to Modify:**
- [src/retrieval/chain.py](src/retrieval/chain.py) - Session management
- [src/retrieval/unified_analyzer.py](src/retrieval/unified_analyzer.py) - Context preservation

**Actions:**
1. Store the last N events shown in session state
2. When user says "the first one" or "the second one", resolve to actual event
3. Maintain search context (jazz/Paris) for subsequent queries

**Acceptance Criteria:**
- Follow-up query "tell me about the first one" returns the first previously shown event
- Context filters (city, category) persist across turns

---

### Priority 3: Handle Vague Queries Gracefully (Medium - 1 day)

**Problem:** Query "events" returns unhelpful response.

**Files to Modify:**
- [src/generation/prompts.py](src/generation/prompts.py) - Clarification prompts
- [src/retrieval/chain.py](src/retrieval/chain.py) - Incompleteness detection

**Actions:**
1. Detect vague queries (no city, no category, no date)
2. Return clarification request: "What city? What type of event?"
3. Or provide smart defaults: "Here are popular events in Paris this week..."

**Acceptance Criteria:**
- Vague queries receive clarification or helpful default
- Quality score >= 0.6 on vague queries

---

### Priority 4: No Results Fallback (Medium - 1 day)

**Problem:** Zero events returns poor response.

**Files to Modify:**
- [src/retrieval/response_builder.py](src/retrieval/response_builder.py) - No results handling

**Actions:**
1. When no events found, suggest broadening search
2. Offer nearby cities or alternative dates
3. Never return quality=0 response

**Acceptance Criteria:**
- No results scenario returns helpful suggestions
- Minimum quality score 0.4 for no-results cases

---

### Priority 5: Event Reference Resolution (Lower - 2 days)

**Problem:** "What's the price for the second one?" fails.

**Files to Modify:**
- [src/retrieval/unified_analyzer.py](src/retrieval/unified_analyzer.py) - Reference detection
- [src/retrieval/chain.py](src/retrieval/chain.py) - Event lookup

**Actions:**
1. Detect ordinal references ("first", "second", "last")
2. Resolve to stored event from session
3. Return event-specific details (price, location, description)

**Acceptance Criteria:**
- Ordinal references resolve to correct event
- Detail queries (price, location, time) answered from event data

---

## Testing Plan

After implementing fixes:

1. **Unit Tests:** Add tests for each failure scenario
2. **Integration Tests:** Run golden dataset through API
3. **Regression Check:** Ensure fixes don't break working queries
4. **Target Metrics:**
   - Quality Score >= 0.70
   - Faithfulness >= 0.70
   - Relevancy >= 0.70
   - Initial Query Quality >= 0.60

---

## Appendix: Raw Metrics

```
Total Queries: 15
Successful: 15 (100%)
Failed: 0

Quality Distribution:
  >= 0.7: 9 queries (60%)
  0.5-0.7: 0 queries (0%)
  < 0.5: 6 queries (40%)

Latency Distribution:
  Average: 3894ms
  P50: ~2000ms
  P95: 19249ms
  Max: 12696ms (follow-up query)
```

---

**Report Generated:** 2026-02-01
**Next Review:** After Priority 1 & 2 fixes implemented
