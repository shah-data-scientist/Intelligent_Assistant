# Response Composition Refactoring (Phase 3B)

## Overview

This document describes the refactoring of response composition logic from scattered string concatenation in `chain.py` to a clean, maintainable **Builder Pattern** implementation.

---

## Problems Identified

### 1. Scattered String Concatenation

**Before:**
```python
# In query_with_metadata() - lines 1543-1566
answer_text = result["answer"].get("answer_text", "")

# Strip existing suffixes (hardcoded markers)
for marker in ["📅 *Results filtered", "💡 *Specify", ...]:
    if marker in answer_text:
        answer_text = answer_text.split(marker)[0].rstrip()

# Add suffixes one by one
refinement_suffix = build_refinement_suffix(...)
answer_text = answer_text + refinement_suffix  # Concatenation #1

if result_count < 8:
    answer_text = answer_text + BROADENING_SUGGESTION[lang]  # Concatenation #2

filter_echo = build_filter_echo(...)
answer_text = answer_text + filter_echo  # Concatenation #3

# Add prefix
if response_prefix:
    answer_text = response_prefix + answer_text  # Concatenation #4
```

**Issues:**
- Fragile string manipulation
- Difficult to reorder components
- No encapsulation of composition logic
- Hard to test individual components

### 2. Hardcoded Constants Inline

**Problem:**
```python
# Line 1545
for marker in ["📅 *Results filtered", "💡 *Specify", "💡 **Want to refine", "**Applied filters:**", "---\n**Applied"]:
```

Adding new markers requires modifying core logic.

### 3. Error Messages Embedded in Code

**Problem:**
```python
# Lines 1585-1654 - 70 lines of inline error message dictionaries
error_messages = {
    "fr": (
        "**Modele en cours de chargement**\n\n"
        "Le modele IA demarre (cela peut prendre 20-30 secondes). "
        "Veuillez reessayer dans un moment."
    ),
    "en": (
        "**Model Loading**\n\n"
        "The AI model is starting up (this may take 20-30 seconds). "
        "Please try again in a moment."
    )
}
```

Error handling logic pollutes the main query flow.

### 4. No Clear Composition Pipeline

**Problem:**
- Response building logic interleaved with business logic
- No clear separation between "what to add" and "how to compose"
- Difficult to modify composition order

---

## Solution: Builder Pattern

### New Architecture

```
src/retrieval/response_builder.py
├── ResponseComponents (dataclass)
│   ├── prefix
│   ├── main_content
│   ├── refinement_suffix
│   ├── broadening_suggestion
│   └── filter_echo
│
├── ResponseBuilder (builder class)
│   ├── set_main_content()
│   ├── add_prefix()
│   ├── add_refinement_suffix()
│   ├── add_broadening_suggestion()
│   ├── add_filter_echo()
│   └── build() → final response
│
└── Utility functions
    ├── build_statistical_response_text()
    └── build_error_response()
```

### Usage Example

**After (Clean Builder Pattern):**
```python
from src.retrieval.response_builder import ResponseBuilder

# Build response using fluent interface
answer_text = (
    ResponseBuilder(language=language)
    .add_prefix(response_prefix)
    .set_main_content(raw_answer)
    .add_refinement_suffix(refinement_suffix)
    .add_broadening_suggestion(result_count, threshold=8)
    .add_filter_echo(filters, search_terms)
    .build()
)
```

---

## Benefits

### 1. Maintainability

| Aspect | Before | After |
|--------|--------|-------|
| Lines of code | Scattered across 200+ lines | Encapsulated in 200 lines |
| Composition logic | Inline string concatenation | Builder pattern |
| Component order | Hardcoded sequence | Chainable methods |
| Testing | Hard (integrated with business logic) | Easy (isolated class) |

### 2. Flexibility

**Before:** To change composition order requires editing core query logic

**After:** Simply reorder method calls:
```python
# Want filter echo before broadening suggestion?
builder.add_filter_echo(...).add_broadening_suggestion(...).build()

# Want to skip broadening suggestion?
builder.add_filter_echo(...).build()  # Just don't call it
```

### 3. Testability

**New Test Coverage:**
```python
def test_response_builder_composition():
    """Test that components are composed in correct order."""
    builder = ResponseBuilder(language="fr")
    response = (
        builder
        .add_prefix("Bonjour! ")
        .set_main_content("Voici 3 concerts.")
        .add_refinement_suffix("\n\n*Astuce*")
        .build()
    )
    assert response == "Bonjour! Voici 3 concerts.\n\n*Astuce*"

def test_broadening_suggestion_threshold():
    """Test that broadening only added when < threshold."""
    builder = ResponseBuilder(language="fr")

    # Below threshold - should add
    builder.add_broadening_suggestion(result_count=5, threshold=8)
    assert builder.components.broadening_suggestion != ""

    # At threshold - should not add
    builder.add_broadening_suggestion(result_count=8, threshold=8)
    assert builder.components.broadening_suggestion == ""
```

### 4. Error Handling Separation

**Before:** Error messages inline with business logic (70 lines)

**After:** Centralized error response builder:
```python
# In chain.py error handler
answer_text = build_error_response(
    error_type="model_loading",
    language=language
)
```

---

## Migration Strategy

### Phase 1: Create New Module (DONE)
- ✅ Create `src/retrieval/response_builder.py`
- ✅ Implement `ResponseBuilder` class
- ✅ Implement `build_error_response()` utility
- ✅ Extract `SUFFIX_MARKERS` constant

### Phase 2: Gradual Adoption (Optional - Future Work)
To integrate into chain.py:

```python
# Replace lines 1543-1566 in chain.py with:
from src.retrieval.response_builder import ResponseBuilder

answer_text = (
    ResponseBuilder(language=language)
    .add_prefix(response_prefix)
    .set_main_content(answer_text)
    .add_refinement_suffix(refinement_suffix)
    .add_broadening_suggestion(result_count)
    .add_filter_echo(pre_filters, search_terms)
    .build()
)
```

### Phase 3: Replace Error Handling (Optional - Future Work)
```python
# Replace lines 1585-1654 with:
from src.retrieval.response_builder import build_error_response

if isinstance(e, HuggingFaceModelLoadingError):
    answer_text = build_error_response("model_loading", language)
elif isinstance(e, HuggingFaceRateLimitError):
    answer_text = build_error_response("rate_limit", language)
elif isinstance(e, TimeoutError):
    answer_text = build_error_response("timeout", language)
else:
    answer_text = build_error_response("generic", language)
```

---

## Design Decisions

### Why Builder Pattern?

**Alternatives Considered:**

| Pattern | Pros | Cons | Verdict |
|---------|------|------|---------|
| **Template Method** | Simple inheritance | Rigid order, hard to customize | ❌ Not flexible enough |
| **Strategy Pattern** | Swappable algorithms | Overkill for composition | ❌ Too complex |
| **Builder Pattern** | Flexible, chainable, testable | Slightly more code | ✅ **Best fit** |
| **Functional Composition** | Pythonic, concise | Hard to debug long chains | ❌ Less readable for this use case |

**Builder Pattern Wins:**
- **Fluent interface**: Readable method chaining
- **Incremental building**: Add components conditionally
- **Immutability option**: Can make components immutable
- **Testability**: Each method tested independently

### Why Separate Module?

**Option 1:** Add to `chain.py`
- ❌ Already 1700+ lines
- ❌ Mixes business logic with presentation

**Option 2:** Add to `prompts.py`
- ❌ ResponseBuilder is about composition, not prompts
- ❌ Prompts are LLM inputs, responses are outputs

**Option 3:** New `response_builder.py` ✅
- ✅ Single responsibility (SRP)
- ✅ Reusable across modules
- ✅ Clean separation of concerns

---

## Backward Compatibility

**100% Backward Compatible:**
- All existing functions in `chain.py` remain unchanged
- New module is optional (no forced migration)
- Can gradually adopt builder where beneficial
- Zero breaking changes to API

---

## Future Enhancements

### 1. Response Templates

```python
# Define templates for common response patterns
RESPONSE_TEMPLATES = {
    "no_results": {
        "fr": "Aucun événement trouvé pour {filters}. Essayez d'élargir votre recherche.",
        "en": "No events found for {filters}. Try broadening your search."
    }
}

builder.use_template("no_results", filters=filter_desc)
```

### 2. Component Validators

```python
@dataclass
class ResponseComponents:
    def validate(self) -> List[str]:
        """Validate components and return warnings."""
        warnings = []
        if len(self.main_content) > 2000:
            warnings.append("Main content too long (>2000 chars)")
        if self.prefix and not self.main_content:
            warnings.append("Prefix without main content")
        return warnings
```

### 3. Metrics/Telemetry

```python
def build(self) -> str:
    """Build and track composition metrics."""
    response = self.components.compose()

    # Track composition patterns
    logger.info(f"[COMPOSITION] prefix={bool(self.components.prefix)}, "
                f"refinement={bool(self.components.refinement_suffix)}, "
                f"broadening={bool(self.components.broadening_suggestion)}")

    return response
```

---

## Conclusion

The ResponseBuilder refactoring provides:
- ✅ **Cleaner code**: Builder pattern vs string concatenation
- ✅ **Better testability**: Isolated components
- ✅ **Easier maintenance**: Single location for composition logic
- ✅ **Flexibility**: Chainable, conditional composition
- ✅ **Backward compatible**: No breaking changes

**Status:** ✅ **Phase 3B Complete**

Future work can gradually migrate `chain.py` to use the builder, but the infrastructure is now in place.
