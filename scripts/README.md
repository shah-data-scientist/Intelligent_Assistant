# Scripts Directory

**Last Updated:** 2026-01-20

This directory contains utility scripts for data processing, evaluation, metadata enrichment, and analysis.

---

## 📁 Directory Structure

```
scripts/
├── README.md                              # This file
├── Data Enrichment/
│   ├── enrich_metadata.py                 # Regex-based metadata inference
│   ├── llm_metadata_extraction.py         # LLM-powered metadata extraction
│   ├── run_llm_extraction_optimized.py    # Optimized LLM extraction
│   ├── test_llm_extraction.py             # Test LLM extraction on 5 events
│   └── add_ground_truth.py                # Add relevance ground truth to queries
├── Evaluation/
│   ├── add_diverse_test_queries.py        # Expand evaluation dataset
│   ├── generate_feedback_report.py        # Generate feedback reports
│   ├── run_evaluation.py                  # Run full evaluation suite
│   └── test_evaluation_backends.py        # Test different LLM backends
├── Data Management/
│   └── test_scraper.py                    # Test web scraping functionality
├── Analysis/
│   ├── analyze_data_gaps.py               # Analyze metadata coverage gaps
│   └── check_metrics.py                   # Quick metrics check (4 queries)
└── Debug/
    ├── debug_context_mismatch.py          # Debug context issues
    ├── debug_q001_retrieval.py            # Debug specific query retrieval
    ├── diagnose_classical_retrieval.py    # Diagnose classical music retrieval
    ├── diagnose_judge_scoring.py          # Diagnose LLM judge scoring
    └── fix_expected_filters.py            # Fix expected filters in queries
```

---

## 🚀 Data Enrichment Scripts

### enrich_metadata.py
**Purpose:** Regex-based metadata inference from event descriptions

**Features:**
- `infer_price_info()`: Detect free events and price patterns
- `infer_accessibility()`: Detect accessibility features
- `infer_age_suitability()`: Detect age appropriateness

**Usage:**
```bash
poetry run python scripts/enrich_metadata.py
```

**Results:** Added 229 metadata entries (Phase 5.3)

---

### llm_metadata_extraction.py
**Purpose:** Use Mistral LLM to extract structured metadata from event descriptions

**Extraction Fields:**
- price_category, price_min, price_max
- age_min, age_max, age_description
- accessibility_features (wheelchair, hearing_impaired, visually_impaired)
- time_of_day (morning, afternoon, evening, night)
- is_outdoor (boolean)

**Usage:**
```bash
poetry run python scripts/llm_metadata_extraction.py
```

**Note:** Processes ALL events (~2-3 hours). Use `run_llm_extraction_optimized.py` for faster execution.

---

### run_llm_extraction_optimized.py
**Purpose:** Optimized LLM extraction for high-value events only

**Optimization:**
- Only processes events with >100 char descriptions
- Only processes events missing metadata
- Processes 882 events (~30 minutes)

**Usage:**
```bash
poetry run python scripts/run_llm_extraction_optimized.py
```

**Results:** Added 380 metadata entries (Phase 5.5)

---

### test_llm_extraction.py
**Purpose:** Test LLM extraction on 5 sample events

**Usage:**
```bash
poetry run python scripts/test_llm_extraction.py
```

**Output:** Shows extracted metadata for 5 events with before/after comparison

---

### add_ground_truth.py
**Purpose:** Add relevance ground truth annotations to priority queries

**Features:**
- Intelligent matching algorithm (category, price, accessibility, city, genre, month)
- Scoring: 1.0 for strong matches (≥3 criteria), 0.5 for partial matches (≥2 criteria)
- Top 3 matches kept per query

**Usage:**
```bash
poetry run python scripts/add_ground_truth.py
```

**Results:** Annotated 8 priority queries (Phase 5.6)

---

## 📊 Evaluation Scripts

### run_evaluation.py
**Purpose:** Run comprehensive evaluation suite

**Features:**
- Full evaluation on golden dataset (118 queries)
- Multiple output formats (JSON, Markdown, HTML)
- Backend selection (Mistral, HuggingFace, Ollama)
- Subset testing support

**Usage:**
```bash
# Full evaluation with Mistral backend
poetry run python scripts/run_evaluation.py

# Evaluate 10 random queries
poetry run python scripts/run_evaluation.py --subset 10

# Use HuggingFace backend (free tier)
poetry run python scripts/run_evaluation.py --backend huggingface

# Generate markdown report
poetry run python scripts/run_evaluation.py --format markdown
```

**Documentation:** See [docs/EVALUATION_GUIDE.md](../docs/EVALUATION_GUIDE.md)

---

### add_diverse_test_queries.py
**Purpose:** Expand evaluation dataset with diverse query types

**Added Query Types:**
- Price-focused, Accessibility, Genre diversity
- Suburbs/regional, Multi-lingual, Age-specific
- Complex multi-criteria, Negative filters
- Time-specific, Venue-specific, Festival/series

**Usage:**
```bash
poetry run python scripts/add_diverse_test_queries.py
```

**Results:** Expanded dataset from 100 to 118 queries (Phase 5.4)

---

### generate_feedback_report.py
**Purpose:** Generate feedback reports from evaluation results

**Usage:**
```bash
poetry run python scripts/generate_feedback_report.py
```

---

### test_evaluation_backends.py
**Purpose:** Test different LLM backends for evaluation

**Backends:**
- Mistral (paid, highest quality)
- HuggingFace (free tier, good quality)
- Ollama (local, unlimited usage)

**Usage:**
```bash
poetry run python scripts/test_evaluation_backends.py
```

**Documentation:** See [docs/EVALUATION_BACKENDS.md](../docs/EVALUATION_BACKENDS.md)

---

## 🔍 Analysis Scripts

### analyze_data_gaps.py
**Purpose:** Analyze metadata coverage gaps in the database

**Features:**
- Counts events with/without each metadata type
- Identifies high-value candidates for enrichment
- Estimates coverage percentages

**Usage:**
```bash
poetry run python scripts/analysis/analyze_data_gaps.py
```

---

### check_metrics.py
**Purpose:** Quick metrics check on 4 representative queries

**Features:**
- Fast evaluation (~2 minutes)
- Tests: Children's concerts, Free jazz, Free family events, Accessible art
- Outputs: Faithfulness, Relevancy, Quality scores

**Usage:**
```bash
poetry run python scripts/analysis/check_metrics.py
```

**Note:** For full evaluation, use `run_evaluation.py`

---

## 🐛 Debug Scripts

These scripts are for debugging and diagnostics:

- **debug_context_mismatch.py**: Debug context building issues
- **debug_q001_retrieval.py**: Debug specific query retrieval (Q001)
- **diagnose_classical_retrieval.py**: Diagnose classical music retrieval issues
- **diagnose_judge_scoring.py**: Diagnose LLM judge scoring behavior
- **fix_expected_filters.py**: Fix expected_filters field in queries

**Usage:** Each script can be run directly with Python
```bash
poetry run python scripts/debug/<script_name>.py
```

---

## 📝 Best Practices

**Before Running Scripts:**
1. Ensure `.env` file is configured with API keys
2. Activate poetry environment: `poetry shell`
3. Database must be initialized: `data/events.db` must exist

**After Data Changes:**
1. Rebuild FAISS index: `poetry run python -m src.models.vector_store`
2. Re-evaluate metrics: `poetry run python scripts/analysis/check_metrics.py`
3. Update documentation if significant changes

**For New Scripts:**
1. Add to appropriate category in this README
2. Include purpose, features, usage, and expected results
3. Follow existing script structure (logging, error handling)
4. Add to git: `git add scripts/<script_name>.py`

---

## 🎯 Recommended Workflow

**For Metadata Enrichment:**
```bash
# 1. Analyze current gaps
poetry run python scripts/analysis/analyze_data_gaps.py

# 2. Run regex-based enrichment (fast)
poetry run python scripts/enrich_metadata.py

# 3. Test LLM extraction on 5 events
poetry run python scripts/test_llm_extraction.py

# 4. Run optimized LLM extraction (~30 min)
poetry run python scripts/run_llm_extraction_optimized.py

# 5. Rebuild FAISS index
poetry run python -m src.models.vector_store

# 6. Check metrics
poetry run python scripts/analysis/check_metrics.py
```

**For Evaluation:**
```bash
# 1. Quick check (4 queries, ~2 min)
poetry run python scripts/analysis/check_metrics.py

# 2. Medium evaluation (10 queries, ~5 min)
poetry run python scripts/run_evaluation.py --subset 10

# 3. Full evaluation (118 queries, ~25 min)
poetry run python scripts/run_evaluation.py --format markdown
```

---

## 📚 Related Documentation

- **[docs/EVALUATION_GUIDE.md](../docs/EVALUATION_GUIDE.md)** - Evaluation procedures
- **[docs/EVALUATION_BACKENDS.md](../docs/EVALUATION_BACKENDS.md)** - LLM backend options
- **[docs/FINAL_METRICS_REPORT.md](../docs/FINAL_METRICS_REPORT.md)** - Complete metrics journey
- **[PROJECT_MEMORY.md](../PROJECT_MEMORY.md)** - Project history and phases

---

**For questions or issues:**
- Check script output for error messages
- Review logs in `logs/` directory
- Consult documentation in `docs/` directory
- Review PROJECT_MEMORY.md for implementation details
