# Tools

Tools available in the workspace for managing tasks, searching, and operating autonomously.

## Task Management

Tasks live in `tasks/` and are managed with [gptodo](https://github.com/gptme/gptme-contrib/tree/master/packages/gptodo). See [`TASKS.md`](./TASKS.md) for the format, states, and how to use a different tracker.

```bash
# View task status (overview — includes blocked/waiting tasks)
gptodo status              # All tasks
gptodo status --compact    # Only backlog/todo/active/ready_for_review

# Select unblocked work (use this instead of scanning status)
gptodo ready                         # Unblocked backlog/todo/active
gptodo ready --skip-claimed --jsonl  # Concurrent sessions: hide already-claimed tasks
gptodo next                          # The single best task to pick up

# View specific task
gptodo show <task-id>

# Update task
gptodo claim <task-id>                   # Set active and record the owner
gptodo edit <task-id> --set state done
gptodo edit <task-id> --set priority high
gptodo edit <task-id> --add tags feature
```

Install: `uv tool install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptodo`

## Communication (optional)

The workspace does not ship a communication system wired in. [gptmail](https://github.com/gptme/gptme-contrib/tree/master/packages/gptmail) is the companion package from gptme-contrib: real email (via `mbsync` + `msmtp`) and SSH-based agent-to-agent messaging, with every message stored as a Markdown file in the workspace and replies tracked so each message is answered once. Any other email client, chat bridge, or message bus works too.

If gptmail is installed and configured (see its README for the `email/` folders, `.env` settings and `messages/agents.yaml` registry):

```bash
# Email
gptmail check-unreplied                  # Unreplied mail from allowlisted senders
gptmail read <message-id> --thread
gptmail reply <message-id> "Thanks, on it."
gptmail send <draft-id>
gptmail mark-no-reply <message-id> --reason "informational"

# Agent-to-agent messages
gptmail agent pending                    # Messages you still owe a reply to
gptmail agent send <agent> "Subject" "Body"
gptmail agent reply <file.md> "Reply"
```

Install: `uv tool install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptmail`

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
# gptme backend — a terminal run skips the session gate
./scripts/runs/autonomous/autonomous-run.sh

# Force a run from a non-TTY context (scripts, CI, cron), either backend
FORCE_SESSION=1 ./scripts/runs/autonomous/autonomous-run.sh
FORCE_SESSION=1 ./scripts/runs/autonomous/autonomous-run-cc.sh

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
3. Check `gptodo ready --skip-claimed --jsonl` for unblocked work
4. Start working

### Committing changes
1. `make format` — fix formatting
2. `git add <files>` — stage explicitly
3. `git-safe-commit <files> -m "type: description"` — conventional commits, explicit paths
4. Pre-commit hooks run automatically

### Finding information
```bash
git grep -i "keyword"              # Search code and docs
git grep -i "keyword" tasks/       # Search tasks
git grep -i "keyword" knowledge/   # Search knowledge base
git log --grep="keyword" --oneline # Search commit history
```
