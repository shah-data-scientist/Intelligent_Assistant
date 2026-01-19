# RAG System Evaluation Report

**Date:** 2026-01-18T16:54:05.291968  
**Dataset:** v2.0  
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.450 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 8517ms | < 2000.0ms | ❌ FAIL |
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
| Faithfulness | 0.300 |
| Relevancy | 0.600 |
| Language Consistency | 100% |
| **Quality Score** | **0.450** |

**Interpretation:**  
- 30% grounding to sources (minimal hallucination)
- 60% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 8517 |
| Min | 6394 |
| P50 (Median) | 8508 |
| P95 | 10648 |
| P99 | 10648 |
| Max | 10648 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | N/A | 0.350 |
| metadata_heavy | 1 | 0.000 | 0.350 |
| simple_search | 1 | 0.000 | 0.650 |

## Recommendations

- **Low Hit Rate (0.00)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.00)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **Low Faithfulness (0.30)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.60)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (8517ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
