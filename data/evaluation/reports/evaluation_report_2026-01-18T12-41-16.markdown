# RAG System Evaluation Report

**Date:** 2026-01-18T12:41:16.581673  
**Dataset:** v2.0  
**Total Queries:** 5

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.520 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 0ms | < 2000.0ms | ✅ PASS |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.380 |
| Relevancy | 0.660 |
| Language Consistency | 60% |
| **Quality Score** | **0.520** |

**Interpretation:**  
- 38% grounding to sources (minimal hallucination)
- 66% relevance to user queries
- 60% language consistency (bilingual support)

## Latency Analysis

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| edge_case | 1 | N/A | 0.650 |
| entity_specific | 1 | N/A | 0.200 |
| metadata_heavy | 1 | N/A | 0.700 |
| simple_search | 2 | N/A | 0.525 |

## Recommendations

- **Low Faithfulness (0.38)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.66)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **Low Performance on 'simple_search' queries (0.52)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'edge_case' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
