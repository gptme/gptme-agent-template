#!/usr/bin/env python3
"""Reject new top-level files/dirs that are not in the allowlist YAML file.

Uses git index (not filesystem) to identify top-level entries, reads the
allowlist from root-structure-allowlist.yaml, and validates against it.

This generalized version allows each repo to own its allowlist in a data file
rather than hardcoding entries. See Phase 2.2 of gptme/gptme-contrib#1445.

Usage:
    python3 scripts/precommit/validators/validate_root_structure_yaml.py [--config root-structure-allowlist.yaml]
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def load_allowlist(config_path: Path) -> set[str]:
    """Load allowed entries from YAML config file."""
    if not config_path.exists():
        print(f"validate-root-structure: config file not found: {config_path}")
        print("Create root-structure-allowlist.yaml at the repo root with:")
        print("  allowed:")
        print("    - file1.txt")
        print("    - dir1/")
        return set()

    try:
        with open(config_path) as f:
            data: Any = yaml.safe_load(f) or {}
        allowed: list[str] = data.get("allowed", [])
        return set(allowed)
    except Exception as e:
        print(f"validate-root-structure: failed to load config: {e}")
        return set()


def tracked_root_entries() -> set[str]:
    """Top-level components of every path in the git index."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {path.split("/", 1)[0] for path in result.stdout.split("\0") if path}
    except subprocess.CalledProcessError as e:
        print(f"validate-root-structure: git ls-files failed: {e}")
        return set()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate root directory structure against allowlist"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("root-structure-allowlist.yaml"),
        help="Path to root-structure-allowlist.yaml (default: root-structure-allowlist.yaml)",
    )
    args = parser.parse_args()

    allowed = load_allowlist(args.config)
    if not allowed:
        return 1

    tracked = tracked_root_entries()
    unexpected = tracked - allowed

    if not unexpected:
        return 0

    print("validate-root-structure: unexpected top-level entries:")
    for name in sorted(unexpected):
        print(f"  {name}")
    print()
    print(
        "Root sprawl is how a workspace rots. Either move it under an existing\n"
        "top-level dir, or — if it genuinely belongs at the root — add it to the\n"
        "'allowed' list in root-structure-allowlist.yaml and explain why in\n"
        "the commit message."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
