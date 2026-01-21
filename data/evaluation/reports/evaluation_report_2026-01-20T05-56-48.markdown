# RAG System Evaluation Report

**Date:** 2026-01-20T05:56:48.400741  
**Dataset:** v2.0  
**Total Queries:** 118

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.609 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 17545ms | < 2000.0ms | ❌ FAIL |
| **Overall** | - | - | ❌ **FAIL** |

## Retrieval Performance

| Metric | Score |
|--------|-------|
| Hit Rate | 0.817 |
| MRR | 0.660 |
| Precision@5 | 0.342 |
| Recall@5 | 0.558 |
| F1@5 | 0.423 |

**Interpretation:**  
- 82% of queries retrieved at least one relevant event
- Average rank of first relevant result: 1.5
- 34% of top-5 results are relevant

## Generation Quality

| Metric | Score |
|--------|-------|
| Faithfulness | 0.370 |
| Relevancy | 0.848 |
| Language Consistency | 59% |
| **Quality Score** | **0.609** |

**Interpretation:**  
- 37% grounding to sources (minimal hallucination)
- 85% relevance to user queries
- 59% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 17545 |
| Min | 3174 |
| P50 (Median) | 18133 |
| P95 | 32192 |
| P99 | 36378 |
| Max | 40616 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| accessibility | 2 | 0.000 | 0.550 |
| age_filter | 2 | N/A | 0.475 |
| comparison | 1 | 1.000 | 0.150 |
| complex | 10 | 0.667 | 0.698 |
| conditional | 2 | 1.000 | 0.700 |
| edge_case | 6 | 1.000 | 0.800 |
| entity_specific | 17 | 0.938 | 0.641 |
| event_series | 1 | N/A | 0.475 |
| follow_up | 2 | 1.000 | 0.800 |
| genre_search | 2 | 0.000 | 0.475 |
| geographic_complex | 4 | 0.750 | 0.487 |
| language | 1 | N/A | 0.475 |
| language_mix | 5 | 0.800 | 0.525 |
| location_specific | 2 | N/A | 0.525 |
| metadata_heavy | 16 | 0.875 | 0.566 |
| multi_criteria | 2 | 0.000 | 0.475 |
| multi_turn | 8 | 1.000 | 0.734 |
| negation | 1 | 1.000 | 0.675 |
| negative_filter | 1 | N/A | 0.475 |
| price_filter | 2 | 0.000 | 0.475 |
| ranking | 1 | 0.000 | 0.425 |
| simple_search | 18 | 0.778 | 0.674 |
| temporal_complex | 7 | 1.000 | 0.479 |
| time_filter | 2 | N/A | 0.475 |
| vague | 2 | 1.000 | 0.550 |
| venue_specific | 1 | N/A | 0.575 |

## Recommendations

- **Low Faithfulness (0.37)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **High Latency (17545ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.67)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.64)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.57)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'complex' queries (0.70)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language_mix' queries (0.53)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'temporal_complex' queries (0.48)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'geographic_complex' queries (0.49)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negation' queries (0.68)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'ranking' queries (0.42)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'comparison' queries (0.15)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'vague' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'price_filter' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'accessibility' queries (0.55)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'genre_search' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'location_specific' queries (0.52)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'age_filter' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'multi_criteria' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negative_filter' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'time_filter' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'venue_specific' queries (0.57)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'event_series' queries (0.47)**: Consider adding more training examples or specific handling for this query type.
