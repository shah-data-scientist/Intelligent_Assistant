"""
FILE: validate_changelog.py
STATUS: Active
RESPONSIBILITY: Validates that changed Python files are documented in CHANGELOG.md.

DEPENDENCIES (Who uses this file):
- Pre-commit hook (.pre-commit-config.yaml): Validates changelog entries for changed files
- Developers: Can run manually to check if changed files have changelog entries

IMPORTS (What this file needs):
- pathlib: File path operations
- subprocess: Git operations
- sys: Exit codes

LAST MAJOR UPDATE: 2026-01-31 (v1.10.0 - removed emojis for Windows compatibility)
MAINTAINER: Infrastructure Team

This pre-commit hook ensures that all code changes are tracked in the changelog.

Exit codes:
    0: All changed files documented in CHANGELOG.md
    1: Some files missing from CHANGELOG.md (commit blocked)
"""

import subprocess
import sys
from pathlib import Path


def get_staged_python_files() -> list[str]:
    """Get list of staged Python files (excluding archived and __init__.py).

    Returns:
        List of staged .py file paths
    """
    try:
        # Get staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], capture_output=True, text=True, check=True
        )

        files = result.stdout.strip().split("\n")

        # Filter to Python files only, exclude archived and __init__.py
        python_files = []
        for f in files:
            if not f:
                continue
            if f.endswith(".py"):
                # Exclude __init__.py
                if f.endswith("__init__.py"):
                    continue
                # Exclude archived folders
                if "_archived" in f or "archived" in f.lower():
                    continue
                # Exclude this script itself
                if "validate_changelog.py" in f:
                    continue
                python_files.append(f)

        return python_files
    except subprocess.CalledProcessError:
        return []


def read_changelog() -> str:
    """Read CHANGELOG.md content.

    Returns:
        CHANGELOG.md content as string, or empty string if not found
    """
    changelog_path = Path("CHANGELOG.md")
    if changelog_path.exists():
        return changelog_path.read_text(encoding="utf-8")
    return ""


def check_file_in_changelog(file_path: str, changelog: str) -> bool:
    """Check if file path or filename is mentioned in [Unreleased] section.

    Args:
        file_path: Path to check (e.g., "src/api/endpoints.py")
        changelog: CHANGELOG.md content

    Returns:
        True if file is mentioned, False otherwise
    """
    # Extract [Unreleased] section
    if "[Unreleased]" not in changelog:
        return False

    unreleased_start = changelog.index("[Unreleased]")
    # Find next version heading or end of file
    next_version_idx = changelog.find("\n## [", unreleased_start + 1)
    if next_version_idx == -1:
        unreleased_section = changelog[unreleased_start:]
    else:
        unreleased_section = changelog[unreleased_start:next_version_idx]

    # Check if file path is mentioned (with or without leading ./)
    file_path_clean = file_path.replace("\\", "/")  # Normalize path separators
    filename = Path(file_path).name

    # Check for full path mention
    if file_path_clean in unreleased_section:
        return True

    # Check for filename mention (in case changelog uses relative paths differently)
    if f"/{filename}" in unreleased_section or f"({filename})" in unreleased_section:
        return True

    # Check for path variations (with ./ prefix)
    if f"./{file_path_clean}" in unreleased_section:
        return True

    return False


def main():
    """Main validation logic."""
    # Get staged Python files
    staged_files = get_staged_python_files()

    if not staged_files:
        # No Python files staged, skip check
        print("[OK] No Python files staged, skipping CHANGELOG validation")
        sys.exit(0)

    # Read CHANGELOG.md
    changelog = read_changelog()

    if not changelog:
        print("[WARNING]  WARNING: CHANGELOG.md not found")
        print("   Consider creating CHANGELOG.md to track changes")
        print("   See: https://keepachangelog.com/")
        # Don't block commit, just warn
        sys.exit(0)

    # Check each file
    missing_files = []
    for file_path in staged_files:
        if not check_file_in_changelog(file_path, changelog):
            missing_files.append(file_path)

    if missing_files:
        print("[ERROR] CHANGELOG VALIDATION FAILED")
        print()
        print("The following Python files were modified but not documented in CHANGELOG.md:")
        for f in missing_files:
            print(f"   - {f}")
        print()
        print("Please add entries to CHANGELOG.md under the [Unreleased] section:")
        print()
        print("## [Unreleased]")
        print()
        print("### Added|Changed|Fixed")
        print(f"- **Feature/Fix**: Description ([{missing_files[0]}]({missing_files[0]}))")
        print()
        print("See CHANGELOG.md for examples and format.")
        sys.exit(1)

    print("[OK] CHANGELOG.md validation passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
