# RAG System Evaluation Report

**Date:** 2026-01-22T00:04:12.211666
**Dataset:** v2.0
**Total Queries:** 118

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.103 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 3261ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 0.519 |
| MRR | 0.376 |
| Precision@5 | 0.158 |
| Recall@5 | 0.263 |
| F1@5 | 0.197 |

**Interpretation:**
- 52% of queries retrieved at least one relevant event
- Average rank of first relevant result: 2.7
- 16% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.109 |
| Relevancy | 0.097 |
| Language Consistency | 64% |
| **Quality Score** | **0.103** |

**Interpretation:**
- 11% grounding to sources (minimal hallucination)
- 10% relevance to user queries
- 64% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 3261 |
| Min | 983 |
| P50 (Median) | 2455 |
| P95 | 8537 |
| P99 | 17347 |
| Max | 22790 |

**SLA Compliance:** 31% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| accessibility | 2 | 0.000 | 0.000 |
| age_filter | 2 | N/A | 0.000 |
| comparison | 1 | 0.000 | 0.000 |
| complex | 10 | 0.667 | 0.173 |
| conditional | 2 | 0.500 | 0.000 |
| edge_case | 6 | 0.667 | 0.092 |
| entity_specific | 17 | 0.500 | 0.091 |
| event_series | 1 | N/A | 0.050 |
| follow_up | 2 | 1.000 | 0.175 |
| genre_search | 2 | 0.000 | 0.025 |
| geographic_complex | 4 | 0.750 | 0.062 |
| language | 1 | N/A | 0.050 |
| language_mix | 5 | 0.200 | 0.210 |
| location_specific | 2 | N/A | 0.025 |
| metadata_heavy | 16 | 0.500 | 0.100 |
| multi_criteria | 2 | 0.000 | 0.000 |
| multi_turn | 8 | 0.750 | 0.056 |
| negation | 1 | 0.000 | 0.000 |
| negative_filter | 1 | N/A | 0.000 |
| price_filter | 2 | 0.000 | 0.050 |
| ranking | 1 | 1.000 | 0.300 |
| simple_search | 18 | 0.500 | 0.114 |
| temporal_complex | 7 | 0.714 | 0.150 |
| time_filter | 2 | N/A | 0.050 |
| vague | 2 | 0.000 | 0.375 |
| venue_specific | 1 | N/A | 0.100 |

## Recommendations

- **Low Hit Rate (0.52)**: Consider improving retrieval by adjusting query refinement or expanding the index.
- **Low MRR (0.38)**: Relevant results are ranked too low. Review ranking algorithm or metadata filtering.
- **Low Faithfulness (0.11)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **Low Relevancy (0.10)**: Answers not addressing queries well. Review generation prompts and retrieval quality.
- **High Latency (3261ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.11)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.09)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.10)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'edge_case' queries (0.09)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'multi_turn' queries (0.06)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'complex' queries (0.17)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language_mix' queries (0.21)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'temporal_complex' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'geographic_complex' queries (0.06)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negation' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'ranking' queries (0.30)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'comparison' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'conditional' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'follow_up' queries (0.17)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'vague' queries (0.38)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'price_filter' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'accessibility' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'genre_search' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'location_specific' queries (0.03)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'age_filter' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'multi_criteria' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negative_filter' queries (0.00)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'time_filter' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'venue_specific' queries (0.10)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'event_series' queries (0.05)**: Consider adding more training examples or specific handling for this query type.
