#!/usr/bin/env python3
"""
Detect non-symlinked scripts/files in agent workspaces that should be symlinks to gptme-contrib.

Usage:
    scripts/check-symlinks.py [<agent-dir>] [--contrib-dir <path>] [--verbose]

When a file in the agent workspace is a verbatim copy of a file in gptme-contrib,
it should instead be a symlink — copies drift and won't receive upstream updates.

Exit codes:
    0 - Clean: all shared files are properly symlinked
    1 - Drift detected: found verbatim copies that should be symlinks
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_contrib_index(contrib_dir: Path) -> dict[str, Path]:
    """Build a hash → path mapping for all files in gptme-contrib."""
    index: dict[str, Path] = {}
    for root, dirs, files in os.walk(contrib_dir):
        # Skip .git internals
        dirs[:] = [
            d for d in dirs if d not in {".git", "__pycache__", ".venv", ".mypy_cache"}
        ]
        root_path = Path(root)
        for fname in files:
            fpath = root_path / fname
            if fpath.is_symlink():
                continue  # Skip symlinks within contrib
            try:
                h = hash_file(fpath)
                index[h] = fpath
            except (OSError, PermissionError):
                pass
    return index


def check_agent_dir(
    agent_dir: Path,
    contrib_dir: Path,
    check_dirs: list[str],
    verbose: bool = False,
) -> list[tuple[Path, Path]]:
    """
    Find regular files in agent_dir that are verbatim copies of gptme-contrib files.

    Returns list of (agent_path, contrib_path) pairs indicating drift.
    """
    if not contrib_dir.exists():
        print(f"WARNING: gptme-contrib not found at {contrib_dir}", file=sys.stderr)
        print("  Run: git submodule update --init gptme-contrib", file=sys.stderr)
        return []

    if verbose:
        print(f"Building index of {contrib_dir}...")
    contrib_index = build_contrib_index(contrib_dir)
    if verbose:
        print(f"  Indexed {len(contrib_index)} contrib files")

    drift: list[tuple[Path, Path]] = []

    for check_dir_name in check_dirs:
        check_path = agent_dir / check_dir_name
        if not check_path.exists():
            continue

        for root, dirs, files in os.walk(check_path):
            root_path = Path(root)

            # If the directory itself is a symlink to contrib, it's correct — skip entirely
            if root_path.is_symlink():
                dirs.clear()  # Don't descend into symlinked dirs
                if verbose:
                    rel = root_path.relative_to(agent_dir)
                    print(f"  OK (dir symlink): {rel}/")
                continue

            dirs[:] = [
                d for d in dirs if d not in {"__pycache__", ".venv", ".mypy_cache"}
            ]

            for fname in files:
                fpath = root_path / fname

                # Symlinks are correct — skip
                if fpath.is_symlink():
                    if verbose:
                        rel = fpath.relative_to(agent_dir)
                        target = os.readlink(fpath)
                        print(f"  OK (symlink): {rel} -> {target}")
                    continue

                # Skip non-executable text files in a few noisy dirs
                rel_path = fpath.relative_to(agent_dir)
                rel_str = str(rel_path)

                # Only flag script-like files: .sh, .py, or files with execute bit
                is_script = (
                    fname.endswith(".sh")
                    or fname.endswith(".py")
                    or os.access(fpath, os.X_OK)
                )
                if not is_script:
                    continue

                try:
                    h = hash_file(fpath)
                except (OSError, PermissionError):
                    continue

                if h in contrib_index:
                    contrib_path = contrib_index[h]
                    drift.append((fpath, contrib_path))
                    if verbose:
                        print(f"  DRIFT: {rel_str}")
                        print(
                            f"         (same as {contrib_path.relative_to(contrib_dir)})"
                        )

    return drift


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect non-symlinked scripts in agent workspaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "agent_dir",
        nargs="?",
        default=".",
        help="Agent workspace directory to check (default: current directory)",
    )
    parser.add_argument(
        "--contrib-dir",
        default=None,
        help="Path to gptme-contrib (default: <agent-dir>/gptme-contrib)",
    )
    parser.add_argument(
        "--check-dirs",
        nargs="+",
        default=["scripts", "packages"],
        help="Directories to scan for drift (default: scripts packages)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all files checked, not just drift",
    )
    args = parser.parse_args()

    agent_dir = Path(args.agent_dir).resolve()
    if not agent_dir.is_dir():
        print(f"Error: {agent_dir} is not a directory", file=sys.stderr)
        return 2

    contrib_dir = (
        Path(args.contrib_dir).resolve()
        if args.contrib_dir
        else agent_dir / "gptme-contrib"
    )

    print(f"Checking agent: {agent_dir}")
    print(f"Contrib dir:    {contrib_dir}")
    print(f"Scanning:       {', '.join(args.check_dirs)}")
    print()

    drift = check_agent_dir(
        agent_dir, contrib_dir, args.check_dirs, verbose=args.verbose
    )

    if not drift:
        print("✓ No drift detected — all shared scripts are properly symlinked.")
        return 0

    print(f"✗ Found {len(drift)} file(s) that should be symlinks to gptme-contrib:\n")
    for agent_path, contrib_path in sorted(drift):
        rel_agent = agent_path.relative_to(agent_dir)
        rel_contrib = contrib_path.relative_to(contrib_dir)
        print(f"  {rel_agent}")
        print(f"    → should symlink to: gptme-contrib/{rel_contrib}")
        # Suggest the fix
        target = os.path.relpath(contrib_path, agent_path.parent)
        print(f"    → fix: ln -sf {target} {agent_path.name}")
        print()

    print("These files are verbatim copies of gptme-contrib files.")
    print("They should be symlinks so they receive upstream updates automatically.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
