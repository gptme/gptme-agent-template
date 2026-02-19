# Agent Instructions

This file is automatically loaded by Claude Code and other agent runtimes.

## Identity

Read the files listed in `gptme.toml` under `[prompt] files` at session start.
These define who you are, how you work, and what you know. Key files:

- **ABOUT.md** — Personality, goals, values
- **ARCHITECTURE.md** — System design, workspace structure
- **TASKS.md** — Task management system

## Core Rules

### File Operations — Use Absolute Paths

```bash
# Correct — use repo root
/path/to/workspace/journal/2025-10-14/topic.md

# Wrong — breaks when cwd changes
journal/2025-10-14/topic.md
```

### Git Workflow

- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **Workspace repo**: Commit directly to master for docs/journal/tasks
- **External repos**: Use branches + PRs, never commit to master directly
- **Stage explicitly**: Use `git add <files>`, never `git add .` or `git commit -a`

### Journal

- **Append-only**: Never modify historical entries
- **Subdirectory format**: `journal/YYYY-MM-DD/HHMMSS-topic.md`
- **Absolute paths**: Always use full paths when creating entries

### Tasks

- Managed via files in `tasks/` with YAML frontmatter
- CLI: `gptodo status|show|edit`
- Assess complexity by scope, not time
- Mark done when core functionality works

### Pre-Commit Hooks

Run automatically on commit. Don't bypass with `--no-verify` unless necessary.

```bash
# Fix formatting
make format

# Run all hooks manually
pre-commit run --all-files
```

### Testing

```bash
make test        # All tests
make typecheck   # Type checking
```

## Multi-Runtime Notes

### gptme
- Identity files auto-loaded via `gptme.toml`
- `context_cmd` runs `scripts/context.sh` for dynamic context
- Lessons matched by keywords automatically

### Claude Code
- Only this file is auto-loaded — read bootstrap files listed above manually
- For autonomous runs, `scripts/build-system-prompt.sh` builds the full context
- Run `scripts/context.sh` to get dynamic context (tasks, GitHub, git status)
