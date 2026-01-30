# Testing Policy & Pre-Commit Requirements

## 🎯 Mandatory Testing Policy

### Core Principle:
**NO CODE CHANGES WITHOUT PASSING TESTS**

This policy applies to:
- ✅ Human developers
- ✅ AI assistants (Claude)
- ✅ All contributors

---

## 📋 Pre-Commit Requirements (MANDATORY)

### Before ANY git commit:

#### 1. Run Tests for Modified Files
```bash
# If you changed src/data/chat_storage.py
pytest tests/test_chat_history.py tests/test_feedback_integration.py -v

# If you changed src/retrieval/chain.py
pytest tests/test_rag_chain.py tests/test_retriever.py -v
```

**Rule:** All tests for modified modules MUST pass ✅

#### 2. Run Full Test Suite
```bash
# Before committing
pytest tests/ -v

# Expected: All tests pass (no failures)
```

**Rule:** Full test suite MUST pass ✅

#### 3. Check Test Coverage (Optional but Recommended)
```bash
pytest tests/ --cov=src --cov-report=term-missing

# Goal: Maintain 80%+ coverage
```

**Rule:** New code should be covered by tests ✅

---

## 🔧 Automated Pre-Commit Hook

### Installation:

1. **Create the pre-commit hook:**
```bash
# This script is in: .git/hooks/pre-commit
```

2. **The hook automatically:**
   - Detects modified Python files
   - Runs corresponding tests
   - Blocks commit if tests fail
   - Allows commit if tests pass

### Manual Override (Use Sparingly):
```bash
# Only in emergencies (e.g., fixing critical bug)
git commit --no-verify -m "Emergency fix"
```

**⚠️ Warning:** Skipping tests can introduce bugs!

---

## 📂 File-to-Test Mapping

### When you modify this file → Run these tests:

| Production File | Test Files |
|----------------|-----------|
| `src/data/chat_storage.py` | `test_chat_history.py`, `test_feedback_integration.py` |
| `src/retrieval/chain.py` | `test_rag_chain.py`, `test_retriever.py` |
| `src/models/vector_store.py` | `test_vector_store.py` |
| `src/security/guardrails.py` | `test_behavior.py` |
| `src/security/sanitization.py` | `test_sanitization.py` |
| `src/retrieval/response_builder.py` | `test_response_builder.py` |
| `src/retrieval/clarifications.py` | `test_clarifications.py` |
| `src/generation/llm.py` | `test_rag_chain.py` |
| `src/generation/prompts.py` | `test_prompts.py` ⚠️ (create if missing) |
| `src/api/endpoints.py` | `test_api_endpoints.py` |
| `src/api/schemas.py` | `test_api_endpoints.py`, `test_data_models.py` |

### Special Cases:

**Prompts changed?** → Run:
```bash
# Test that prompts generate correct outputs
pytest tests/test_prompts.py -v  # Create if missing
pytest tests/test_rag_chain.py -v  # End-to-end validation
```

**Configuration changed?** → Run:
```bash
# Test configuration loading
pytest tests/test_config.py -v  # Create if missing
pytest tests/ -v  # Full suite to ensure nothing broke
```

**Data models changed?** → Run:
```bash
pytest tests/test_data_models.py -v
pytest tests/test_storage.py -v
```

---

## 🧪 What Gets Tested?

### 1. ✅ Python Code (Functions, Classes)

**Example:**
```python
# Production code
def add_feedback(msg_id, is_positive):
    rating = "positive" if is_positive else "negative"
    return rating

# Test code
def test_add_feedback_positive():
    result = add_feedback(1, True)
    assert result == "positive"  # ✓
```

### 2. ✅ LLM Prompts (Text Templates)

**Yes! Prompts can and SHOULD be tested:**

```python
# Production prompt (src/generation/prompts.py)
RAG_SYSTEM_PROMPT = """You are an assistant...
Rules:
1. Only use provided sources
2. Return JSON format
"""

# Test for prompt
def test_prompt_contains_rules():
    """Test prompt includes critical rules."""
    assert "Only use provided sources" in RAG_SYSTEM_PROMPT
    assert "JSON format" in RAG_SYSTEM_PROMPT

def test_prompt_generates_valid_response():
    """Test prompt produces correct output."""
    response = llm.invoke(RAG_SYSTEM_PROMPT + user_query)
    parsed = json.loads(response)  # Should not crash
    assert "answer_text" in parsed
```

### 3. ✅ Configuration (Settings, Constants)

**Configuration can be tested:**

```python
# Production config
BROADENING_SUGGESTION = "Try broadening your search..."

# Test config
def test_broadening_suggestion_not_empty():
    assert len(BROADENING_SUGGESTION) > 0

def test_broadening_suggestion_used_in_response():
    result = build_response(filters, has_results=False)
    assert BROADENING_SUGGESTION in result
```

### 4. ✅ Data Structures (Pydantic Models, JSON Schemas)

**Data structures are tested:**

```python
# Production model
class SearchFilters(BaseModel):
    city: Optional[str] = None
    month: Optional[int] = None

# Test model
def test_search_filters_validates_month():
    with pytest.raises(ValidationError):
        SearchFilters(month=13)  # Invalid month

def test_search_filters_accepts_valid():
    filters = SearchFilters(city="Paris", month=2)
    assert filters.city == "Paris"  # ✓
```

### 5. ✅ Database Schemas (Tables, Columns)

**Database structure is tested:**

```python
# Test database schema
def test_conversations_table_has_feedback_columns():
    """Test feedback columns exist."""
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [row[1] for row in cursor.fetchall()]

    assert "feedback_rating" in columns
    assert "feedback_comment" in columns
    assert "feedback_timestamp" in columns
```

### 6. ✅ API Schemas (Request/Response Formats)

**API contracts are tested:**

```python
# Test API schema
def test_chat_response_schema():
    """Test ChatResponse has required fields."""
    response = client.post("/chat", json={"question": "Test"})

    assert "answer" in response.json()
    assert "sources" in response.json()
    assert "structured_events" in response.json()
```

---

## 🎯 Testing Non-Code Structures

### Prompts Testing Strategy:

#### Level 1: Structure Tests (Fast)
```python
def test_prompt_has_required_sections():
    """Verify prompt structure."""
    assert "You are" in RAG_SYSTEM_PROMPT
    assert "Rules:" in RAG_SYSTEM_PROMPT
    assert "{today}" in RAG_SYSTEM_PROMPT  # Template variable
```

#### Level 2: Format Tests (Medium)
```python
def test_prompt_generates_json():
    """Verify prompt produces JSON output."""
    response = llm.invoke(RAG_SYSTEM_PROMPT + "Test query")
    data = json.loads(response)  # Should not crash
    assert "answer_text" in data
```

#### Level 3: Quality Tests (Slow - Evaluation)
```python
# This goes in evaluation/, not tests/
def evaluate_prompt_faithfulness():
    """Evaluate if prompt prevents hallucinations."""
    sources = ["Event A on Feb 15"]
    response = llm.invoke(prompt, sources)

    # Should not mention events not in sources
    assert "Event B" not in response
```

### Configuration Testing Strategy:

#### Level 1: Validation Tests
```python
def test_config_values_valid():
    """Test config has valid values."""
    from src.config import settings

    assert settings.db_path.endswith(".db")
    assert settings.max_results > 0
    assert settings.app_api_key is not None
```

#### Level 2: Integration Tests
```python
def test_config_used_correctly():
    """Test config values are actually used."""
    from src.config import settings

    storage = EventStorage()
    assert storage.db_path == settings.db_path
```

### Data Structure Testing Strategy:

```python
# Test Pydantic models
def test_event_model_required_fields():
    """Test Event requires title and date."""
    with pytest.raises(ValidationError):
        Event()  # Missing required fields

def test_event_model_optional_fields():
    """Test Event allows optional fields."""
    event = Event(title="Concert", start_date="2026-02-15")
    assert event.description is None  # Optional field
```

---

## 🚫 What Doesn't Need Tests

### 1. ❌ Pure Data Files (Unless Structure Matters)

**Skip:**
- CSV data files (raw data)
- JSON data dumps (if format is arbitrary)

**Test:**
- JSON schemas (if format is required)
- Data validation (if structure matters)

### 2. ❌ Documentation (Usually)

**Skip:**
- README.md
- Documentation files
- Comments in code

**Test:**
- Code examples IN documentation (should work!)

### 3. ❌ Generated Files

**Skip:**
- `htmlcov/` (coverage reports)
- `__pycache__/`
- `.pyc` files

---

## 📊 Audit: Are Tests Up-to-Date?

### Current Status Check:

Run this to see test coverage:
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

**Red lines = Code not covered by tests**
**Green lines = Code covered by tests**

### Gap Analysis:

| Module | Coverage | Missing Tests |
|--------|----------|---------------|
| `src/generation/prompts.py` | ⚠️ Low | Need prompt structure tests |
| `src/config.py` | ⚠️ Low | Need config validation tests |
| `src/retrieval/unified_analyzer.py` | ⚠️ Medium | Need LLM analyzer tests |

### Action Items:

1. **Create `test_prompts.py`** - Test prompt structures
2. **Create `test_config.py`** - Test configuration validation
3. **Enhance `test_unified_analyzer.py`** - Test LLM-based analysis

---

## 🔄 Workflow with Testing Policy

### Daily Development:

```bash
# 1. Pull latest
git pull

# 2. Create branch
git checkout -b feature/my-feature

# 3. Make changes
vim src/some_file.py

# 4. Run tests for changed file
pytest tests/test_some_file.py -v

# 5. If tests fail → Fix code → Repeat step 4

# 6. Run full test suite
pytest tests/ -v

# 7. Commit (pre-commit hook runs automatically)
git add .
git commit -m "Add feature"

# 8. Push
git push origin feature/my-feature
```

### When Adding New Feature:

```bash
# 1. Write test first (TDD)
vim tests/test_new_feature.py

def test_new_feature():
    result = new_feature(input)
    assert result == expected

# 2. Run test (should fail - feature doesn't exist yet)
pytest tests/test_new_feature.py -v  # ✗ FAIL

# 3. Write minimal code to pass test
vim src/module.py

# 4. Run test again
pytest tests/test_new_feature.py -v  # ✓ PASS

# 5. Refactor and improve
# Tests ensure you don't break it

# 6. Commit
git commit -m "Add new feature with tests"
```

---

## 🎓 For AI Assistants (Claude)

### Policy for Claude:

When assisting with code changes:

1. **Before modifying code:**
   - Identify which test files will be affected
   - Run those tests to establish baseline

2. **After modifying code:**
   - Run affected tests immediately
   - If tests fail → Fix the code
   - Run full test suite before committing

3. **When adding new functionality:**
   - Write tests first (or alongside code)
   - Ensure new code has 80%+ coverage
   - Update test documentation

4. **When tests fail:**
   - Analyze why (code broke vs. intentional change)
   - Fix code OR update test (with justification)
   - Never skip tests without user approval

### Example Claude Response:

```
User: "Add feedback analysis feature"

Claude:
1. I'll first check existing tests:
   pytest tests/test_feedback_integration.py -v

2. I'll add the feature to src/analysis/feedback_analyzer.py

3. I'll create tests in tests/test_feedback_integration.py

4. I'll run tests to verify:
   pytest tests/test_feedback_integration.py -v

5. I'll run full suite before committing:
   pytest tests/ -v

All tests pass ✓ Ready to commit!
```

---

## 📝 Summary

### Mandatory Requirements:

1. ✅ Run tests before EVERY commit
2. ✅ Tests for modified files MUST pass
3. ✅ Full test suite MUST pass
4. ✅ New code MUST have tests (80%+ coverage)
5. ✅ Prompts and configs SHOULD be tested
6. ✅ Pre-commit hook enforces this

### Testing Checklist:

- [ ] Modified files identified
- [ ] Corresponding tests run and pass
- [ ] Full test suite run and passes
- [ ] Coverage checked (80%+)
- [ ] Commit with confidence!

### Remember:

**Tests are not optional. They are your safety net.** 🛡️

**Without tests = Shipping bugs to users** ❌
**With tests = Confident, safe deployments** ✅

---

## 📚 Related Documentation

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Complete testing guide
- [TEST_SUITE_OVERVIEW.md](TEST_SUITE_OVERVIEW.md) - All tests explained
- [TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md) - Cheat sheet
