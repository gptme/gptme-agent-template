#!/usr/bin/env python3
"""Assert a created agent workspace kept the template's prompt configuration.

``gptme-agent create`` customizes the template's ``gptme.toml``. The 2026-10-26
walkthrough found it rewriting the file and dropping the ``[prompt]`` table,
which silently disabled every auto-include and the dynamic context command
(gptme/gptme#4498).

``gptme-agent doctor`` does warn about that — but its printer emits only the
check *message* and never the check name, so CI cannot grep for
``"Context command: not configured"``: that string appears nowhere. Grepping
doctor's prose is fragile in both directions (it can go dead when a message is
reworded). This asserts the config structure directly, which does not depend on
doctor's output evolving.

Usage:
    tests/check_onboarding_config.py <workspace-dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    sys.exit("::error:: this check needs Python 3.11+ (tomllib)")


def check_workspace(workspace: Path) -> list[str]:
    """Return a list of problems with the workspace's prompt configuration."""
    toml_path = workspace / "gptme.toml"
    if not toml_path.is_file():
        return [f"{toml_path} does not exist"]

    config = tomllib.loads(toml_path.read_text())
    prompt = config.get("prompt")
    if not isinstance(prompt, dict):
        # The template ships a [prompt] table. A missing table means `create`
        # rewrote the file into the legacy flat form or dropped the section
        # entirely; either way the template contract did not survive.
        return ["gptme.toml has no [prompt] table — prompt auto-includes will not work"]

    problems = []
    files = prompt.get("files")
    if not isinstance(files, list) or not files:
        problems.append(
            "[prompt].files is missing or empty — no files are auto-included"
        )
    context_cmd = prompt.get("context_cmd")
    if not isinstance(context_cmd, str) or not context_cmd.strip():
        problems.append("[prompt].context_cmd is missing or empty — no dynamic context")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="created agent workspace to check")
    args = parser.parse_args(argv)

    problems = check_workspace(args.workspace)
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        return 1
    print(
        f"OK: {args.workspace}/gptme.toml keeps [prompt].files and [prompt].context_cmd"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
