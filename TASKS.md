# Tasks

This document describes the task management system used in the workspace.

Tasks are individual Markdown files with YAML frontmatter under `./tasks/`. Because they are plain files in git, task state survives across sessions, shows up in diffs, and can be edited by humans and agents alike.

The workspace is set up for [**gptodo**](https://github.com/gptme/gptme-contrib/tree/master/packages/gptodo), the task CLI from gptme-contrib. gptodo is optional: the task files are readable without it, and you can replace it with your own tracker (see [Using a different task tracker](#using-a-different-task-tracker)).

The system provides:

- Structured task tracking with YAML frontmatter metadata
- Work selection that only returns unblocked tasks (`gptodo ready`, `gptodo next`)
- Pre-commit validation hooks for data integrity
- Integration with journal entries for progress tracking

## gptodo

gptodo answers the question an agent asks at the start of every session: *what should I work on next?* It adds dependency-aware selection (`ready`, `next`), ownership (`claim`), a task state machine, and frontmatter checks (`check`, `lint`) on top of the files in `tasks/`. It can also link tasks to GitHub issues and pull requests.

Where this workspace uses it:

- `scripts/context.sh` includes the output of `gptodo status --compact` in every session's context (it prints an install hint instead if gptodo is missing).
- The `validate-task-metadata` pre-commit hook runs `gptodo check` (skipped if gptodo is missing).
- [`WORKFLOW.md`](./WORKFLOW.md) selects work with `gptodo ready`.

**Installation**:

```sh
uv tool install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptodo
# or
pipx install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptodo
```

Full documentation: [gptodo README](https://github.com/gptme/gptme-contrib/tree/master/packages/gptodo).

### Commands

```sh
# View task status (overview — includes blocked/waiting tasks)
gptodo status              # Show all tasks
gptodo status --compact    # Only backlog/todo/active/ready_for_review

# Select unblocked work (use this instead of scanning `gptodo status`)
gptodo ready                         # Unblocked backlog/todo/active
gptodo ready --state todo --jsonl    # One state, one JSON object per line
gptodo ready --skip-claimed --jsonl  # Concurrent sessions: hide already-claimed tasks
gptodo next                          # The single best task to pick up

# Create and claim
gptodo add --priority high --tags docs "Write project README"
gptodo claim <task-id>     # Set state active and record the owner

# List tasks
gptodo list               # List all tasks
gptodo list --sort state  # Sort by state
gptodo list --sort date   # Sort by date

# Show task details
gptodo show <task-id>     # Show specific task

# Validate
gptodo check              # Integrity: broken references, unparseable frontmatter
gptodo lint               # Unknown or deprecated frontmatter fields
```

### Selecting work (`gptodo ready`)

`gptodo status` is an overview of everything, including blocked and waiting tasks. Concurrent sessions that pick from status will converge on the same blocked work.

`gptodo ready` is the selector: it lists tasks that are genuinely unblocked (no unresolved `requires`, no `waiting_for` blocker, no future `wait` date). `--state backlog|todo|active|ready_for_review` narrows the pool; `--jsonl` is the machine-readable form for autonomous runners.

For concurrent sessions, add `--skip-claimed`. It hides tasks already held by another coordination session (`state/coordination/coord.db`, keys like `cascade:task:<id>`). If that DB is absent — a typical fresh fork — the flag degrades silently and you still get the unblocked set.

Re-install gptodo from gptme-contrib if `gptodo ready --help` does not list `--skip-claimed`.

### Task Metadata Updates

```sh
# Basic usage
gptodo edit <task-id> [--set|--add|--remove <field> <value>]

# Examples
gptodo edit my-task --set state active        # Set task state
gptodo edit my-task --set priority high       # Set priority
gptodo edit my-task --add tags feature        # Add a tag
gptodo edit my-task --add requires other-task # Add dependency

# Multiple changes
gptodo edit my-task \
  --set state active \
  --add tags feature \
  --add requires other-task

# Multiple tasks
gptodo edit task-1 task-2 --set state done
```

Valid values:

- `--set state`: see [Task states](#task-states)
- `--set priority`: high, medium, low, none
- `--add/--remove tags`: any string without spaces
- `--add/--remove requires`: any valid task ID or issue URL

`gptodo edit` warns on illegal state transitions and refuses to reopen `done`/`cancelled` tasks without `--force`. `gptodo transitions` prints the full table.

## Task Format

### Task Metadata

Tasks are stored as Markdown files with YAML frontmatter. The task ID is the filename without `.md`.

```yaml
---
# Required fields
state: backlog # See "Task states" below
created: 2025-04-13 # Creation date (ISO 8601)

# Optional fields
priority: high # Priority level: low, medium, high
tags: [ai, dev] # List of categorization tags
requires: [other-task] # Tasks (or issue URLs) that must be done first
waiting_for: "Reply from reviewer" # External blocker (use with state: waiting)
---
```

`depends` is a deprecated alias for `requires`. The full field list and behaviour (`wait`, `recur`, `assigned_to`, structured `waiting_for`, …) are in the [gptodo README](https://github.com/gptme/gptme-contrib/tree/master/packages/gptodo#task-files).

### Task states

| State | Meaning |
|-------|---------|
| `backlog` | Queued, not yet triaged. Default for new tasks. |
| `todo` | Triaged and ready to pick up. |
| `active` | Someone is working on it **right now**. Not "recently touched". |
| `waiting` | Blocked on an external event (date, reply, approval, merge). Set `waiting_for` and/or `wait`. |
| `ready_for_review` | Work done, awaiting sign-off. |
| `draft` | A plan filed so it isn't lost, but not released for work. |
| `someday` | Parked idea that may never be picked up. |
| `done` / `cancelled` | Terminal. |

`new` and `paused` are deprecated aliases for `backlog`. A `paused` task is still picked up by `ready`/`next`; use `draft`, `someday` or `waiting` to hold a task. Blocked-on-another-task is expressed with `requires`, not a state.

### Task Body

Example task demonstrating best practices:

```markdown
---
state: active
created: 2025-04-13T18:51:53+02:00
priority: high
tags: [infrastructure, ai]
requires: [implement-task-metadata]
---

# Task Title

Task description and details...

## Subtasks

- [ ] First subtask
- [x] Completed subtask
- [ ] Another subtask

## Notes

Additional notes, context, or documentation...

## Related

- Links to related files
- URLs to relevant resources
```

## Task Lifecycle

1. **Creation**

   - Create a task file in `tasks/` (by hand or with `gptodo add`)
   - New tasks start in `backlog`; move to `todo` once triaged

2. **Activation**

   - Claim it (`gptodo claim <task-id>`) or set `state: active`
   - Create journal entry about starting task

3. **Progress Tracking**

   - Daily updates in journal entries
   - Update task metadata as needed
   - Track subtask completion

4. **Waiting**

   - Set `state: waiting` with `waiting_for` (and optionally a `wait` date)
   - Document the blocker in the task body

5. **Completion/Cancellation**

   - Set state to `done` (or `ready_for_review` if sign-off is needed) or `cancelled`
   - Final journal entry documenting outcomes

## Task Validation

Tasks are validated using pre-commit hooks:

1. `validate-task-frontmatter` checks required fields and allowed values (states, priorities, task types).
2. `validate-task-metadata` runs `gptodo check` for broken references and unparseable frontmatter (skipped if gptodo is not installed).
3. Markdown link checks cover internal links in task files.

## Using a different task tracker

gptodo is one well-integrated option, not a requirement. You can track work in GitHub Issues, Linear, a single `TODO.md`, or anything else. To swap it out:

1. **Context**: `scripts/context.sh` is a symlink into the gptme-contrib submodule that runs `gptodo status --compact`. Replace the symlink with your own script, or point `context_cmd` in [`gptme.toml`](./gptme.toml) at one, that prints your open work.
2. **Pre-commit**: remove or replace the `validate-task-frontmatter` and `validate-task-metadata` hooks in `.pre-commit-config.yaml` if you no longer keep tasks in `tasks/`.
3. **Workflow**: update the `tracker` block and the Phase 2 selection commands in [`WORKFLOW.md`](./WORKFLOW.md), and the task-selection steps in the prompts inside `scripts/runs/autonomous/autonomous-run.sh` and `autonomous-run-cc.sh`.
4. **Docs the agent reads**: this file and [`TOOLS.md`](./TOOLS.md) are included in every session via `gptme.toml`, and [`AGENTS.md`](./AGENTS.md) is read by other harnesses. Rewrite their task sections so the agent calls your tool instead of `gptodo`.

gptodo can also sit alongside an external tracker: `gptodo import --source github` and `--source linear` create task files from issues, and `gptodo sync` compares task states with linked GitHub issues.

## Best Practices

1. **File Management**

   - Always treat `tasks/` as single source of truth
   - Update task state by editing frontmatter (or `gptodo edit`)
   - Pre-commit hooks validate changes

2. **Task Creation**

   - Use clear, specific titles
   - Break down into manageable subtasks
   - Include success criteria
   - Link related resources
   - Follow metadata format specification

3. **Progress Updates**

   - Regular updates in journal entries
   - Document blockers and dependencies
   - Keep metadata current and accurate

4. **Documentation**

   - Cross-reference related tasks using paths relative to repository root
   - Document decisions and rationale
   - Link to relevant documents and resources
   - Update knowledge base as needed

5. **Linking**
   - Always link to referenced resources (tasks, knowledge, URLs)
   - Use relative paths from repository root when possible
   - Common links to include:
     - Tasks mentioned in journal entries
     - Related tasks in task descriptions
     - People mentioned in any document
     - Projects being discussed
     - Knowledge base articles
   - Use descriptive link text that makes sense out of context
