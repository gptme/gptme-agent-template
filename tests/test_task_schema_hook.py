"""Run the template's actual task hook against every canonical gptodo state."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRIB = ROOT / "gptme-contrib"


def test_task_hook_uses_one_schema_and_staged_files(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"].startswith("validate-task-")
    ]
    assert (
        len(hooks) == 1
    ), "Do not duplicate gptodo's schema or scan the whole workspace"
    hook = hooks[0]
    assert hook["pass_filenames"] is True
    assert hook["language"] == "system"
    assert shlex.split(hook["entry"])[-2:] == ["gptodo", "lint"]
    for filename in ("tasks/probe.md", "tasks/archive/probe.md"):
        assert re.search(hook["files"], filename)
    for filename in ("tasks/templates/probe.md", "tasks/video-scripts/probe.md"):
        assert re.search(hook["exclude"], filename)

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "gptme-contrib").symlink_to(CONTRIB, target_is_directory=True)
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    # Read the states from the exact package the hook installs, not a copied list.
    result = subprocess.run(
        [
            "python3",
            "-c",
            "from gptodo.utils import get_canonical_states; print(' '.join(get_canonical_states()))",
        ],
        env={**os.environ, "PYTHONPATH": str(CONTRIB / "packages/gptodo/src")},
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for state in result.stdout.split():
        path = tasks / f"{state}.md"
        path.write_text(f"---\nstate: {state}\ncreated: 2026-11-13\n---\n# Task\n")
        files.append(str(path.relative_to(tmp_path)))
    # An unrelated invalid task must not block this staged-file invocation.
    (tasks / "unstaged.md").write_text("---\nstate: bogus\n---\n")
    command = shlex.split(hook["entry"])
    result = subprocess.run(
        command + files, cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{len(files)} task(s)" in result.stdout

    bad = tasks / "bad.md"
    for content in ("---\nstate: bogus\n---\n", "---\nstate: [broken\n---\n"):
        bad.write_text(content)
        result = subprocess.run(
            command + ["tasks/bad.md"], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert "schema error" in result.stdout
