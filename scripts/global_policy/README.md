# Global Policy Enforcement Scripts

**Version:** 2.0
**Last Updated:** 2026-01-30
**Policy Reference:** `GLOBAL_POLICY.md` v1.6
**Location:** `scripts/global_policy/` (portable to any project)

## Overview

This folder contains **project-independent** enforcement scripts for `GLOBAL_POLICY.md`. These scripts validate code quality, file organization, and documentation standards across all projects.

**Key Features:**
- ✅ **Portable** - Works with any Python project
- ✅ **Configurable** - Uses command-line arguments (no hardcoded paths)
- ✅ **Pre-commit integrated** - Runs automatically before commits
- ✅ **Non-destructive** - Only validates, never modifies files

---

## Current Scripts (5 Total)

### 1. validate_changed_files.py ⭐ (RECOMMENDED)
**Purpose:** Unified validation for documentation headers + comment hygiene
**Status:** Active

**What it checks:**
- All 7 required documentation fields
- FILE field matches actual filename
- No commented-out code (3+ consecutive lines)
- All TODO/FIXME have dates
- No misleading comments (warnings)

**Usage:**
```bash
# Check all files (default)
python scripts/global_policy/validate_changed_files.py

# Check only staged files (for pre-commit)
python scripts/global_policy/validate_changed_files.py --staged-only
```

---

### 2. validate_file_locations.py
**Purpose:** Enforces file placement rules

**What it checks:**
- Docs: Only README.md + PROJECT_MEMORY.md in root
- Scripts: All .py scripts in scripts/ (not root/src/)
- Tests: All test_*.py in tests/ or scripts/

**Usage:**
```bash
python scripts/global_policy/validate_file_locations.py
```

---

###3. check_orphaned_files.py (Warning Only)
**Purpose:** Detects potentially orphaned/outdated files

**What it checks:**
- Debug scripts >30 days old
- Scripts without documentation
- Scripts not modified in 90+ days
- Large scripts (>100 LOC) without tests

**Usage:**
```bash
python scripts/global_policy/check_orphaned_files.py --verbose
```

**Exit code:** Always 0 (warnings only, never blocks)

---

### 4. check_clean_working_directory.py
**Purpose:** Ensures working directory is clean before commit

**What it checks:**
- No unstaged modifications
- No untracked files (unless in .gitignore)

**Usage:**
```bash
python scripts/global_policy/check_clean_working_directory.py
```

---

### 5. setup_pre_commit.py
**Purpose:** Helper to install pre-commit hooks

**Usage:**
```bash
python scripts/global_policy/setup_pre_commit.py
```

---

## Installation (New Project)

### Automated (Recommended)
```bash
# From coding_agent_policies directory
python setup_new_project.py /path/to/new/project
```

### Manual
```bash
# 1. Copy scripts
cp -r global_policy_scripts/ /path/to/project/scripts/global_policy/

# 2. Copy pre-commit config
cp .pre-commit-config-template.yaml /path/to/project/.pre-commit-config.yaml

# 3. Install hooks
cd /path/to/project && pre-commit install
```

---

## Pre-Commit Hooks

### Recommended .pre-commit-config.yaml
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-changed-files
        name: Validate Changed Files (Headers + Comments)
        entry: python scripts/global_policy/validate_changed_files.py --staged-only
        language: system
        pass_filenames: false
        stages: [pre-commit]

      - id: validate-file-locations
        name: Validate File Locations
        entry: python scripts/global_policy/validate_file_locations.py
        language: system
        pass_filenames: false
        stages: [pre-commit]

      - id: check-orphaned-files
        name: Check Orphaned Files (Warning)
        entry: python scripts/global_policy/check_orphaned_files.py --verbose
        language: system
        pass_filenames: false
        stages: [pre-commit]
        verbose: true
```

---

## Workflow

```
Developer commits: git commit -m "message"
    ↓
validate-changed-files (BLOCKING)
  → Checks headers + comments on staged files
    ↓
validate-file-locations (BLOCKING)
  → Checks file placement rules
    ↓
check-orphaned-files (WARNING ONLY)
  → Warns about old scripts
    ↓
All passed → Commit succeeds ✅
```

---

## Project Independence

These scripts are **fully project-independent**:

✅ No hardcoded paths - All paths runtime-determined
✅ No project-specific logic - Works with any Python project
✅ Configurable via args - All settings command-line
✅ Standalone - No external dependencies

**This means:**
- Copy to any project
- Use across multiple projects
- Update in one place (coding_agent_policies/)
- Version control independently

---

## Updating All Projects

When you update scripts in `coding_agent_policies/`:

```bash
# Option 1: Re-run automated setup
python setup_new_project.py /path/to/project

# Option 2: Manual copy
cp -r global_policy_scripts/* /path/to/project/scripts/global_policy/
```

---

## References

- **GLOBAL_POLICY.md** v1.6 - Policy source of truth
- **.pre-commit-config-template.yaml** - Hook configuration
- **setup_new_project.py** - Automated setup script

**Last Updated:** 2026-01-30
**Maintainer:** Infrastructure Team
