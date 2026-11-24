# Workspace Structure for Forkable Agents

This describes the template's manual `scripts/fork.sh` path.
<!--template-->
The `gptme-agent create` CLI is implemented by gptme and can evolve independently;
check its output rather than assuming the two paths customize every file alike.
<!--/template-->

## Directory Structure Overview

A default manual fork includes:

```tree
.
├── README.md              # Overview, with template-only sections removed
├── ABOUT.md               # Identity scaffold customized with the new name
├── SOUL.md                # Runtime voice/persona scaffold
├── ARCHITECTURE.md        # System architecture
├── AGENTS.md              # Cross-runtime instructions
├── TASKS.md               # Task conventions
├── WORKFLOW.md            # Autonomous workflow contract
├── TOOLS.md               # Tool integrations
├── gptme.toml             # Agent configuration and prompt files
├── docs/                  # First-task and operations guides
├── scripts/               # Helpers and optional autonomous launchers
├── gptme-contrib/          # Shared helpers, lessons and packages (submodule)
├── tasks/                 # Flat Markdown tasks; state is YAML frontmatter
│   └── templates/         # Includes the initial identity-interview template
├── journal/               # Empty initially
├── knowledge/             # Selected forking guides, not a copied knowledge corpus
├── memory/                # MEMORY.md stub for durable memory
├── lessons/               # Lesson scaffolding and selected examples
├── people/templates/      # Person template; no pre-created creator profile
├── projects/              # Optional project area
└── state/                 # Optional queue/state area
```

`--minimal` disables autonomous operation, people, projects and state by default.
The corresponding `--with-*` flags opt them back in. Some disabled areas receive
stub READMEs so links still resolve; a directory existing does not prove its
feature is enabled. Use `scripts/fork.sh --help` for the exact flag set.

## What Stays

The script explicitly selects core documentation, configuration, helper scripts,
lesson scaffolding and templates. It copies `docs/` (excluding the template demo
media), the two forking guides `knowledge/agent-forking.md` and
`knowledge/forking-workspace.md`, and the memory index stub. It does not preserve
an arbitrary `knowledge/ai/` directory, all technical designs, or every source
knowledge document. The copy list in `scripts/fork.sh` is authoritative.

## What Starts Fresh

- Journal entries, active task content, project links and personal histories are
  not inherited as a working corpus.
- Identity files are scaffolds customized with the new name, not a completed
  identity interview. Review them before giving the agent real work.
- The default person template is copied, but the creator's profile must be
  supplied by the new workspace owner.
- A task's lifecycle state belongs in its YAML frontmatter, not `tasks/active/`
  or `tasks/done/` directories.

## Fork Creation Steps

1. Initialize the source checkout's submodules and run `scripts/fork.sh` with a
   new target directory and name.
2. Inspect the generated workspace and its printed next steps.
3. Configure provider access and review identity/configuration files.
4. Complete the identity interview in
   [`tasks/templates/initial-agent-setup.md`](../tasks/templates/initial-agent-setup.md).
5. Try the disposable coding loop in
   [`docs/first-task-walkthrough.md`](../docs/first-task-walkthrough.md).
6. Before scheduling autonomous runs, configure and manually test the selected
   launcher; see the
   [autonomous setup guide](../scripts/runs/autonomous/README.md).

For the detailed process, see [agent-forking.md](./agent-forking.md).
