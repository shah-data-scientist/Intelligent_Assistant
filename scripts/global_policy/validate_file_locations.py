#!/usr/bin/env python3
"""
FILE: validate_file_locations.py
STATUS: Active
RESPONSIBILITY: Enforces strict file placement rules to prevent repository clutter (docs only in docs/, scripts only in scripts/).

DEPENDENCIES (Who uses this file):
- Pre-commit hook (.pre-commit-config.yaml): Validates file locations before commit
- GLOBAL_POLICY.md: File Organization Policy enforcement

IMPORTS (What this file needs):
- pathlib: File system traversal
- sys: Exit codes

LAST MAJOR UPDATE: 2026-01-30 (Initial implementation)
MAINTAINER: Infrastructure Team
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Allowed documentation files in root
ALLOWED_ROOT_DOCS = {"README.md", "PROJECT_MEMORY.md", "LICENSE", "LICENSE.txt", "CHANGELOG.md"}

# Documentation extensions
DOC_EXTENSIONS = {".md", ".pdf", ".txt", ".rst", ".adoc"}

# Script extensions
SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh"}

# Temporary/debug file patterns
TEMP_PATTERNS = ["scratch", "temp", "tmp", "debug_", "test_", "check_", "dump", "backup"]

# Directories to exclude from validation
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "egg-info",
    ".tox",
}


class FileLocationValidator:
    """Validates file placement according to organization policy."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors = []

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path is in an excluded directory."""
        path_parts = path.relative_to(self.project_root).parts
        return any(excluded in path_parts for excluded in EXCLUDED_DIRS)

    def check_documentation_files(self) -> List[str]:
        """Check for documentation files in wrong locations."""
        errors = []

        # Check root directory for unauthorized docs
        for file in self.project_root.iterdir():
            if file.is_file() and file.suffix in DOC_EXTENSIONS:
                if file.name not in ALLOWED_ROOT_DOCS:
                    errors.append(
                        f"{file.name}: Documentation file in root directory. "
                        f"Move to docs/ folder. Only README.md and PROJECT_MEMORY.md allowed in root."
                    )

        # Check src/ directory for documentation files
        src_path = self.project_root / "src"
        if src_path.exists():
            for doc_file in src_path.rglob("*"):
                if doc_file.is_file() and doc_file.suffix in DOC_EXTENSIONS and not self._is_excluded(doc_file):
                    errors.append(
                        f"{doc_file.relative_to(self.project_root)}: "
                        f"Documentation file in src/. Move to docs/ folder."
                    )

        return errors

    def check_script_files(self) -> List[str]:
        """Check for script files in wrong locations."""
        errors = []

        # Check root directory for scripts
        for file in self.project_root.iterdir():
            if file.is_file() and file.suffix == ".py":
                # Exclude setup.py and other standard files
                if file.name not in {"setup.py", "__init__.py"}:
                    errors.append(f"{file.name}: Python script in root directory. " f"Move to scripts/ folder.")

        # Check src/ directory for debug/test scripts
        src_path = self.project_root / "src"
        if src_path.exists():
            for script_file in src_path.rglob("*.py"):
                if script_file.is_file() and not self._is_excluded(script_file):
                    # Check for temporary/debug script patterns
                    for pattern in TEMP_PATTERNS:
                        if pattern in script_file.name.lower():
                            errors.append(
                                f"{script_file.relative_to(self.project_root)}: "
                                f"Debug/temp script in src/. Move to scripts/debug/ folder."
                            )
                            break

        return errors

    def check_temporary_files(self) -> List[str]:
        """Check for temporary files that should be gitignored."""
        warnings = []

        # Common temporary file patterns
        temp_files = []
        for pattern in ["*.tmp", "*.log", "*.cache", "temp_*", "scratch.*", "dump.*"]:
            temp_files.extend(self.project_root.glob(pattern))

        for temp_file in temp_files:
            if temp_file.is_file():
                warnings.append(
                    f"{temp_file.name}: Temporary file detected. " f"Add to .gitignore or move to data/temp/"
                )

        return warnings

    def check_test_files_location(self) -> List[str]:
        """Check for test files outside tests/ directory."""
        errors = []

        # Check for test_*.py files not in tests/ or scripts/
        for test_file in self.project_root.rglob("test_*.py"):
            if test_file.is_file() and not self._is_excluded(test_file):
                # Allowed if in tests/ or scripts/
                try:
                    relative = test_file.relative_to(self.project_root)
                    parts = relative.parts
                    if parts[0] not in {"tests", "scripts"}:
                        errors.append(
                            f"{relative}: Test file outside tests/ or scripts/. " f"Move to appropriate location."
                        )
                except ValueError:
                    pass

        return errors


def main():
    """Main validation logic."""
    parser = argparse.ArgumentParser(description="Validate file locations according to organization policy")
    parser.add_argument(
        "--project-root", type=str, default=None, help="Project root directory (default: current directory)"
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path.cwd()

    print("\n" + "=" * 80)
    print("File Location Validator")
    print("=" * 80)
    print(f"Project root: {project_root}\n")

    validator = FileLocationValidator(project_root)

    # Run all checks
    doc_errors = validator.check_documentation_files()
    script_errors = validator.check_script_files()
    test_errors = validator.check_test_files_location()
    temp_warnings = validator.check_temporary_files()

    all_errors = doc_errors + script_errors + test_errors

    # Report errors
    if doc_errors:
        print("[DOCUMENTATION FILES]")
        for error in doc_errors:
            print(f"  ERROR: {error}")
        print()

    if script_errors:
        print("[SCRIPT FILES]")
        for error in script_errors:
            print(f"  ERROR: {error}")
        print()

    if test_errors:
        print("[TEST FILES]")
        for error in test_errors:
            print(f"  ERROR: {error}")
        print()

    if temp_warnings:
        print("[TEMPORARY FILES]")
        for warning in temp_warnings:
            print(f"  WARNING: {warning}")
        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Errors: {len(all_errors)}")
    print(f"Warnings: {len(temp_warnings)}")

    if all_errors:
        print("\n[FAILED] Fix file location violations before committing")
        print("\nOrganization Rules:")
        print("1. Documentation: Only README.md & PROJECT_MEMORY.md in root, all else in docs/")
        print("2. Scripts: All .py scripts must be in scripts/ folder")
        print("3. Tests: test_*.py files must be in tests/ or scripts/")
        print("4. Temporary files: Add to .gitignore or move to data/temp/")
        sys.exit(1)
    elif temp_warnings and args.strict:
        print("\n[FAILED] Warnings treated as errors (--strict mode)")
        sys.exit(1)
    else:
        if temp_warnings:
            print("\n[WARNING] Review temporary files")
        else:
            print("\n[SUCCESS] All files properly organized")
        sys.exit(0)


if __name__ == "__main__":
    main()
