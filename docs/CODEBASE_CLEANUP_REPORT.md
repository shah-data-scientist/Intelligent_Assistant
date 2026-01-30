# Codebase Cleanup & Refactoring Report

**Generated:** 2026-01-30
**Analyzed:** 51 Python files in `src/` directory
**Total Issues Found:** 67 (3 dead modules + 40 unused imports + 6 large files + 18 refactoring opportunities)

---

## Executive Summary

| Category | Count | Priority |
|----------|-------|----------|
| **Dead Modules** | 3 | 🔴 HIGH |
| **Unused Imports** | 40 across 24 files | 🟡 MEDIUM |
| **Large Files (>500 lines)** | 6 files | 🟢 LOW |
| **Refactoring Opportunities** | 18 identified | 🟡 MEDIUM |

**Estimated Cleanup Time:** 4-6 hours
**Risk Level:** LOW (mostly deletions, no breaking changes)

---

## 1. DEAD MODULES (3 files - 100% unused)

### Priority: 🔴 HIGH - Safe to Delete

#### 1.1 `src/frontend/app.py` (Streamlit UI)

**Status:** ❌ NEVER IMPORTED
**References:** 0
**Lines:** ~200
**Reason:** Frontend is not part of the FastAPI backend

**Recommendation:**
```bash
# DELETE - Not part of the API backend
git rm src/frontend/app.py
git rm src/frontend/__init__.py
```

**Impact:** None - frontend is separate from the API


#### 1.2 `src/retrieval/intent_classifier.py`

**Status:** ❌ SUPERSEDED by `unified_analyzer.py` (Phase 17)
**References:** 0
**Lines:** ~150
**Reason:** Rule-based intent classification replaced by LLM-based unified analyzer

**Original Purpose:**
- Fast, rule-based intent classification
- Pattern matching for greetings, directions, abuse

**Why It's Dead:**
- `UnifiedAnalyzer` (Phase 17) now handles ALL intent classification using LLM
- More accurate, handles edge cases, multi-dimensional analysis
- No code imports this module

**Recommendation:**
```bash
# ARCHIVE first (move to _archived_scripts/obsolete_modules/)
mkdir -p _archived_scripts/obsolete_modules
git mv src/retrieval/intent_classifier.py _archived_scripts/obsolete_modules/
```

**Impact:** None - functionality completely replaced


#### 1.3 `src/retrieval/entity_extractor.py`

**Status:** ❌ SUPERSEDED by `unified_analyzer.py` (Phase 17)
**References:** 0
**Lines:** ~180
**Reason:** LLM-based entity extraction replaced by unified analyzer

**Original Purpose:**
- City name normalization (Plessis → Plessis-Robinson)
- Location extraction from varied prepositions
- Query completeness analysis

**Why It's Dead:**
- `UnifiedAnalyzer` now handles ALL entity extraction
- Single LLM call extracts city, event_type, timeframe, filters
- No fallback needed - Pydantic structured output (Phase 2) guarantees valid schema

**Recommendation:**
```bash
# ARCHIVE first
git mv src/retrieval/entity_extractor.py _archived_scripts/obsolete_modules/
```

**Impact:** None - functionality completely replaced

---

## 2. UNUSED IMPORTS (40 across 24 files)

### Priority: 🟡 MEDIUM - Safe Cleanup

**Files Affected:** 24 (47% of codebase)

### Critical Files with Unused Imports:

#### 2.1 `src/retrieval/chain.py` (8 unused imports)

**Lines:**
- Line 9: `RunnableBranch` - Never used (dead LangChain pattern)
- Line 10: `StrOutputParser` - Replaced by `RobustJsonParser`
- Line 10: `JsonOutputParser` - Same as above
- Line 12: `HumanMessage` - Not directly used (created via prompt template)
- Line 12: `AIMessage` - Not directly used
- Line 16: `MistralLLM` - Legacy import (now using `get_chat_llm()`)

**Recommendation:**
```python
# REMOVE these imports (lines 9-16):
from langchain_core.runnables import RunnableBranch  # ❌ UNUSED
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser  # ❌ UNUSED
from langchain_core.messages import HumanMessage, AIMessage  # ❌ UNUSED
from src.generation.llm import MistralLLM  # ❌ UNUSED (legacy)
```

**Impact:** None - code still runs, just cleaner imports


#### 2.2 `src/models/__init__.py` (2 unused imports)

**Lines:**
- Line 3: `from src.models.embeddings import EventEmbedder` - Not re-exported
- Line 4: `from src.models.vector_store import EventVectorStore` - Not re-exported

**Recommendation:**
```python
# DELETE entire file if not re-exporting
# OR keep only if needed for package initialization
```


#### 2.3 `src/frontend/app.py` (2 unused imports)

**Note:** Entire file is dead (see Section 1.1), so unused imports don't matter.


### Batch Cleanup Script:

Create `scripts/cleanup_unused_imports.py`:
```python
"""Remove unused imports from all files."""

CLEANUP_ACTIONS = {
    "src/api/endpoints.py": [("JSONResponse", 7)],
    "src/api/main.py": [("Request", 9)],
    "src/retrieval/chain.py": [
        ("RunnableBranch", 9),
        ("StrOutputParser", 10),
        ("JsonOutputParser", 10),
        ("HumanMessage", 12),
        ("AIMessage", 12),
        ("MistralLLM", 16),
    ],
    # ... etc
}
```

**Estimated Time:** 2 hours (manual review + testing)

---

## 3. LARGE FILES (6 files >500 lines)

### Priority: 🟢 LOW - Optional Refactoring

| File | Lines | Functions | Classes | Refactoring Priority |
|------|-------|-----------|---------|---------------------|
| `src/retrieval/chain.py` | **1739** | 29 | 3 | 🔴 HIGH |
| `src/retrieval/unified_analyzer.py` | **1270** | 18 | 4 | 🟡 MEDIUM |
| `src/utils/keywords.py` | **662** | 22 | 2 | 🟢 LOW |
| `src/models/vector_store.py` | **656** | 16 | 1 | 🟢 LOW |
| `src/data/storage.py` | **578** | 19 | 3 | 🟢 LOW |
| `src/security/guardrails.py` | **539** | 10 | 3 | 🟢 LOW |

### 3.1 `src/retrieval/chain.py` (1739 lines) - NEEDS REFACTORING

**Issues:**
- **Monolithic RAG orchestration** - Does too many things
- **Mixed responsibilities** - Query parsing, retrieval, response building, error handling
- **Hard to test** - Tightly coupled components
- **Phase 3B only partially applied** - ResponseBuilder integrated but `build_*` functions still in this file

**Refactoring Opportunities:**

1. **Extract Response Building** (Phase 3B continuation)
   - Move `build_filter_description()` (line 431) → `response_builder.py`
   - Move `build_statistical_response()` (line 459) → `response_builder.py`
   - Move `build_filter_echo()` (line 543) → `response_builder.py`
   - Move `build_refinement_suffix()` (line 629) → `response_builder.py`
   - **Impact:** Reduce chain.py by ~200 lines

2. **Extract Error Handling**
   - Lines 1572-1654: Error response logic (70 lines)
   - Already has `build_error_response()` in response_builder.py
   - Move error handling to separate `src/retrieval/error_handler.py`
   - **Impact:** Reduce chain.py by ~80 lines

3. **Extract Constants**
   - Lines 382-428: Large response dictionaries (BROADENING_SUGGESTION, etc.)
   - Move to `src/retrieval/constants.py` or `config.py`
   - **Impact:** Reduce chain.py by ~50 lines

4. **Extract Clarifications**
   - Lines 1266-1348: Clarification logic already has `clarifications.py` module
   - Function `compose_response_prefix()` (line 385) could move to `clarifications.py`
   - **Impact:** Better organization

**Total Potential Reduction:** ~330 lines (1739 → ~1400)

**Recommendation:**
```
Phase 3D (future): Complete ResponseBuilder migration
- Move all build_* functions to response_builder.py
- Create error_handler.py for error response logic
- Create constants.py for static dictionaries
- Result: chain.py focused on orchestration only
```


### 3.2 `src/retrieval/unified_analyzer.py` (1270 lines) - ACCEPTABLE

**Complexity is justified:**
- Handles 7 dimensions of analysis
- Multiple intent types
- Fallback extraction logic
- Pydantic schema conversion
- Already optimized in Phase 18 (prompt reduced by 74%)

**No refactoring needed** - Size is due to comprehensive analysis logic


### 3.3 Other Large Files - ACCEPTABLE

All other large files (keywords.py, vector_store.py, storage.py, guardrails.py) have justified complexity:
- **keywords.py**: Large keyword mappings (data, not logic)
- **vector_store.py**: Hybrid FAISS+BM25 implementation
- **storage.py**: Database models and CRUD operations
- **guardrails.py**: Security patterns (necessary)

**No refactoring needed**

---

## 4. REFACTORING OPPORTUNITIES (18 identified)

### Priority: 🟡 MEDIUM

### 4.1 Consolidate Response Building (Phase 3D)

**Current State:**
- `build_*` functions split between `chain.py` and `response_builder.py`
- ResponseBuilder integrated (Phase 3B) but incomplete migration

**Recommendation:**
```python
# MOVE from chain.py to response_builder.py:
- build_filter_description() → ResponseBuilder.build_filter_description()
- build_statistical_response() → ResponseBuilder.build_statistical_response()
- build_filter_echo() → Already exists (keep current)
- build_refinement_suffix() → ResponseBuilder.build_refinement_suffix()
```

**Benefit:**
- Single source of truth for response composition
- Easier testing
- Complete Phase 3B vision


### 4.2 Extract Constants from chain.py

**Current:**
```python
# Lines 382-428 in chain.py
BROADENING_SUGGESTION = {
    "fr": "\n\n💡 *Specify date/type for more results.*",
    "en": "\n\n💡 *Specify date/type for more results.*"
}

OUT_OF_SCOPE_CITY_RESPONSES = { ... }
INCOMPLETE_QUERY_RESPONSES = { ... }
# etc.
```

**Recommendation:**
```python
# NEW FILE: src/retrieval/constants.py
class ResponseConstants:
    BROADENING_SUGGESTION = { ... }
    OUT_OF_SCOPE_CITY_RESPONSES = { ... }
    INCOMPLETE_QUERY_RESPONSES = { ... }
```

**Benefit:**
- Cleaner chain.py
- Easier to maintain translations
- Constants are testable


### 4.3 Remove Circular Import Risk

**Issue:** Several `__init__.py` files have unused re-exports

**Affected:**
- `src/models/__init__.py` - Imports but doesn't re-export
- `src/retrieval/__init__.py` - Empty (good!)
- `src/evaluation/__init__.py` - Empty (good!)

**Recommendation:**
```python
# DELETE unused __init__.py imports
# Keep __init__.py files empty unless actively re-exporting
```


### 4.4 Standardize Error Response Format

**Current:**
- `build_error_response()` in response_builder.py (new, Phase 3B)
- Inline error dictionaries in chain.py (old, lines 1585-1654)

**Recommendation:**
```python
# MIGRATE all error handling to use build_error_response()
# DELETE inline error dictionaries from chain.py
# Result: Single error response system
```


### 4.5 Consolidate Filter Building Logic

**Observation:**
- `filters.py` exists but underutilized
- Filter logic scattered across chain.py, unified_analyzer.py, manager.py

**Recommendation:**
```python
# STRENGTHEN filters.py as single source of truth
# Move filter validation, normalization, merging to filters.py
# Result: Cleaner separation of concerns
```


### 4.6 Remove Dead Fallback Code

**Issue:** `_fallback_extraction()` in unified_analyzer.py (lines 697-803)

**Current Usage:**
- Fallback when LLM returns invalid JSON
- With Pydantic structured output (Phase 2), this rarely triggers for Gemini

**Recommendation:**
```python
# KEEP for non-Gemini backends (Mistral, Ollama, HuggingFace)
# But add clear comment that it's only for non-structured-output backends
# Consider logging when fallback is used (metrics)
```


### 4.7 Deprecate Legacy LLM Wrapper

**Issue:** `src/generation/llm.py` has `MistralLLM` class (line 40)

**Current Usage:**
- Imported but never used (switched to `get_chat_llm()`)

**Recommendation:**
```python
# REMOVE MistralLLM class if confirmed unused
# Keep only get_chat_llm() function
```


### 4.8 Standardize Logging

**Observation:** Inconsistent logging levels and formats

**Examples:**
- Some use `logger.info(f"[TAG] message")`
- Others use `logger.info("message")`
- Tags vary: `[UNIFIED]`, `[MULTI-DIM]`, `[STRUCTURED]`, `[FALLBACK]`

**Recommendation:**
```python
# STANDARDIZE logging format across codebase
# Use consistent tags for each module
# Example:
#   chain.py:           [CHAIN]
#   unified_analyzer:   [ANALYZER]
#   response_builder:   [BUILDER]
```


### 4.9 Type Hints Consistency

**Observation:** Mixed type hint styles

**Examples:**
```python
# Modern (good):
def foo(x: str | None) -> dict[str, Any]:

# Legacy (inconsistent):
def bar(x: Optional[str]) -> Dict[str, Any]:
```

**Recommendation:**
```python
# STANDARDIZE on Python 3.10+ union syntax
# Use: str | None (not Optional[str])
# Use: dict (not Dict), list (not List)
```


### 4.10 Test Coverage Gaps

**Modules with NO tests:**
- `src/retrieval/response_builder.py` (Phase 3B - NEW)
- `src/retrieval/clarifications.py`
- `src/security/sanitization.py`

**Recommendation:**
```python
# CREATE test files:
# - tests/test_response_builder.py (Phase 3B completion)
# - tests/test_clarifications.py
# - tests/test_sanitization.py
```


### 4.11 Duplicate City Normalization

**Observation:** City normalization logic appears in multiple places

**Locations:**
- `unified_analyzer.py` - LLM-based normalization
- `filters.py` - Rule-based normalization
- `geo.py` - Geocoding with normalization

**Recommendation:**
```python
# CONSOLIDATE to single source of truth in utils/geo.py
# Other modules call geo.normalize_city(city_name, known_cities)
```


### 4.12 Remove Debug Code

**Check for:**
- `print()` statements (should use logging)
- Commented-out code blocks
- Debug flags

**Recommendation:** Audit and clean


### 4.13 Optimize Imports

**Issue:** Some files import entire modules when only using one function

**Example:**
```python
# Current:
import json
# Then only: json.loads()

# Better:
from json import loads
```

**Recommendation:** Low priority, but cleaner


### 4.14 Extract Magic Numbers

**Examples:**
```python
# chain.py:
if result_count < 8:  # Magic number!
    add_broadening_suggestion()

# unified_analyzer.py:
cities_sample = known_cities[:30]  # Magic number!
```

**Recommendation:**
```python
# Create constants:
BROADENING_THRESHOLD = 8
MAX_CITIES_IN_PROMPT = 30
```


### 4.15 Async Consistency

**Observation:** Some async functions, some sync

**Current:**
- `add_chat_message_async()` - Async
- `get_chat_history()` - Sync

**Recommendation:** Document why each is async/sync (performance vs simplicity)


### 4.16 Error Message Localization

**Issue:** Error messages hardcoded in English in some places

**Example:**
```python
raise ValueError("City not found")  # English only!
```

**Recommendation:**
```python
# Use error_messages dict like response messages
# Result: Consistent bilingual error handling
```


### 4.17 Deprecation Warnings

**Issue:** No deprecation warnings for superseded functions

**Example:**
```python
# entity_extractor.py and intent_classifier.py were silently replaced
# No deprecation warnings if someone tries to import them
```

**Recommendation:**
```python
# ADD __init__.py warnings:
import warnings
def __getattr__(name):
    if name in ['entity_extractor', 'intent_classifier']:
        warnings.warn(f"{name} is deprecated, use unified_analyzer", DeprecationWarning)
```


### 4.18 Documentation Completeness

**Modules lacking docstrings:**
- Several utility functions in `keywords.py`
- Some methods in `RetrievalManager`

**Recommendation:** Add missing docstrings for public APIs

---

## 5. RECOMMENDED CLEANUP PHASES

### Phase A: Dead Code Removal (1 hour)

**Priority: 🔴 HIGH - Do First**

```bash
# 1. Archive dead modules
mkdir -p _archived_scripts/obsolete_modules
git mv src/frontend/app.py _archived_scripts/obsolete_modules/
git mv src/frontend/__init__.py _archived_scripts/obsolete_modules/
git mv src/retrieval/intent_classifier.py _archived_scripts/obsolete_modules/
git mv src/retrieval/entity_extractor.py _archived_scripts/obsolete_modules/

# 2. Update .gitignore
echo "_archived_scripts/" >> .gitignore

# 3. Commit
git commit -m "chore: Archive dead modules (frontend/app, intent_classifier, entity_extractor)"
```

**Impact:**
- Remove 530+ lines of dead code
- Cleaner codebase
- No risk (modules unused)


### Phase B: Unused Imports Cleanup (2 hours)

**Priority: 🟡 MEDIUM**

```python
# Use automated tool or manual cleanup
# Focus on critical files:
1. chain.py (8 unused imports)
2. unified_analyzer.py (check carefully - used in fallback logic)
3. API files (endpoints.py, main.py)

# Test after each file
pytest tests/ -v
```

**Impact:**
- Cleaner imports
- Slightly faster module loading
- Better code clarity


### Phase C: Response Builder Consolidation (2 hours)

**Priority: 🟡 MEDIUM - Completes Phase 3B**

```python
# Move build_* functions from chain.py to response_builder.py
1. build_filter_description() → ResponseBuilder static method
2. build_statistical_response() → ResponseBuilder.build_statistical_response()
3. Move constants (BROADENING_SUGGESTION, etc.) → constants.py

# Update imports in chain.py
# Test thoroughly
```

**Impact:**
- Complete Phase 3B vision
- chain.py reduces from 1739 → ~1400 lines
- Better separation of concerns


### Phase D: Test Coverage (3 hours)

**Priority: 🟢 LOW - Future Work**

```python
# Add missing tests:
tests/test_response_builder.py - NEW (Phase 3B)
tests/test_clarifications.py - NEW
tests/test_sanitization.py - NEW

# Target: 85%+ coverage (currently ~80%)
```

**Impact:**
- Better confidence in refactoring
- Catch regressions early


### Phase E: Documentation & Standards (2 hours)

**Priority: 🟢 LOW - Future Work**

```python
# Standardize:
1. Logging format (consistent tags)
2. Type hints (modern Python 3.10+ syntax)
3. Docstrings for public APIs
4. Error messages (bilingual)
```

**Impact:**
- Better maintainability
- Easier onboarding for new developers

---

## 6. IMMEDIATE ACTIONS (Next 30 Minutes)

### Quick Wins - No Risk, High Impact:

1. **Delete 3 dead modules** (5 minutes)
   ```bash
   mkdir -p _archived_scripts/obsolete_modules
   git mv src/frontend/app.py _archived_scripts/obsolete_modules/
   git mv src/retrieval/intent_classifier.py _archived_scripts/obsolete_modules/
   git mv src/retrieval/entity_extractor.py _archived_scripts/obsolete_modules/
   git commit -m "chore: Archive dead modules"
   ```

2. **Clean chain.py imports** (10 minutes)
   - Remove 8 unused imports
   - Test with `pytest tests/test_rag_chain.py`

3. **Update PROJECT_MEMORY.md** (10 minutes)
   - Document dead module removal
   - Note Phase 3D opportunities

4. **Run tests** (5 minutes)
   ```bash
   pytest tests/ -v --tb=short
   ```

---

## 7. SUMMARY

| Metric | Count | Estimated Cleanup Time |
|--------|-------|------------------------|
| Dead modules to archive | 3 | 5 minutes |
| Unused imports to remove | 40 | 2 hours |
| Build functions to move | 4 | 2 hours |
| Large files to refactor | 1 (chain.py) | 4 hours (Phase 3D) |
| Missing tests to add | 3 | 3 hours |
| **TOTAL** | **51 items** | **~12 hours** |

**Priority Breakdown:**
- 🔴 **HIGH (do now):** Dead module removal, critical unused imports
- 🟡 **MEDIUM (next sprint):** Response builder consolidation, test coverage
- 🟢 **LOW (future):** Documentation, standards, optional refactoring

**Risk Assessment:** ✅ LOW
- Most changes are deletions (dead code)
- Refactoring follows existing patterns (Phase 3B)
- All changes are testable

---

## 8. APPENDIX: DETAILED FILE-BY-FILE UNUSED IMPORTS

<details>
<summary>Click to expand full list of 40 unused imports</summary>

### src/api/endpoints.py
- Line 7: `JSONResponse` from `fastapi.responses`

### src/api/main.py
- Line 9: `Request` from `fastapi`

### src/data/ingestion.py
- Line 5: `timedelta` from `datetime`
- Line 8: `settings` from `src.config`

### src/data/storage.py
- Line 20: `Session` from `sqlalchemy.orm`

### src/frontend/app.py (DEAD FILE - DELETE)
- Line 3: `pd` import
- Line 8: `datetime` from `datetime`

### src/generation/llm.py
- Line 12: `CircuitBreakerError` from `pybreaker`

### src/models/embeddings.py
- Line 10: `List` from `typing`
- Line 10: `Optional` from `typing`

### src/models/__init__.py
- Line 3: `EventEmbedder` from `src.models.embeddings`
- Line 4: `EventVectorStore` from `src.models.vector_store`

### src/retrieval/cache.py
- Line 4: `json` import

### src/retrieval/chain.py (8 CRITICAL)
- Line 9: `RunnableBranch`
- Line 10: `StrOutputParser`
- Line 10: `JsonOutputParser`
- Line 12: `HumanMessage`
- Line 12: `AIMessage`
- Line 16: `MistralLLM`
- Line 20: `SQLiteChatMessageHistory`
- Line 26: `map_category_to_db`

### (23 more files with minor unused imports)

</details>

---

**Report Generated:** 2026-01-30
**Analyzer:** Claude Sonnet 4.5
**Codebase Version:** After Phase 18 (Prompt Optimization & ResponseBuilder Integration)
