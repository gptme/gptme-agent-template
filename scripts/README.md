# Scripts Directory

This directory contains scripts for agent workspace automation and operations.

## Structure

```txt
scripts/
├── context.sh              # Main context generation orchestrator
├── context-journal.sh      # Recent journal entries context
├── context-workspace.sh    # Workspace files overview
├── tasks.py*              # Task management CLI (optional, from gptme-contrib)
├── search.sh              # Multi-source search across workspace
├── compare.sh             # Compare files or directories
├── fork.py                # Agent forking automation
├── runs/                  # Autonomous run infrastructure
│   └── autonomous/
│       ├── autonomous-run.sh      # Main autonomous run script
│       └── autonomous-prompt.txt  # Prompt template for runs
├── precommit/             # Pre-commit hook implementations
│   └── [various validation scripts]
└── README.md              # This file
```

## Context Generation System

The context generation system provides dynamic context to gptme sessions by gathering information from various workspace sources.

### Main Script: context.sh

**Purpose**: Orchestrate context generation from multiple providers.

**Usage**:
```bash
# Generate full context
./scripts/context.sh

# Use in gptme.toml
context_cmd = "/path/to/scripts/context.sh"
```

**What it does**:
1. Generates context summary header with timestamp
2. Calls component scripts (journal, workspace)
3. Shows task status via tasks.py
4. Displays git status

**Output format**:
```txt
# Context Summary
Generated on: [timestamp]

# Journal Context
[Recent journal entries]

# Tasks
[Task status overview]

# Workspace Structure
[File tree and overview]

# Git
[Git status]
```

### Component Scripts

#### context-journal.sh

**Purpose**: Extract recent journal entries for session continuity.

**What it includes**:
- Today's journal entries
- Recent session summaries
- Links to older sessions

**Customization**: Edit to control:
- Number of recent entries
- Date range to include
- Summary format

#### context-workspace.sh

**Purpose**: Provide overview of workspace structure and files.

**What it includes**:
- Directory tree
- Key file listings
- Project structure

**Customization**: Edit to control:
- Which directories to show
- Tree depth
- File patterns to include/exclude

### Customizing Context Generation

**For your agent**, customize:

1. **context-journal.sh**:
   - Adjust how many recent journal entries to include
   - Change summary format
   - Add agent-specific journal sections

2. **context-workspace.sh**:
   - Include agent-specific directories
   - Exclude irrelevant paths
   - Add custom file listings

3. **context.sh**:
   - Add new component scripts
   - Reorder sections
   - Add agent-specific providers

**Example customization**:
```bash
# In context.sh, add custom provider:
$SCRIPT_DIR/context-notifications.sh  # Your custom script
```

## Task Management: tasks.py (Optional)

**Purpose**: CLI for task management (status, list, edit operations).

**Note**: This tool is provided by gptme-contrib when available. See gptme-contrib documentation for installation.

**Common commands**:
```bash
# View task status
./scripts/tasks.py status

# Compact view (for context)
./scripts/tasks.py status --compact

# List all tasks
./scripts/tasks.py list

# Show specific task
./scripts/tasks.py show <task-id>

# Edit task metadata
./scripts/tasks.py edit <task-id> --set state active
```

## Autonomous Run Infrastructure

Located in `scripts/runs/autonomous/`:

**autonomous-run.sh**:
- Main script for autonomous operation
- Implements CASCADE workflow (loose ends → task selection → execution)
- Handles git operations, session logging, queue updates
- See scripts/runs/autonomous/README.md for details

**autonomous-prompt.txt**:
- Template prompt for autonomous sessions
- Loaded by autonomous-run.sh
- Customizable per agent

## Search and Utilities

**search.sh**:
- Multi-source search across tasks, knowledge, lessons
- Usage: `./scripts/search.sh "query"`

**compare.sh**:
- Compare files or directories
- Usage: `./scripts/compare.sh file1 file2`

**fork.py**:
- Automate agent forking from template
- Creates new agent workspace with proper initialization
- See fork.sh in repo root for usage

## Pre-commit Hooks

Located in `scripts/precommit/`:

Validation scripts run by pre-commit framework:
- Task frontmatter validation
- Lesson format checking
- Markdown link verification
- YAML syntax validation

Configure in `.pre-commit-config.yaml` at repo root.

## Best Practices

**Context Generation**:
- Keep scripts fast (<5 seconds total)
- Filter output to relevant information
- Use compact formats for token efficiency

**Customization**:
- Copy and modify component scripts
- Don't edit shared scripts (tasks.py)
- Document customizations in comments

**Integration**:
- Configure context_cmd in gptme.toml
- Test context generation manually first
- Monitor token usage with large contexts

## Related

- gptme.toml - Context command configuration
- state/README.md - Work queue system documentation
- scripts/runs/autonomous/README.md - Autonomous run details
- TOOLS.md - Tool usage documentation
