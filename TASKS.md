# Tasks

This document describes and provides instructions for the task management system used in the workspace.

The system provides:

- Structured task tracking with YAML frontmatter metadata
- CLI tools for task management and status tracking
- Pre-commit validation hooks for data integrity
- Integration with journal entries for progress tracking
- Best practices for task creation and management

All task details are maintained as individual Markdown files under `./tasks/`.

See [Task Management System](./knowledge/task-management.md) for a complete overview of the task management system.

## Task CLI Usage

The task system provides a CLI for managing tasks:

```sh
# View task status
./scripts/tasks.py status              # Show all tasks
./scripts/tasks.py status --compact    # Show only new/active
./scripts/tasks.py status --type tasks # Show specific type

# List tasks
./scripts/tasks.py list               # List all tasks
./scripts/tasks.py list --sort state  # Sort by state
./scripts/tasks.py list --sort date   # Sort by date

# Show task details
./scripts/tasks.py show <task-id>     # Show specific task
```

### Task Metadata Updates

The task system provides a CLI for updating task metadata:

```sh
# Basic usage
./scripts/tasks.py edit <task-id> [--set|--add|--remove <field> <value>]

# Examples
./scripts/tasks.py edit my-task --set state active       # Set task state
./scripts/tasks.py edit my-task --set priority high      # Set priority
./scripts/tasks.py edit my-task --add tag feature        # Add a tag
./scripts/tasks.py edit my-task --add depends other-task # Add dependency

# Multiple changes
./scripts/tasks.py edit my-task \
  --set state active \
  --add tag feature \
  --add depends other-task

# Multiple tasks
./scripts/tasks.py edit task-1 task-2 --set state done
```

Valid fields and values:

- `--set state`: new, active, paused, done, cancelled
- `--set priority`: high, medium, low, none
- `--add/--remove tags`: any string without spaces
- `--add/--remove depends`: any valid task ID

## Task Format

### Task Metadata

Tasks are stored as Markdown files with YAML frontmatter for metadata. The schema is:

```yaml
---
# Required fields
state: active # Task state: new, active, paused, done, cancelled
created: 2025-04-13 # Creation date (ISO 8601)

# Optional fields
priority: high # Priority level: low, medium, high
tags: [ai, dev] # List of categorization tags
depends: [other-task] # List of dependent task IDs
---
```

### Task Body

Example task demonstrating best practices:

```markdown
---
state: active
created: 2025-04-13T18:51:53+02:00
priority: high
tags: [infrastructure, ai]
depends: [implement-task-metadata]
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

   - Create new task file in `tasks/` with frontmatter

2. **Activation**

   - Update state in frontmatter to 'active'
   - Create journal entry about starting task
   - Monitor progress with tasks.py

3. **Progress Tracking**

   - Daily updates in journal entries
   - Update task metadata as needed
   - Track subtask completion
   - View progress with tasks.py

4. **Completion/Cancellation**

   - Update state in frontmatter to 'done'/'cancelled'
   - Final journal entry documenting outcomes

5. **Pausing**
   - Update state in frontmatter to 'paused'
   - Document progress in journal
   - Document pause reason in task description

## Task Validation

Tasks are validated using pre-commit hooks that check:

1. Metadata format and values (as specified in task metadata format above)
2. File structure:
   - Valid markdown syntax
   - Valid internal links

## Best Practices

1. **File Management**

   - Always treat `tasks/` as single source of truth
   - Never modify files directly in state directories
   - Update task state by editing frontmatter
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
   - Track progress with tasks.py
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
