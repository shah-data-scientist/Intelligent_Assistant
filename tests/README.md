# Test Suite Organization

**Last Updated:** 2026-01-30
**Total Tests:** 29 test files
**Structure:** Organized by test type

---

## Directory Structure

```
tests/
├── unit/              # Fast, isolated tests (< 1s each)
├── integration/       # Component interaction tests (1-5s each)
├── e2e/              # End-to-end tests (5s+)
├── security/         # Security-specific tests
├── evaluation/       # AI quality tests (NOT software tests)
└── README.md         # This file
```

---

## Test Categories

### Unit Tests (5 files)
**Purpose:** Test individual functions/classes in isolation

| Test File | Tests What | Key Tests |
|-----------|------------|-----------|
| test_data_models.py | Pydantic models validation | Event, SearchFilters validation |
| test_data_processor.py | Data cleaning & normalization | Title cleaning, deduplication |
| test_clarifications.py | Clarification question generation | Missing city, date templates |
| test_response_builder.py | Response composition logic | Filter description, statistics |
| test_storage.py | Database operations | Save, retrieve events |
| test_prompts.py | LLM prompt structure & content | Template variables, JSON format, anti-hallucination |

**Run:** `pytest tests/unit/ -v`

---

### Integration Tests (11 files)
**Purpose:** Test how components work together

| Test File | Tests What | Key Tests |
|-----------|------------|-----------|
| test_vector_store.py | FAISS + BM25 hybrid search | RRF fusion, indexing |
| test_rag_chain.py | RAG pipeline end-to-end | Query processing, context retrieval |
| test_chat_history.py | Chat message storage | History retrieval, ordering |
| test_feedback_integration.py | Feedback storage & analysis | Pattern detection, satisfaction rate |
| test_advanced_retrieval.py | Reranking, deduplication | Multi-stage retrieval |
| test_code_integration.py | Code component integration | Cross-module interactions |
| test_phase_8_features.py | Phase 8 features (security) | Circuit breaker, PII detection |
| test_core_logic_coverage.py | Core logic coverage | Business logic validation |
| test_data_flow_coverage.py | Data flow coverage | Pipeline validation |
| test_manager_coverage.py | Manager components | Orchestration logic |
| test_utils_coverage.py | Utility functions | Helper function coverage |
| test_circuit_breaker_integration.py | Circuit breaker integration | None handling, metrics endpoint |

**Run:** `pytest tests/integration/ -v`

---

### E2E Tests (6 files)
**Purpose:** Test entire system like a user would

| Test File | Tests What | Key Tests |
|-----------|------------|-----------|
| test_api_endpoints.py | FastAPI REST endpoints | /chat, /feedback, /metrics |
| test_conversational_behavior.py | Multi-turn conversations | Context retention, follow-ups |
| test_dataflow_complete.py | Complete data flow | End-to-end pipeline |
| test_api_security_latency.py | API security & performance | Rate limiting, latency |
| test_structured_output.py | Structured output format | JSON schema validation |
| test_coreference.py | Coreference resolution | "Show me more like that" |

**Run:** `pytest tests/e2e/ -v`

---

### Security Tests (3 files)
**Purpose:** Test security features & edge cases

| Test File | Tests What | Key Tests |
|-----------|------------|-----------|
| test_security_robustness.py | Security robustness | Unicode evasion, homoglyphs |
| test_sanitization.py | PII detection & removal | Email, phone, credit card |
| test_behavior.py | Expected system behaviors | Edge case handling |

**Run:** `pytest tests/security/ -v`

---

### Evaluation Tests (4 files)
**Purpose:** Test AI quality (NOT software quality)

| Test File | Tests What | Key Tests |
|-----------|------------|-----------|
| test_evaluation_metrics.py | Metric calculations | Precision, recall, F1, MRR |
| test_llm_judge.py | LLM-as-judge evaluation | Faithfulness, relevance scoring |
| test_post_hybrid_evaluation.py | Post-hybrid search evaluation | Search quality metrics |
| test_language_consistency.py | Bilingual query handling | French/English equivalence |

**Run:** `pytest tests/evaluation/ -v`

---

## Quick Commands

```bash
# Run all tests
pytest tests/ -v

# Run by category
pytest tests/unit/ -v                  # Fast unit tests only
pytest tests/integration/ -v            # Integration tests
pytest tests/e2e/ -v                    # End-to-end tests
pytest tests/security/ -v               # Security tests
pytest tests/evaluation/ -v             # AI quality tests

# Run specific test file
pytest tests/unit/test_prompts.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only fast tests
pytest tests/unit/ tests/integration/ -v

# Stop on first failure
pytest tests/ -v -x

# Run tests matching pattern
pytest tests/ -k "prompt" -v
```

---

## Test Execution Time

| Category | Avg Time | Total Time |
|----------|----------|------------|
| Unit (6 files) | <1s each | ~5s |
| Integration (11 files) | 1-5s each | ~30s |
| E2E (6 files) | 5-20s each | ~60s |
| Security (3 files) | 1-5s each | ~10s |
| Evaluation (4 files) | 1-5s each | ~15s |
| **TOTAL (29 files)** | - | **~2 minutes** |

---

## Test Coverage

**Current Coverage:** ~85%

**Coverage by Module:**
```
src/api/             95%  ✅
src/data/            90%  ✅
src/generation/      85%  ✅
src/models/          88%  ✅
src/retrieval/       82%  ✅
src/security/        92%  ✅
src/utils/           75%  ⚠️
```

**Check coverage:**
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html
```

---

## Test Organization Benefits

### Before Reorganization:
- ❌ 29 files in flat `tests/` directory
- ❌ Hard to understand test types
- ❌ No clear separation of concerns
- ❌ Difficult to run specific test categories

### After Reorganization:
- ✅ Clear test type hierarchy
- ✅ Easy to run specific categories
- ✅ Faster local development (run unit tests only)
- ✅ Better CI/CD organization (parallel test execution)
- ✅ Self-documenting structure

---

## When to Run Which Tests

**During development:**
```bash
# Make code changes
pytest tests/unit/ -v                    # Run fast unit tests

# If unit tests pass
pytest tests/integration/ -v              # Run integration tests
```

**Before committing:**
```bash
pytest tests/ -v                         # Run all tests
pytest tests/ --cov=src                  # Check coverage
```

**In CI/CD pipeline:**
```bash
# Stage 1: Fast feedback
pytest tests/unit/ -v

# Stage 2: Integration
pytest tests/integration/ -v

# Stage 3: E2E
pytest tests/e2e/ tests/security/ -v

# Stage 4: Quality
pytest tests/evaluation/ -v
```

---

## Adding New Tests

### Unit Test Example:
```python
# tests/unit/test_my_module.py
def test_my_function():
    """Test my_function does X."""
    result = my_function(input)
    assert result == expected
```

### Integration Test Example:
```python
# tests/integration/test_my_integration.py
def test_components_work_together():
    """Test Component A and B integrate correctly."""
    a = ComponentA()
    b = ComponentB(a)
    result = b.process()
    assert result is not None
```

### E2E Test Example:
```python
# tests/e2e/test_my_endpoint.py
def test_full_user_flow():
    """Test complete user interaction."""
    client = TestClient(app)
    response = client.post("/endpoint", json=data)
    assert response.status_code == 200
```

---

## Test Naming Conventions

**File names:**
- `test_<module>.py` - Tests for specific module
- `test_<feature>_integration.py` - Integration tests for feature
- `test_<endpoint>_e2e.py` - End-to-end tests for endpoint

**Test names:**
- `test_<what>_<condition>()` - What it tests + condition
- Example: `test_prompt_format_with_zero_results()`

---

## Related Documentation

- [TESTING_POLICY.md](../docs/TESTING_POLICY.md) - Mandatory testing requirements
- [TESTING_GUIDE.md](../docs/TESTING_GUIDE.md) - Complete testing guide
- [TEST_SUITE_OVERVIEW.md](../docs/TEST_SUITE_OVERVIEW.md) - All test files explained
- [TESTING_QUICK_REFERENCE.md](../docs/TESTING_QUICK_REFERENCE.md) - Command cheat sheet

---

## Summary

✅ **29 test files** organized into 5 categories
✅ **~85% code coverage** (exceeds 80% goal)
✅ **Clear structure** for easy navigation
✅ **Fast feedback** with unit tests (< 5s)
✅ **Comprehensive coverage** with all test types

**Tests are your safety net!** 🛡️
