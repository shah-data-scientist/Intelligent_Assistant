# RAG System Evaluation Report

**Date:** 2026-01-18T18:07:21.381643  
**Dataset:** v2.0  
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.700 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 8060ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 1.000 |
| MRR | 1.000 |
| Precision@5 | 0.600 |
| Recall@5 | 1.000 |
| F1@5 | 0.750 |

**Interpretation:**  
- 100% of queries retrieved at least one relevant event
- Average rank of first relevant result: 1.0
- 60% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.867 |
| Relevancy | 0.533 |
| Language Consistency | 67% |
| **Quality Score** | **0.700** |

**Interpretation:**  
- 87% grounding to sources (minimal hallucination)
- 53% relevance to user queries
- 67% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 8060 |
| Min | 5632 |
| P50 (Median) | 6995 |
| P95 | 11552 |
| P99 | 11552 |
| Max | 11552 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | 1.000 | 0.550 |
| metadata_heavy | 1 | 1.000 | 0.650 |
| simple_search | 1 | 1.000 | 0.900 |

## Recommendations

- **Low Relevancy (0.53)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (8060ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'entity_specific' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
