#!/usr/bin/env python3
"""
Python wrapper for the fork.sh script.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fork a gptme agent workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s alice-agent Alice
  %(prog)s /path/to/bob-agent Bob
  %(prog)s ./charlie-agent
        """,
    )
    parser.add_argument("target_dir", help="Target directory for new agent workspace")
    parser.add_argument(
        "agent_name", nargs="?", help="Name of the new agent (optional)"
    )
    dotfiles_group = parser.add_mutually_exclusive_group()
    dotfiles_group.add_argument(
        "--dotfiles",
        "--with-dotfiles",
        dest="dotfiles",
        action="store_true",
        default=True,
        help="Include dotfiles / global git hooks (default)",
    )
    dotfiles_group.add_argument(
        "--no-dotfiles",
        "--without-dotfiles",
        dest="dotfiles",
        action="store_false",
        help="Exclude dotfiles / global git hooks",
    )

    args = parser.parse_args()

    # Get the fork.sh script path (same directory as this wrapper)
    script_dir = Path(__file__).parent
    fork_script = script_dir / "fork.sh"

    if not fork_script.exists():
        print(f"Error: fork.sh not found at {fork_script}")
        return 1

    # Build command
    cmd = [str(fork_script)]
    if not args.dotfiles:
        cmd.append("--no-dotfiles")
    cmd.append(args.target_dir)
    if args.agent_name:
        cmd.append(args.agent_name)

    # Execute the bash script
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error: fork.sh failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print(f"Error: Could not execute {fork_script}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
