# RAG System Evaluation Report

**Date:** 2026-01-22T00:45:36.554002
**Dataset:** v2.0
**Total Queries:** 118

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.036 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 5110ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 0.625 |
| MRR | 0.390 |
| Precision@5 | 0.000 |
| Recall@5 | 0.000 |
| F1@5 | 0.000 |

**Interpretation:**
- 62% of queries retrieved at least one relevant event
- Average rank of first relevant result: 2.6
- 0% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.015 |
| Relevancy | 0.057 |
| Language Consistency | 64% |
| **Quality Score** | **0.036** |

**Interpretation:**
- 2% grounding to sources (minimal hallucination)
- 6% relevance to user queries
- 64% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 5110 |
| Min | 2202 |
| P50 (Median) | 3952 |
| P95 | 9884 |
| P99 | 16901 |
| Max | 45738 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| accessibility | 2 | 0.000 | 0.025 |
| age_filter | 2 | N/A | 0.000 |
| comparison | 1 | 0.000 | 0.000 |
| complex | 10 | 0.667 | 0.092 |
| conditional | 2 | 1.000 | 0.000 |
| edge_case | 6 | 0.833 | 0.092 |
| entity_specific | 17 | 0.688 | 0.026 |
| event_series | 1 | N/A | 0.050 |
| follow_up | 2 | 1.000 | 0.050 |
| genre_search | 2 | 0.000 | 0.025 |
| geographic_complex | 4 | 0.500 | 0.000 |
| language | 1 | N/A | 0.050 |
| language_mix | 5 | 0.600 | 0.150 |
| location_specific | 2 | N/A | 0.025 |
| metadata_heavy | 16 | 0.625 | 0.003 |
| multi_criteria | 2 | 0.000 | 0.000 |
| multi_turn | 8 | 0.875 | 0.056 |
| negation | 1 | 0.000 | 0.000 |
| negative_filter | 1 | N/A | 0.000 |
| price_filter | 2 | 0.500 | 0.050 |
| ranking | 1 | 1.000 | 0.050 |
| simple_search | 18 | 0.556 | 0.017 |
| temporal_complex | 7 | 0.714 | 0.014 |
| time_filter | 2 | N/A | 0.050 |
| vague | 2 | 0.000 | 0.000 |
| venue_specific | 1 | N/A | 0.100 |

## Recommendations

- **Low Hit Rate (0.62)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.39)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **Low Faithfulness (0.02)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.06)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (5110ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.02)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'edge_case' queries (0.09)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'multi_turn' queries (0.06)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'complex' queries (0.09)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language_mix' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'temporal_complex' queries (0.01)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'geographic_complex' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negation' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'ranking' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'comparison' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'conditional' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'vague' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'price_filter' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'accessibility' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'genre_search' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'location_specific' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'age_filter' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'multi_criteria' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negative_filter' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'time_filter' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'venue_specific' queries (0.10)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'event_series' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
