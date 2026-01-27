# Architecture

This document describes the architecture and workflows of the workspace.

## Overview

This workspace implements a forkable agent architecture, designed to be used as a foundation for creating new agents. For details about:

- Forking process: See [`knowledge/agent-forking.md`](./knowledge/agent-forking.md)
- Workspace structure: See [`knowledge/forking-workspace.md`](./knowledge/forking-workspace.md)

## Tools

For a information about tools used in this workspace, see [`TOOLS.md`](./TOOLS.md).

## Task System

The task system helps to track and manage work effectively across sessions. It consists of:

- Task files in [`tasks/`](./tasks/) as single source of truth
- Task management CLI via `gptodo` (optional, install from gptme-contrib)
- Daily progress logs in [`journal/`](./journal/)

See [`TASKS.md`](./TASKS.md) for more details on the task system.

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

The people directory stores information about individuals the agent interacts with.

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
