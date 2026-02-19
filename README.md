# gptme-agent-template

[![built using gptme](https://img.shields.io/badge/built%20using-gptme%20%F0%9F%A4%96-5151f5?style=flat)](https://github.com/ErikBjare/gptme)
<!--template-->

[![Test](https://github.com/ErikBjare/gptme-agent-template/actions/workflows/test.yml/badge.svg)](https://github.com/ErikBjare/gptme-agent-template/actions/workflows/test.yml)

> [!NOTE]
> This is a template for a [gptme](https://gptme.org)-based agent. See the [agents documentation](https://gptme.org/docs/agents.html) for more information about gptme agents and how they work.
>
> [Fork it](#forking) to create a new agent with its own identity.

<!--/template-->
The name of the agent is gptme-agent.

This git repository is the brain of gptme-agent. It is a workspace of their thoughts and ideas.

 - gptme-agent will write their thoughts, plans, and ideas in this repository.
 - gptme-agent's agent harness, including this repo, is in-progress.
 - gptme-agent is encouraged to suggest improvements to their harness.

Information about gptme-agent can be found in [`ABOUT.md`](./ABOUT.md), including their personality and goals.
Information about gptme-agent's harness and architecture can be found in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

<!--template-->
## Prerequisites

Before forking or using this template, ensure you have the required dependencies installed.

**Quick Check:**
```sh
./install-deps.sh
```

**Auto-Install (where possible):**
```sh
./install-deps.sh --install
```

### Required Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| `git` | Version control | Package manager |
| `python3` | Python 3.10+ runtime | Package manager |
| `pipx` | Python CLI tool installer | `python3 -m pip install --user pipx` |
| `uv` | Fast Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `gptme` | Agent framework | `pipx install gptme` |

### Recommended Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| `tree` | Directory visualization | `apt/brew/dnf install tree` |
| `jq` | JSON processing | `apt/brew/dnf install jq` |
| `gh` | GitHub CLI | [cli.github.com](https://cli.github.com/) |
| `pre-commit` | Git hooks | `pipx install pre-commit` |
| `shellcheck` | Shell script linter | `apt/brew/dnf install shellcheck` |
<!--/template-->

## Quick Start

The easiest way to create a new agent from this template is with the `gptme-agent` CLI (included with gptme):

```sh
pipx install gptme

# Create a new agent workspace from this template
gptme-agent create ~/my-agent --name MyAgent

cd ~/my-agent

# Run the agent interactively
gptme "hello"
```

The agent's context is automatically loaded via `gptme.toml` which configures the files and context command to include.

### Claude Code Backend

The template also supports Claude Code as an alternative backend:

```sh
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Authenticate
claude /login

# Run interactively (reads AGENTS.md automatically)
claude

# Run autonomously
./scripts/runs/autonomous/autonomous-run-cc.sh
```

The `scripts/build-system-prompt.sh` script reads `gptme.toml` and builds a system prompt for Claude Code, so both backends share the same identity files and context.

## Autonomous Operation

Agents can run autonomously on a schedule using systemd (Linux) or launchd (macOS):

```sh
# Install as a system service (runs every 30 minutes by default)
gptme-agent install

# Customize the schedule
gptme-agent install --schedule "*:00"    # Every hour

# Manage the agent
gptme-agent status              # Check status
gptme-agent logs --follow       # Monitor logs
gptme-agent run                 # Trigger immediate run
gptme-agent stop                # Pause scheduled runs
```

To customize the autonomous behavior, edit the run script for your backend:
- **gptme**: `scripts/runs/autonomous/autonomous-run.sh`
- **Claude Code**: `scripts/runs/autonomous/autonomous-run-cc.sh`

**See**: [`scripts/runs/autonomous/README.md`](./scripts/runs/autonomous/README.md) for complete documentation.

**Features**:
- CASCADE workflow (Loose Ends → Task Selection → Execution)
- Two-queue system (manual + generated priorities)
- Safety guardrails (GREEN/YELLOW/RED operation classification)
- Session documentation and state management
- **Multi-backend**: Supports both gptme and Claude Code backends

## Forking (manual alternative)

If you prefer to fork manually instead of using `gptme-agent create`:

```sh
git clone https://github.com/gptme/gptme-agent-template
cd gptme-agent-template
git submodule update --init --recursive

./scripts/fork.sh <path> [<agent-name>]
```

Then follow the instructions in the output.

## Workspace Structure

 - gptme-agent keeps track of tasks in [`TASKS.md`](./TASKS.md)
 - gptme-agent keeps a journal in [`./journal/`](./journal/)
 - gptme-agent keeps a knowledge base in [`./knowledge/`](./knowledge/)
 - gptme-agent maintains profiles of people in [`./people/`](./people/)
 - gptme-agent manages work priorities in [`./state/`](./state/) using the two-queue system (manual + generated)
 - gptme-agent uses scripts in [`./scripts/`](./scripts/) for context generation, task management, and automation
 - gptme-agent can add files to [`gptme.toml`](./gptme.toml) to always include them in their context

### Key Directories

**[`state/`](./state/)**: Work queue management
- `queue-manual.md` - Manually maintained work queue with strategic context
- `queue-generated.md` - Auto-generated queue from tasks and GitHub
- See [`state/README.md`](./state/README.md) for detailed documentation

**[`scripts/`](./scripts/)**: Automation and utilities
- `context.sh` - Main context generation orchestrator
- `gptodo` - Task management CLI (install from gptme-contrib)
- `runs/autonomous/` - Autonomous operation infrastructure
- See [`scripts/README.md`](./scripts/README.md) for complete documentation

**[`lessons/`](./lessons/)**: Behavioral patterns and constraints
- Prevents known failure modes through structured guidance
- See [`lessons/README.md`](./lessons/README.md) for lesson system documentation
