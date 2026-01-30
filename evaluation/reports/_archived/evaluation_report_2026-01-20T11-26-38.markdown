# RAG System Evaluation Report

**Date:** 2026-01-20T11:26:38.980420
**Dataset:** v2.0
**Total Queries:** 4

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.606 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 14041ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 0.000 |
| MRR | 0.000 |
| Precision@5 | 0.000 |
| Recall@5 | 0.000 |
| F1@5 | 0.000 |

**Interpretation:**
- 0% of queries retrieved at least one relevant event
- Average rank of first relevant result: inf
- 0% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.550 |
| Relevancy | 0.662 |
| Language Consistency | 50% |
| **Quality Score** | **0.606** |

**Interpretation:**
- 55% grounding to sources (minimal hallucination)
- 66% relevance to user queries
- 50% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 14041 |
| Min | 5372 |
| P50 (Median) | 18920 |
| P95 | 24934 |
| P99 | 24934 |
| Max | 24934 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| accessibility | 1 | 0.000 | 0.875 |
| metadata_heavy | 1 | 0.000 | 0.875 |
| price_filter | 2 | 0.000 | 0.338 |

## Recommendations

- **Low Hit Rate (0.00)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.00)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **Low Faithfulness (0.55)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.66)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (14041ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'price_filter' queries (0.34)**: Consider adding more training examples or specific handling for this query type.
