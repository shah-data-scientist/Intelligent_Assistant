# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Full i18n Migration**: Completed migration of all remaining files to use JSON-based i18n framework
  - [src/retrieval/response_builder.py](src/retrieval/response_builder.py) - Migrated filters, responses, errors to i18n (200 lines → 150 lines)
  - [src/retrieval/clarifications.py](src/retrieval/clarifications.py) - Migrated clarification questions to i18n (316 lines → 33 lines)
  - [src/generation/prompts.py](src/generation/prompts.py) - Migrated system prompts to i18n framework (150+ lines → 90 lines)

### Changed
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
