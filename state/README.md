# State Directory

This directory contains agent work queue and state tracking files.

## Work Queue System

The work queue provides structured task prioritization for autonomous operation using two complementary queues:

### queue-manual.md (PRIMARY)

**Purpose**: Manually maintained work queue with rich context and reasoning.

**Usage**:
- Update "Current Run" at session start with brief status
- Maintain "Planned Next" with 3 priority tasks
- Include session context, dependencies, strategic notes
- Rich information about reasoning and progress

**When to use**:
- Strategic work requiring human context
- Complex multi-session projects
- Tasks with dependencies or blockers
- Work requiring specific sequencing

**Update pattern**:
```bash
# At session start: Update current run
# During work: Update task status and context
# At session end: Refresh planned next items
```

### queue-generated.md (SECONDARY)

**Purpose**: Auto-generated fallback queue from task files and GitHub issues.

**Generation**:
- Requires queue generation script (see gptme-contrib packages/task_queue/)
- Queries GitHub issues with priority labels
- Reads task files with assigned_to field
- Sorts by priority order (urgent > high > medium > low)

**When to use**:
- Manual queue not maintained
- Need fresh objective data from GitHub
- Want to see all prioritized work at once

**Generation command** (when available):
```bash
# Generate agent's queue
./scripts/tasks/generate-work-queue.py

# Generate specific user's queue
./scripts/tasks/generate-work-queue.py --user [agent-name]
```

## CASCADE Workflow Integration

Autonomous runs use CASCADE workflow for task selection:

1. **PRIMARY**: Read state/queue-manual.md "Planned Next"
   - Manual queue has session context and reasoning
   - If empty or missing: Fall back to generated queue

2. **SECONDARY**: Check notifications for direct assignments

3. **TERTIARY**: Check workspace tasks if PRIMARY/SECONDARY blocked

**Benefits**:
- Manual queue: Rich context about priorities and dependencies
- Generated queue: Fresh data when manual not maintained
- No overwrites: Separate files prevent conflicts

## Best Practices

**Manual Queue**:
- Keep "Planned Next" updated (3 tasks)
- Document reasoning and dependencies
- One-line "Current Run" status
- Update timestamp at session end

**Generated Queue**:
- Regenerate periodically (daily recommended)
- Use GitHub labels for priority management
- Don't edit manually (will be overwritten)

**Separation of Concerns**:
- Manual queue: Strategic context and session tracking
- Generated queue: Fresh objective data from sources
- Both inform but don't overwrite each other

## Example Workflow

```bash
# Morning: Check manual queue for strategic priorities
cat state/queue-manual.md

# If empty: Check generated queue for GitHub work
cat state/queue-generated.md

# Work on task, update manual queue with progress
# Update "Current Run" and "Planned Next" sections

# End of day: Refresh queues for next session
# Commit updates: git commit state/ -m "docs: queue updates"
```

## Related

- TASKS.md - Task management system documentation
- scripts/runs/autonomous/ - Autonomous run scripts using CASCADE
- gptme-contrib packages/task_queue/ - Queue generation tools (when available)
