---
# WORKFLOW.md — Repo-Versioned Autonomous Workflow Contract
# v1.0 — Template
#
# YAML front matter: runtime config.
# Markdown body: agent instructions with {{PLACEHOLDER}} injection.
#
# Placeholders (set at run time by workflow-render.py):
#   WORKSPACE    — repo root absolute path
#   DATE         — today's date (YYYY-MM-DD)
#   AGENT_NAME   — your agent's name
#   CREATOR      — your human collaborator's name/call-name
#   SESSION_HASH — short hash identifying this session run

harness:
  allowed:
    - gptme
    - claude-code
  default: gptme
  # model_routing: customize per-harness model in your fork, e.g.:
  #   gptme: "openrouter/anthropic/claude-3.5-sonnet"
  #   claude-code: "claude-sonnet-4-5"

tracker:
  kind: gptodo
  tasks_dir: "{{WORKSPACE}}/tasks"

session:
  default_timeout: 45
  commit_style: conventional
  require_precommit: true

workspace:
  root: "{{WORKSPACE}}"
  journal_dir: "{{WORKSPACE}}/journal/{{DATE}}"
  state_dir: "{{WORKSPACE}}/state"

hooks:
  post_commit: "git push origin HEAD"

context:
  prebuilt:
    - README.md
    - gptme.toml
    - ABOUT.md
    - SOUL.md
    - ARCHITECTURE.md
    - TASKS.md
  dynamic_cmd: "{{WORKSPACE}}/scripts/context.sh"
  lesson_dirs:
    - "{{WORKSPACE}}/lessons"
    - "{{WORKSPACE}}/skills"
    - "{{WORKSPACE}}/gptme-contrib/lessons"
    - "{{WORKSPACE}}/gptme-contrib/skills"
---

# Autonomous Workflow — {{AGENT_NAME}}

You are **{{AGENT_NAME}}**, an autonomous agent. Your identity files
are in the runtime context. This file defines the session workflow.

## Phase 1 — Loose Ends (2 min)

1. Run `git status` and check for staged or uncommitted work.
2. Scan for new issues assigned to you by {{CREATOR}} (check GitHub CLI).
   - If it belongs to another agent's domain, route it and confirm.
   - If it's yours, schedule it or act.
3. Check `state/salvage/` for uncommitted work from timed-out sessions.
4. Handle any quick fix (< 5 min) before selecting primary work.

**Scope boundary**: PR reviews, CI failures, and generic GitHub notifications
are handled by dedicated services. Do NOT treat them as a work queue.

## Phase 2 — Task Selection (3 min)

Try these tiers in order until you find actionable work:

### Tier 1 — Active tasks
Run `gptodo status --compact`. If a task is `active` or `ready_for_review`,
inspect it. Skip tasks with `waiting_for` set.

### Tier 2 — Backlog candidates
`gptodo ready --state backlog --jsonl`. Prefer small, self-contained work
completable in one session.

### Tier 3 — Self-improvement work
If all tasks are blocked, do productive internal work. Pick from this list
(ordered by typical impact):

1. **Idea backlog**: Check `knowledge/strategic/idea-backlog.md` if it exists.
   Advance the highest-scored item (research, design doc, prototype).
2. **Internal code**: Improve workspace packages, scripts, tooling.
3. **Infrastructure**: Fix services, improve health checks, harden automation.
4. **Cleanup**: Remove stale code or config — prefer net-negative LOC.
5. **Content**: Draft a blog post from recent interesting work.
6. **Code quality**: Run `make typecheck` and `make test`, fix regressions.
7. **Task hygiene**: Close stale tasks, update metadata, fix `waiting_for` fields.
8. **Lesson quality**: Review recent lessons for accuracy, merge duplicates.

**Minimum viable progress**: There is always Tier 3 work available.
Even a small commit (task metadata, lesson fix, doc correction) is better
than a NOOP session.

## Phase 3 — Execution

Do the work:
- Make real, meaningful progress (commits, code changes, docs, lessons)
- Follow the git workflow: conventional commits, run tests, pre-commit hooks
- Update task state when done: `gptodo edit <task> --set state done`
- If stuck > 10 minutes, pivot to the next task

## Phase 4 — Completion (2 min)

1. Log progress in `journal/{{DATE}}/autonomous-session-{{SESSION_HASH}}.md`
   using the standard template (see any existing journal entry for format).
2. Commit with a descriptive conventional commit message.
3. Push to origin: `git push origin HEAD`.

---

*To customize this workflow: edit the YAML front matter for config changes,
or modify the Markdown body for instruction changes. Placeholders are
injected by `scripts/workflow-render.py` at run time.*
