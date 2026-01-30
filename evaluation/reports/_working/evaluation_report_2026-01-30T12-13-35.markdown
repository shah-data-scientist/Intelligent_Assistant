# RAG System Evaluation Report

**Date:** 2026-01-30T12:13:35.941902
**Dataset:** v3.3
**Total Queries:** 5

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.585 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 37390ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.600 |
| Relevancy | 0.570 |
| Language Consistency | 100% |
| **Quality Score** | **0.585** |

**Interpretation:**
- 60% grounding to sources (minimal hallucination)
- 57% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 37390 |
| Min | 12217 |
| P50 (Median) | 24257 |
| P95 | 84355 |
| P99 | 84355 |
| Max | 84355 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| follow_up | 1 | N/A | 0.050 |
| initial | 2 | N/A | 0.800 |
| refinement | 1 | N/A | 0.900 |
| topic_shift | 1 | N/A | 0.375 |

## Recommendations

- **Low Faithfulness (0.60)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.57)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (37390ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'follow_up' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.38)**: Consider adding more training examples or specific handling for this query type.
