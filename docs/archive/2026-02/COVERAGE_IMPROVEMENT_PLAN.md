# Coverage Improvement Plan

**Last Updated:** 2026-01-30
**Current Overall Coverage:** ~85%
**Target:** 90%+

---

## Current Coverage by Module

| Module | Current | Target | Gap | Priority |
|--------|---------|--------|-----|----------|
| `src/api/` | 95% | 95% | ✅ 0% | - |
| `src/security/` | 92% | 92% | ✅ 0% | - |
| `src/data/` | 90% | 90% | ✅ 0% | - |
| `src/models/` | 88% | 90% | 2% | Medium |
| `src/generation/` | 85% | 90% | 5% | Medium |
| `src/retrieval/` | 82% | 85% | 3% | Medium |
| `src/utils/` | **75%** | **85%** | **10%** | **HIGH** |

---

## Priority 1: src/utils/ (75% → 85%)

### Uncovered Areas

**Check coverage report:**
```bash
pytest tests/ --cov=src/utils --cov-report=html
# Open htmlcov/src/utils/index.html
```

### Likely Gaps

1. **Error handling branches**
   - Try/except blocks
   - Edge case validation

2. **Utility functions**
   - Date parsing edge cases
   - String normalization variants

3. **Helper methods**
   - Rarely used code paths
   - Debug/logging functions

### Action Plan

**Step 1: Identify uncovered lines**
```bash
pytest tests/ --cov=src/utils --cov-report=term-missing
```

**Step 2: Add missing tests**
```python
# tests/unit/test_utils_complete.py

def test_edge_case_empty_string():
    """Test utility handles empty strings."""
    result = normalize_text("")
    assert result == ""

def test_edge_case_none_value():
    """Test utility handles None."""
    result = normalize_text(None)
    assert result is None

def test_error_handling():
    """Test utility raises expected errors."""
    with pytest.raises(ValueError):
        parse_date("invalid-date")
```

**Step 3: Test error branches**
```python
def test_fallback_logic():
    """Test fallback when primary method fails."""
    with patch('module.primary_method', side_effect=Exception):
        result = function_with_fallback()
        assert result is not None  # Uses fallback
```

---

## Priority 2: src/generation/ (85% → 90%)

### Focus Areas

1. **LLM error handling**
   - Retry logic
   - Circuit breaker states
   - Timeout handling

2. **Prompt templates**
   - Edge cases (zero results, very long queries)
   - Template variable combinations

### Missing Test Coverage

**Check:**
```bash
pytest tests/ --cov=src/generation --cov-report=term-missing
```

**Add tests:**
```python
# tests/integration/test_llm_error_handling.py

def test_llm_timeout_handling():
    """Test LLM call handles timeout gracefully."""
    with patch('llm.invoke', side_effect=TimeoutError):
        result = get_chat_llm().invoke("test")
        # Should handle timeout without crashing

def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold."""
    # Simulate 5 consecutive failures
    # Verify circuit breaker opens
```

---

## Priority 3: src/retrieval/ (82% → 85%)

### Focus Areas

1. **Orchestrator edge cases**
   - Empty results handling
   - Filter combinations
   - Fallback strategies

2. **Query refinement**
   - Ambiguous queries
   - Multi-language queries

### Missing Tests

**Add:**
```python
# tests/integration/test_retrieval_edge_cases.py

def test_empty_results_with_fallback():
    """Test retrieval falls back when no exact matches."""
    result = orchestrator.search(query, filters)
    # Should have nearby results

def test_conflicting_filters():
    """Test handling of conflicting filter combinations."""
    filters = SearchFilters(city="Paris", city="Lyon")  # Invalid
    # Should handle gracefully
```

---

## Priority 4: src/models/ (88% → 90%)

### Focus Areas

1. **Vector store edge cases**
   - Empty corpus
   - Single document
   - Very large results

2. **Embedding generation**
   - Batch processing
   - Error handling

### Missing Tests

```python
# tests/unit/test_vector_store_edge_cases.py

def test_search_empty_corpus():
    """Test search with no documents."""
    store = EventVectorStore()
    results = store.search("query")
    assert results == []

def test_search_single_document():
    """Test search with exactly one document."""
    store = EventVectorStore()
    store.add_document("doc1")
    results = store.search("doc1")
    assert len(results) == 1
```

---

## General Strategies

### 1. Test Edge Cases

**Common edge cases to test:**
- Empty input (`""`, `[]`, `{}`, `None`)
- Single item (`[1]`, `"a"`)
- Very large input (100+ items)
- Invalid input (wrong type, out of range)
- Boundary values (0, -1, max_int)

### 2. Test Error Paths

**Every try/except should be tested:**
```python
# Production code
try:
    result = risky_operation()
except SpecificError:
    result = fallback()

# Test should trigger both paths
def test_risky_operation_success():
    result = risky_operation()
    assert result is not None

def test_risky_operation_fallback():
    with patch('risky_operation', side_effect=SpecificError):
        result = function_with_fallback()
        assert result is not None  # Fallback worked
```

### 3. Test Conditional Branches

**Every if/else should be tested:**
```python
# Production code
if condition:
    path_a()
else:
    path_b()

# Tests
def test_condition_true():
    """Test path A when condition is true."""
    # ...

def test_condition_false():
    """Test path B when condition is false."""
    # ...
```

### 4. Use Coverage-Guided Testing

**Workflow:**
```bash
# 1. Run coverage
pytest tests/ --cov=src --cov-report=html

# 2. Open report
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows

# 3. Find red lines (uncovered code)

# 4. Write tests to cover those lines

# 5. Repeat until target reached
```

---

## Quick Wins

### Low-Hanging Fruit

**1. Test constants and enums**
```python
def test_constants_defined():
    """Test all required constants are defined."""
    assert MAX_RESULTS > 0
    assert DEFAULT_LANGUAGE in ["fr", "en"]
```

**2. Test simple getters/setters**
```python
def test_property_getter():
    """Test property returns expected value."""
    obj = MyClass(value=5)
    assert obj.value == 5
```

**3. Test default parameters**
```python
def test_function_with_defaults():
    """Test function works with default parameters."""
    result = function()  # No arguments
    assert result is not None
```

---

## Tracking Progress

### Weekly Coverage Check

```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=term-missing > coverage_report.txt

# Compare to baseline
diff baseline_coverage.txt coverage_report.txt
```

### Coverage Badge

**Add to README.md:**
```markdown
![Coverage](https://img.shields.io/badge/coverage-85%25-green)
```

### Coverage Trend

| Date | Coverage | Change |
|------|----------|--------|
| 2026-01-20 | 80% | - |
| 2026-01-25 | 82% | +2% |
| 2026-01-30 | 85% | +3% |
| **Target** | **90%** | +5% |

---

## Timeline

### Week 1: src/utils/ (75% → 85%)
- Identify uncovered lines
- Add 10-15 new tests
- Focus on error handling

### Week 2: src/generation/ (85% → 90%)
- Test LLM error paths
- Add circuit breaker tests
- Test prompt edge cases

### Week 3: src/retrieval/ (82% → 85%)
- Test orchestrator edge cases
- Add filter combination tests
- Test fallback logic

### Week 4: src/models/ (88% → 90%)
- Test vector store edge cases
- Add embedding tests
- Final coverage check

**Target: 90%+ coverage by end of month**

---

## Success Criteria

✅ **Overall coverage ≥90%**
✅ **No module below 85%**
✅ **All error paths tested**
✅ **All edge cases covered**
✅ **No skipped tests without justification**

---

## Commands

```bash
# Check current coverage
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src --cov-report=html

# Check specific module
pytest tests/ --cov=src/utils --cov-report=term-missing

# Fail if coverage below threshold
pytest tests/ --cov=src --cov-fail-under=90
```

---

## Resources

- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](../TESTING_GUIDE.md)

**Remember:** Coverage is a tool, not a goal. 100% coverage doesn't mean bug-free code!
