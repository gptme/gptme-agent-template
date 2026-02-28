#!/usr/bin/env python3
"""
Detect non-symlinked scripts/files in agent workspaces that should be symlinks to gptme-contrib.

Usage:
    scripts/check-symlinks.py [<agent-dir>] [--contrib-dir <path>] [--verbose]

Two checks:
  1. Hash match:  Agent file is a verbatim copy of a contrib file (should be a symlink).
  2. Name match:  Agent file has the same name as a contrib file but different content
                  (likely drifted — should be consolidated in contrib and symlinked).

Exit codes:
    0 - Clean: no issues found
    1 - Issues detected: found copies or name collisions
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


def is_script_file(path: Path) -> bool:
    """Check if a file is a script (.sh, .py, or executable)."""
    return (
        path.name.endswith(".sh")
        or path.name.endswith(".py")
        or os.access(path, os.X_OK)
    )


SKIP_DIRS = {".git", "__pycache__", ".venv", ".mypy_cache", "node_modules"}


def build_contrib_index(
    contrib_dir: Path, verbose: bool = False
) -> tuple[dict[str, Path], dict[str, list[Path]]]:
    """
    Build two indexes of gptme-contrib:
      1. hash_index:  SHA-256 hash → contrib path  (for exact-copy detection)
      2. name_index:  filename → [contrib paths]    (for name-collision detection)
    """
    hash_index: dict[str, Path] = {}
    name_index: dict[str, list[Path]] = {}

    for root, dirs, files in os.walk(contrib_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        root_path = Path(root)
        for fname in files:
            fpath = root_path / fname
            if fpath.is_symlink():
                continue
            if not is_script_file(fpath):
                continue
            try:
                h = hash_file(fpath)
                hash_index[h] = fpath
                name_index.setdefault(fname, []).append(fpath)
            except (OSError, PermissionError):
                pass

    if verbose:
        print(
            f"  Indexed {len(hash_index)} script files, {len(name_index)} unique names"
        )
    return hash_index, name_index


def check_agent_dir(
    agent_dir: Path,
    contrib_dir: Path,
    check_dirs: list[str],
    verbose: bool = False,
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, list[Path]]]]:
    """
    Find script files in agent_dir that overlap with gptme-contrib.

    Returns:
      - exact_copies: (agent_path, contrib_path) — verbatim copies
      - name_collisions: (agent_path, [contrib_paths]) — same name, different content
    """
    if not contrib_dir.exists():
        print(f"WARNING: gptme-contrib not found at {contrib_dir}", file=sys.stderr)
        print("  Run: git submodule update --init gptme-contrib", file=sys.stderr)
        return [], []

    if verbose:
        print(f"Building index of {contrib_dir}...")
    hash_index, name_index = build_contrib_index(contrib_dir, verbose)

    exact_copies: list[tuple[Path, Path]] = []
    name_collisions: list[tuple[Path, list[Path]]] = []

    for check_dir_name in check_dirs:
        check_path = agent_dir / check_dir_name
        if not check_path.exists():
            continue

        for root, dirs, files in os.walk(check_path):
            root_path = Path(root)

            # Symlinked directories are correct — skip
            if root_path.is_symlink():
                dirs.clear()
                if verbose:
                    rel = root_path.relative_to(agent_dir)
                    print(f"  OK (dir symlink): {rel}/")
                continue

            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in files:
                fpath = root_path / fname

                # Symlinks are correct — skip
                if fpath.is_symlink():
                    if verbose:
                        rel = fpath.relative_to(agent_dir)
                        target = os.readlink(fpath)
                        print(f"  OK (symlink): {rel} -> {target}")
                    continue

                if not is_script_file(fpath):
                    continue

                rel_str = str(fpath.relative_to(agent_dir))

                try:
                    h = hash_file(fpath)
                except (OSError, PermissionError):
                    continue

                # Check 1: exact hash match (verbatim copy)
                if h in hash_index:
                    contrib_path = hash_index[h]
                    exact_copies.append((fpath, contrib_path))
                    if verbose:
                        print(f"  COPY: {rel_str}")
                        print(
                            f"        (same as {contrib_path.relative_to(contrib_dir)})"
                        )
                # Check 2: same filename, different content (drifted)
                elif fname in name_index:
                    contrib_paths = name_index[fname]
                    name_collisions.append((fpath, contrib_paths))
                    if verbose:
                        print(f"  DRIFT: {rel_str}")
                        for cp in contrib_paths:
                            print(
                                f"         (same name as {cp.relative_to(contrib_dir)})"
                            )

    return exact_copies, name_collisions


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
        help="Show all files checked, not just issues",
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

    exact_copies, name_collisions = check_agent_dir(
        agent_dir, contrib_dir, args.check_dirs, verbose=args.verbose
    )

    issues = False

    if exact_copies:
        issues = True
        print(
            f"✗ Found {len(exact_copies)} verbatim copy(s) that should be symlinks:\n"
        )
        for agent_path, contrib_path in sorted(exact_copies):
            rel_agent = agent_path.relative_to(agent_dir)
            rel_contrib = contrib_path.relative_to(contrib_dir)
            print(f"  {rel_agent}")
            print(f"    → same content as: gptme-contrib/{rel_contrib}")
            target = os.path.relpath(contrib_path, agent_path.parent)
            print(f"    → fix: ln -sf {target} {agent_path.name}")
            print()

    if name_collisions:
        issues = True
        print(
            f"⚠ Found {len(name_collisions)} script(s) sharing names with contrib "
            f"(possible drift):\n"
        )
        for agent_path, contrib_paths in sorted(name_collisions):
            rel_agent = agent_path.relative_to(agent_dir)
            print(f"  {rel_agent}")
            for cp in contrib_paths:
                rel_contrib = cp.relative_to(contrib_dir)
                print(f"    → same name as: gptme-contrib/{rel_contrib}")
            print(
                "    → Action: consolidate into contrib and replace with symlink, "
                "or verify this is intentionally agent-specific."
            )
            print()

    if not issues:
        print("✓ No issues — all shared scripts are properly symlinked.")
        return 0

    # Exact copies are errors (exit 1), name collisions are warnings (exit 0)
    if exact_copies:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
