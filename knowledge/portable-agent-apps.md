# Portable Agent Apps

An agent app is a repository that packages a domain workflow for an agent to
operate. It is more than a prompt and less than a bespoke runtime. The repo owns
the workflow, state boundaries, validation, and update rules for a specific
class of work.

Examples:

- a release manager for an open source project
- a support triage operator
- a research assistant for a lab
- a personal finance operator
- a self-monitoring agent over local activity data

The useful shape is one shared workflow contract with thin runtime adapters.
Do not maintain separate full prompts for every harness.

Source design note: [originating design note](https://github.com/TimeToBuild%42ob/%62ob/blob/master/knowledge/technical-designs/portable-agent-app-packaging.md).

## Core Rule

Keep workflow truth in one place.

Runtime-specific files may point to that workflow, wrap it, or expose it through
a schema a harness understands. They should not copy the workflow body by hand.
If two files repeat the same domain procedure in full, one of them is already
rotting.

## System Layer And User Layer

Split the app into two layers before adding features.

The system layer is upgradeable product surface:

- runtime entrypoints such as `AGENTS.md` and `WORKFLOW.md`
- commands, bundles, and skills
- shared procedures and checklists
- scripts, templates, and validators
- generated compatibility exports

The user layer is private or identity-bearing state:

- profiles, preferences, and local policy
- tasks and journals
- generated reports and run history
- credentials, tokens, and secrets
- long-lived local data stores

System updates may replace or regenerate system-layer files. They must preserve
user-layer files by default.

## Minimal Directory Shape

Use names that fit the app, but keep the ownership boundary visible.

```txt
agent-app/
  AGENTS.md                  # portable entrypoint; routes to owners
  WORKFLOW.md                # autonomous workflow contract, if used
  gptme.toml                 # runtime context and prompt configuration
  commands/                  # single-step procedures
  bundles/                   # ordered multi-step workflows
  skills/                    # procedural runtime guidance
  knowledge/                 # decisions, reference docs, domain context
  scripts/                   # validation, update, and export helpers
  tasks/                     # durable work state
  journal/                   # append-only operational history
  state/                     # generated runtime state
  user/                      # optional ignored/private user layer
```

The invariant is not the exact spelling. The invariant is that an update can
tell which files are product surface and which files belong to the user.

## Shared Procedure, Thin Adapters

Start with one canonical procedure. Then expose it through whatever surfaces are
actually needed.

```txt
commands/release-triage.md
```

```markdown
# Release Triage

1. Check open release blockers.
2. Read failing checks and recent maintainer comments.
3. Classify each blocker as code, docs, dependency, or human decision.
4. Update `tasks/release-triage.md`.
5. Append evidence to `journal/YYYY-MM-DD/release-triage.md`.
```

`AGENTS.md` should route to it:

```markdown
For release triage, follow `commands/release-triage.md`.
Do not duplicate the checklist here.
```

A skill wrapper should route to it too:

```markdown
# Release Triage Skill

Use `commands/release-triage.md` as the workflow owner.
Load `knowledge/releases/current.md` for release-specific context.
Write findings to `journal/`.
```

A foreign runtime export, if one is genuinely needed, should be generated or
kept as a small wrapper:

```markdown
# Release Triage

This runtime wrapper delegates to `commands/release-triage.md`.
```

That is enough. The adapter exists to satisfy the harness. The command remains
the authority.

## Update Preservation Rule

Every reusable app needs an update rule:

1. Mark generated files with their source or exporter.
2. Keep user-owned files out of generated paths.
3. Preserve `tasks/`, `journal/`, secrets, and local profiles by default.
4. Detect drift before overwriting user-edited system files.
5. Run validation after every update.

If an app cannot say what survives an update, it is a fork trap.

## Validation Checklist

Before publishing or updating an agent app, check:

- There is one canonical owner for each workflow.
- Runtime adapters route to owners instead of copying full procedures.
- User-owned paths are documented and preserved.
- Secrets and private profiles are ignored or otherwise protected.
- Operational history is append-only where practical.
- Generated files are marked or reproducible.
- Update steps include drift detection and post-update validation.
- A new runtime can be added without forking the full prompt.

## What Not To Build Yet

Do not add a marketplace, update manager, or runtime-specific export just
because the app could eventually need one. Teach the boundary first. Add
adapters when a real execution surface consumes them.
