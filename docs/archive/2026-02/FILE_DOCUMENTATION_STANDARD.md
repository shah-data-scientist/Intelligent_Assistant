# Mandatory File Documentation Standard

> **⚠️ DEPRECATED:** This document has been integrated into `C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md` (v1.4)
>
> **Please refer to:** GLOBAL_POLICY.md → "File Documentation Standard (MANDATORY)" section
>
> **Reason for deprecation:** The File Documentation Standard applies to ALL projects and ALL script files, so it has been promoted to the global policy document. This standalone file is kept for historical reference only.

**Version:** 1.0
**Effective Date:** 2026-01-30
**Scope:** All Python files in `src/` directory
**Enforcement:** Pre-commit hook validation
**Status:** DEPRECATED - Integrated into GLOBAL_POLICY.md v1.4

---

## Purpose

Every Python file must act as its own "ID Card," declaring exactly:
1. **What it does** (Responsibility)
2. **Who uses it** (Dependencies)
3. **Whether it is alive** (Status)

This transforms the codebase into a **self-documenting system** where you can open any file and immediately understand its role.

---

## Mandatory Documentation Format

Every Python file (except `__init__.py`) MUST start with a module docstring in this exact format:

```python
"""
FILE: <filename>.py
STATUS: <Active|Deprecated|Experimental>
RESPONSIBILITY: <One-sentence description of what this file does>

DEPENDENCIES (Who uses this file):
- <module1.py>: <why it needs this file>
- <module2.py>: <why it needs this file>
- tests/<test_file>.py: <test coverage>

IMPORTS (What this file needs):
- <external_library>: <what it's used for>
- src.<internal_module>: <what it's used for>

LAST MAJOR UPDATE: <YYYY-MM-DD>
MAINTAINER: <Team or person responsible>
"""
```

---

## Documentation Fields Explained

### 1. FILE
- The filename (e.g., `storage.py`)
- Must match the actual filename

### 2. STATUS
**Required values:**
- `Active` - Currently used in production
- `Deprecated` - Marked for removal, use alternatives
- `Experimental` - Under development, not production-ready

**Examples:**
```python
STATUS: Active
STATUS: Deprecated (use storage.py instead, remove after 2026-02-15)
STATUS: Experimental (Phase 4 feature, not yet integrated)
```

### 3. RESPONSIBILITY
**One sentence** describing what this file does.

**Good Examples:**
```python
RESPONSIBILITY: SQLite storage for cultural event data with CRUD operations.
RESPONSIBILITY: Pydantic models defining the Event and ChatMessage schemas.
RESPONSIBILITY: FastAPI endpoints for the chat and feedback APIs.
```

**Bad Examples (Too Vague):**
```python
RESPONSIBILITY: Handles data.  ❌ (What kind of data?)
RESPONSIBILITY: Storage class.  ❌ (What does it store?)
RESPONSIBILITY: Utility functions.  ❌ (What utilities?)
```

### 4. DEPENDENCIES (Who uses this file)
List all files that import from this file.

**Format:**
```python
DEPENDENCIES (Who uses this file):
- src/models/vector_store.py: Reads events from storage for indexing
- src/api/endpoints.py: Queries event details for API responses
- tests/test_storage.py: Unit tests for CRUD operations
```

**How to Find Dependencies:**
```bash
# Find all files that import from storage.py
grep -r "from src.data.storage import" src/ tests/
```

### 5. IMPORTS (What this file needs)
List all external and internal dependencies.

**Format:**
```python
IMPORTS (What this file needs):
- sqlalchemy: Database ORM for SQLite operations
- pydantic: Data validation via Event model
- src.config: Database path configuration
```

### 6. LAST MAJOR UPDATE
Date of the last significant change (not minor tweaks).

**Format:** `YYYY-MM-DD`

**Examples:**
```python
LAST MAJOR UPDATE: 2026-01-28 (Added migration system)
LAST MAJOR UPDATE: 2026-01-15 (Initial implementation)
```

### 7. MAINTAINER
Team or person responsible for this file.

**Examples:**
```python
MAINTAINER: Data Team
MAINTAINER: @username
MAINTAINER: Core Backend Team
```

---

## Complete Example

Here's a fully documented file:

```python
"""
FILE: storage.py
STATUS: Active
RESPONSIBILITY: SQLite storage for cultural event data with CRUD operations and migrations.

DEPENDENCIES (Who uses this file):
- src/models/vector_store.py: Loads events for FAISS/BM25 indexing
- src/api/endpoints.py: Queries event details for API responses
- src/data/ingestion.py: Stores newly ingested events
- tests/unit/test_storage.py: Unit tests for CRUD operations
- tests/integration/test_vector_store.py: Integration tests with vector store

IMPORTS (What this file needs):
- sqlalchemy: Database ORM for SQLite operations
- sqlite3: Raw SQL for migrations
- pydantic: Data validation via Event model
- src.config: Database path configuration
- src.data.models: Event, EventLocation Pydantic models

LAST MAJOR UPDATE: 2026-01-27 (Added v5 migration for search_keywords table)
MAINTAINER: Data Team
"""

import sqlite3
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String
# ... rest of the file
```

---

## Validation Rules

### Pre-Commit Hook Check

The following validation MUST pass before commit:

1. **All `.py` files** (except `__init__.py`) have a module docstring
2. **Module docstring starts with** `"""` and contains all required fields:
   - FILE
   - STATUS
   - RESPONSIBILITY
   - DEPENDENCIES
   - IMPORTS
   - LAST MAJOR UPDATE
   - MAINTAINER
3. **STATUS** is one of: `Active`, `Deprecated`, `Experimental`
4. **RESPONSIBILITY** is a single sentence (<150 characters)

### Script to Validate

```bash
# scripts/validate_file_docs.py
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = ["FILE:", "STATUS:", "RESPONSIBILITY:", "DEPENDENCIES", "IMPORTS", "LAST MAJOR UPDATE:", "MAINTAINER:"]

def validate_file(filepath):
    """Check if file has proper documentation."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract module docstring
    match = re.search(r'^"""(.*?)"""', content, re.DOTALL | re.MULTILINE)
    if not match:
        return False, "Missing module docstring"

    docstring = match.group(1)

    # Check for all required fields
    missing = [field for field in REQUIRED_FIELDS if field not in docstring]
    if missing:
        return False, f"Missing fields: {', '.join(missing)}"

    return True, "OK"

# Run on all Python files
for py_file in Path("src").rglob("*.py"):
    if py_file.name == "__init__.py":
        continue
    valid, message = validate_file(py_file)
    if not valid:
        print(f"❌ {py_file}: {message}")
        sys.exit(1)

print("✅ All files properly documented")
```

---

## Benefits

### 1. Instant Understanding
Opening any file immediately answers:
- "What does this file do?"
- "Is it still used?"
- "Who depends on it?"

### 2. Safe Refactoring
Before modifying a file, you know:
- All files that will be affected (DEPENDENCIES)
- Why this file exists (RESPONSIBILITY)
- If it's safe to remove (STATUS: Deprecated)

### 3. Onboarding Speed
New developers can:
- Understand the codebase structure in minutes
- Identify entry points (files with many DEPENDENCIES)
- Avoid modifying deprecated code

### 4. Dead Code Detection
Files with:
- `DEPENDENCIES: (none)` = Potential dead code
- `STATUS: Deprecated` = Scheduled for removal
- Empty IMPORTS = Utility/helper files

---

## Migration Plan

### Phase 1: Core Data Layer (Week 1)
- ✅ Document all 9 files in `src/data/`
- ✅ Create validation script
- ✅ Update GLOBAL_POLICY.md

### Phase 2: Critical Paths (Week 2)
- Document `src/api/` (API endpoints)
- Document `src/retrieval/` (RAG chain)
- Document `src/models/` (Vector store)

### Phase 3: Full Coverage (Week 3-4)
- Document `src/generation/` (LLM wrappers)
- Document `src/security/` (Guardrails)
- Document `src/utils/` (Utilities)

### Phase 4: Enforcement (Week 5)
- Add pre-commit hook
- Run validation in CI/CD
- Document all test files

---

## Maintenance

### When to Update Documentation

**UPDATE required when:**
- ✅ Adding new imports
- ✅ Changing the file's core responsibility
- ✅ Deprecating the file
- ✅ Major refactoring

**UPDATE NOT required for:**
- ❌ Minor bug fixes
- ❌ Code formatting
- ❌ Adding comments
- ❌ Small logic tweaks

### Who Updates Documentation

**File Author:** Responsible for initial documentation
**Code Reviewer:** Must verify documentation in PR review
**Maintainer:** Updates when DEPENDENCIES change

---

## Integration with Global Policy

This standard is now part of:
- `C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md`
- Section: **File Documentation Standard (v1.0)**
- Enforcement: Pre-commit hook + CI/CD validation
- Applies to: All new files, updated files in active development

---

## Examples from src/data/

### Good Example: storage.py (Active, Well-Documented)
```python
"""
FILE: storage.py
STATUS: Active
RESPONSIBILITY: SQLite storage for cultural event data with CRUD operations and migrations.

DEPENDENCIES (Who uses this file):
- src/models/vector_store.py: Loads events for FAISS/BM25 indexing
- src/api/endpoints.py: Queries event details for API responses
- src/data/ingestion.py: Stores newly ingested events
- tests/unit/test_storage.py: Unit tests for CRUD operations

IMPORTS (What this file needs):
- sqlalchemy: Database ORM for SQLite operations
- src.data.models: Event, EventLocation Pydantic models
- src.config: Database path configuration

LAST MAJOR UPDATE: 2026-01-27
MAINTAINER: Data Team
"""
```

### Bad Example: mystery_helper.py (Undocumented)
```python
# Some helper functions

def process_data(data):
    return data.strip()
```
**Problems:**
- ❌ No module docstring
- ❌ No responsibility statement
- ❌ No dependencies listed
- ❌ No status indicator

---

## FAQ

### Q: What about `__init__.py` files?
**A:** They are exempt from this standard (too short). However, they SHOULD contain a brief module-level docstring explaining the package.

### Q: What if a file has no dependencies?
**A:** List it explicitly:
```python
DEPENDENCIES (Who uses this file):
- (none - dead code candidate)
```

### Q: How strict is the format?
**A:** The field names and order are flexible, but all fields must be present. Use the template as a guide.

### Q: Can I add custom fields?
**A:** Yes! You can add fields like:
- `RELATED_DOCS: docs/ARCHITECTURE.md`
- `KNOWN_ISSUES: #123, #456`
- `PERFORMANCE: O(n) indexing time`

---

## Summary

✅ **Every file = Self-documenting ID card**
✅ **7 mandatory fields**
✅ **Validation via pre-commit hook**
✅ **Eliminates "mystery file" problem**

**Result:** A codebase where every file tells you exactly what it does, who uses it, and whether it's alive.
