"""Lesson hooks use the workspace venv when present, else python3 on PATH."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def _hook_commands(event):
    settings = json.loads((ROOT / ".claude/settings.json").read_text())
    return [
        hook["command"] for group in settings["hooks"][event] for hook in group["hooks"]
    ]


def _fake_python(path, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\nprintf "{label} %s\\n" "$1"\n')
    path.chmod(0o755)


def _install_hook_files(workspace):
    hooks = workspace / ".claude/hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(ROOT / ".claude/hooks/run-hook.sh", hooks / "run-hook.sh")
    (hooks / "match-lessons.py").touch()


@pytest.mark.parametrize("event", ["UserPromptSubmit", "PreToolUse"])
def test_lesson_hooks_use_quoted_workspace_venv(tmp_path, event):
    workspace = tmp_path / "agent with spaces"
    _install_hook_files(workspace)
    _fake_python(workspace / ".venv/bin/python3", "venv")
    (command,) = _hook_commands(event)
    result = subprocess.run(
        command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(workspace)},
    )
    assert result.stdout.strip() == f"venv {workspace}/.claude/hooks/match-lessons.py"


@pytest.mark.parametrize("event", ["UserPromptSubmit", "PreToolUse"])
def test_lesson_hooks_fall_back_to_path_python_without_venv(tmp_path, event):
    # A fresh fork set up with install-deps.sh (pipx) has no .venv.
    workspace = tmp_path / "agent with spaces"
    _install_hook_files(workspace)
    bindir = tmp_path / "bin"
    _fake_python(bindir / "python3", "path")
    (command,) = _hook_commands(event)
    result = subprocess.run(
        command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(workspace),
            "PATH": f"{bindir}:{os.environ['PATH']}",
        },
    )
    assert result.stdout.strip() == f"path {workspace}/.claude/hooks/match-lessons.py"
