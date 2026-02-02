"""
FILE: smart_test_runner.py
STATUS: Active
RESPONSIBILITY: Build dependency graph via AST and run targeted tests for modified files.
LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Core Team
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class DependencyGraph(NamedTuple):
    """Dependency information for a file."""

    file_path: str
    imports: list[str]  # What this file imports (forward deps)
    imported_by: list[str]  # Who imports this file (reverse deps)
    tests: list[str]  # Test files for this file


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


def parse_imports(file_path: Path, project_root: Path) -> list[str]:
    """Parse a Python file and extract local project imports via AST."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    module_path = alias.name.replace(".", "/") + ".py"
                    imports.append(module_path)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src"):
                module_path = node.module.replace(".", "/") + ".py"
                full_path = project_root / module_path
                if not full_path.exists():
                    package_path = node.module.replace(".", "/") + "/__init__.py"
                    if (project_root / package_path).exists():
                        module_path = package_path
                imports.append(module_path)

    return list(set(imports))


def build_dependency_graph(project_root: Path) -> dict[str, DependencyGraph]:
    """Build complete dependency graph for all Python files via AST parsing."""
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"

    src_files = [f for f in src_dir.rglob("*.py") if "_archived" not in str(f)]
    test_files = [f for f in tests_dir.rglob("*.py") if "_archived" not in str(f)] if tests_dir.exists() else []

    # Build forward dependencies
    forward_deps: dict[str, list[str]] = {}
    for file_path in src_files + test_files:
        rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")
        forward_deps[rel_path] = parse_imports(file_path, project_root)

    # Build reverse dependencies
    reverse_deps: dict[str, list[str]] = {str(f.relative_to(project_root)).replace("\\", "/"): [] for f in src_files}

    for file_path, imports in forward_deps.items():
        for imported in imports:
            if imported in reverse_deps:
                reverse_deps[imported].append(file_path)

    # Find test files for each source file
    def find_tests(src_path: str) -> list[str]:
        tests = []
        src_name = Path(src_path).stem

        for test_file in test_files:
            test_rel = str(test_file.relative_to(project_root)).replace("\\", "/")
            test_name = test_file.stem

            # Match by naming convention
            if test_name == f"test_{src_name}" or test_name == f"{src_name}_test":
                tests.append(test_rel)
            # Match if test imports the source
            elif src_path in forward_deps.get(test_rel, []):
                tests.append(test_rel)

        return sorted(set(tests))

    # Build final graph
    graph: dict[str, DependencyGraph] = {}
    for file_path in src_files:
        rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")
        graph[rel_path] = DependencyGraph(
            file_path=rel_path,
            imports=forward_deps.get(rel_path, []),
            imported_by=sorted(reverse_deps.get(rel_path, [])),
            tests=find_tests(rel_path),
        )

    return graph


def get_staged_files(project_root: Path) -> list[str]:
    """Get list of staged Python files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    return [f for f in result.stdout.strip().split("\n") if f.endswith(".py") and f]


def get_modified_files(project_root: Path) -> list[str]:
    """Get list of modified (staged + unstaged) Python files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    return [f for f in result.stdout.strip().split("\n") if f.endswith(".py") and f]


def find_tests_for_files(modified_files: list[str], graph: dict[str, DependencyGraph]) -> list[str]:
    """Find all tests that should run for the modified files."""
    tests_to_run: set[str] = set()

    for mod_file in modified_files:
        mod_file = mod_file.replace("\\", "/")

        # If it's a test file itself, include it
        if mod_file.startswith("tests/"):
            tests_to_run.add(mod_file)
            continue

        # If it's a source file, find its tests
        if mod_file in graph:
            dep = graph[mod_file]

            # Direct tests for this file
            tests_to_run.update(dep.tests)

            # Tests for files that import this file (reverse deps)
            for importer in dep.imported_by:
                if importer.startswith("tests/"):
                    tests_to_run.add(importer)
                elif importer in graph:
                    tests_to_run.update(graph[importer].tests)

    return sorted(tests_to_run)


def run_tests(
    test_files: list[str], project_root: Path, coverage: bool = True, verbose: bool = True
) -> tuple[int, str]:
    """Run pytest on the specified test files."""
    if not test_files:
        return 0, "No tests to run"

    cmd = ["pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-fail-under=0"])

    cmd.extend(test_files)

    print(f"\n{'=' * 60}")
    print(f"Running {len(test_files)} test file(s):")
    for tf in test_files:
        print(f"  - {tf}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

    output = result.stdout + result.stderr
    return result.returncode, output


def print_graph(graph: dict[str, DependencyGraph], file_filter: str | None = None):
    """Print dependency graph in readable format."""
    import json

    if file_filter:
        filtered = {k: v for k, v in graph.items() if file_filter in k}
    else:
        filtered = graph

    graph_dict = {k: {"imported_by": v.imported_by, "tests": v.tests} for k, v in filtered.items()}
    print(json.dumps(graph_dict, indent=2))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Smart test runner - builds dependency graph and runs targeted tests")
    parser.add_argument("--staged", action="store_true", help="Only test staged files (for pre-commit)")
    parser.add_argument("--modified", action="store_true", help="Test all modified files (staged + unstaged)")
    parser.add_argument("--files", nargs="*", help="Specific files to find tests for")
    parser.add_argument("--show-graph", action="store_true", help="Print dependency graph as JSON")
    parser.add_argument("--filter", type=str, help="Filter graph output by path substring")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--dry-run", action="store_true", help="Show tests without running")
    args = parser.parse_args()

    project_root = get_project_root()
    print(f"Project root: {project_root}")
    print("Building dependency graph via AST...")

    graph = build_dependency_graph(project_root)
    print(f"Analyzed {len(graph)} source files")

    if args.show_graph:
        print_graph(graph, args.filter)
        return 0

    # Determine which files to analyze
    if args.staged:
        modified_files = get_staged_files(project_root)
        print(f"\nStaged files: {len(modified_files)}")
    elif args.modified:
        modified_files = get_modified_files(project_root)
        print(f"\nModified files: {len(modified_files)}")
    elif args.files:
        modified_files = args.files
        print(f"\nSpecified files: {len(modified_files)}")
    else:
        print("\nNo files specified. Use --staged, --modified, or --files")
        return 1

    if not modified_files or modified_files == [""]:
        print("No Python files to test")
        return 0

    for f in modified_files:
        print(f"  - {f}")

    # Find tests to run
    tests_to_run = find_tests_for_files(modified_files, graph)

    if not tests_to_run:
        print("\nNo tests found for modified files")
        return 0

    print(f"\nTests to run: {len(tests_to_run)}")

    if args.dry_run:
        print("\n[DRY RUN] Would run:")
        for t in tests_to_run:
            print(f"  - {t}")
        return 0

    # Run tests
    exit_code, output = run_tests(tests_to_run, project_root, coverage=not args.no_coverage)

    print(output)

    if exit_code != 0:
        print(f"\n{'=' * 60}")
        print("❌ TESTS FAILED")
        print(f"{'=' * 60}")
        print("\nOptions:")
        print("  [1] Fix the code to match expected behavior")
        print("  [2] Update tests if new behavior is intentional")
        print("  [3] Run with --dry-run to see test list")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print("✅ ALL TARGETED TESTS PASSED")
        print(f"{'=' * 60}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
