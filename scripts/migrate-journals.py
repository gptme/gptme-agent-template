#!/usr/bin/env python3
"""Migrate journal files from flat to subdirectory structure.

This script migrates journals from the legacy flat format:
    journal/2025-12-24-topic.md

To the new subdirectory format:
    journal/2025-12-24/topic.md

Usage:
    ./scripts/migrate-journals.py           # Dry run (shows what would happen)
    ./scripts/migrate-journals.py --execute # Actually perform migration
"""

import re
import shutil
import sys
from pathlib import Path


def find_workspace_root(start_path: Path) -> Path | None:
    """Find the workspace root by looking for identifying files."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / "gptme.toml").exists():
            return current
        if (current / ".git").exists() and (current / "journal").is_dir():
            return current
        current = current.parent
    return None


def migrate_journals(journal_dir: Path, dry_run: bool = True) -> tuple[int, int, int]:
    """Migrate flat journal files to date subdirectories.

    Args:
        journal_dir: Path to journal directory
        dry_run: If True, only print what would happen without moving files

    Returns:
        Tuple of (migrated, skipped, errors)
    """
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")

    migrated = 0
    skipped = 0
    errors = 0

    # Get all markdown files in the journal root (not in subdirectories)
    for file in sorted(journal_dir.glob("*.md")):
        if not file.is_file():
            continue

        match = pattern.match(file.name)
        if not match:
            print(f"Skipping (no date prefix): {file.name}")
            skipped += 1
            continue

        date_str, topic = match.groups()
        new_dir = journal_dir / date_str
        new_path = new_dir / f"{topic}.md"

        # Check if target already exists
        if new_path.exists():
            print(f"Skipping (target exists): {file.name} -> {date_str}/{topic}.md")
            skipped += 1
            continue

        if dry_run:
            print(f"Would move: {file.name} -> {date_str}/{topic}.md")
        else:
            try:
                new_dir.mkdir(exist_ok=True)
                shutil.move(str(file), str(new_path))
                print(f"Moved: {file.name} -> {date_str}/{topic}.md")
            except Exception as e:
                print(f"Error moving {file.name}: {e}")
                errors += 1
                continue

        migrated += 1

    return migrated, skipped, errors


def main() -> int:
    """Main entry point."""
    dry_run = "--execute" not in sys.argv

    # Find workspace root
    workspace = find_workspace_root(Path.cwd())
    if not workspace:
        print("Error: Could not find workspace root (gptme.toml or .git + journal/)")
        return 1

    journal_dir = workspace / "journal"
    if not journal_dir.is_dir():
        print(f"Error: Journal directory not found: {journal_dir}")
        return 1

    print(f"Workspace: {workspace}")
    print(f"Journal directory: {journal_dir}")
    print()

    if dry_run:
        print("=" * 60)
        print("DRY RUN - No files will be moved")
        print("Use --execute to actually perform the migration")
        print("=" * 60)
        print()

    migrated, skipped, errors = migrate_journals(journal_dir, dry_run)

    print()
    print("=" * 60)
    print("Summary:")
    print(f"  {'Would migrate' if dry_run else 'Migrated'}: {migrated} files")
    print(f"  Skipped: {skipped} files")
    if errors:
        print(f"  Errors: {errors} files")
    print("=" * 60)

    if dry_run and migrated > 0:
        print()
        print("To execute the migration, run:")
        print("  ./scripts/migrate-journals.py --execute")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
