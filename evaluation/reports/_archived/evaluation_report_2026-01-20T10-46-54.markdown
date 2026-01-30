# RAG System Evaluation Report

**Date:** 2026-01-20T10:46:54.906362
**Dataset:** v2.0
**Total Queries:** 118

---

## Overall Status

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality Score | 0.671 | ≥ 0.8 | ❌ FAIL |
| Avg Latency | 14653ms | < 2000.0ms | ❌ FAIL |
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
| Faithfulness | 0.600 |
| Relevancy | 0.743 |
| Language Consistency | 56% |
| **Quality Score** | **0.671** |

**Interpretation:**
- 60% grounding to sources (minimal hallucination)
- 74% relevance to user queries
- 56% language consistency (bilingual support)

## Latency Analysis

| Percentile | Latency (ms) |
|------------|--------------|
| Average | 14653 |
| Min | 2502 |
| P50 (Median) | 11794 |
| P95 | 36492 |
| P99 | 39539 |
| Max | 85286 |

**SLA Compliance:** 0% of queries under 2000ms

## Query Type Breakdown

| Query Type | Count | Avg Hit Rate | Avg Quality |
|------------|-------|--------------|-------------|
| accessibility | 2 | 0.000 | 0.825 |
| age_filter | 2 | N/A | 0.875 |
| comparison | 1 | 1.000 | 0.875 |
| complex | 10 | 0.667 | 0.758 |
| conditional | 2 | 1.000 | 0.338 |
| edge_case | 6 | 1.000 | 0.650 |
| entity_specific | 17 | 0.938 | 0.678 |
| event_series | 1 | N/A | 0.425 |
| follow_up | 2 | 1.000 | 0.800 |
| genre_search | 2 | 0.000 | 0.875 |
| geographic_complex | 4 | 0.750 | 0.444 |
| language | 1 | N/A | 0.900 |
| language_mix | 5 | 0.800 | 0.480 |
| location_specific | 2 | N/A | 0.800 |
| metadata_heavy | 16 | 0.875 | 0.609 |
| multi_criteria | 2 | 0.000 | 0.825 |
| multi_turn | 8 | 1.000 | 0.778 |
| negation | 1 | 1.000 | 0.450 |
| negative_filter | 1 | N/A | 0.825 |
| price_filter | 2 | 0.000 | 0.800 |
| ranking | 1 | 0.000 | 0.825 |
| simple_search | 18 | 0.778 | 0.697 |
| temporal_complex | 7 | 1.000 | 0.618 |
| time_filter | 2 | N/A | 0.575 |
| vague | 2 | 1.000 | 0.287 |
| venue_specific | 1 | N/A | 0.900 |

## Recommendations

- **Low Faithfulness (0.60)**: High hallucination risk. Review RAG prompts and grounding instructions.
- **High Latency (14653ms)**: Exceeds SLA. Optimize FAISS search, reduce LLM token usage, or use caching.
- **Low Performance on 'simple_search' queries (0.70)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'entity_specific' queries (0.68)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'metadata_heavy' queries (0.61)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'edge_case' queries (0.65)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'language_mix' queries (0.48)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'temporal_complex' queries (0.62)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'geographic_complex' queries (0.44)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'negation' queries (0.45)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'conditional' queries (0.34)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'vague' queries (0.29)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'time_filter' queries (0.57)**: Consider adding more training examples or specific handling for this query type.
- **Low Performance on 'event_series' queries (0.42)**: Consider adding more training examples or specific handling for this query type.
