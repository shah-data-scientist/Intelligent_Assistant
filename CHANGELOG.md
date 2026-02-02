# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **UI Redesign**: Removed sidebar, added inline language selection and Start Fresh button
  - [src/frontend/app.py](src/frontend/app.py) - Cleaner interface without collapsible sidebar
  - Language buttons (EN/FR) now in header row
  - Session info displayed inline with version

### Fixed
- **City Typo Correction**: Added fuzzy matching fallback for misspelled city names
  - [src/retrieval/unified_analyzer.py](src/retrieval/unified_analyzer.py) - Uses Levenshtein distance (threshold 0.75) for typos
  - Examples: "Possy" → "Poissy", "Versailes" → "Versailles", "Pari" → "Paris"
  - Triggers typo acknowledgment in response when correction applied
- **Venue Address Display**: Disabled ADDRESS pattern in PII detection - venue addresses are public info
  - [src/security/sanitization.py](src/security/sanitization.py) - Removed ADDRESS from PII patterns
  - Users need venue addresses to attend events (was showing `[ADDRESS_REDACTED]`)
- **Category Validation**: Validate categories against whitelist to prevent invalid database filters
  - [src/retrieval/unified_analyzer.py](src/retrieval/unified_analyzer.py) - `map_category_to_db()` now returns `None` for invalid categories like "event"
  - Prevents generic terms from being used as category filters
- **Database Lock Prevention**: Stop tracking `chat_history.db` as git-tracked file
  - [.gitignore](.gitignore) - Added `data/chat_history.db` to prevent pre-commit stash failures
  - Runtime database artifacts should not be version controlled

### Added
- **Documentation Headers**: Added proper documentation headers to src/ and test files
  - [src/frontend/app.py](src/frontend/app.py) - Added FILE/STATUS/RESPONSIBILITY/DEPENDENCIES/IMPORTS headers
  - [src/security/sanitization.py](src/security/sanitization.py) - Added documentation headers
  - [src/utils/language.py](src/utils/language.py) - Added documentation headers
  - [src/retrieval/manager.py](src/retrieval/manager.py) - Completed DEPENDENCIES/IMPORTS headers
  - [tests/unit/test_endpoints.py](tests/unit/test_endpoints.py) - Added documentation headers
  - [tests/integration/test_api_endpoints.py](tests/integration/test_api_endpoints.py) - Added documentation headers
  - [tests/integration/test_llm_live.py](tests/integration/test_llm_live.py) - Added documentation headers

### Fixed
- **Pre-commit Compliance**: Fixed issues for all pre-commit hooks to pass
  - [src/retrieval/chain.py](src/retrieval/chain.py) - Added missing `Set` import, `STATISTICAL_TEMPLATES`, `build_filter_description` import
  - [src/retrieval/chain.py](src/retrieval/chain.py) - Fixed bare `except` to `except Exception`
  - [src/retrieval/manager.py](src/retrieval/manager.py) - Fixed bare `except` to specific exceptions
  - [src/frontend/app.py](src/frontend/app.py) - Fixed bare `except` to `except (ValueError, KeyError)`
  - [src/utils/language.py](src/utils/language.py) - Removed unused `LangDetectException` import
  - [pyproject.toml](pyproject.toml) - Added ruff configuration with sensible ignores
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Fixed bandit config (pass_filenames: false)

- **Full i18n Migration**: Completed migration of all remaining files to use JSON-based i18n framework
  - [src/retrieval/response_builder.py](src/retrieval/response_builder.py) - Migrated filters, responses, errors to i18n (200 lines → 150 lines)
  - [src/retrieval/clarifications.py](src/retrieval/clarifications.py) - Migrated clarification questions to i18n (316 lines → 33 lines)
  - [src/generation/prompts.py](src/generation/prompts.py) - Migrated system prompts to i18n framework (150+ lines → 90 lines)

### Changed
- **Code Formatting**: Applied Black and Ruff formatting across entire codebase (128 files)
  - Consistent line length (120 chars), import sorting, whitespace cleanup
  - All src/, scripts/, tests/, evaluation/ Python files reformatted
- **Pre-commit Validation Scope**: Updated validation hooks to focus on core code only
  - [scripts/global_policy/validate_changed_files.py](scripts/global_policy/validate_changed_files.py) - Now validates src/ and tests/ only (excludes scripts/, evaluation/)
  - [scripts/global_policy/validate_changelog.py](scripts/global_policy/validate_changelog.py) - Excludes utility scripts from changelog requirement
- **Code Simplification**: Removed 400+ lines of duplicated French/English text across 3 files
- **Maintainability**: All bilingual text now centralized in [data/locales/](data/locales/) JSON files

### Documentation
- **Terminology Clarification**: Documented event_type vs category distinction
  - [docs/DATA_FLOW.md](docs/DATA_FLOW.md) - Added "Entity → Filter Conversion" section explaining event_type (user input) vs category (database filter)
  - [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Added filter derivation logic in UnifiedAnalyzer section
  - [src/retrieval/unified_analyzer.py](src/retrieval/unified_analyzer.py:888-896) - Enhanced inline comments explaining terminology
  - [src/retrieval/schemas.py](src/retrieval/schemas.py) - Updated field descriptions for event_type and category fields
  - [PROJECT_MEMORY.md](PROJECT_MEMORY.md) - Added "Data Model Conventions" section with conversion logic examples

## [v1.10.0] - 2026-01-31

### Added
- **i18n Framework**: JSON-based internationalization system with locale files ([data/locales/fr.json](data/locales/fr.json), [data/locales/en.json](data/locales/en.json))
  - Created [src/utils/i18n.py](src/utils/i18n.py) translator utility
  - Centralized all bilingual text (prompts, UI, responses, errors)
- **Welcome Message**: Concise 8-line version with expandable detailed info ([src/frontend/app.py](src/frontend/app.py))
- **Event Card Display**: Always show times and venue fields (even if "Unknown")
- **CHANGELOG.md**: This file to track all changes across versions
- **Pre-commit Hook**: Validate changelog entries for modified files

### Changed
- **Event Consolidation**: Same event on same day now shows ONE card with consolidated times ([src/generation/prompts.py](src/generation/prompts.py))
  - Example: "Jazz Night" on Feb 15 @ 19:30 and 21:30 → single card with times_display: "19:30, 21:30"
- **Event Schema**: Made location and times_display required fields (default: "Unknown") ([src/api/schemas.py](src/api/schemas.py))
- **Date Format**: Enforced date-only format (YYYY-MM-DD) in event cards, times shown separately

### Fixed
- **Welcome Message Verbosity**: Reduced from 22 lines to 8 lines (details in expander)
- **Event Display**: Date and time no longer run together

### Documentation
- Updated [GLOBAL_POLICY.md](C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md) with changelog requirements
- Added i18n documentation in locale files

## [v1.9.0] - 2026-01-31

### Added
- Repository reorganization (208 files changed)
- 7-field documentation headers for 28+ Python files
- .gitignore exclusions for archived folders and .secrets.baseline

### Changed
- Moved docs to docs/, tests reorganized by type
- Consolidated Docker files to docker/ folder
- Pre-commit hooks exclude global_policy scripts

### Fixed
- Pre-commit validation for global_policy scripts
- Removed --baseline requirement from detect-secrets hook

## [v1.8.0] - 2026-01-28

### Added
- Prompt optimization for faithfulness grounding
- PROJECT_MEMORY.md protection rules

### Changed
- Enhanced RAG system prompts with explicit grounding rules

### Fixed
- Faithfulness issues via stricter prompt constraints

## [Earlier Versions]

See git history: `git log --oneline --all`

---

## How to Update This File

When making changes:

1. **Add entry under [Unreleased]** section
2. **Use these categories**:
   - **Added**: New features
   - **Changed**: Changes to existing functionality
   - **Deprecated**: Soon-to-be removed features
   - **Removed**: Removed features
   - **Fixed**: Bug fixes
   - **Security**: Security improvements

3. **Format**:
   ```markdown
   - **Feature Name**: Description ([file.py](path/to/file.py))
   ```

4. **On release**: Move [Unreleased] items to new version heading

5. **Pre-commit hook**: Will validate that changed files have changelog entries
