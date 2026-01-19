# RAG System Evaluation Report

**Date:** 2026-01-18T18:26:23.925882  
**Dataset:** v2.0  
**Total Queries:** 10

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.595 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 8931ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 1.000 |
| MRR | 1.000 |
| Precision@5 | 0.644 |
| Recall@5 | 1.000 |
| F1@5 | 0.778 |

**Interpretation:**  
- 100% of queries retrieved at least one relevant event
- Average rank of first relevant result: 1.0
- 64% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.670 |
| Relevancy | 0.520 |
| Language Consistency | 30% |
| **Quality Score** | **0.595** |

**Interpretation:**  
- 67% grounding to sources (minimal hallucination)
- 52% relevance to user queries
- 30% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 8931 |
| Min | 4024 |
| P50 (Median) | 9163 |
| P95 | 22522 |
| P99 | 22522 |
| Max | 22522 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| complex | 4 | 1.000 | 0.613 |
| entity_specific | 2 | 1.000 | 0.475 |
| metadata_heavy | 1 | 1.000 | 0.700 |
| negation | 1 | 1.000 | 0.700 |
| ranking | 1 | 1.000 | 0.700 |
| vague | 1 | 1.000 | 0.450 |

## Recommendations

- **Low Faithfulness (0.67)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.52)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (8931ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'complex' queries (0.61)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.48)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'vague' queries (0.45)**: Consider adding more training examples or specific handling for this query type.
