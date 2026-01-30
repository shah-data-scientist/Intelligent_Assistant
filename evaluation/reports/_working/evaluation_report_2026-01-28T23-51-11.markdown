# RAG System Evaluation Report

**Date:** 2026-01-28T23:51:11.502256
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.615 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 15404ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.540 |
| Relevancy | 0.690 |
| Language Consistency | 60% |
| **Quality Score** | **0.615** |

**Interpretation:**
- 54% grounding to sources (minimal hallucination)
- 69% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 15404 |
| Min | 4826 |
| P50 (Median) | 14637 |
| P95 | 27886 |
| P99 | 27886 |
| Max | 27886 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.525 |
| follow_up | 1 | N/A | 0.925 |
| initial | 4 | N/A | 0.706 |
| refinement | 2 | N/A | 0.287 |
| topic_shift | 1 | N/A | 0.775 |

## Recommendations

- **Low Faithfulness (0.54)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.69)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (15404ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'refinement' queries (0.29)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.53)**: Consider adding more training examples or specific handling for this query type.
