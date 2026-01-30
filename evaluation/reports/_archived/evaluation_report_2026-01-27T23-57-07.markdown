# RAG System Evaluation Report

**Date:** 2026-01-27T23:57:07.066024
**Dataset:** v3.0
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.520 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 13246ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.410 |
| Relevancy | 0.630 |
| Language Consistency | 60% |
| **Quality Score** | **0.520** |

**Interpretation:**
- 41% grounding to sources (minimal hallucination)
- 63% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 13246 |
| Min | 87 |
| P50 (Median) | 16514 |
| P95 | 22700 |
| P99 | 22700 |
| Max | 22700 |

**SLA Compliance:** 10% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.388 |
| follow_up | 1 | N/A | 0.100 |
| initial | 4 | N/A | 0.650 |
| refinement | 2 | N/A | 0.425 |
| topic_shift | 1 | N/A | 0.875 |

## Recommendations

- **Low Faithfulness (0.41)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.63)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (13246ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.42)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.10)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.39)**: Consider adding more training examples or specific handling for this query type.
