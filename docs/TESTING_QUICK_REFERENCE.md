# Testing Quick Reference

## 🎯 Most Important Things to Remember

### 1. What Are Tests?
**Tests = Code that checks if your code works correctly**

Think of it like a spell checker for your code:
- Spell checker catches typos automatically
- Tests catch bugs automatically

### 2. Why Test?
- **Catch bugs immediately** (not when users complain)
- **Safe refactoring** (change code confidently)
- **Documentation** (tests show how to use code)
- **Prevent regressions** (bugs can't come back)

### 3. Two Types of Testing (DON'T CONFUSE THEM!)

| Test Coverage | Evaluation Metrics |
|--------------|-------------------|
| **Software quality** | **AI performance** |
| "Does code work?" | "Is AI good?" |
| 80% of code tested | 85% retrieval precision |
| `pytest tests/` | `python scripts/run_evaluation.py` |

---

## 🚀 Daily Workflow

### Step 1: Make changes to code
```bash
# Edit some file
code src/retrieval/chain.py
```

### Step 2: Run tests for what you changed
```bash
# Fast (1 second)
pytest tests/test_rag_chain.py -v
```

### Step 3: If tests pass, commit
```bash
git add .
git commit -m "Your change"
```

### Step 4: Before pushing, run ALL tests
```bash
# Comprehensive (10 seconds)
pytest tests/ -v
```

---

## 🔥 When Tests Fail

### Decision Tree:

```
Test fails after my change
    |
    ├─ Did I intentionally change behavior?
    │   ├─ YES → Update the test
    │   └─ NO → Fix my code (I broke it)
```

### Example 1: You Broke It (Fix Your Code)

```python
# You changed:
def format_date(date):
    return date.strftime("%d/%m/%Y")  # ← Changed format

# Test fails:
def test_format_date():
    result = format_date(some_date)
    assert result == "2026-01-30"  # ✗ Expected this format

# Action: FIX YOUR CODE (revert or update correctly)
```

### Example 2: Intentional Change (Update Test)

```python
# You migrated feedback to conversations table
# Test fails because it looks for old table

# Action: UPDATE THE TEST to use new table
```

**Golden Rule:** If unsure → Your code is probably wrong, not the test!

---

## 📊 Test Coverage Explained

### What is 80% Coverage?

**Coverage = % of code lines executed by tests**

```python
def process(x):
    if x > 0:        # ← Tested ✓
        return x * 2 # ← Tested ✓
    else:
        return 0     # ← NOT tested ✗

# Coverage: 75% (3 of 4 lines)
```

### How to Check Coverage:

```bash
# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Open report
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
```

**Green lines = Tested ✓**
**Red lines = Not tested ✗**

### Your Goal: 80%+ Coverage ✅

You already have this! 🎉

---

## 📁 Your Test Files (20 files)

### Quick Reference:

**Core RAG (5 files):**
- `test_rag_chain.py` - Main pipeline
- `test_vector_store.py` - Search (FAISS + BM25)
- `test_advanced_retrieval.py` - Reranking, filters
- `test_search_filters.py` - Filter extraction
- `test_language_consistency.py` - Bilingual

**Data & Storage (5 files):**
- `test_data_models.py` - Pydantic models
- `test_data_processor.py` - Data cleaning
- `test_storage.py` - Database operations
- `test_chat_history.py` - Chat storage
- `test_feedback_integration.py` - Feedback (NEW!)

**Components (5 files):**
- `test_response_builder.py` - Response composition (NEW!)
- `test_clarifications.py` - Clarification questions (NEW!)
- `test_sanitization.py` - PII detection (NEW!)
- `test_retriever.py` - Retrieval logic
- `test_conversational_behavior.py` - Multi-turn

**API & Interface (2 files):**
- `test_api_endpoints.py` - REST API
- `test_behavior.py` - Edge cases

**Evaluation (3 files):**
- `test_evaluation_metrics.py` - Metric calculations
- `test_llm_judge.py` - LLM-as-judge
- `test_golden_dataset.py` - Dataset validation

---

## 🎯 Common Commands

```bash
# Run all tests
pytest tests/ -v

# Run one test file
pytest tests/test_feedback_integration.py -v

# Run one specific test
pytest tests/test_feedback_integration.py::test_analyze_feedback -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Stop on first failure
pytest tests/ -v -x

# Show print statements
pytest tests/ -v -s

# Run tests matching pattern
pytest tests/ -k "feedback" -v
```

---

## ❓ Common Questions

### Q: Should I run tests after EVERY change?
**A: YES!** Run tests for the file you changed. Takes 1 second.

### Q: When do tests fail?
**A: Usually when you broke something.** Sometimes when you intentionally changed behavior.

### Q: How do I know if I broke it vs. test needs update?
**A: Ask: "Did I intentionally change this behavior?"**
- If NO → You broke it, fix your code
- If YES → Update the test

### Q: What if I don't understand why test fails?
**A: Read the test!** Tests show expected behavior. Compare to your code.

### Q: Can I skip tests?
**A: NO!** Tests are your safety net. Skipping them = shipping bugs to users.

### Q: What's the difference between `tests/` and `evaluation/`?
**A:**
- `tests/` = Software quality (does code work?)
- `evaluation/` = AI quality (is AI good?)

Both are important! Run both!

---

## 🎓 Learning Path

### Beginner (You are here!)
1. ✅ Understand what tests are
2. ✅ Run tests after changes
3. ✅ Read test failures carefully
4. ⬜ Write your first test

### Intermediate
1. Write tests for new features (TDD)
2. Debug failing tests confidently
3. Improve test coverage to 90%+

### Advanced
1. Write integration tests
2. Mock external dependencies
3. Optimize test performance

---

## 📚 Full Documentation

For detailed explanations, read:
1. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Complete testing guide
2. **[TEST_SUITE_OVERVIEW.md](TEST_SUITE_OVERVIEW.md)** - All test files explained

---

## 💡 Key Takeaways

1. **Tests check if code works** ✓
2. **Run tests after every change** ✓
3. **Test failure = You probably broke it** ✓
4. **Coverage ≠ Evaluation** ✓
5. **80% coverage = Good** ✓ (You have this!)
6. **Tests = Safety net** ✓

**You're doing great! Keep testing! 🚀**
