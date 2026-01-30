# Dead Code Prevention Policy - Implementation Summary

**Date:** 2026-01-30
**Policy Version:** GLOBAL_POLICY.md v1.7 (Updated to Archiving)
**Status:** ✅ Implemented & Transitioned to Archiving

## Problem Identified

**User's observation:** "I'm ending up with dead code and unnecessary dead files all the time"

**Root cause:** When creating consolidated/unified files that replace old files, the old files were being kept as "legacy" or "deprecated" instead of being removed from active codebase.

**Policy Evolution:**
- **v1.7 (Initial):** Delete old files immediately
- **v1.7 (Updated):** Archive old files to `_archived/YYYY-MM/` folders for safety while keeping active codebase clean

**Example from this session:**
```
Before:
scripts/global_policy/
├── validate_file_docs.py      ← Old file (validates headers)
├── validate_comments.py        ← Old file (validates comments)
└── validate_changed_files.py   ← NEW file (does both)

Problem: 3 files exist, but only 1 is needed!
```

---

## Solution Implemented

### 1. ✅ Removed Obsolete Files from Active Codebase

**Files Removed (v1.7 Initial - Before Archiving Policy):**
- `scripts/global_policy/validate_file_docs.py` (replaced by validate_changed_files.py)
- `scripts/global_policy/validate_comments.py` (replaced by validate_changed_files.py)

**Note:** These files were deleted under the initial v1.7 policy. Under the **updated v1.7 archiving policy**, they would have been archived to `scripts/global_policy/_archived/2026-01/` instead.

**Verification:**
```bash
grep -r "validate_file_docs\|validate_comments" .pre-commit-config.yaml
# → No references found (safe to remove from active codebase)

# Updated Policy (v1.7 Archiving):
mkdir -p scripts/global_policy/_archived/2026-01/
mv scripts/global_policy/validate_file_docs.py scripts/global_policy/_archived/2026-01/
mv scripts/global_policy/validate_comments.py scripts/global_policy/_archived/2026-01/
```

**Result:**
```
After (Current State):
scripts/global_policy/
├── validate_changed_files.py   ✅ Single unified validator
├── validate_file_locations.py
├── check_orphaned_files.py
├── check_clean_working_directory.py
└── setup_pre_commit.py

Total: 5 active scripts (was 7 with 2 obsolete)

Future State (with archiving):
scripts/global_policy/
├── validate_changed_files.py   ✅ Single unified validator
├── _archived/                  ✅ Old files preserved
│   └── 2026-01/
│       ├── validate_file_docs.py
│       └── validate_comments.py
└── ... (4 other active scripts)
```

---

### 2. ✅ Updated Documentation

**scripts/global_policy/README.md:**
- Changed "7 Total" → "5 Total"
- Removed "Legacy" sections for deleted files
- Updated description to not mention replacement

**Before:**
```markdown
## Current Scripts (7 Total)

### 1. validate_changed_files.py
Status: Active (replaces validate_file_docs.py + validate_comments.py)

...

### 5. validate_file_docs.py (Legacy)
**Status:** DEPRECATED - Use validate_changed_files.py instead

### 6. validate_comments.py (Legacy)
**Status:** DEPRECATED - Use validate_changed_files.py instead
```

**After:**
```markdown
## Current Scripts (5 Total)

### 1. validate_changed_files.py ⭐ (RECOMMENDED)
**Purpose:** Unified validation for documentation headers + comment hygiene
**Status:** Active

... (only active scripts listed)
```

---

### 3. ✅ Added Policy to GLOBAL_POLICY.md v1.7

**New Section:** "Dead Code Prevention Policy (MANDATORY)"

**Key Principles:**

#### The Golden Rule
> **When creating a new file that consolidates, replaces, or supersedes existing files, the old files MUST BE ARCHIVED IMMEDIATELY** (moved to `_archived/YYYY-MM/` folders).

#### Why This Matters
- ❌ Dead code accumulation
- ❌ Confusion (which file to use?)
- ❌ Maintenance burden
- ❌ False documentation
- ❌ Technical debt compounds over time

#### AI Assistant Policy

**AI assistants MUST:**
1. ✅ Identify all old files being replaced
2. ✅ Search for references to old files
3. ✅ Update all references to new file
4. ✅ **Archive old files** by moving to `_archived/YYYY-MM/` folder
5. ✅ Update documentation
6. ✅ Verify no broken imports
7. ✅ Commit archiving with new file (atomic)
8. ✅ **Exclude _archived/ from searches** (add to .gitignore)

**AI assistants MUST NOT:**
- ❌ Mark files as "deprecated" or "legacy" without archiving
- ❌ Keep old files in active directories "just in case"
- ❌ Assume user wants to keep old files in production locations
- ❌ Wait for user to explicitly request archiving
- ❌ Search or reference archived files unless explicitly requested

#### Proactive Archiving (Expected Behavior)

```
AI: "I've created validate_all.py which consolidates validate_docs.py
     and validate_style.py. I'm now archiving the old files to _archived/
     to prevent clutter while preserving history."

[Creates _archived/YYYY-MM/, moves old files, updates references, commits]
```

**No asking permission - just archive and explain.**

---

## Examples from Policy

### ✅ CORRECT Approach

```bash
# 1. Create new unified file
cat > validate_all.py <<EOF
# Combines functionality from validate_docs.py + validate_style.py
EOF

# 2. ARCHIVE old files immediately (create _archived/ folder if needed)
mkdir -p _archived/$(date +%Y-%m)/
mv validate_docs.py _archived/$(date +%Y-%m)/
mv validate_style.py _archived/$(date +%Y-%m)/

# 3. Update references
sed -i 's/validate_docs.py/validate_all.py/g' .pre-commit-config.yaml

# 4. Update .gitignore to exclude archives from searches
echo "_archived/" >> .gitignore

# 5. Commit together
git add validate_all.py _archived/ .gitignore
git commit -m "Consolidate validators

- Merged validate_docs.py + validate_style.py into validate_all.py
- Archived obsolete files to _archived/$(date +%Y-%m)/
- Updated .pre-commit-config.yaml"
```

### ❌ WRONG Approach

```bash
# ❌ Creating new file but keeping old ones
cat > validate_all.py

# ❌ Marking old files as "deprecated"
sed -i '1i# DEPRECATED - Use validate_all.py\n' validate_docs.py

# Result: 3 files instead of 1 → CLUTTER!
```

---

## When to Archive Files

**Archive immediately when:**

| Scenario | Example | Action |
|----------|---------|--------|
| **Code consolidation** | 3 auth files → 1 auth.py | Archive old 3 files to _archived/YYYY-MM/ |
| **Refactoring** | utils/helpers.py → core/utilities.py | Archive utils/helpers.py to _archived/YYYY-MM/ |
| **Feature replacement** | legacy_parser.py → modern_parser.py | Archive legacy_parser.py to _archived/YYYY-MM/ |
| **Deprecation completed** | old_api.py (deprecated 6mo ago) | Archive old_api.py to _archived/YYYY-MM/ |

---

## Exceptions (Rare)

**Only keep old files if ALL of these apply:**

1. ✅ Backward compatibility required (external systems depend on it)
2. ✅ Migration period needed (max 3-6 months)
3. ✅ Clear deprecation plan with removal date
4. ✅ Maintained separately (security fixes)

**If keeping:**
- Add deprecation warning with removal date
- Runtime warnings when used
- Calendar reminder for deletion

---

## Enforcement

### Manual (Current)

**Developer checklist:**
- [ ] Created new file consolidating old functionality?
- [ ] Searched for all references to old files?
- [ ] Updated all references to new file?
- [ ] Archived old files to _archived/YYYY-MM/?
- [ ] Updated .gitignore to exclude _archived/?
- [ ] Updated documentation?
- [ ] Tests still pass?

### Automated (Future Enhancement)

```bash
# Detect files marked as deprecated for >30 days
python scripts/global_policy/detect_deprecated_files.py

# Monthly cleanup
grep -r "DEPRECATED\|LEGACY\|OLD" --include="*.py" src/
```

---

## Impact of This Policy

### Before Policy
```
Repository over time:
Year 1: 100 files
Year 2: 150 files (50 new, 0 deleted)
Year 3: 220 files (70 new, 0 deleted)

Result: 120 files of dead code (54% of repository!)
```

### After Policy
```
Repository over time:
Year 1: 100 files
Year 2: 120 files (50 new, 30 obsolete deleted)
Year 3: 140 files (70 new, 50 obsolete deleted)

Result: ~0 files of dead code (clean!)
```

---

## Files Modified

| File | Change | Why |
|------|--------|-----|
| scripts/global_policy/validate_file_docs.py | 🗂️ REMOVED (should be ARCHIVED) | Replaced by validate_changed_files.py |
| scripts/global_policy/validate_comments.py | 🗂️ REMOVED (should be ARCHIVED) | Replaced by validate_changed_files.py |
| scripts/global_policy/README.md | ✏️ Updated | Removed legacy sections, updated count |
| GLOBAL_POLICY.md | ✏️ Updated | Added v1.7 - Dead Code Prevention Policy (updated to archiving) |
| GLOBAL_POLICY_HISTORY.md | ➕ Created | Version history separated from main policy |

**Note:** Files were removed under initial v1.7 policy (deletion). Under updated v1.7 policy (archiving), they would be in `scripts/global_policy/_archived/2026-01/`.

---

## Success Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Scripts in global_policy/ | 7 | 5 | 2 fewer (28% reduction) |
| Obsolete files | 2 | 0 | ✅ 100% cleaned |
| "Legacy" references in docs | 2 | 0 | ✅ Eliminated |
| Policy documentation | None | Comprehensive | ✅ Added |

---

## Going Forward

### For Developers

**When consolidating code:**
1. Create new file
2. **ARCHIVE old files immediately** to _archived/YYYY-MM/
3. Update references
4. Update .gitignore to exclude _archived/
5. Update docs
6. Commit together

**No exceptions unless justified (see policy).**

### For AI Assistants (Claude, etc.)

**Proactive behavior:**
- Detect when creating consolidated files
- Search for references
- Update references
- **Archive old files automatically** to _archived/YYYY-MM/
- Exclude _archived/ from future searches
- Explain what was archived and why

**No asking "should I archive?" - just do it and explain.**

---

## References

- **GLOBAL_POLICY.md v1.7** - Full policy text
- **scripts/global_policy/README.md** - Updated script documentation
- **This document** - Implementation summary

---

## Conclusion

This policy prevents **dead code accumulation** - a major source of technical debt. By requiring immediate deletion of obsolete files (not deprecation), we keep the codebase:

✅ **Clean** - Only active code exists
✅ **Clear** - No confusion about which files to use
✅ **Maintainable** - Changes only in one place
✅ **Documented** - Docs match reality

**Remember:** The best code to maintain is code that doesn't exist in active directories. Archive obsolete files immediately to _archived/ for safety while keeping the active codebase clean!

**Last Updated:** 2026-01-30
**Policy Owner:** Infrastructure Team
