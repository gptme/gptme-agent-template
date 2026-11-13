"""Lesson hooks use the interpreter where gptme-rag is installed."""

import json
import os
import subprocess
from pathlib import Path


def test_lesson_hooks_use_quoted_workspace_venv(tmp_path):
    root = Path(__file__).parents[1]
    settings = json.loads((root / ".claude/settings.json").read_text())
    workspace = tmp_path / "agent with spaces"
    interpreter = workspace / ".venv/bin/python3"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text('#!/bin/sh\nprintf "%s\\n" "$1"\n')
    interpreter.chmod(0o755)
    expected_script = str(workspace / ".claude/hooks/match-lessons.py")
    for event in ("UserPromptSubmit", "PreToolUse"):
        commands = [
            hook["command"]
            for group in settings["hooks"][event]
            for hook in group["hooks"]
        ]
        assert len(commands) == 1
        assert commands[0].startswith('"$CLAUDE_PROJECT_DIR/.venv/bin/python3" ')
        result = subprocess.run(
            commands[0],
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(workspace)},
        )
        assert result.stdout.strip() == expected_script
