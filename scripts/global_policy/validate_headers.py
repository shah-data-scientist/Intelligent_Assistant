#!/usr/bin/env python3
"""
FILE: validate_headers.py
STATUS: Active
RESPONSIBILITY: Unified file header validation, creation, and auto-correction with comment hygiene checks.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Infrastructure Team

USAGE:
    # Fast mode (pre-commit) - structural checks only, no LLM
    python validate_headers.py --fast --staged-only

    # Full validation with LLM semantic check
    python validate_headers.py --verbose

    # Auto-fix everything (headers + descriptions)
    python validate_headers.py --fix --verbose

MODES:
    --fast: Structural validation only (no LLM, fast, for pre-commit)
    --fix: Auto-fix issues using LLM (creates headers, corrects descriptions)

PORTABLE: This script auto-detects project root and can be copied to any project.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Tuple


# Auto-detect project root (look for .git, pyproject.toml, or setup.py)
def find_project_root(start_path: Path = None) -> Path:
    """Find project root by looking for common project markers."""
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = start_path
    markers = [".git", "pyproject.toml", "setup.py", "setup.cfg"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    # Fallback to script's grandparent (scripts/global_policy -> project root)
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = find_project_root()

# Try to import LLM dependencies (optional for --fast mode)
LLM_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    LLM_AVAILABLE = True
except ImportError:
    pass


# ============================================================================
# CONFIGURATION
# ============================================================================

REQUIRED_FIELDS = {
    "FILE": r"FILE:\s*(\S+)",
    "STATUS": r"STATUS:\s*(.+)",
    "RESPONSIBILITY": r"RESPONSIBILITY:\s*(.+)",
    "LAST MAJOR UPDATE": r"LAST MAJOR UPDATE:\s*(.+)",
    "MAINTAINER": r"MAINTAINER:\s*(.+)",
}

SCAN_DIRS = ["src", "scripts", "tests"]

EXCLUDE_PATTERNS = ["_archived", "__pycache__", ".venv", "global_policy", "_working", "node_modules"]

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bTBD\b",
    r"\bPLACEHOLDER\b",
    r"\bXXX\b",
    r"<[^>]+>",
    r"\.\.\.",
]

COMMENTED_CODE_PATTERNS = [
    r"^\s*#\s*(def |class |import |from |if |for |while |return |print\()",
    r"^\s*#\s*[a-z_]+\s*=\s*",
    r"^\s*#\s*(try:|except |finally:|with |async |await )",
]

TODO_FIXME_PATTERN = r"#\s*(TODO|FIXME|HACK|XXX)(?!\([^\)]*\d{4})"

MISLEADING_COMMENT_PATTERNS = [
    r"#.*\b(old|previous|deprecated|obsolete|legacy|unused)\b",
    r"#.*\bused to\b",
    r"#.*\bwill be\b.*\bremoved\b",
    r"#.*\bno longer\b",
    r"#.*\bdon\'t use\b",
]

# LLM Prompts
VALIDATION_PROMPT = """Evaluate if this file's RESPONSIBILITY description accurately reflects the code.

FILE: {filename}
CURRENT RESPONSIBILITY: {responsibility}

CODE:
```python
{code_content}
```

RESPOND: "ACCURATE" or "NEEDS_UPDATE" (one word only)"""

GENERATE_DESCRIPTION_PROMPT = """Generate a one-sentence RESPONSIBILITY description for this Python file.

FILE: {filename}

CODE:
```python
{code_content}
```

RULES:
1. One sentence, max 100 characters
2. Start with verb (Provides, Handles, Manages, Implements)
3. Describe PRIMARY purpose
4. Be specific, not vague
5. No period at end

Return ONLY the description text."""


# ============================================================================
# LLM FUNCTIONS
# ============================================================================


def get_llm():
    """Initialize Google Generative AI client."""
    if not LLM_AVAILABLE:
        raise RuntimeError("LLM dependencies not available. Install google-genai and python-dotenv.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable required for LLM features.")

    return genai.Client(api_key=api_key)


def generate_description(file_path: Path, content: str, llm) -> str | None:
    """Generate RESPONSIBILITY description using LLM."""
    code_content = truncate_code(content)

    prompt = GENERATE_DESCRIPTION_PROMPT.format(
        filename=file_path.name,
        code_content=code_content,
    )

    try:
        response = llm.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )
        description = response.text.strip().strip("\"'")
        if description.endswith("."):
            description = description[:-1]

        # Truncate without using ... (triggers placeholder warning)
        if len(description) > 100:
            last_space = description[:100].rfind(" ")
            description = description[:last_space] if last_space > 50 else description[:97]

        return description
    except Exception:
        return None


def validate_description_accuracy(file_path: Path, responsibility: str, content: str, llm) -> bool:
    """Check if RESPONSIBILITY accurately describes the code using LLM."""
    code_content = truncate_code(content)

    prompt = VALIDATION_PROMPT.format(
        filename=file_path.name,
        responsibility=responsibility,
        code_content=code_content,
    )

    try:
        response = llm.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        result = response.text.strip().upper()
        return "ACCURATE" in result and "NEEDS" not in result
    except Exception:
        return True  # Assume accurate on error


# ============================================================================
# FILE UTILITIES
# ============================================================================


def truncate_code(content: str, max_lines: int = 150) -> str:
    """Truncate code for LLM processing."""
    lines = content.split("\n")

    # Skip header docstring
    in_docstring = False
    code_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                code_start = i + 1
                break
            else:
                in_docstring = True

    code_lines = lines[code_start:]

    if len(code_lines) <= max_lines:
        return "\n".join(code_lines)

    return "\n".join(code_lines[:100] + ["# ... (truncated) ..."] + code_lines[-50:])


def get_python_files(project_root: Path, staged_only: bool = False) -> list[Path]:
    """Get Python files to validate."""
    if staged_only:
        return get_staged_files(project_root)

    all_files = []
    for scan_dir in SCAN_DIRS:
        dir_path = project_root / scan_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if any(excl in py_file.parts for excl in EXCLUDE_PATTERNS):
                continue
            if py_file.name == "__init__.py":
                continue
            all_files.append(py_file)

    return sorted(all_files)


def get_staged_files(project_root: Path) -> list[Path]:
    """Get staged Python files for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )

        files = []
        for file_path in result.stdout.strip().split("\n"):
            if file_path and file_path.endswith(".py"):
                full_path = project_root / file_path
                if full_path.exists():
                    files.append(full_path)
        return files
    except subprocess.CalledProcessError:
        return []


# ============================================================================
# HEADER FUNCTIONS
# ============================================================================


def generate_complete_header(filename: str, responsibility: str, maintainer: str = "Team") -> str:
    """Generate complete file header."""
    today = date.today().isoformat()
    return f'''"""
FILE: {filename}
STATUS: Active
RESPONSIBILITY: {responsibility}
LAST MAJOR UPDATE: {today}
MAINTAINER: {maintainer}
"""

'''


def has_valid_header(content: str) -> bool:
    """Check if file has valid header with all required fields."""
    lines = content.split("\n", 1)
    content_to_check = lines[1] if lines[0].startswith("#!") and len(lines) > 1 else content

    stripped = content_to_check.strip()
    if not stripped.startswith('"""') and not stripped.startswith("'''"):
        return False

    docstring_match = re.search(r"^([\'\"]{3})(.*?)\1", stripped, re.DOTALL)
    if not docstring_match:
        return False

    docstring = docstring_match.group(2)
    return all(re.search(pattern, docstring, re.MULTILINE) for pattern in REQUIRED_FIELDS.values())


def extract_header_info(content: str) -> dict | None:
    """Extract header field values."""
    lines = content.split("\n", 1)
    content_to_check = lines[1] if lines[0].startswith("#!") and len(lines) > 1 else content

    stripped = content_to_check.strip()
    if not stripped.startswith('"""') and not stripped.startswith("'''"):
        return None

    docstring_match = re.search(r"^([\'\"]{3})(.*?)\1", stripped, re.DOTALL)
    if not docstring_match:
        return None

    docstring = docstring_match.group(2)
    result = {}
    for field_name, pattern in REQUIRED_FIELDS.items():
        match = re.search(pattern, docstring, re.MULTILINE)
        if match:
            result[field_name] = match.group(1).strip()

    return result if result else None


def has_placeholder(value: str) -> bool:
    """Check if value contains placeholder text."""
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS)


def add_header_to_file(file_path: Path, responsibility: str, maintainer: str = "Team") -> bool:
    """Add complete header to file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return False

    header = generate_complete_header(file_path.name, responsibility, maintainer)
    stripped = content.lstrip()

    if stripped.startswith('"""') or stripped.startswith("'''"):
        quote_char = stripped[:3]
        docstring_end = stripped.find(quote_char, 3)
        if docstring_end != -1:
            after_docstring = stripped[docstring_end + 3 :].lstrip("\n")
            new_content = header + after_docstring
        else:
            new_content = header + content
    elif content.startswith("#!"):
        first_newline = content.find("\n")
        if first_newline != -1:
            shebang = content[: first_newline + 1]
            rest = content[first_newline + 1 :].lstrip("\n")
            new_content = shebang + header + rest
        else:
            new_content = content + "\n" + header
    else:
        new_content = header + content

    try:
        file_path.write_text(new_content, encoding="utf-8")
        return True
    except Exception:
        return False


def update_responsibility(file_path: Path, new_responsibility: str) -> bool:
    """Update RESPONSIBILITY field in file header."""
    try:
        content = file_path.read_text(encoding="utf-8")
        new_content, count = re.subn(r"(RESPONSIBILITY:\s*)(.+)", rf"\g<1>{new_responsibility}", content, count=1)
        if count > 0:
            file_path.write_text(new_content, encoding="utf-8")
            return True
    except Exception:
        pass
    return False


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_header_structure(file_path: Path, content: str, project_root: Path) -> Tuple[list, list]:
    """Validate header structure (no LLM)."""
    errors = []
    warnings = []
    rel_path = file_path.relative_to(project_root)

    lines = content.split("\n", 1)
    content_to_check = lines[1] if lines[0].startswith("#!") and len(lines) > 1 else content

    stripped = content_to_check.strip()
    if not stripped.startswith('"""') and not stripped.startswith("'''"):
        errors.append(f"{rel_path}: Missing module docstring header")
        return errors, warnings

    docstring_match = re.search(r"^([\'\"]{3})(.*?)\1", stripped, re.DOTALL)
    if not docstring_match:
        errors.append(f"{rel_path}: Malformed docstring")
        return errors, warnings

    docstring = docstring_match.group(2)

    # Check required fields
    missing = [name for name, pattern in REQUIRED_FIELDS.items() if not re.search(pattern, docstring, re.MULTILINE)]
    if missing:
        errors.append(f"{rel_path}: Missing fields: {', '.join(missing)}")

    # Check FILE field matches
    file_match = re.search(REQUIRED_FIELDS["FILE"], docstring)
    if file_match and file_match.group(1) != file_path.name:
        errors.append(f"{rel_path}: FILE mismatch: '{file_match.group(1)}' vs '{file_path.name}'")

    # Check for placeholders
    for field_name in ["RESPONSIBILITY", "STATUS", "MAINTAINER"]:
        field_match = re.search(REQUIRED_FIELDS[field_name], docstring)
        if field_match and has_placeholder(field_match.group(1)):
            warnings.append(f"{rel_path}: {field_name} contains placeholder")

    return errors, warnings


def validate_comments(file_path: Path, content: str, project_root: Path) -> Tuple[list, list]:
    """Validate comment hygiene."""
    errors = []
    warnings = []
    rel_path = file_path.relative_to(project_root)

    lines = content.split("\n")
    consecutive_code_comments = 0
    comment_start_line = 0

    for i, line in enumerate(lines, 1):
        # Skip docstrings
        if '"""' in line or "'''" in line:
            consecutive_code_comments = 0
            continue

        # Check for commented-out code
        is_code_comment = any(re.match(pattern, line) for pattern in COMMENTED_CODE_PATTERNS)
        if is_code_comment:
            if consecutive_code_comments == 0:
                comment_start_line = i
            consecutive_code_comments += 1
        else:
            if consecutive_code_comments >= 3:
                errors.append(
                    f"{rel_path}:{comment_start_line}: {consecutive_code_comments} lines of commented-out code"
                )
            consecutive_code_comments = 0

        # Check TODO/FIXME without date
        if re.search(TODO_FIXME_PATTERN, line, re.IGNORECASE):
            errors.append(f"{rel_path}:{i}: TODO/FIXME without date (use TODO(YYYY-MM-DD))")

        # Check misleading comments
        if "#" in line:
            for pattern in MISLEADING_COMMENT_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    warnings.append(f"{rel_path}:{i}: Potentially outdated comment")
                    break

    # Check final block
    if consecutive_code_comments >= 3:
        errors.append(f"{rel_path}:{comment_start_line}: {consecutive_code_comments} lines of commented-out code")

    return errors, warnings


def validate_file(
    file_path: Path, project_root: Path, llm=None, fix_mode: bool = False, maintainer: str = "Team"
) -> dict:
    """
    Validate a single file.

    Returns dict with:
        status: ACCURATE, FIXED, HEADER_ADDED, NEEDS_FIX, NEEDS_HEADER, ERROR
        errors: list of blocking errors
        warnings: list of non-blocking warnings
        old_value: previous RESPONSIBILITY (if changed)
        new_value: new RESPONSIBILITY (if fixed)
    """
    result = {
        "status": "ACCURATE",
        "errors": [],
        "warnings": [],
        "old_value": None,
        "new_value": None,
    }

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(f"Could not read file: {e}")
        return result

    # Structural validation (always)
    header_errors, header_warnings = validate_header_structure(file_path, content, project_root)
    comment_errors, comment_warnings = validate_comments(file_path, content, project_root)

    result["errors"].extend(header_errors)
    result["errors"].extend(comment_errors)
    result["warnings"].extend(header_warnings)
    result["warnings"].extend(comment_warnings)

    # Check if header is valid
    if not has_valid_header(content):
        if fix_mode and llm:
            new_desc = generate_description(file_path, content, llm)
            if new_desc and add_header_to_file(file_path, new_desc, maintainer):
                result["status"] = "HEADER_ADDED"
                result["new_value"] = new_desc
                result["errors"] = []  # Clear header errors since we fixed them
            else:
                result["status"] = "ERROR"
                result["errors"].append("Failed to add header")
        else:
            result["status"] = "NEEDS_HEADER"
        return result

    # Semantic validation (if LLM available)
    if llm:
        header_info = extract_header_info(content)
        responsibility = header_info.get("RESPONSIBILITY", "") if header_info else ""

        # Check for placeholder or semantic accuracy
        needs_update = has_placeholder(responsibility)
        if not needs_update:
            needs_update = not validate_description_accuracy(file_path, responsibility, content, llm)

        if needs_update:
            new_desc = generate_description(file_path, content, llm)
            if fix_mode and new_desc:
                if update_responsibility(file_path, new_desc):
                    result["status"] = "FIXED"
                    result["old_value"] = responsibility
                    result["new_value"] = new_desc
                    # Remove placeholder warnings since we fixed them
                    result["warnings"] = [w for w in result["warnings"] if "placeholder" not in w.lower()]
                else:
                    result["status"] = "ERROR"
                    result["errors"].append("Failed to update RESPONSIBILITY")
            else:
                result["status"] = "NEEDS_FIX"
                result["old_value"] = responsibility
                result["new_value"] = new_desc

    # Determine final status
    if result["status"] == "ACCURATE" and result["errors"]:
        result["status"] = "HAS_ERRORS"

    return result


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Validate and fix file headers and comments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Pre-commit (fast, staged files only)
  python validate_headers.py --fast --staged-only

  # Full validation with semantic check
  python validate_headers.py --verbose

  # Auto-fix everything
  python validate_headers.py --fix --verbose

  # Single file
  python validate_headers.py --file src/config.py --fix
""",
    )
    parser.add_argument("--project-root", type=str, help="Project root (auto-detected if not specified)")
    parser.add_argument("--file", type=str, help="Validate single file")
    parser.add_argument("--limit", type=int, default=0, help="Limit files to process")
    parser.add_argument("--fast", action="store_true", help="Fast mode: structural checks only, no LLM")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues using LLM")
    parser.add_argument("--staged-only", action="store_true", help="Only check staged files")
    parser.add_argument("--maintainer", type=str, default="Team", help="Maintainer for new headers")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Determine project root
    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT

    # Mode description
    if args.fast:
        mode = "Fast (structural only)"
    elif args.fix:
        mode = "Fix (auto-correct with LLM)"
    else:
        mode = "Full (with LLM validation)"

    print(f"\nHeader Validation - {mode}")
    print(f"Project: {project_root}")
    print("=" * 80)

    # Initialize LLM if needed
    llm = None
    if not args.fast:
        if not LLM_AVAILABLE:
            print("Warning: LLM not available. Running in fast mode.")
            args.fast = True
        else:
            try:
                llm = get_llm()
                print("LLM: Google Gemini (gemini-2.0-flash)")
            except (RuntimeError, ValueError) as e:
                print(f"Warning: {e}. Running in fast mode.")
                args.fast = True

    # Get files
    if args.file:
        files = [Path(args.file).resolve()]
    else:
        files = get_python_files(project_root, args.staged_only)

    if args.limit > 0:
        files = files[: args.limit]

    if not files:
        print("\nNo files to validate.")
        return 0

    print(f"Files: {len(files)}\n")

    # Process files
    all_errors = []
    all_warnings = []
    stats = {
        "ACCURATE": 0,
        "FIXED": 0,
        "HEADER_ADDED": 0,
        "NEEDS_FIX": 0,
        "NEEDS_HEADER": 0,
        "HAS_ERRORS": 0,
        "ERROR": 0,
    }

    for i, file_path in enumerate(files, 1):
        rel_path = file_path.relative_to(project_root)

        if args.verbose:
            print(f"[{i}/{len(files)}] {rel_path}...", end=" ", flush=True)

        result = validate_file(file_path, project_root, llm, args.fix, args.maintainer)
        stats[result["status"]] = stats.get(result["status"], 0) + 1

        for err in result["errors"]:
            all_errors.append(err)
        for warn in result["warnings"]:
            all_warnings.append(warn)

        if args.verbose:
            print(result["status"])
            if result["status"] in ("FIXED", "HEADER_ADDED") and result["new_value"]:
                if result["old_value"]:
                    print(f"         Old: {result['old_value']}")
                print(f"         New: {result['new_value']}")
            elif result["status"] in ("NEEDS_FIX", "NEEDS_HEADER") and result["new_value"]:
                if result["old_value"]:
                    print(f"         Current: {result['old_value']}")
                print(f"         Suggested: {result['new_value']}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nAccurate: {stats['ACCURATE']}")
    if stats["FIXED"]:
        print(f"Fixed: {stats['FIXED']}")
    if stats["HEADER_ADDED"]:
        print(f"Headers added: {stats['HEADER_ADDED']}")
    if stats["NEEDS_FIX"]:
        print(f"Need fix: {stats['NEEDS_FIX']}")
    if stats["NEEDS_HEADER"]:
        print(f"Need header: {stats['NEEDS_HEADER']}")
    if stats["HAS_ERRORS"]:
        print(f"Have errors: {stats['HAS_ERRORS']}")
    if stats["ERROR"]:
        print(f"Failed: {stats['ERROR']}")

    if all_errors:
        print(f"\n[ERRORS] ({len(all_errors)}):")
        for err in all_errors[:20]:  # Limit output
            print(f"  {err}")
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more")

    if all_warnings:
        print(f"\n[WARNINGS] ({len(all_warnings)}):")
        for warn in all_warnings[:10]:
            print(f"  {warn}")
        if len(all_warnings) > 10:
            print(f"  ... and {len(all_warnings) - 10} more")

    # Exit code
    needs_action = stats["NEEDS_FIX"] + stats["NEEDS_HEADER"] + stats["HAS_ERRORS"]
    if all_errors and not args.fix:
        print("\n[FAILED] Fix errors before committing")
        return 1
    elif needs_action > 0 and not args.fix:
        print(f"\n[ACTION REQUIRED] Run with --fix to correct {needs_action} files")
        return 1
    elif stats["FIXED"] + stats["HEADER_ADDED"] > 0:
        print(f"\n[SUCCESS] Fixed {stats['FIXED'] + stats['HEADER_ADDED']} files")
        return 0
    else:
        print("\n[SUCCESS] All files valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
