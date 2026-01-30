# RAG System Evaluation Report

**Date:** 2026-01-28T22:38:16.572426
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.603 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 12373ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.760 |
| Relevancy | 0.445 |
| Language Consistency | 50% |
| **Quality Score** | **0.603** |

**Interpretation:**
- 76% grounding to sources (minimal hallucination)
- 44% relevance to user queries
- 50% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 12373 |
| Min | 3922 |
| P50 (Median) | 13277 |
| P95 | 15293 |
| P99 | 15293 |
| Max | 15293 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.512 |
| follow_up | 1 | N/A | 0.650 |
| initial | 4 | N/A | 0.612 |
| refinement | 2 | N/A | 0.675 |
| topic_shift | 1 | N/A | 0.550 |

## Recommendations

- **Low Faithfulness (0.76)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.45)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (12373ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.61)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.68)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.51)**: Consider adding more training examples or specific handling for this query type.
