# RAG System Evaluation Report

**Date:** 2026-01-18T16:49:46.887696
**Dataset:** v2.0
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.283 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 5669ms | < 2000.0ms | ❌ FAIL |
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
| Faithfulness | 0.000 |
| Relevancy | 0.567 |
| Language Consistency | 67% |
| **Quality Score** | **0.283** |

**Interpretation:**
- 0% grounding to sources (minimal hallucination)
- 57% relevance to user queries
- 67% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 5669 |
| Min | 3745 |
| P50 (Median) | 4486 |
| P95 | 8775 |
| P99 | 8775 |
| Max | 8775 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | N/A | 0.200 |
| metadata_heavy | 1 | 0.000 | 0.350 |
| simple_search | 1 | N/A | 0.300 |

## Recommendations

- **Low Hit Rate (0.00)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.00)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **Low Faithfulness (0.00)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.57)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (5669ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.30)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.35)**: Consider adding more training examples or specific handling for this query type.
