# RAG System Evaluation Report

**Date:** 2026-02-01T00:28:02.079547
**Dataset:** v3.3
**Total Queries:** 5

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.325 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 35122ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.280 |
| Relevancy | 0.370 |
| Language Consistency | 100% |
| **Quality Score** | **0.325** |

**Interpretation:**
- 28% grounding to sources (minimal hallucination)
- 37% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 35122 |
| Min | 12187 |
| P50 (Median) | 17280 |
| P95 | 105876 |
| P99 | 105876 |
| Max | 105876 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| follow_up | 1 | N/A | 0.400 |
| initial | 2 | N/A | 0.050 |
| refinement | 1 | N/A | 0.750 |
| topic_shift | 1 | N/A | 0.375 |

## Recommendations

- **Low Faithfulness (0.28)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.37)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (35122ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'initial' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.40)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'topic_shift' queries (0.38)**: Consider adding more training examples or specific handling for this query type.
