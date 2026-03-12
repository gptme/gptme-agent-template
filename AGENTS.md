# Agent Instructions

This file is automatically loaded by Claude Code and other agent runtimes.

## Identity

Read the files listed in `gptme.toml` under `[prompt] files` at session start.
These define who you are, how you work, and what you know. Key files:

- **ABOUT.md** — Personality, goals, values
- **ARCHITECTURE.md** — System design, workspace structure
- **TASKS.md** — Task management system

**Important**: Get the repo root dynamically — never hardcode paths:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
```

## Core Rules

### File Operations — Use Absolute Paths

```bash
# Correct — derive repo root, then use absolute path
REPO_ROOT=$(git rev-parse --show-toplevel)
echo "entry" >> "$REPO_ROOT/journal/2025-10-14/topic.md"

# Wrong — breaks when cwd changes
echo "entry" >> journal/2025-10-14/topic.md
```

### Git Workflow

- **Default branch is `master`** — not `main`. Never assume `main`.
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **Workspace repo**: Commit directly to master for docs/journal/tasks
- **External repos**: Use branches + PRs from worktrees at `/tmp/worktrees/<repo>/<branch>/`
- **Stage explicitly**: Use `git add <files>`, never `git add .` or `git commit -a`
- **PR merge strategy**: Always `--squash` when merging
- **No AI attribution**: Never add `Co-Authored-By: Claude` or "Generated with Claude Code" to commits/PRs

### Safety Rules

- **Never force-push to master/main**
- **Never skip hooks** with `--no-verify` unless explicitly asked
- **Never commit secrets** — check with `git diff --staged` before committing
- **Verify CI passes** after pushing: `gh pr checks <num> --watch`

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

Run automatically on commit. Don't bypass with `--no-verify` unless explicitly asked.

```bash
# Fix formatting
make format

# Run all hooks manually (prek is faster if available, falls back to pre-commit)
if command -v prek &>/dev/null; then
    prek run --all-files
else
    pre-commit run --all-files
fi
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

### Claude Code / Codex
- Only this file is auto-loaded — **manually read bootstrap files** listed above
- Run `scripts/context.sh` at session start for dynamic context (tasks, GitHub, git status)
- No automatic lesson injection — check `lessons/` when relevant

### Working on External Repos

For any code change outside the workspace repo, use worktrees:

```bash
# New feature/fix in an external repo
cd /path/to/external-repo
BRANCH="fix-my-issue"
git worktree add "/tmp/worktrees/$(basename $PWD)/$BRANCH" -b "$BRANCH" origin/master
cd "/tmp/worktrees/$(basename $PWD)/$BRANCH"
git branch --unset-upstream   # prevent accidental push to master
# ... make changes, commit ...
git push -u origin "$BRANCH"
gh pr create
```
