# Architecture

This document describes the architecture and workflows of Bob's workspace.

## Overview

This workspace implements a forkable agent architecture, designed to be used as a foundation for creating new agents. For details about:
- Forking process: See [`knowledge/agent-forking.md`](./knowledge/agent-forking.md)
- Workspace structure: See [`knowledge/forking-workspace.md`](./knowledge/forking-workspace.md)

## Tools

For a information about tools used in this workspace, see [`TOOLS.md`](./TOOLS.md).

## Task System

The task system is designed to help Bob track and manage work effectively across sessions.

### Components

1. [**`TASKS.md`**](./TASKS.md)
   - Main task registry
   - Contains all tasks categorized by area
   - Each task has a clear status indicator
   - Links to task files in `tasks/`

2. **Task Files**
   - All task files stored in [`tasks/`](./tasks) as single source of truth
   - Task state managed via symlinks in state directories:
     - `tasks/new/`: Symlinks to new tasks
     - `tasks/active/`: Symlinks to tasks being worked on
     - `tasks/paused/`: Symlinks to temporarily paused tasks
     - `tasks/done/`: Symlinks to completed tasks
     - `tasks/cancelled/`: Symlinks to cancelled tasks
   - Never modify task files directly in state directories, always modify in `tasks/`

3. **Journal Entries**
   - Daily progress logs in [`journal/`](./journal)
   - Each entry documents work done on tasks
   - Includes reflections and next steps

### Task Lifecycle

0. **Retrieval**
   - Retrieve context needed to plan the task
      - Quick search:
        ```sh
        # Find files containing term
        git grep -li <query>

        # Show matching lines
        git grep -i <query>
        ```
      - Detailed search with context:
        ```sh
        # Show matching lines
        ./scripts/search.sh "<query>"

        # Show with context
        ./scripts/search.sh "<query>" 1
        ```
      - Common locations:
        - `tasks/` - Task details
        - `journal/` - Daily updates
        - `knowledge/` - Documentation

1. **Creation**
   - Create new task file in `tasks/`
   - Add symlink in `tasks/new/`: `ln -s ../taskname.md tasks/new/`
   - Add to `TASKS.md` with 🆕 status

2. **Activation**
   - Move symlink from `new/` to `active/`: `mv tasks/new/taskname.md tasks/active/`
   - Update status in `TASKS.md` to 🏃
   - Create journal entry about starting task

3. **Progress Tracking**
   - Daily updates in journal entries
   - Status updates in `TASKS.md`
   - Subtask completion tracking
   - All edits made to file in `tasks/`

4. **Completion/Cancellation**
   - Update status in `TASKS.md` to ✅ or ❌
   - Move symlink to done/ or cancelled/: `mv tasks/active/taskname.md tasks/done/`
   - Final journal entry documenting outcomes

5. **Pausing**
   - Move symlink from `active/` to `paused/`: `mv tasks/active/taskname.md tasks/paused/`
   - Update status in `TASKS.md` to ⏸️
   - Document progress in journal

### Status Indicators

- 🆕 NEW: Task has been created
- 🏃 IN_PROGRESS: Task is being worked on
- ⏸️ PAUSED: Task was temporarily paused
- ✅ COMPLETED: Task has been completed
- ❌ CANCELLED: Task was cancelled

### Best Practices

1. **File Management**
   - Always treat `tasks/` as single source of truth
   - Never modify files directly in state directories
   - Use proper symlink commands for state transitions
   - Verify symlinks after state changes

2. **Task Creation**
   - Use clear, specific titles
   - Break down into manageable subtasks
   - Include success criteria
   - Link related resources
   - Create files in `tasks/` first, then symlink

3. **Progress Updates**
   - Regular status updates in `TASKS.md`
   - Document blockers/issues
   - Track dependencies
   - All edits made to files in `tasks/`

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

## Journal System

The journal system provides a daily log of activities, thoughts, and progress.

### Structure
- One file per day: `YYYY-MM-DD.md`
- Located in [`journal/`](./journal) directory
- Entries are to be appended, not overwritten
- Historical entries are not to be modified
- Contains:
  - Task progress updates
  - Decisions and rationale
  - Reflections and insights
  - Plans for next steps

## Knowledge Base

The knowledge base stores long-term information and documentation.

### Structure
- Located in [`knowledge/`](./knowledge)
- Organized by topic/domain
- Includes:
  - Technical documentation
  - Best practices
  - Project insights
  - Reference materials

## People Directory

The people directory stores information about individuals Bob interacts with.

### Structure
- Located in [`people/`](./people)
- Contains:
  - Individual profiles in Markdown format
  - Templates for consistent profile creation
- Each profile includes:
  - Basic information
  - Contact details
  - Interests and skills
  - Project collaborations
  - Notes and history
  - Preferences
  - TODOs and action items

### Best Practices
1. **Privacy**
   - Respect privacy preferences
   - Only include publicly available information
   - Maintain appropriate level of detail

2. **Updates**
   - Keep interaction history current
   - Update project collaborations
   - Maintain active TODO lists

3. **Organization**
   - Use consistent formatting via templates
   - Cross-reference with projects and tasks
   - Link to relevant knowledge base entries
