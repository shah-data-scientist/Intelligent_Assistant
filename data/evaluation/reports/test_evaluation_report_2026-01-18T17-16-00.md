# RAG System Evaluation Report

**Date:** 2026-01-18T17:16:00.579886  
**Dataset:** v2.0  
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.300 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 6518ms | < 2000.0ms | ❌ FAIL |
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
| Faithfulness | 0.000 |
| Relevancy | 0.600 |
| Language Consistency | 100% |
| **Quality Score** | **0.300** |

**Interpretation:**  
- 0% grounding to sources (minimal hallucination)
- 60% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 6518 |
| Min | 4740 |
| P50 (Median) | 7341 |
| P95 | 7472 |
| P99 | 7472 |
| Max | 7472 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | 1.000 | 0.200 |
| metadata_heavy | 1 | 1.000 | 0.350 |
| simple_search | 1 | 1.000 | 0.350 |

## Recommendations

- **Low Faithfulness (0.00)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.60)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (6518ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
