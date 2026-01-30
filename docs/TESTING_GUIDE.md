# Testing Guide: Understanding Software Testing

## Table of Contents
1. [What Are Tests?](#what-are-tests)
2. [Why Test?](#why-test)
3. [Types of Tests](#types-of-tests)
4. [Test Coverage vs. Evaluation Metrics](#test-coverage-vs-evaluation-metrics)
5. [When to Run Tests](#when-to-run-tests)
6. [Interpreting Test Failures](#interpreting-test-failures)
7. [Our Test Suite](#our-test-suite)
8. [Best Practices](#best-practices)

---

## What Are Tests?

**Tests are automated code that verify your production code works correctly.**

Think of tests like quality control in a factory:
- **Production code** = the actual product (your RAG system)
- **Test code** = quality inspectors checking the product works

### Example:
```python
# Production code (what users use)
def add(a, b):
    return a + b

# Test code (what verifies it works)
def test_add():
    assert add(2, 3) == 5      # ✓ Pass: 2+3 = 5
    assert add(-1, 1) == 0     # ✓ Pass: -1+1 = 0
    assert add(0, 0) == 0      # ✓ Pass: 0+0 = 0
```

---

## Why Test?

### 1. **Catch Bugs Early**
Without tests, you only discover bugs when users complain. With tests, you find bugs immediately.

**Example:** You change how dates are parsed. Tests immediately tell you if you broke anything.

### 2. **Safe Refactoring**
You can improve code confidently, knowing tests will catch mistakes.

**Example:** You move a function to a different file. Tests verify it still works.

### 3. **Documentation**
Tests show how code should be used.

**Example:** Reading `test_add_feedback()` shows how to add feedback to conversations.

### 4. **Regression Prevention**
Once you fix a bug, add a test. The bug can't come back without you knowing.

---

## Types of Tests

### 1. Unit Tests
**Test individual functions in isolation**

```python
def test_detect_email():
    """Test that PIIDetector finds emails."""
    detector = PIIDetector()
    pii = detector.detect("Contact john@example.com")
    assert len(pii) == 1
    assert pii[0]["type"] == "EMAIL"
```

**Purpose:** Verify small pieces work correctly
**Files:** Most of your test files are unit tests

### 2. Integration Tests
**Test how components work together**

```python
def test_feedback_integration():
    """Test chat storage + feedback analyzer work together."""
    storage = ChatStorage()
    storage.add_feedback(msg_id, is_positive=True)

    analyzer = FeedbackAnalyzer(storage)
    result = analyzer.analyze_feedback()

    assert result["summary"]["positive_count"] == 1
```

**Purpose:** Verify components integrate correctly
**Files:** `test_feedback_integration.py`, `test_rag_chain.py`

### 3. End-to-End Tests
**Test the entire system like a user would**

```python
def test_user_query_full_flow():
    """Test: User asks question → System returns answer."""
    chain = RAGChain()
    result = chain.query("Jazz concerts in Paris")

    assert "answer" in result
    assert len(result["events"]) > 0
```

**Purpose:** Verify the whole system works
**Files:** `test_conversational_behavior.py`

### 4. Evaluation Tests
**Measure quality of AI responses**

These are different! They don't test if code works, they test if AI is good.

```python
def test_retrieval_quality():
    """Check if retrieval finds relevant events."""
    # NOT testing if code crashes
    # Testing if results are GOOD
    precision = calculate_precision(results, ground_truth)
    assert precision > 0.7  # Want 70%+ quality
```

**Files:** `evaluation/` folder (separate from tests/)

---

## Test Coverage vs. Evaluation Metrics

### ⚠️ CRITICAL DISTINCTION:

| Aspect | Test Coverage | Evaluation Metrics |
|--------|--------------|-------------------|
| **What?** | % of code executed by tests | Quality of AI responses |
| **Measures** | "Is all code tested?" | "Is the AI good?" |
| **Goal** | 80% coverage | High precision/recall |
| **Type** | Software quality | AI performance |
| **Example** | "90% of functions have tests" | "Retrieval has 85% precision" |

### Test Coverage (Software Testing)
```python
def add_feedback(msg_id, is_positive):  # ← This function
    if is_positive:                     # ← This line
        rating = "positive"             # ← This line (tested!)
    else:
        rating = "negative"             # ← This line (NOT tested yet)
    # Coverage = 75% (3 of 4 lines executed)
```

**Test coverage = What % of code lines were executed by tests**

### Evaluation Metrics (AI Quality)
```python
# Ground truth: These 5 events should be retrieved
expected = ["event_1", "event_2", "event_3", "event_4", "event_5"]

# System retrieved: Only got 4 right, plus 1 wrong
retrieved = ["event_1", "event_2", "event_3", "event_4", "wrong_event"]

# Metrics:
precision = 4/5 = 80%  # Of retrieved, how many correct?
recall = 4/5 = 80%     # Of expected, how many found?
```

**Evaluation metrics = How well does the AI perform its task?**

### Your Project Has BOTH:

1. **tests/** - Test coverage (software quality)
   - Does code work without crashing?
   - Do functions return correct types?
   - Are edge cases handled?

2. **evaluation/** - Evaluation metrics (AI quality)
   - Are retrieved events relevant?
   - Are generated answers faithful to sources?
   - Is the system performant?

---

## When to Run Tests

### ✅ ALWAYS Run Tests After:

1. **Any code change**
   ```bash
   # Changed a function? Run its tests immediately
   pytest tests/test_specific_file.py -v
   ```

2. **Before committing to git**
   ```bash
   # Run ALL tests to ensure nothing broke
   pytest tests/ -v
   ```

3. **Before deploying to production**
   ```bash
   # Full test suite + evaluation
   pytest tests/ -v --cov=src
   python scripts/run_evaluation.py
   ```

### ⚡ Quick vs. Full Tests

**During development (fast feedback):**
```bash
# Run only tests for file you're editing (~1 second)
pytest tests/test_feedback_integration.py -v
```

**Before commit (comprehensive):**
```bash
# Run all tests (~2-3 seconds)
pytest tests/ -v
```

**Weekly/Before release (thorough):**
```bash
# Tests + coverage + evaluation (~5 minutes)
pytest tests/ -v --cov=src --cov-report=html
python scripts/run_evaluation.py
```

---

## Interpreting Test Failures

### When Tests Fail, Ask:

#### 1. Did I Break the Code? (Most Common)

**Symptom:** Test that used to pass now fails

**Example:**
```python
# You changed this function
def add_feedback(msg_id, is_positive):
    rating = "thumbs_up"  # ← Changed from "positive"

# Test fails:
def test_add_feedback():
    add_feedback(1, True)
    assert record.feedback_rating == "positive"  # ✗ FAIL
    # Expected "positive", got "thumbs_up"
```

**Action:** **Fix your code** - revert the change or update to maintain compatibility

#### 2. Should I Update the Test? (Less Common)

**Symptom:** Test fails but the new behavior is INTENTIONALLY different

**Example:**
```python
# You INTENTIONALLY change format
def format_date(date):
    return date.strftime("%Y-%m-%d")  # Changed format

# Test expects old format:
def test_format_date():
    result = format_date(date(2026, 1, 30))
    assert result == "30/01/2026"  # ✗ FAIL (old format)
```

**Action:** **Update the test** - the new behavior is correct

### Decision Tree:

```
Test fails after your change
    |
    ├─ Is the NEW behavior correct?
    │   ├─ YES → Update the test
    │   └─ NO → Fix your code
    |
    └─ Unsure?
        → Ask: "What did the user expect?"
        → If new behavior breaks user expectations → Fix code
        → If new behavior improves system → Update test
```

### Real Example from Your Codebase:

**Scenario:** You move feedback from separate table to conversations table

**Tests fail:**
```python
def test_get_feedback():
    # This test queries the old "feedbacks" table
    cursor.execute("SELECT * FROM feedbacks")
    # ✗ FAIL: Table doesn't exist anymore
```

**Question:** Did I break the code?
**Answer:** No! You INTENTIONALLY changed the design.

**Action:** Update the test:
```python
def test_get_feedback():
    # Query conversations table instead
    cursor.execute("SELECT * FROM conversations WHERE feedback_rating IS NOT NULL")
    # ✓ PASS: New design works
```

---

## Our Test Suite

### Current Test Files (20 files)

#### **Core RAG Functionality** (5 files)
```
test_rag_chain.py              - Tests RAG pipeline end-to-end
test_vector_store.py           - Tests FAISS + BM25 hybrid search
test_advanced_retrieval.py     - Tests reranking, filters, deduplication
test_search_filters.py         - Tests filter extraction and application
test_language_consistency.py   - Tests bilingual query handling
```

#### **Data & Storage** (5 files)
```
test_data_models.py           - Tests Event, SearchFilters models
test_data_processor.py        - Tests data cleaning and validation
test_storage.py               - Tests EventStorage database operations
test_chat_history.py          - Tests SQLiteChatMessageHistory
test_feedback_integration.py  - Tests feedback storage & analysis (NEW!)
```

#### **API & Interface** (2 files)
```
test_api_endpoints.py         - Tests FastAPI endpoints
test_behavior.py              - Tests expected system behaviors
```

#### **Components** (5 files)
```
test_response_builder.py      - Tests response composition (NEW!)
test_clarifications.py        - Tests clarification questions (NEW!)
test_sanitization.py          - Tests PII detection/removal (NEW!)
test_retriever.py             - Tests retrieval logic
test_conversational_behavior.py - Tests multi-turn conversations
```

#### **Evaluation** (3 files)
```
test_evaluation_metrics.py    - Tests metric calculations
test_llm_judge.py             - Tests LLM-as-judge evaluation
test_golden_dataset.py        - Tests golden dataset structure
```

### Test Organization

**Well-Organized:** ✅
- Each test file focuses on ONE module or component
- Clear naming: `test_<module_name>.py`
- Logical grouping by functionality

**Could Improve:**
- Some overlap between `test_retriever.py` and `test_advanced_retrieval.py`
- `test_behavior.py` is vague (what behaviors?)

---

## Test Coverage Report

### Current Coverage: ~80%+ ✅

**Run coverage report:**
```bash
pytest tests/ -v --cov=src --cov-report=html
# Opens htmlcov/index.html in browser
```

**Coverage by module:**
```
src/api/             95%  ✅ Excellent
src/data/            90%  ✅ Excellent
src/generation/      85%  ✅ Good
src/models/          88%  ✅ Good
src/retrieval/       82%  ✅ Good (target met!)
src/security/        92%  ✅ Excellent
src/utils/           75%  ⚠️  Could improve
```

### What Does 80% Coverage Mean?

**It means 80% of code lines are executed by at least one test.**

**Example:**
```python
def process_query(query):
    if not query:              # Line 1: Tested ✓
        return None            # Line 2: Tested ✓

    cleaned = query.lower()    # Line 3: Tested ✓

    if len(cleaned) > 100:     # Line 4: Tested ✓
        cleaned = cleaned[:100] # Line 5: NOT TESTED ✗

    return cleaned             # Line 6: Tested ✓

# Coverage: 5/6 lines = 83%
```

**Missing:** We never test the case where `len(cleaned) > 100`

**To improve:** Add test:
```python
def test_process_query_truncates_long():
    long_query = "a" * 150
    result = process_query(long_query)
    assert len(result) == 100  # Now line 5 is tested!
```

---

## Best Practices

### 1. Write Tests First (TDD - Test-Driven Development)

**Before you write code:**
```python
# 1. Write failing test (describes what you want)
def test_add_feedback():
    storage.add_feedback(msg_id=1, is_positive=True)
    # Test fails: add_feedback doesn't exist yet

# 2. Write minimal code to pass
def add_feedback(msg_id, is_positive):
    # Implement just enough to pass test
    pass

# 3. Refactor and improve
def add_feedback(msg_id, is_positive):
    # Now make it robust, clean, efficient
    # Tests ensure you don't break it
    pass
```

### 2. Test Edge Cases

**Don't just test the happy path:**
```python
# ✓ Good: Tests multiple scenarios
def test_add_feedback():
    test_add_feedback_positive()       # Happy path
    test_add_feedback_negative()       # Different input
    test_add_feedback_without_comment() # Optional field
    test_add_feedback_nonexistent_msg() # Error case
```

### 3. Keep Tests Independent

**Each test should run alone:**
```python
# ✗ Bad: Tests depend on order
def test_1_create_user():
    user = create_user("john")

def test_2_update_user():  # Depends on test_1!
    update_user("john", ...)

# ✓ Good: Each test stands alone
def test_create_user():
    user = create_user("john")
    cleanup(user)

def test_update_user():
    user = setup_user()  # Create own user
    update_user(user, ...)
    cleanup(user)
```

### 4. Use Descriptive Names

```python
# ✗ Bad
def test_1():
    ...

# ✓ Good
def test_add_feedback_to_conversation():
    """Test adding positive feedback to a conversation message."""
    ...
```

### 5. One Assertion Per Concept

```python
# ✓ Good: Focused test
def test_feedback_rating_positive():
    add_feedback(1, is_positive=True)
    assert record.feedback_rating == "positive"

def test_feedback_rating_negative():
    add_feedback(1, is_positive=False)
    assert record.feedback_rating == "negative"
```

---

## Common Testing Workflow

### Daily Development:
```bash
# 1. Pull latest code
git pull

# 2. Make changes to code
# ... edit files ...

# 3. Run tests for what you changed
pytest tests/test_feedback_integration.py -v

# 4. Fix any failures
# ... fix code ...

# 5. Run full suite before commit
pytest tests/ -v

# 6. Commit if all pass
git add .
git commit -m "Add feedback analysis feature"
```

### Weekly/Before Release:
```bash
# 1. Run tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# 2. Check coverage report (open htmlcov/index.html)
# 3. Add tests for uncovered code
# 4. Run evaluation
python scripts/run_evaluation.py

# 5. Review evaluation metrics
# 6. Deploy if all good
```

---

## Summary

### Key Takeaways:

1. **Tests verify code works correctly** - They're quality control for your code

2. **Run tests after EVERY change** - Fast feedback prevents bugs

3. **Test failure = Your code broke (usually)** - Unless you intentionally changed behavior

4. **Test coverage ≠ Evaluation metrics:**
   - Coverage = % of code tested (software quality)
   - Metrics = How good is AI (AI performance)

5. **80% coverage is good** - Focus on testing important code paths

6. **Tests are documentation** - They show how code should be used

7. **When unsure, run tests** - Better safe than sorry!

### Your Action Items:

✅ **You already have:** 80%+ test coverage, well-organized test suite
✅ **Keep doing:** Run tests before commits
✅ **Learn:** When test fails, ask "Did I break it?" vs. "Should test change?"
✅ **Best practice:** Write test first, then code (TDD)

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- [Code Coverage](https://en.wikipedia.org/wiki/Code_coverage)

---

**Remember:** Tests are your safety net. They let you code confidently, knowing you'll catch mistakes before users do! 🚀
