# RAG System Evaluation Report

**Date:** 2026-01-28T23:01:50.179761
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.585 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 15651ms | < 2000.0ms | ❌ FAIL |
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
| Average | 15651 |
| Min | 2772 |
| P50 (Median) | 16977 |
| P95 | 23275 |
| P99 | 23275 |
| Max | 23275 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.150 |
| follow_up | 1 | N/A | 0.875 |
| initial | 4 | N/A | 0.688 |
| refinement | 2 | N/A | 0.575 |
| topic_shift | 1 | N/A | 0.775 |

## Recommendations

- **Low Faithfulness (0.50)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.67)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (15651ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.69)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.57)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
