# Claude Code Project Instructions

## Python Environment

**IMPORTANT:** This project uses Python 3.11.9 via Poetry virtualenv.

**ALWAYS** use one of these methods to run Python commands:

1. **Preferred:** Use the full path to the virtualenv Python:
   ```bash
   "C:\Users\shahu\.venvs\intelligent-assistant-JzYLCfru-py3.11\Scripts\python.exe" -m <module>
   ```

2. **Alternative:** Use `poetry run`:
   ```bash
   poetry run python -m <module>
   ```

**NEVER** use plain `python` - it may use the wrong Python version (3.14).

## Starting Services

- **API Server:**
  ```bash
  "C:\Users\shahu\.venvs\intelligent-assistant-JzYLCfru-py3.11\Scripts\python.exe" -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
  ```

- **UI Server:**
  ```bash
  "C:\Users\shahu\.venvs\intelligent-assistant-JzYLCfru-py3.11\Scripts\python.exe" -m streamlit run src/frontend/app.py --server.port 8501
  ```

## Running Tests

```bash
poetry run pytest tests/
```

## Git Policy

- Never use `git stash`
- Never use `--no-verify` flag
- Always run pre-commit hooks

---

## ⚠️ MANDATORY: GLOBAL_POLICY Compliance Checklist

**Reference:** `C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md` (v1.15)

### Before EVERY Commit

- [ ] **CHANGELOG.md updated** - Entry for all changes in `[Unreleased]` section
- [ ] **Tests pass** - Run `poetry run pytest tests/unit -v`
- [ ] **Comments match code** - Review all comments in changed sections
- [ ] **No dead code** - Archive obsolete files to `_archived/YYYY-MM/`

### Before Modifying ANY File

- [ ] **Read file first** - Never modify unread files
- [ ] **Check header exists** - FILE, STATUS, RESPONSIBILITY fields
- [ ] **Note RESPONSIBILITY** - Ensure changes match purpose

### After Modifying ANY File

- [ ] **Update LAST MAJOR UPDATE** if significant change
- [ ] **Verify comments still accurate** - Update or remove stale comments
- [ ] **Run validation** - `poetry run python scripts/global_policy/validate_headers.py --fix`

### Code Safety (CRITICAL)

- [ ] **NEVER claim code unused** without grep verification
- [ ] **User approval required** for deletions, API changes, deprecations
- [ ] **Evidence required** for "unused" claims: grep command + output

### PROJECT_MEMORY.md Rules

- [ ] **APPEND ONLY** - Never replace existing content
- [ ] **Use Edit tool** - Never Write tool
- [ ] **Date-stamp entries** - YYYY-MM-DD format

### File Organization

- [ ] **Docs in docs/** - Only README.md and PROJECT_MEMORY.md in root
- [ ] **Scripts in scripts/** - No scripts in root or src/
- [ ] **_working/ is gitignored** - Don't track working files

### On Test Failure

- [ ] **Show full error** - Don't summarize
- [ ] **Analyze WHY** - Expected vs actual
- [ ] **Present options** - Let user decide
- [ ] **NEVER auto-fix** without approval

### On Pre-Commit Failure

- [ ] **STOP and inform user** - Show full output
- [ ] **NEVER bypass** with --no-verify
- [ ] **NEVER use git stash** without permission
- [ ] **Wait for user decision**

---

## Quick Reference

```bash
# Validate before commit
poetry run python scripts/global_policy/validate_headers.py --fix
poetry run python scripts/global_policy/validate_file_locations.py

# Run targeted tests (smart runner)
poetry run python scripts/global_policy/smart_test_runner.py --staged

# Full test suite
poetry run pytest tests/unit -v
```
