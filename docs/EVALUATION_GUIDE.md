# Evaluation Framework Guide

This guide explains how to use the RAG system evaluation framework to assess retrieval quality, generation quality, and overall system performance.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Metrics Explained](#metrics-explained)
- [Running Evaluations](#running-evaluations)
- [Understanding Reports](#understanding-reports)
- [Golden Dataset](#golden-dataset)
- [Adding Custom Queries](#adding-custom-queries)
- [Troubleshooting](#troubleshooting)

## Overview

The evaluation framework provides automated testing of your RAG system across three dimensions:

1. **Retrieval Quality**: How well does the system find relevant events?
2. **Generation Quality**: How accurate and relevant are the generated answers?
3. **Performance**: Does the system meet latency SLAs?

**Key Features:**
- 50-query golden dataset with diverse query types
- LLM-as-a-Judge for quality evaluation
- Multi-backend support (Mistral/Hugging Face/Ollama)
- Multi-format reports (JSON/Markdown/HTML)
- SLA compliance checking (Quality > 0.8, Latency < 2s)

## Quick Start

### 1. Run Quick Test (5 queries)

```bash
# Using Mistral (default, requires API key)
poetry run python -m scripts.run_evaluation --subset 5

# Using Hugging Face (free, requires HF_TOKEN)
export HF_TOKEN=hf_your_token_here
poetry run python -m scripts.run_evaluation --subset 5 --judge-backend huggingface

# Using Ollama (local, completely free)
ollama serve  # In another terminal
poetry run python -m scripts.run_evaluation --subset 5 --judge-backend ollama
```

### 2. Run Full Evaluation (50 queries)

```bash
# Full evaluation with markdown report
poetry run python -m scripts.run_evaluation --format markdown

# Multiple formats
poetry run python -m scripts.run_evaluation --format markdown --format json --format html
```

### 3. View Results

Reports are saved to `data/evaluation/reports/`:

```bash
# View latest markdown report
cat data/evaluation/reports/evaluation_report_*.md | tail -1
```

## Metrics Explained

### Retrieval Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Hit Rate** | Did we retrieve at least one relevant document? | 0.0-1.0, higher is better |
| **MRR** | Mean Reciprocal Rank of first relevant document | 0.0-1.0, rewards top results |
| **Precision@k** | Fraction of retrieved docs that are relevant | 0.0-1.0, higher is better |
| **Recall@k** | Fraction of relevant docs that were retrieved | 0.0-1.0, higher is better |
| **F1@k** | Harmonic mean of Precision and Recall | 0.0-1.0, balanced metric |
| **NDCG@k** | Normalized Discounted Cumulative Gain | 0.0-1.0, rewards ranking |

**Example:**
```
Hit Rate: 0.85  →  85% of queries found at least one relevant event
MRR: 0.65       →  Relevant events appear at average rank ~1.5
Precision@5: 0.60 → 60% of top-5 results are relevant
```

### Generation Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Faithfulness** | Are answers grounded in sources? | 0.0-1.0, detects hallucination |
| **Relevancy** | Do answers address the query? | 0.0-1.0, measures usefulness |
| **Language Consistency** | Does answer match query language? | 0-100%, validates bilingual support |
| **Quality Score** | Average of Faithfulness + Relevancy | 0.0-1.0, overall quality metric |

**Faithfulness Example:**
```
Score: 0.9  →  90% grounding to sources (minimal hallucination)
Score: 0.3  →  30% grounding (high hallucination risk)
```

**Relevancy Example:**
```
Score: 0.9  →  Answer directly addresses query
Score: 0.4  →  Answer is vague or off-topic
```

### Latency Analysis

| Metric | Description | SLA Target |
|--------|-------------|------------|
| **Avg Latency** | Mean response time | < 2000ms |
| **P50 Latency** | 50th percentile (median) | < 2000ms |
| **P95 Latency** | 95th percentile | < 3000ms |
| **P99 Latency** | 99th percentile | < 4000ms |
| **SLA Compliance Rate** | % of queries meeting SLA | > 95% |

### SLA Thresholds

| Metric | Threshold | Status |
|--------|-----------|--------|
| Quality Score | ≥ 0.8 | ✅ PASS / ❌ FAIL |
| Avg Latency | < 2000ms | ✅ PASS / ❌ FAIL |

## Running Evaluations

### CLI Options

```bash
poetry run python -m scripts.run_evaluation [OPTIONS]
```

**Common Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `--subset N` | Evaluate only first N queries | `--subset 10` |
| `--judge-backend` | LLM backend (mistral/huggingface/ollama) | `--judge-backend huggingface` |
| `--format` | Report format (json/markdown/html) | `--format markdown` |
| `--output-dir` | Report output directory | `--output-dir ./reports` |
| `--dataset` | Custom dataset path | `--dataset ./my_dataset.json` |
| `--retrieval-k` | Number of docs to retrieve | `--retrieval-k 10` |
| `--verbose` | Enable debug logging | `--verbose` |

**Hugging Face Options:**
```bash
--judge-backend huggingface \
--hf-token hf_your_token \
--hf-model mistralai/Mistral-7B-Instruct-v0.2
```

**Ollama Options:**
```bash
--judge-backend ollama \
--ollama-model mistral
```

### Programmatic Usage

```python
from src.evaluation.evaluators.system_evaluator import SystemEvaluator
from src.evaluation.reports.reporter import ReportGenerator

# Initialize evaluator
evaluator = SystemEvaluator(judge_backend="mistral")

# Run evaluation
report = evaluator.run_full_evaluation(
    golden_dataset_path="data/evaluation/golden_dataset.json",
    retrieval_k=5
)

# Generate report
reporter = ReportGenerator()
reporter.save_report(report, "my_report.md", format="markdown")

# Check SLA
if report.overall_status["overall_pass"]:
    print("✅ System meets SLA requirements")
else:
    print("❌ System fails SLA requirements")
```

## Understanding Reports

### Report Structure

```markdown
# RAG System Evaluation Report

## Overall Status
- Quality Score: 0.85 ✅ PASS
- Avg Latency: 1500ms ✅ PASS
- Overall: ✅ PASS

## Retrieval Performance
- Hit Rate: 0.90
- MRR: 0.75
- Precision@5: 0.80

## Generation Quality
- Faithfulness: 0.82 (82% grounding)
- Relevancy: 0.88 (88% relevance)
- Quality Score: 0.85

## Latency Analysis
- P50: 1200ms
- P95: 1800ms
- P99: 2100ms
- SLA Compliance: 95%

## Query Type Breakdown
- simple_search: 0.90 quality
- complex: 0.80 quality
- multi_turn: 0.85 quality

## Recommendations
- ✅ System performing well
- Consider improving X...
```

### Interpreting Recommendations

The report automatically generates recommendations based on metric thresholds:

| Condition | Recommendation |
|-----------|----------------|
| Hit Rate < 0.7 | Low Hit Rate: Improve retrieval (embeddings, filters) |
| MRR < 0.5 | Low MRR: Relevant docs not ranking high (add reranking) |
| Faithfulness < 0.7 | High hallucination: Review RAG prompts and grounding |
| Relevancy < 0.6 | Low relevance: Review generation prompts |
| P95 > 3000ms | Slow queries: Optimize retrieval or add caching |

## Golden Dataset

### Dataset Structure

The golden dataset is located at [data/evaluation/golden_dataset.json](../data/evaluation/golden_dataset.json).

**Current Stats (v2.0):**
- 50 total queries
- Query types: simple_search (10), complex (10), multi_turn (8), entity_specific (8), edge_case (6), metadata_heavy (4), language_mix (4)
- Languages: French (17), English (29), Mixed (4)

**Query Schema:**
```json
{
  "id": "Q001",
  "query": "Concerts de jazz à Paris en février",
  "language": "fr",
  "query_type": "simple_search",
  "complexity": "low",
  "expected_entities": ["jazz", "Paris", "février"],
  "expected_categories": ["Musique"],
  "expected_filters": {
    "city": "Paris",
    "month": 2,
    "category": "Musique"
  },
  "relevance_ground_truth": [
    {"event_id": "evt_123", "relevance_score": 1.0}
  ],
  "generation_expectations": {
    "must_contain_keywords": ["jazz", "Paris"],
    "must_not_hallucinate": true,
    "should_ask_clarification": false,
    "expected_language": "fr"
  }
}
```

### Query Types

| Type | Description | Count | Example |
|------|-------------|-------|---------|
| **simple_search** | Basic keyword searches | 10 | "Music concerts in Versailles" |
| **complex** | Multi-filter searches | 10 | "Free outdoor events in Paris during June for families" |
| **multi_turn** | Conversation context | 8 | "Tell me more about the first one" |
| **entity_specific** | Named entities | 8 | "Calogero performances and concerts" |
| **edge_case** | Boundary conditions | 6 | "events", "unicorn exhibitions" |
| **metadata_heavy** | Metadata filters | 4 | "Events with audio description and subtitles" |
| **language_mix** | Mixed languages | 4 | "Je cherche des concerts but tell me in English" |

## Adding Custom Queries

### Option 1: Edit JSON Directly

1. Open [data/evaluation/golden_dataset.json](../data/evaluation/golden_dataset.json)
2. Add a new query following the schema above
3. Get real event IDs from the database:

```python
from src.data.storage import EventStorage
storage = EventStorage()
events = storage.get_all_events()

# Find relevant events
for event in events:
    if "jazz" in event.title.lower():
        print(f"ID: {event.event_id}, Title: {event.title}")
```

4. Save and validate:

```python
from src.evaluation.datasets.golden_dataset import GoldenDataset
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")
print(f"Total queries: {dataset.total_queries}")  # Should increment
```

### Option 2: Programmatic Addition

```python
from src.evaluation.datasets.golden_dataset import GoldenDataset, Query

# Load existing dataset
dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")

# Create new query
new_query = Query(
    id=f"Q{len(dataset.queries) + 1:03d}",
    query="What are the best theater shows this month?",
    language="en",
    query_type="simple_search",
    complexity="low",
    expected_entities=["theater", "shows", "month"],
    expected_categories=["Théâtre"],
    expected_filters={"category": "Théâtre"},
    relevance_ground_truth=[],
    generation_expectations={
        "must_contain_keywords": ["theater", "show"],
        "must_not_hallucinate": True,
        "should_ask_clarification": False,
        "expected_language": "en"
    }
)

# Add to dataset
dataset.queries.append(new_query)

# Save
dataset.save("data/evaluation/golden_dataset.json")
```

### Best Practices

1. **Diverse Query Types**: Include various query types to test different aspects
2. **Real Event IDs**: Use actual event IDs from the database for ground truth
3. **Balanced Languages**: Maintain 60/40 English/French ratio
4. **Edge Cases**: Include challenging queries (typos, vague, no results)
5. **Complexity Mix**: Vary complexity (low/medium/high)

## Troubleshooting

### Common Issues

**Issue: "No module named 'src'"**
```bash
# Solution: Run as module
poetry run python -m scripts.run_evaluation
```

**Issue: "Hugging Face Authentication failed"**
```bash
# Solution: Set HF_TOKEN
export HF_TOKEN=hf_your_token_here
poetry run python -m scripts.run_evaluation --judge-backend huggingface
```

**Issue: "Ollama connection refused"**
```bash
# Solution: Start Ollama server
ollama serve

# In another terminal
poetry run python -m scripts.run_evaluation --judge-backend ollama
```

**Issue: "No index loaded" errors**
```bash
# Solution: Rebuild FAISS index
poetry run python scripts/rebuild_index.py
```

**Issue: Low quality scores**
- **High hallucination (low faithfulness)**: Review RAG prompts in [src/retrieval/chain.py](../src/retrieval/chain.py)
- **Low relevancy**: Improve retrieval quality or generation prompts
- **Poor retrieval**: Rebuild index with better embeddings

### Debug Mode

```bash
# Enable verbose logging
poetry run python -m scripts.run_evaluation --verbose --subset 3
```

### Validation

```python
# Test individual components
from src.evaluation.metrics.retrieval import RetrievalMetrics

retrieved = ["evt_1", "evt_2", "evt_3"]
relevant = ["evt_2", "evt_5"]

print(f"Hit Rate: {RetrievalMetrics.hit_rate(retrieved, relevant)}")
print(f"MRR: {RetrievalMetrics.mean_reciprocal_rank(retrieved, relevant)}")
```

## Next Steps

1. **Baseline Evaluation**: Run full evaluation to establish baseline metrics
2. **Identify Issues**: Review report recommendations
3. **Iterate**: Improve retrieval/generation based on findings
4. **Re-evaluate**: Run evaluation again to measure improvement
5. **Monitor**: Set up regular evaluations (CI/CD)

## Additional Resources

- **Backend Setup**: [EVALUATION_BACKENDS.md](EVALUATION_BACKENDS.md)
- **API Reference**: Generated docs in `docs/api/`
- **Test Examples**: [tests/test_evaluation_metrics.py](../tests/test_evaluation_metrics.py)
- **Project Memory**: [PROJECT_MEMORY.md](../PROJECT_MEMORY.md)
