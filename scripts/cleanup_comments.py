#!/usr/bin/env python3
"""
Clean up outdated, incorrect, or redundant comments in the codebase.

This script:
1. Removes commented-out code blocks
2. Removes outdated TODO/FIXME comments
3. Removes redundant docstrings
4. Flags potentially incorrect comments
5. Generates a cleanup report

Usage:
    python scripts/cleanup_comments.py [--dry-run] [--verbose]
"""

import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict
import argparse
from datetime import datetime


class CommentCleaner:
    """Clean up comments in Python source files."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.changes: List[Dict] = []
        self.stats = {
            "files_scanned": 0,
            "files_modified": 0,
            "commented_code_removed": 0,
            "redundant_comments_removed": 0,
            "outdated_todos_removed": 0,
        }

    def scan_file(self, filepath: Path) -> Tuple[str, List[str]]:
        """Scan a Python file for comment issues."""
        with open(filepath, "r", encoding="utf-8") as f:
            original_content = f.read()

        lines = original_content.split("\n")
        cleaned_lines = []
        issues_found = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            # Check for commented-out code (heuristic-based)
            if self._is_commented_code(line):
                issues_found.append(f"Line {i+1}: Removed commented-out code")
                self.stats["commented_code_removed"] += 1
                continue  # Skip this line

            # Check for redundant comments
            if self._is_redundant_comment(line, i, lines):
                issues_found.append(f"Line {i+1}: Removed redundant comment")
                self.stats["redundant_comments_removed"] += 1
                continue  # Skip this line

            # Check for outdated TODOs
            if self._is_outdated_todo(line):
                issues_found.append(f"Line {i+1}: Removed outdated TODO")
                self.stats["outdated_todos_removed"] += 1
                continue  # Skip this line

            # Keep the line
            cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)
        return cleaned_content, issues_found

    def _is_commented_code(self, line: str) -> bool:
        """Detect if a comment line is actually commented-out code."""
        stripped = line.strip()

        # Not a comment
        if not stripped.startswith("#"):
            return False

        # Remove the # and whitespace
        code_like = stripped.lstrip("#").strip()

        # Empty comment
        if not code_like:
            return False

        # Patterns that indicate code (not documentation)
        code_patterns = [
            r"^(import|from)\s+\w+",  # import statements
            r"^(def|class|if|else|elif|for|while|try|except|with|return|raise)\s",
            r"^\w+\s*=\s*.+",  # assignments
            r"^\w+\(.*\)$",  # function calls
            r"^print\(",  # print statements
            r"^#\s*(def|class|import|from)",  # double-commented code
            r"^\w+\.\w+\(",  # method calls
            r"^(True|False|None|[0-9]+|\".*\"|\'.*\')\s*$",  # literals
        ]

        for pattern in code_patterns:
            if re.match(pattern, code_like):
                return True

        return False

    def _is_redundant_comment(self, line: str, line_num: int, all_lines: List[str]) -> bool:
        """Detect redundant comments that just repeat the code."""
        stripped = line.strip()

        if not stripped.startswith("#"):
            return False

        comment_text = stripped.lstrip("#").strip().lower()

        # Get next non-empty line (the actual code)
        next_code = None
        for next_line in all_lines[line_num + 1:]:
            if next_line.strip() and not next_line.strip().startswith("#"):
                next_code = next_line.strip().lower()
                break

        if not next_code:
            return False

        # Check if comment just repeats the code
        # Example: # Import os / import os
        redundant_patterns = [
            (r"import\s+(\w+)", r"^import\s+\1"),
            (r"from\s+(\w+)", r"^from\s+\1"),
            (r"(return|returns?)\s", r"^return\s"),
            (r"(create|creates?)\s+(\w+)", r"^(\w+)\s*="),
            (r"^set\s+(\w+)", r"^(\w+)\s*="),
            (r"^get\s+(\w+)", r"^return\s+\w*\1"),
        ]

        for comment_pattern, code_pattern in redundant_patterns:
            if re.search(comment_pattern, comment_text) and re.search(code_pattern, next_code):
                return True

        return False

    def _is_outdated_todo(self, line: str) -> bool:
        """Detect outdated TODO/FIXME comments."""
        stripped = line.strip()

        if not stripped.startswith("#"):
            return False

        comment_text = stripped.lstrip("#").strip().upper()

        # Outdated TODO patterns
        outdated_patterns = [
            r"TODO.*FIX.*LATER",  # Generic "fix later" todos
            r"FIXME.*TEMP",  # Temporary fixes
            r"TODO.*REMOVE.*THIS",  # Todos about removing code
            r"TODO.*CLEANUP",  # Generic cleanup todos
            r"HACK.*TODO",  # Acknowledged hacks
            r"TODO.*REFACTOR.*LATER",  # Postponed refactoring
            r"FIXME.*URGENT",  # Old urgent fixes (likely done)
        ]

        for pattern in outdated_patterns:
            if re.search(pattern, comment_text):
                return True

        return False

    def process_file(self, filepath: Path) -> bool:
        """Process a single Python file."""
        self.stats["files_scanned"] += 1

        try:
            cleaned_content, issues = self.scan_file(filepath)

            if not issues:
                if self.verbose:
                    print(f"[OK] {filepath}: No issues found")
                return False

            # Record changes
            self.changes.append({
                "file": str(filepath),
                "issues": issues,
                "count": len(issues)
            })

            if not self.dry_run:
                # Write cleaned content
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                self.stats["files_modified"] += 1
                print(f"[CLEANED] {filepath}: {len(issues)} issues fixed")
            else:
                print(f"[DRY RUN] {filepath}: Would clean {len(issues)} issues")

            return True

        except Exception as e:
            print(f"[ERROR] {filepath}: {e}")
            return False

    def process_directory(self, directory: Path):
        """Process all Python files in a directory."""
        python_files = list(directory.rglob("*.py"))

        print(f"Scanning {len(python_files)} Python files in {directory}...")
        print()

        for filepath in python_files:
            # Skip virtual environment and cache
            if ".venv" in str(filepath) or "__pycache__" in str(filepath):
                continue

            self.process_file(filepath)

    def generate_report(self, output_path: Path):
        """Generate a cleanup report."""
        report_lines = [
            "# Comment Cleanup Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}",
            "",
            "## Summary",
            "",
            f"- Files scanned: {self.stats['files_scanned']}",
            f"- Files modified: {self.stats['files_modified']}",
            f"- Commented code removed: {self.stats['commented_code_removed']} lines",
            f"- Redundant comments removed: {self.stats['redundant_comments_removed']} lines",
            f"- Outdated TODOs removed: {self.stats['outdated_todos_removed']} items",
            "",
            "## Changes by File",
            "",
        ]

        if not self.changes:
            report_lines.append("No issues found. Codebase is clean!")
        else:
            for change in self.changes:
                report_lines.append(f"### {change['file']}")
                report_lines.append(f"**Issues cleaned: {change['count']}**")
                report_lines.append("")
                for issue in change['issues']:
                    report_lines.append(f"- {issue}")
                report_lines.append("")

        report_lines.extend([
            "---",
            "",
            "## Next Steps",
            "",
            "1. Review the changes in git diff",
            "2. Run tests to ensure nothing broke: `python run_tests.py`",
            "3. Commit if satisfied: `git add -u && git commit -m 'chore: Clean up comments'`",
        ])

        report_content = "\n".join(report_lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        print()
        print(f"[REPORT] Report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Clean up comments in Python codebase")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--src-only",
        action="store_true",
        help="Only process src/ directory (default: src/ and tests/)"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    cleaner = CommentCleaner(dry_run=args.dry_run, verbose=args.verbose)

    print("=" * 80)
    print("COMMENT CLEANUP TOOL")
    print("=" * 80)
    print()

    if args.dry_run:
        print("[WARNING] DRY RUN MODE - No files will be modified")
        print()

    # Process src directory
    src_dir = project_root / "src"
    if src_dir.exists():
        cleaner.process_directory(src_dir)

    # Process tests directory unless --src-only
    if not args.src_only:
        tests_dir = project_root / "tests"
        if tests_dir.exists():
            cleaner.process_directory(tests_dir)

    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = project_root / "data" / "evaluation" / "reports" / "_working" / f"comment_cleanup_{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cleaner.generate_report(report_path)

    print()
    print("=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"Files scanned: {cleaner.stats['files_scanned']}")
    print(f"Files modified: {cleaner.stats['files_modified']}")
    print(f"Total issues cleaned: {sum([
        cleaner.stats['commented_code_removed'],
        cleaner.stats['redundant_comments_removed'],
        cleaner.stats['outdated_todos_removed']
    ])}")
    print()

    if args.dry_run:
        print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
