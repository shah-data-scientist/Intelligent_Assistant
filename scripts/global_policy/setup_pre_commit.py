#!/usr/bin/env python3
"""
FILE: setup_pre_commit.py
STATUS: Active
RESPONSIBILITY: Project-independent installer for pre-commit hooks enforcing GLOBAL_POLICY.md standards.

DEPENDENCIES (Who uses this file):
- Any Python project adopting GLOBAL_POLICY.md standards
- Developers during initial project setup

IMPORTS (What this file needs):
- subprocess: Execute shell commands for pre-commit installation
- pathlib: Check for .pre-commit-config.yaml existence
- sys: Exit codes and arguments
- argparse: Command-line argument parsing

LAST MAJOR UPDATE: 2026-01-30 (Made project-independent)
MAINTAINER: Infrastructure Team
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str, cwd: Path | None = None) -> bool:
    """Execute a command and report success/failure.

    Args:
        cmd: Command and arguments to execute
        description: Human-readable description of the command
        cwd: Working directory for command execution

    Returns:
        True if command succeeded, False otherwise
    """
    print(f"\n[RUNNING] {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
        print(f"[SUCCESS] {description}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAILED] {description}")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"[FAILED] {description} - Command not found")
        return False


def main():
    """Install and configure pre-commit hooks."""
    parser = argparse.ArgumentParser(description="Setup pre-commit hooks for GLOBAL_POLICY.md enforcement")
    parser.add_argument(
        "--project-root", type=str, default=None, help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--skip-install-package",
        action="store_true",
        help="Skip installing pre-commit package (assume already installed)",
    )

    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path.cwd()

    print("=" * 60)
    print("Pre-Commit Hooks Setup")
    print("=" * 60)
    print(f"Project root: {project_root}")

    # Check if .pre-commit-config.yaml exists
    config_file = project_root / ".pre-commit-config.yaml"
    if not config_file.exists():
        print("\n[ERROR] .pre-commit-config.yaml not found")
        print(f"Expected location: {config_file}")
        print("\nCreate a .pre-commit-config.yaml file first, or run from the correct directory")
        sys.exit(1)

    print("\n[INFO] Found .pre-commit-config.yaml")

    # Install pre-commit package
    if not args.skip_install_package:
        # Try poetry first
        if (project_root / "pyproject.toml").exists():
            print("\n[INFO] Detected pyproject.toml, using Poetry...")
            if not run_command(
                ["poetry", "add", "--group", "dev", "pre-commit"],
                "Installing pre-commit package via Poetry",
                cwd=project_root,
            ):
                print("\n[WARN] Failed to install via Poetry, trying pip...")
                if not run_command(
                    ["pip", "install", "pre-commit"], "Installing pre-commit package via pip", cwd=project_root
                ):
                    print("\n[ERROR] Failed to install pre-commit")
                    sys.exit(1)
        else:
            # Use pip
            if not run_command(
                ["pip", "install", "pre-commit"], "Installing pre-commit package via pip", cwd=project_root
            ):
                print("\n[ERROR] Failed to install pre-commit")
                sys.exit(1)
    else:
        print("\n[INFO] Skipping package installation (--skip-install-package)")

    # Install pre-commit hooks
    if not run_command(["pre-commit", "install"], "Installing pre-commit hooks to .git/hooks", cwd=project_root):
        print("\n[ERROR] Failed to install pre-commit hooks")
        sys.exit(1)

    # Run hooks on all files to verify setup
    print("\n" + "=" * 60)
    print("Testing hooks on all files (this may take a minute)...")
    print("=" * 60)

    run_command(["pre-commit", "run", "--all-files"], "Running all hooks on existing files", cwd=project_root)
    # Note: This may fail on first run if files need formatting
    # That's OK - the hooks will auto-fix on next commit

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nPre-commit hooks are now active. They will run automatically on:")
    print("  - Every git commit")
    print("  - File documentation validation (mandatory)")
    print("  - Code formatting (black, ruff)")
    print("  - Security checks (bandit, detect-secrets)")
    print("  - File hygiene (trailing whitespace, etc.)")
    print("\nTo run hooks manually:")
    print("  pre-commit run --all-files")
    print("\nTo bypass hooks (NOT RECOMMENDED):")
    print("  git commit --no-verify")


if __name__ == "__main__":
    main()
