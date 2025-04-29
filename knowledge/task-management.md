# Task Management System

## Overview

Our task management system uses Markdown files with YAML frontmatter for metadata, tracked in git. The system prioritizes simplicity, git-friendliness, and cross-platform compatibility.

## Directory Structure

```shell
TASKS.md     # Task system documentation
tasks/
├── templates/    # Task templates
└── *.md         # Task files with frontmatter metadata
```

## Key Files

- `TASKS.md`: Instructions for task system
- `tasks/*.md`: Individual task files with metadata and details
- `scripts/tasks.py`: Primary task management tool

## Task Metadata

Tasks use YAML frontmatter for metadata:

```yaml
---
state: active # Required: Task state
created: 2025-04-13 # Required: Creation timestamp
priority: high # Optional: Priority level
tags: [ai, dev] # Optional: Task categories
depends: [] # Optional: Task dependencies
---
```

All timestamps are ISO 8601.

## Task Lifecycle

1. Creation

   - Create new task file in tasks/ with frontmatter
   - Set state: new
   - Add to TASKS.md with 🆕 status

2. Activation

   - Update state to: active
   - Update TASKS.md status to 🏃
   - Create journal entry about starting task

3. Pausing

   - Update state to: paused
   - Update TASKS.md status to ⏸️
   - Document progress in journal

4. Completion
   - Update state to: done
   - Update TASKS.md status to ✅
   - Document completion in journal

## Task File Format

Each task file should include:

1. Frontmatter metadata
2. Title (h1)
3. Status section
4. Overview/objectives
5. Implementation details/progress
6. Success criteria
7. Notes and considerations
8. Related tasks/files

## Tools

### tasks.py

Primary task management tool with commands:

- `tasks ls`: List tasks with rich formatting
  - Sort by state, date, or name
  - Show dependencies and priorities
  - Task ID mapping for easy reference
- `tasks status`: Enhanced status view
  - Compact mode for active tasks
  - Multiple directory type support
  - Summary statistics
- `tasks verify`: Task integrity checking
  - Metadata validation
  - Dependency verification
  - Circular dependency detection

### state-status.py

General state directory viewer:

- Git status-like view of state directories
- Basic metadata reporting
- Multiple directory type support (tasks, tweets, email)

### Pre-commit Hooks

- Validate frontmatter schema
- Check required fields
- Verify metadata consistency
- Ensure proper formatting

## Best Practices

1. Use Frontmatter

   - Always include required metadata
   - Keep metadata fields consistent
   - Use standard date formats

2. Task Content

   - Clear, specific titles
   - Well-structured sections
   - Regular progress updates
   - Link to related resources

3. Documentation

   - Keep TASKS.md updated
   - Regular journal entries
   - Cross-reference related tasks
   - Document decisions and changes

4. Git Workflow
   - Atomic commits for task updates
   - Clear commit messages
   - Regular status updates
   - Proper branching for major changes

## Task Organization Principles

### Priority Levels

- 🔴 High: Core infrastructure or blocking tasks
  - Foundation for other work (e.g., MIQ framework)
  - Critical bug fixes
  - Blocking dependencies
- 🟡 Medium: Important but not blocking
  - Active infrastructure improvements
  - Time-sensitive tasks
  - User-facing features
- 🟢 Low: Nice to have
  - Quality of life improvements
  - Non-critical enhancements
  - Research and experiments

### Dependencies

Add dependencies when:

- Task requires another task's output
- Task builds on another task's functionality
- Task needs patterns/lessons from another task
- Task improves with another task's capabilities

Avoid dependencies when:

- Tasks can be done in parallel
- Relationship is weak or optional
- Would create circular dependencies
- Would over-constrain scheduling

### Strategic Organization

1. Core Capabilities

   - Focus on foundational improvements
   - Build reusable patterns
   - Enhance autonomous operation
   - Document patterns for reuse

2. Infrastructure

   - Prioritize blocking issues
   - Regular maintenance
   - Technical debt reduction
   - CI/CD improvements

3. User-Facing Features

   - Align with project goals
   - Consider user impact
   - Balance with infrastructure needs
   - Document user feedback

4. Research & Exploration
   - Keep experimental tasks separate
   - Document learnings
   - Consider strategic value
   - Plan integration paths

### Task State Changes

Document state changes in:

1. Task metadata (frontmatter)
2. TASKS.md status
3. Journal entries with:
   - Reason for change
   - Initial development plan
   - Related tasks/dependencies
   - Next steps

### Task Documentation

Each significant task should have:

1. Clear success criteria
2. Implementation phases
3. Technical requirements
4. Testing strategy
5. Integration plans
6. Related documentation

### Version Control

Organize commits by:

1. Area of change (feat, docs, etc.)
2. Component affected
3. Implementation phase
4. Related tasks

Example commit structure:

```sh
feat(identity): select main profile picture
docs(twitter): add profile setup details
chore(make): reduce format command verbosity
```

### Task Review & Reflection

Regular task review helps maintain focus and track progress:

1. Daily Reviews

   - Document progress in journal
   - Update task status
   - Plan next steps
   - Note blockers/dependencies

2. Task Transitions

   - Document completion criteria met
   - Summarize key learnings
   - Update related tasks
   - Plan follow-up work

3. Progress Tracking

   - Update subtask completion
   - Document milestone achievements
   - Track dependency status
   - Note implementation phases

4. Knowledge Capture
   - Document patterns discovered
   - Update technical designs
   - Create reusable templates
   - Share learnings in knowledge base

This reflection process ensures:

- Clear progress tracking
- Knowledge preservation
- Pattern recognition
- Continuous improvement

### Periodic Task Reviews

Regular comprehensive task reviews help maintain organization and focus. Example prompt:

```markdown
Let's go through the tasks one by one and mark them as paused or active.

Process:

1. Use tasks.py status to see current state
2. For each task:
   - Review state and priority
   - Check dependencies
   - Consider strategic alignment
   - Update metadata as needed
3. Document changes in journal
4. Update documentation if patterns emerge

Tools to use:

- tasks.py status/list for overview
- git grep to find related documentation
- perl for bulk metadata updates
- patch/append for documentation updates
```

This review process should:

1. Start with current status
2. Make systematic changes
3. Check documentation
4. Document decisions
5. Update processes if needed

The review can reveal:

- Task organization patterns
- Missing dependencies
- Documentation needs
- Process improvements

Document review outcomes in:

1. Journal entry with:
   - Changes made
   - Rationale
   - New patterns found
   - Process improvements
2. Updated documentation
3. New tasks if needed

### Review-Driven Improvements

Task reviews often lead to system improvements. Example from our review process:

1. Pattern Discovery

   - Used git grep to find task organization patterns
   - Reviewed journal entries for historical context
   - Found common metadata update needs

2. Documentation Updates

   - Added discovered patterns to documentation
   - Created examples from real usage
   - Documented common operations

3. Tool Improvements
   - Identified need for better metadata management
   - Created task for CLI-based updates
   - Documented interim perl patterns

This iterative process helps:

- Discover and document patterns
- Improve tooling based on real needs
- Maintain institutional knowledge
- Evolve the system organically

## Implementation Notes

The system uses frontmatter metadata instead of symlinks for several benefits:

- Better git compatibility
- Reduced filesystem complexity
- Cross-platform support
- Enhanced metadata capabilities
- Easier validation and tooling
- Single source of truth in task files
