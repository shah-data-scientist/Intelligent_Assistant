#!/usr/bin/env python3
"""
Automated Test Runner for Cultural Events RAG Assistant

This script runs all unit tests, generates coverage reports, and produces
a comprehensive summary with metrics.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Skip slow tests
    python run_tests.py --module data      # Run specific module
    python run_tests.py --html             # Generate HTML coverage report
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import argparse


class TestRunner:
    """Automated test runner with comprehensive reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run_tests(
        self, quick: bool = False, module: Optional[str] = None, html_report: bool = False, verbose: bool = True
    ) -> Dict:
        """
        Run pytest with coverage and generate reports.

        Args:
            quick: Skip slow integration tests
            module: Specific module to test (e.g., 'data', 'retrieval')
            html_report: Generate HTML coverage report
            verbose: Show detailed test output

        Returns:
            Dict with test results and metrics
        """
        print("=" * 80)
        print("CULTURAL EVENTS RAG ASSISTANT - AUTOMATED TEST SUITE")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Root: {self.project_root}")
        print()

        # Build pytest command
        cmd = [
            "poetry",
            "run",
            "pytest",
            str(self.test_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--cov=src",
            "--cov-report=term-missing",
            f"--cov-report=json:{self.reports_dir / 'coverage.json'}",
        ]

        if html_report:
            cmd.append(f"--cov-report=html:{self.reports_dir / 'htmlcov'}")

        if quick:
            cmd.extend(["-m", "not slow"])
            print("⚡ Quick mode: Skipping slow integration tests")

        if module:
            test_pattern = f"test_{module}*.py"
            cmd.append("-k")
            cmd.append(test_pattern)
            print(f"🎯 Testing specific module: {module}")

        print()
        print("Running command:")
        print(" ".join(cmd))
        print()
        print("-" * 80)

        # Run tests
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=False, text=True)
        elapsed = time.time() - start_time

        print("-" * 80)
        print()

        # Parse results
        test_results = {
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
            "command": " ".join(cmd),
        }

        # Load coverage data if available
        coverage_file = self.reports_dir / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)
                test_results["coverage"] = {
                    "percent": round(coverage_data["totals"]["percent_covered"], 2),
                    "lines_covered": coverage_data["totals"]["covered_lines"],
                    "lines_total": coverage_data["totals"]["num_statements"],
                    "missing_lines": coverage_data["totals"]["missing_lines"],
                }

        return test_results

    def generate_summary(self, test_results: Dict) -> str:
        """Generate human-readable test summary."""
        summary_lines = []

        summary_lines.append("=" * 80)
        summary_lines.append("TEST SUMMARY")
        summary_lines.append("=" * 80)
        summary_lines.append("")

        # Overall result
        if test_results["success"]:
            summary_lines.append("✅ OVERALL RESULT: ALL TESTS PASSED")
        else:
            summary_lines.append("❌ OVERALL RESULT: SOME TESTS FAILED")

        summary_lines.append(f"⏱️  Execution Time: {test_results['elapsed_seconds']}s")
        summary_lines.append("")

        # Coverage metrics
        if "coverage" in test_results:
            cov = test_results["coverage"]
            summary_lines.append("📊 CODE COVERAGE:")
            summary_lines.append(f"  Overall: {cov['percent']}%")
            summary_lines.append(f"  Lines Covered: {cov['lines_covered']} / {cov['lines_total']}")
            summary_lines.append(f"  Missing Lines: {cov['missing_lines']}")

            # Coverage quality assessment
            if cov["percent"] >= 90:
                summary_lines.append("  ✅ Excellent coverage (≥90%)")
            elif cov["percent"] >= 80:
                summary_lines.append("  ✅ Good coverage (≥80%)")
            elif cov["percent"] >= 70:
                summary_lines.append("  ⚠️  Acceptable coverage (≥70%)")
            else:
                summary_lines.append("  ❌ Low coverage (<70%)")

        summary_lines.append("")
        summary_lines.append("=" * 80)

        return "\n".join(summary_lines)

    def save_results(self, test_results: Dict, summary: str):
        """Save test results and summary to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        json_file = self.reports_dir / f"test_results_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(test_results, f, indent=2)
        print(f"📄 JSON results saved: {json_file}")

        # Save text summary
        summary_file = self.reports_dir / f"test_summary_{timestamp}.txt"
        with open(summary_file, "w") as f:
            f.write(summary)
        print(f"📄 Summary saved: {summary_file}")

        # Save as latest
        latest_json = self.reports_dir / "latest_results.json"
        latest_summary = self.reports_dir / "latest_summary.txt"

        with open(latest_json, "w") as f:
            json.dump(test_results, f, indent=2)

        with open(latest_summary, "w") as f:
            f.write(summary)

        print(f"📄 Latest results: {latest_json}")
        print(f"📄 Latest summary: {latest_summary}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run automated test suite for Cultural Events RAG Assistant")
    parser.add_argument("--quick", action="store_true", help="Skip slow integration tests")
    parser.add_argument("--module", type=str, help="Test specific module (e.g., 'data', 'retrieval', 'api')")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent

    # Run tests
    runner = TestRunner(project_root)
    results = runner.run_tests(quick=args.quick, module=args.module, html_report=args.html, verbose=not args.quiet)

    # Generate summary
    summary = runner.generate_summary(results)
    print()
    print(summary)
    print()

    # Save results
    runner.save_results(results, summary)

    # HTML coverage report info
    if args.html:
        html_index = runner.reports_dir / "htmlcov" / "index.html"
        if html_index.exists():
            print()
            print(f"🌐 HTML Coverage Report: file://{html_index.absolute()}")

    # Exit with test status
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
