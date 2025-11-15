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

## Usage

Run gptme-agent with:

```sh
pipx install gptme

# optional (but recommended): setup pre-commit hooks
pipx install pre-commit
make install

# run gptme-agent
./run.sh "<prompt>"
```

## Autonomous Operation

gptme-agent can run autonomously on a schedule using the included infrastructure:

**Quick Setup**:
1. Customize `scripts/runs/autonomous/autonomous-run.sh` with your agent's details
2. Edit the prompt template in the script to match your agent's goals
3. Set up systemd timer (Linux) or cron job for scheduling
4. Monitor via logs: `journalctl --user -u agent-autonomous.service`

**See**: [`scripts/runs/autonomous/README.md`](./scripts/runs/autonomous/README.md) for complete documentation.

**Features**:
- CASCADE workflow (Loose Ends → Task Selection → Execution)
- Two-queue system (manual + generated priorities)
- Safety guardrails (GREEN/YELLOW/RED operation classification)
- Session documentation and state management
- Systemd timer templates included

## Forking

You can create a clean fork of gptme-agent by running:

```sh
./fork.sh <path> [<agent-name>]
```

Then simply follow the instructions in the output.

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
- `tasks.py` - Task management CLI (optional, from gptme-contrib)
- `runs/autonomous/` - Autonomous operation infrastructure
- See [`scripts/README.md`](./scripts/README.md) for complete documentation

**[`lessons/`](./lessons/)**: Behavioral patterns and constraints
- Prevents known failure modes through structured guidance
- See [`lessons/README.md`](./lessons/README.md) for lesson system documentation
