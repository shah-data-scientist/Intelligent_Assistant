# RAG System Evaluation Report

**Date:** 2026-01-28T16:37:20.420392
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.480 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 10799ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.460 |
| Relevancy | 0.500 |
| Language Consistency | 60% |
| **Quality Score** | **0.480** |

**Interpretation:**
- 46% grounding to sources (minimal hallucination)
- 50% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 10799 |
| Min | 1336 |
| P50 (Median) | 11251 |
| P95 | 23140 |
| P99 | 23140 |
| Max | 23140 |

**SLA Compliance:** 10% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.175 |
| follow_up | 1 | N/A | 0.925 |
| initial | 4 | N/A | 0.431 |
| refinement | 2 | N/A | 0.487 |
| topic_shift | 1 | N/A | 0.825 |

## Recommendations

- **Low Faithfulness (0.46)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.50)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (10799ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.43)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.49)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.17)**: Consider adding more training examples or specific handling for this query type.
