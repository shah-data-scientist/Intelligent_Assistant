# RAG System Evaluation Report

**Date:** 2026-01-22T19:34:37.024794
**Dataset:** v2.0
**Total Queries:** 5

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.800 | ≥ 0.8 | ✅ PASS |
| Avg Latency | 18059ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 0.600 |
| MRR | 0.467 |
| Precision@5 | 0.120 |
| Recall@5 | 0.200 |
| F1@5 | 0.150 |

**Interpretation:**
- 60% of queries retrieved at least one relevant event
- Average rank of first relevant result: 2.1
- 12% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.900 |
| Relevancy | 0.700 |
| Language Consistency | 100% |
| **Quality Score** | **0.800** |

**Interpretation:**
- 90% grounding to sources (minimal hallucination)
- 70% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 18059 |
| Min | 9708 |
| P50 (Median) | 17710 |
| P95 | 27624 |
| P99 | 27624 |
| Max | 27624 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| edge_case | 1 | 1.000 | 0.875 |
| entity_specific | 1 | 1.000 | 0.775 |
| metadata_heavy | 1 | 0.000 | 0.650 |
| simple_search | 2 | 0.500 | 0.850 |

## Recommendations

- **Low Hit Rate (0.60)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.47)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **High Latency (18059ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'metadata_heavy' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
