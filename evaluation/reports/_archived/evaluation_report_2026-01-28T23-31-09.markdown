# RAG System Evaluation Report

**Date:** 2026-01-28T23:31:09.430747
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.585 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 15536ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.500 |
| Relevancy | 0.670 |
| Language Consistency | 70% |
| **Quality Score** | **0.585** |

**Interpretation:**
- 50% grounding to sources (minimal hallucination)
- 67% relevance to user queries
- 70% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 15536 |
| Min | 5682 |
| P50 (Median) | 15494 |
| P95 | 24318 |
| P99 | 24318 |
| Max | 24318 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.537 |
| follow_up | 1 | N/A | 0.000 |
| initial | 4 | N/A | 0.688 |
| refinement | 2 | N/A | 0.625 |
| topic_shift | 1 | N/A | 0.775 |

## Recommendations

- **Low Faithfulness (0.50)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.67)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (15536ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.69)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.62)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.54)**: Consider adding more training examples or specific handling for this query type.
