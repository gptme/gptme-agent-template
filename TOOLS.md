# Tools

Tools available in the workspace for managing tasks, searching, and operating autonomously.

## Task Management

```bash
# View task status
gptodo status              # All tasks
gptodo status --compact    # Active only

# View specific task
gptodo show <task-id>

# Update task
gptodo edit <task-id> --set state active
gptodo edit <task-id> --set priority high
gptodo edit <task-id> --add tag feature
```

Install: `pipx install gptme-contrib` or `uv pip install gptme-contrib`

## Search & Navigation

```bash
# Quick search (respects .gitignore)
git grep -li <query>       # Find files containing term
git grep -i <query>        # Show matching lines

# Workspace search script
./scripts/search.sh <query>
```

Common locations:
- `tasks/` — Task details
- `journal/` — Daily updates
- `knowledge/` — Documentation
- `lessons/` — Behavioral patterns

Avoid `grep` or `find` — they don't respect `.gitignore`.

## Context Generation

```bash
# Generate full context summary (tasks, git, workspace state)
./scripts/context.sh

# Component scripts
./scripts/context-journal.sh    # Recent journal entries
./scripts/context-workspace.sh  # Workspace structure
```

## GitHub Integration

```bash
# Issues
gh issue list --state open
gh issue view <number> --comments

# Pull requests
gh pr list --state open
gh pr view <number> --comments
gh pr checks <number>

# Notifications
gh api notifications --jq '.[].subject.title'
```

Always read both basic view AND `--comments` for full context.

## Pre-Commit Hooks

```bash
# Fix formatting
make format

# Run all hooks
make check
# or: pre-commit run --all-files

# Run specific hook
pre-commit run ruff-format --all-files
pre-commit run mypy --all-files
```

## Autonomous Operation

```bash
# Run with gptme backend
./scripts/runs/autonomous/autonomous-run.sh

# Run with Claude Code backend
./scripts/runs/autonomous/autonomous-run-cc.sh

# Build system prompt for Claude Code
./scripts/build-system-prompt.sh
```

## Template Management

```bash
# Compare agent workspace against template
./scripts/compare.sh

# Migrate journal to subdirectory format
python3 ./scripts/migrate-journals.py
```

## Common Workflows

### Starting a session
1. Read identity files (ABOUT.md, ARCHITECTURE.md, TASKS.md)
2. Run `./scripts/context.sh` for dynamic context
3. Check `gptodo status --compact` for active work
4. Start working

### Committing changes
1. `make format` — fix formatting
2. `git add <files>` — stage explicitly
3. `git commit -m "type: description"` — conventional commits
4. Pre-commit hooks run automatically

### Finding information
```bash
git grep -i "keyword"              # Search code and docs
git grep -i "keyword" tasks/       # Search tasks
git grep -i "keyword" knowledge/   # Search knowledge base
git log --grep="keyword" --oneline # Search commit history
```
