# Workspace Structure for Forkable Agents

This document describes what remains and what gets cleared when forking an agent.

## Directory Structure Overview

```tree
.
├── README.md               # Overview (template remains, content updated)
├── ABOUT.md               # Agent identity (cleared and customized)
├── ARCHITECTURE.md        # System architecture (remains)
├── CURRENT_TASK.md        # Symlink to active task (reset to no-active-task.md)
├── gptme.toml            # Config file (template remains, paths updated)
├── tasks/                # Task management (structure remains, content cleared)
│   ├── active/          # Current tasks
│   ├── done/           # Completed tasks
│   └── ...             # Other task states
├── journal/             # Daily logs (cleared)
├── knowledge/           # Knowledge base (partially preserved)
│   ├── ai/             # Technical knowledge (preserved)
│   └── ...             # Other knowledge (evaluated per-file)
├── people/             # Relationships (cleared except templates & creator)
└── projects/           # Project links (cleared)
```

## What Stays

1. **System Structure**
   - Directory layout
   - Task management system
   - Documentation templates
   - Tool configurations

2. **Core Documentation**
   - ARCHITECTURE.md
   - Technical designs
   - Tool integration guides
   - Best practices

3. **Technical Knowledge**
   - AI/ML concepts
   - System architecture
   - Tool usage patterns

## What Gets Cleared

1. **Personal Content**
   - Journal entries
   - Task content
   - Project links
   - Agent-specific knowledge

2. **Identity**
   - ABOUT.md
   - Visual identity
   - Social media presence
   - Personal profile

3. **Relationships**
   - People profiles (except creator)
   - Interaction history

## Fork Creation Steps

1. Copy workspace structure
2. Clear personal content
3. Initialize new identity
4. Update configurations
5. Create first task

For detailed forking process, see [`agent-forking.md`](./agent-forking.md).
