# Architecture

This document describes the architecture and workflows of the workspace.

## Overview

This workspace implements a forkable agent architecture, designed to be used as a foundation for creating new agents. For details about:

- Forking process: See [`knowledge/agent-forking.md`](./knowledge/agent-forking.md)
- Workspace structure: See [`knowledge/forking-workspace.md`](./knowledge/forking-workspace.md)

## Tools

For information about tools used in this workspace, see [`TOOLS.md`](./TOOLS.md).

## Task System

The task system helps to track and manage work effectively across sessions. It consists of:

- Task files in [`tasks/`](./tasks/) as single source of truth
- Task management CLI via `gptodo` (optional, install from gptme-contrib)
- Daily progress logs in [`journal/`](./journal/)

See [`TASKS.md`](./TASKS.md) for more details on the task system.

## Journal System

The journal system provides a daily log of activities, thoughts, and progress.

### Structure

- Subdirectory per day: `journal/YYYY-MM-DD/HHMMSS-topic.md`
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

Agent workspaces include shared content via git submodules. Each layer has a different scope — knowing where information belongs prevents duplication and staleness.

| Layer | Repo | Scope | Content |
|-------|------|-------|---------|
| **Agent template** | gptme-agent-template | All agents | Workspace structure, scripts, configs, templates |
| **Public shared** | gptme-contrib | All gptme users | Packages, plugins, lessons, pre-commit hooks |
| **Org shared** | (e.g. gptme-superuser) | Org agents | Strategy, people, operations, processes |
| **Agent workspace** | (this repo) | Single agent | Identity, journals, tasks, knowledge |

### Template and contrib relationship

Most files in the agent template should be **symlinks into gptme-contrib** — this way agents get updates by simply updating the contrib submodule. Examples: pre-commit hooks, lesson files, shared scripts, validators.

Some files **cannot be symlinks** because they are agent-specific or need local customization: `ABOUT.md`, `SOUL.md`, `gptme.toml`, `README.md`, task/journal content.

The rule of thumb: if the content is generic and useful across agents, it should live in contrib with the template symlinking to it. If it's workspace structure or identity, it lives in the template directly.

### Staying current with the template

Agents forked from this template will drift over time as the template evolves. To check what's changed:

```sh
# Add template as a remote (one-time)
git remote add template https://github.com/gptme/gptme-agent-template.git

# Fetch and diff against current template
git fetch template master
git diff HEAD...template/master -- ARCHITECTURE.md scripts/ .pre-commit-config.yaml
```

For contrib, agents using symlinks get updates automatically when the submodule is bumped. Check for broken or missing symlinks with: `find . -xtype l` (finds broken symlinks).

### Where does new content go?

- **Should new agents start with it?** → agent template (symlink to contrib if generic)
- **Is it useful to all gptme users?** → contrib (package, lesson, or script)
- **Is it org-level context shared across agents?** → org repo (as submodule)
- **Is it specific to this agent?** → agent workspace

### When to upstream

- If you build a script/lesson that other agents could use → propose for contrib
- If you establish a structural pattern that should be the default → propose for the template
- Org-level docs should contain long-term content only; volatile details stay in agent workspaces
