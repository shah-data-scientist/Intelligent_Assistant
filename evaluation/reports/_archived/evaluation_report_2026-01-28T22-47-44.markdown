# RAG System Evaluation Report

**Date:** 2026-01-28T22:47:44.760847
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.375 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 10587ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.360 |
| Relevancy | 0.390 |
| Language Consistency | 70% |
| **Quality Score** | **0.375** |

**Interpretation:**
- 36% grounding to sources (minimal hallucination)
- 39% relevance to user queries
- 70% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 10587 |
| Min | 2730 |
| P50 (Median) | 10753 |
| P95 | 15769 |
| P99 | 15769 |
| Max | 15769 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.150 |
| follow_up | 1 | N/A | 0.875 |
| initial | 4 | N/A | 0.431 |
| refinement | 2 | N/A | 0.150 |
| topic_shift | 1 | N/A | 0.550 |

## Recommendations

- **Low Faithfulness (0.36)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.39)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (10587ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.43)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
