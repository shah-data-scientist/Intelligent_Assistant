# RAG System Evaluation Report

**Date:** 2026-01-18T17:03:27.979927  
**Dataset:** v2.0  
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.417 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 6843ms | < 2000.0ms | ❌ FAIL |
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
| Faithfulness | 0.233 |
| Relevancy | 0.600 |
| Language Consistency | 100% |
| **Quality Score** | **0.417** |

**Interpretation:**  
- 23% grounding to sources (minimal hallucination)
- 60% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 6843 |
| Min | 4505 |
| P50 (Median) | 7438 |
| P95 | 8585 |
| P99 | 8585 |
| Max | 8585 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | 1.000 | 0.200 |
| metadata_heavy | 1 | 1.000 | 0.350 |
| simple_search | 1 | 1.000 | 0.700 |

## Recommendations

- **Low Faithfulness (0.23)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.60)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (6843ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'entity_specific' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
