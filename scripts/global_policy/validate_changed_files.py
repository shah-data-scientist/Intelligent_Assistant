#!/usr/bin/env python3
"""
FILE: validate_changed_files.py
STATUS: Active
RESPONSIBILITY: Validates documentation headers and comment hygiene for changed files only (staged for commit).

DEPENDENCIES (Who uses this file):
- Pre-commit hook (.pre-commit-config.yaml): Validates only files being committed
- Developers: Can run manually to check staged changes

IMPORTS (What this file needs):
- pathlib: File system operations
- subprocess: Git operations to find changed files
- sys: Exit codes
- re: Pattern matching

LAST MAJOR UPDATE: 2026-01-30 (Unified validator for changed files)
MAINTAINER: Infrastructure Team
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Set


# Required documentation fields
REQUIRED_FIELDS = {
    "FILE": r"FILE:\s*(\S+)",
    "STATUS": r"STATUS:\s*(.+)",
    "RESPONSIBILITY": r"RESPONSIBILITY:\s*(.+)",
    "DEPENDENCIES": r"DEPENDENCIES\s*\(Who uses this file\):",
    "IMPORTS": r"IMPORTS\s*\(What this file needs\):",
    "LAST MAJOR UPDATE": r"LAST MAJOR UPDATE:\s*(.+)",
    "MAINTAINER": r"MAINTAINER:\s*(.+)",
}

# Comment validation patterns
COMMENTED_CODE_PATTERNS = [
    r"^\s*#\s*(def |class |import |from |if |for |while |return |print\()",
    r"^\s*#\s*[a-z_]+\s*=\s*",
    r"^\s*#\s*(try:|except |finally:|with |async |await )",
]

TODO_FIXME_PATTERN = r"#\s*(TODO|FIXME|HACK|XXX)(?!\([^\)]*\d{4})"

MISLEADING_INDICATORS = [
    r"#.*\b(old|previous|deprecated|obsolete|legacy|unused)\b",
    r"#.*\bused to\b",
    r"#.*\bwill be\b.*\bremoved\b",
    r"#.*\bno longer\b",
    r"#.*\bdon\'t use\b",
]


class ChangedFileValidator:
    """Validates documentation and comments for ALL Python files."""

    def __init__(self, project_root: Path, check_all_files: bool = True):
        self.project_root = project_root
        self.check_all_files = check_all_files
        self.errors = []
        self.warnings = []

    def get_all_python_files(self) -> Set[Path]:
        """Get all Python files in src/, scripts/, and tests/."""
        all_files = set()

        # Check src/ directory
        src_path = self.project_root / "src"
        if src_path.exists():
            all_files.update(src_path.rglob("*.py"))

        # Check scripts/ directory (excluding _archived and global_policy)
        scripts_path = self.project_root / "scripts"
        if scripts_path.exists():
            for py_file in scripts_path.rglob("*.py"):
                # Exclude archived and policy scripts
                if "_archived" not in py_file.parts and "global_policy" not in py_file.parts:
                    all_files.add(py_file)

        # Check tests/ directory (excluding _archived)
        tests_path = self.project_root / "tests"
        if tests_path.exists():
            for py_file in tests_path.rglob("*.py"):
                if "_archived" not in py_file.parts:
                    all_files.add(py_file)

        return all_files

    def get_changed_python_files(self) -> Set[Path]:
        """Get list of Python files (ALL files by default, or staged if check_all_files=False)."""
        if self.check_all_files:
            return self.get_all_python_files()

        try:
            # Get staged files only
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            changed_files = set()
            for file_path in result.stdout.strip().split("\n"):
                if file_path and file_path.endswith(".py"):
                    full_path = self.project_root / file_path
                    if full_path.exists() and full_path.is_file():
                        changed_files.add(full_path)

            return changed_files

        except subprocess.CalledProcessError:
            # Fallback: check all files
            print("Warning: Git command failed, falling back to all files")
            return self.get_all_python_files()

    def validate_documentation_header(self, file_path: Path, content: str) -> List[str]:
        """Validate that file has proper documentation header and it matches content."""
        errors = []

        # Check for docstring at start of file
        if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
            errors.append(
                f"{file_path.relative_to(self.project_root)}: "
                f"Missing module docstring. Add documentation header at top of file."
            )
            return errors

        # Extract docstring
        docstring_match = re.search(r"^([\'\"]{3})(.*?)\1", content, re.DOTALL | re.MULTILINE)
        if not docstring_match:
            errors.append(
                f"{file_path.relative_to(self.project_root)}: "
                f"Malformed docstring. Ensure proper triple-quote format."
            )
            return errors

        docstring = docstring_match.group(2)

        # Check all required fields
        missing_fields = []
        for field_name, field_pattern in REQUIRED_FIELDS.items():
            if not re.search(field_pattern, docstring, re.MULTILINE):
                missing_fields.append(field_name)

        if missing_fields:
            errors.append(
                f"{file_path.relative_to(self.project_root)}: "
                f"Missing required documentation fields: {', '.join(missing_fields)}"
            )

        # Validate FILE field matches actual filename
        file_field_match = re.search(REQUIRED_FIELDS["FILE"], docstring)
        if file_field_match:
            declared_filename = file_field_match.group(1)
            actual_filename = file_path.name
            if declared_filename != actual_filename:
                errors.append(
                    f"{file_path.relative_to(self.project_root)}: "
                    f"FILE field mismatch: declared '{declared_filename}', actual '{actual_filename}'"
                )

        return errors

    def validate_comments(self, file_path: Path, content: str) -> Tuple[List[str], List[str]]:
        """Validate comment hygiene: no commented-out code, dated TODOs, no misleading comments."""
        errors = []
        warnings = []

        lines = content.split("\n")

        # Check for consecutive commented-out code
        consecutive_code_comments = 0
        commented_code_lines = []

        for i, line in enumerate(lines, 1):
            # Skip docstrings
            if '"""' in line or "'''" in line:
                consecutive_code_comments = 0
                continue

            # Check if this looks like commented-out code
            is_code_comment = any(re.match(pattern, line) for pattern in COMMENTED_CODE_PATTERNS)

            if is_code_comment:
                consecutive_code_comments += 1
                commented_code_lines.append(i)
            else:
                # If we had 3+ consecutive code comments, that's an error
                if consecutive_code_comments >= 3:
                    errors.append(
                        f"{file_path.relative_to(self.project_root)}:{commented_code_lines[0]}-{commented_code_lines[-1]}: "
                        f"Found {consecutive_code_comments} consecutive lines of commented-out code. "
                        f"Remove dead code instead of commenting it out."
                    )
                consecutive_code_comments = 0
                commented_code_lines = []

            # Check for TODO/FIXME without date
            if re.search(TODO_FIXME_PATTERN, line, re.IGNORECASE):
                errors.append(
                    f"{file_path.relative_to(self.project_root)}:{i}: "
                    f"TODO/FIXME without date. Use format: TODO(YYYY-MM-DD): description"
                )

            # Check for misleading comment indicators (warning only)
            if "#" in line:
                for pattern in MISLEADING_INDICATORS:
                    if re.search(pattern, line, re.IGNORECASE):
                        warnings.append(
                            f"{file_path.relative_to(self.project_root)}:{i}: "
                            f"Potentially outdated comment: {line.strip()}"
                        )
                        break

        # Check final consecutive code comments
        if consecutive_code_comments >= 3:
            errors.append(
                f"{file_path.relative_to(self.project_root)}:{commented_code_lines[0]}-{commented_code_lines[-1]}: "
                f"Found {consecutive_code_comments} consecutive lines of commented-out code. "
                f"Remove dead code instead of commenting it out."
            )

        return errors, warnings

    def validate_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Validate a single file: documentation header + comments."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return ([f"{file_path.relative_to(self.project_root)}: Failed to read file: {e}"], [])

        errors = []
        warnings = []

        # Skip __init__.py files (they may not need full documentation)
        if file_path.name == "__init__.py":
            return errors, warnings

        # Validate documentation header
        doc_errors = self.validate_documentation_header(file_path, content)
        errors.extend(doc_errors)

        # Validate comments
        comment_errors, comment_warnings = self.validate_comments(file_path, content)
        errors.extend(comment_errors)
        warnings.extend(comment_warnings)

        return errors, warnings

    def validate_all_changed_files(self) -> bool:
        """Validate all changed files and return success status."""
        changed_files = self.get_changed_python_files()

        if not changed_files:
            print("No Python files changed in this commit.")
            return True

        print(f"\nValidating {len(changed_files)} changed Python file(s)...")
        print("=" * 80)

        all_errors = []
        all_warnings = []

        for file_path in sorted(changed_files):
            errors, warnings = self.validate_file(file_path)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

        # Display results
        if all_errors:
            print("\n[ERRORS - BLOCKING]")
            for error in all_errors:
                print(f"  ERROR: {error}")

        if all_warnings:
            print("\n[WARNINGS - REVIEW RECOMMENDED]")
            for warning in all_warnings:
                print(f"  WARNING: {warning}")

        print("\n" + "=" * 80)
        print(f"Summary: {len(all_errors)} errors, {len(all_warnings)} warnings")

        if all_errors:
            print("\n[FAILED] Fix errors before committing")
            print("\nRequired fixes:")
            print("1. Add missing documentation headers (FILE/STATUS/RESPONSIBILITY/etc.)")
            print("2. Remove commented-out code (or move to version control)")
            print("3. Add dates to TODO/FIXME comments: TODO(2026-01-30): description")
            return False
        else:
            if all_warnings:
                print("\n[PASSED] with warnings - Review recommended but not blocking")
            else:
                print("\n[PASSED] All validations successful")
            return True


def main():
    """Main validation logic."""
    parser = argparse.ArgumentParser(description="Validate documentation headers and comments for ALL Python files")
    parser.add_argument(
        "--project-root", type=str, default=None, help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--staged-only", action="store_true", help="Check only staged files (for git commits) instead of all files"
    )

    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path.cwd()

    # Default: check ALL files. Use --staged-only for git commits.
    check_all = not args.staged_only

    validator = ChangedFileValidator(project_root, check_all_files=check_all)

    success = validator.validate_all_changed_files()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
