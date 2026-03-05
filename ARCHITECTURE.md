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

The people directory stores long-term information about individuals the agent interacts with.

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
  - Notes
  - Preferences

### Best Practices

1. **Long-term content only** — profiles should contain stable information (identity, role, skills, preferences). Volatile details (current tasks, session counts, interaction timestamps) belong in journals or task files.

2. **Privacy** — respect privacy preferences, only include publicly available information, maintain appropriate level of detail.

3. **Organization** — use consistent formatting via templates, cross-reference with projects and tasks, link to relevant knowledge base entries.

## Content Layers

Agent workspaces can include shared content via git submodules. Each layer has a different scope and audience — knowing where information belongs prevents duplication and staleness.

| Layer | Repo | Scope | Content | Audience |
|-------|------|-------|---------|----------|
| **Public shared** | gptme-contrib | All gptme users | Packages, plugins, lessons, scripts | Open source community |
| **Agent template** | gptme-agent-template | New agents | Workspace structure, templates, default configs | Agents at creation time |
| **Org shared** | (e.g. gptme-superuser) | All org agents | Strategy, people, operations, processes | Internal team |
| **Agent workspace** | (this repo) | Single agent | Identity, journals, tasks, knowledge | The agent itself |

### Where does new content go?

- **Is it useful to all gptme users?** → contrib (package, lesson, or script)
- **Should new agents start with it?** → agent template
- **Is it org-level context shared across agents?** → org repo (as submodule)
- **Is it specific to this agent?** → agent workspace

### When to upstream

- If you build a script that other agents could use → propose for contrib or org repo
- If you establish a pattern that should be the default for new agents → propose for the template
- Org-level docs should contain long-term content only; volatile details stay in agent workspaces
