# RAG System Evaluation Report

**Date:** 2026-01-27T16:42:02.048416
**Dataset:** v3.0
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.593 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 2715ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.460 |
| Relevancy | 0.725 |
| Language Consistency | 60% |
| **Quality Score** | **0.593** |

**Interpretation:**
- 46% grounding to sources (minimal hallucination)
- 72% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 2715 |
| Min | 37 |
| P50 (Median) | 2577 |
| P95 | 5199 |
| P99 | 5199 |
| Max | 5199 |

**SLA Compliance:** 20% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.838 |
| follow_up | 1 | N/A | 0.300 |
| initial | 4 | N/A | 0.706 |
| refinement | 2 | N/A | 0.375 |
| topic_shift | 1 | N/A | 0.375 |

## Recommendations

- **Low Faithfulness (0.46)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **High Latency (2715ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'refinement' queries (0.38)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.30)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.38)**: Consider adding more training examples or specific handling for this query type.
