# RAG System Evaluation Report

**Date:** 2026-01-28T15:51:36.454831
**Dataset:** v3.1
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.485 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 12453ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.280 |
| Relevancy | 0.690 |
| Language Consistency | 60% |
| **Quality Score** | **0.485** |

**Interpretation:**
- 28% grounding to sources (minimal hallucination)
- 69% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 12453 |
| Min | 1363 |
| P50 (Median) | 16309 |
| P95 | 24528 |
| P99 | 24528 |
| Max | 24528 |

**SLA Compliance:** 10% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| clarification_response | 2 | N/A | 0.125 |
| follow_up | 1 | N/A | 0.925 |
| initial | 4 | N/A | 0.656 |
| refinement | 2 | N/A | 0.312 |
| topic_shift | 1 | N/A | 0.425 |

## Recommendations

- **Low Faithfulness (0.28)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.69)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (12453ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.66)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'refinement' queries (0.31)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.42)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'clarification_response' queries (0.12)**: Consider adding more training examples or specific handling for this query type.
