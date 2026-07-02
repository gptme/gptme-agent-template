---
match:
  keywords:
    - "command not found exit 127"
    - "binary not in PATH workspace"
    - "exit code 127 in workspace"
description: "Use uv run when child process exits with status 127 because the binary or executable is not found on PATH in workspace project"
status: active
---

# Exit Code 127 Means Command Not Found — Use uv run in Workspace Projects

## Rule
When a bash command exits with code 127, the executable wasn't found in PATH — use `uv run` for project tools rather than assuming global availability.

## Context
When running project tools (pytest, mypy, project CLIs) in uv workspace projects. Many tools are installed only in `.venv` and aren't on `$PATH` unless explicitly activated.

## Detection
Observable signals:
- `Exit code 127` from any bash command
- `bash: <command>: command not found` in stderr
- Running `pytest`, `mypy`, or project CLIs without venv activation
- Common in uv workspace contexts where `.venv/bin` isn't on PATH

## Pattern
```bash
# Wrong: assuming tool is on global PATH
pytest tests/           # → Exit code 127: bash: pytest: command not found
mypy src/               # → Exit code 127

# Correct: use uv run to invoke tools in the project venv
uv run pytest tests/
uv run python3 script.py
uv run mypy src/

# For project-installed CLIs:
uv run <cli-name> args

# Or explicit venv path:
.venv/bin/pytest tests/
```

## Outcome
- Eliminates "command not found" failures in uv workspace projects
- Consistent tool invocation regardless of shell activation state
- Works correctly in autonomous/non-interactive sessions

## Related
- [frontend-worktree-node-modules.md](./frontend-worktree-node-modules.md) — JS worktree tooling gap
