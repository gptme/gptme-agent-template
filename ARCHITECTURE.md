# Architecture

This document describes the architecture and workflows of the workspace.

## Overview

This workspace implements a forkable agent architecture, designed to be used as a foundation for creating new agents. For details about:
- Forking process: See [`knowledge/agent-forking.md`](./knowledge/agent-forking.md)
- Workspace structure: See [`knowledge/forking-workspace.md`](./knowledge/forking-workspace.md)

## Search & Navigation

The workspace provides several ways to search and navigate content:
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
  - tasks/all/ - Task details
  - journal/ - Daily updates
  - knowledge/ - Documentation

## Task System
The task system is designed to help track and manage work effectively across sessions.

### Components

1. **TASKS.md**
   - Main task registry
   - Contains all tasks categorized by area
   - Each task has a clear status indicator
   - Links to task files in tasks/all/


2. **Task Files**
   - All task files stored in `tasks/all/` as single source of truth
   - Task state managed via symlinks in state directories:
     - `tasks/new/`: Symlinks to new tasks
     - `tasks/active/`: Symlinks to tasks being worked on
     - `tasks/paused/`: Symlinks to temporarily paused tasks
     - `tasks/done/`: Symlinks to completed tasks
     - `tasks/cancelled/`: Symlinks to cancelled tasks
   - Never modify task files directly in state directories, always modify in tasks/all/

3. **CURRENT_TASK.md**
   - Always a symlink, never modify directly
   - Points to active task in tasks/all/ when task is active
   - Points to tasks/all/no-active-task.md when no task is active
   - Updated using ln -sf command when switching tasks

4. **Journal Entries**
   - Daily progress logs in `./journal/`
   - Each entry documents work done on tasks
   - Includes reflections and next steps

### Task Lifecycle

0. **Retrieval**
   - Retrieve context needed to plan the task using the search tools described in "Search & Navigation" above
   - Review tasks/all/no-active-task.md if starting fresh

1. **Creation**
   - Create new task file in tasks/all/
   - Add symlink in tasks/new/: `ln -s all/taskname.md tasks/new/`
   - Add to TASKS.md with 🆕 status
   - CURRENT_TASK.md remains linked to no-active-task.md

2. **Activation**
   - Move symlink from new/ to active/: `mv tasks/new/taskname.md tasks/active/`
   - Update CURRENT_TASK.md symlink: `ln -sf tasks/all/taskname.md CURRENT_TASK.md`
   - Update status in TASKS.md to 🏃
   - Create journal entry about starting task

3. **Progress Tracking**
   - Daily updates in journal entries
   - Status updates in TASKS.md
   - Subtask completion tracking
   - All edits made to file in tasks/all/

4. **Completion/Cancellation**
   - Update status in TASKS.md to ✅ or ❌
   - Move symlink to done/ or cancelled/: `mv tasks/active/taskname.md tasks/done/`
   - Reset CURRENT_TASK.md to no-active-task.md: `ln -sf tasks/all/no-active-task.md CURRENT_TASK.md`
   - Final journal entry documenting outcomes

5. **Pausing**
   - Move symlink from active/ to paused/: `mv tasks/active/taskname.md tasks/paused/`
   - Reset CURRENT_TASK.md to no-active-task.md: `ln -sf tasks/all/no-active-task.md CURRENT_TASK.md`
   - Update status in TASKS.md to ⏸️
   - Document progress in journal

### Status Indicators

- 🆕 NEW: Task has been created
- 🏃 IN_PROGRESS: Task is being worked on
- ⏸️ PAUSED: Task was temporarily paused
- ✅ COMPLETED: Task has been completed
- ❌ CANCELLED: Task was cancelled

### Best Practices

1. **File Management**
   - Always treat tasks/all/ as single source of truth
   - Never modify files directly in state directories
   - Use proper symlink commands for state transitions
   - Verify symlinks after state changes
   - Keep no-active-task.md as template for inactive state

2. **Document Linking**
   - Always link to referenced tasks and documents
   - Use relative paths from repository root when possible
   - Common links to include:
     - Tasks mentioned in journal entries
     - Related tasks in task descriptions
     - People mentioned in any document
     - Projects being discussed
     - Knowledge base articles
   - Use descriptive link text that makes sense out of context

3. **Task Creation**
   - Use clear, specific titles
   - Break down into manageable subtasks
   - Include success criteria
   - Link related resources
   - Create files in tasks/all/ first, then symlink

3. **Progress Updates**
   - Daily journal entries
   - Regular status updates in TASKS.md
   - Document blockers/issues
   - Track dependencies
   - All edits made to files in tasks/all/

4. **Documentation**
   - Never modify CURRENT_TASK.md directly (it's a symlink)
   - Cross-reference related tasks using paths relative to repository root
   - Document decisions and rationale
   - Link to relevant documents and resources
   - Update knowledge base as needed


## Journal System

The journal system provides a daily log of activities, thoughts, and progress.

### Structure
- One file per day: `YYYY-MM-DD.md`
- Located in `./journal/` directory
- Entries are to be appended, not overwritten
- Contains:
  - Task progress updates
  - Decisions and rationale
  - Reflections and insights
  - Plans for next steps

## Knowledge Base

The knowledge base stores long-term information and documentation.

### Structure
- Located in `./knowledge/`
- Organized by topic/domain
- Includes:
  - Technical documentation
  - Best practices
  - Project insights
  - Reference materials

## People Directory

The people directory stores information about individuals the agent interacts with.

### Structure
- Located in `./people/`
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
