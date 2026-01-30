# RAG System Evaluation Report

**Date:** 2026-01-28T23:44:52.174432
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.510 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 15907ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.320 |
| Relevancy | 0.700 |
| Language Consistency | 70% |
| **Quality Score** | **0.510** |

**Interpretation:**
- 32% grounding to sources (minimal hallucination)
- 70% relevance to user queries
- 70% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 15907 |
| Min | 11430 |
| P50 (Median) | 15985 |
| P95 | 22421 |
| P99 | 22421 |
| Max | 22421 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.600 |
| follow_up | 1 | N/A | 0.150 |
| initial | 4 | N/A | 0.600 |
| refinement | 2 | N/A | 0.287 |
| topic_shift | 1 | N/A | 0.775 |

## Recommendations

- **Low Faithfulness (0.32)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **High Latency (15907ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.60)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.29)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.60)**: Consider adding more training examples or specific handling for this query type.
