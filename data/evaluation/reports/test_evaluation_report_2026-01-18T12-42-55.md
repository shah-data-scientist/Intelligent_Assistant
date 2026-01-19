# RAG System Evaluation Report

**Date:** 2026-01-18T12:42:55.569265  
**Dataset:** v2.0  
**Total Queries:** 3

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.317 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 0ms | < 2000.0ms | ✅ PASS |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| *No ground truth available* | - |

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.133 |
| Relevancy | 0.500 |
| Language Consistency | 100% |
| **Quality Score** | **0.317** |

**Interpretation:**  
- 13% grounding to sources (minimal hallucination)
- 50% relevance to user queries
- 100% language consistency (bilingual support)

## Latency Analysis

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| entity_specific | 1 | N/A | 0.200 |
| metadata_heavy | 1 | N/A | 0.550 |
| simple_search | 1 | N/A | 0.200 |

## Recommendations

- **Low Faithfulness (0.13)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.50)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **Low Performance on 'simple_search' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.20)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
