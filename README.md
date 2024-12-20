# gptme-agent-template

[![built using gptme](https://img.shields.io/badge/built%20using-gptme%20%F0%9F%A4%96-5151f5?style=flat)](https://github.com/ErikBjare/gptme)

<!--template-->
> [!NOTE]
> This is a template for a [gptme](https://gptme.org)-based agent.
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
 - gptme-agent can add files to [`gptme.toml`](./gptme.toml) to always include them in their context
