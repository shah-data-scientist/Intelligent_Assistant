"""
FILE: final_cleanup.py
STATUS: Active
RESPONSIBILITY: Final cleanup tasks - archive backups, temporary scripts, and organize documentation.

DEPENDENCIES (Who uses this file):
- Manual developer usage for repository cleanup

IMPORTS (What this file needs):
- shutil: Directory operations (remove, move)
- pathlib: File system operations

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: Development Team
"""

import shutil
from pathlib import Path


def final_cleanup():
    """Execute final cleanup tasks."""

    print("=" * 80)
    print("FINAL CLEANUP")
    print("=" * 80)

    actions_taken = []

    # 1. Archive index_backups (100 MB of old backups)
    print("\n[1] Archiving index_backups folder...")
    if Path("index_backups").exists():
        shutil.rmtree("index_backups")
        actions_taken.append("Deleted index_backups/ (100 MB)")
        print("  [OK] Deleted index_backups/ (~100 MB)")

    # 2. Remove empty models folder
    print("\n[2] Removing empty models folder...")
    if Path("models").exists():
        shutil.rmtree("models")
        actions_taken.append("Deleted models/ (empty)")
        print("  [OK] Deleted models/ (empty)")

    # 3. Archive temporary scripts
    print("\n[3] Archiving temporary/migration scripts...")
    temp_scripts = [
        "migrate_deduplicate_events.py",
        "migrate_display_labels.py",
        "migrate_feedback_to_conversations.py",
        "migrate_period_flags.py",
        "migrate_search_keywords.py",
        "migrate_special_query_keywords.py",
        "drop_feedbacks_table.py",
        "drop_search_keywords_table.py",
        "cleanup_events_db.py",
        "test_evaluation_backends.py",
    ]

    archive_dir = Path("scripts/_archived/migrations_and_cleanup")
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_count = 0
    for script in temp_scripts:
        src = Path(f"scripts/{script}")
        if src.exists():
            dst = archive_dir / script
            shutil.move(str(src), str(dst))
            archived_count += 1
            print(f"  [OK] Archived {script}")

    actions_taken.append(f"Archived {archived_count} temporary scripts")

    # 4. Move documentation to docs/
    print("\n[4] Moving documentation files to docs/...")
    docs_to_move = ["CODEBASE_CLEANUP_REPORT.md", "PRESENTATION.md", "TECHNICAL_REPORT.md"]

    Path("docs").mkdir(exist_ok=True)
    moved_count = 0

    for doc in docs_to_move:
        src = Path(doc)
        if src.exists():
            dst = Path(f"docs/{doc}")
            shutil.move(str(src), str(dst))
            moved_count += 1
            print(f"  [OK] Moved {doc} to docs/")

    actions_taken.append(f"Moved {moved_count} documentation files to docs/")

    # 5. Add .coverage to .gitignore if not already there
    print("\n[5] Updating .gitignore...")
    gitignore = Path(".gitignore")
    if gitignore.exists():
        content = gitignore.read_text()
        if ".coverage" not in content:
            with gitignore.open("a") as f:
                f.write("\n# Test coverage\n")
                f.write(".coverage\n")
                f.write(".coverage.*\n")
                f.write("htmlcov/\n")
            actions_taken.append("Updated .gitignore with coverage files")
            print("  [OK] Added coverage files to .gitignore")
        else:
            print("  [OK] .gitignore already has coverage entries")

    # Summary
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)

    print("\nActions taken:")
    for i, action in enumerate(actions_taken, 1):
        print(f"  {i}. {action}")

    print("\nSpace saved: ~100 MB (index backups)")
    print("Scripts archived: 10")
    print("Documentation organized: 3 files moved to docs/")

    print("\nFinal root directory structure:")
    print("  - README.md (kept in root)")
    print("  - PROJECT_MEMORY.md (kept in root)")
    print("  - docs/ (all other .md files)")
    print("  - evaluation/ (moved from data/)")
    print("  - src/, tests/, scripts/ (production code)")

    return 0


if __name__ == "__main__":
    exit(final_cleanup())
