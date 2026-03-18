# Skills Directory

This directory contains **agent-specific skills** — enhanced lessons that bundle workflows, scripts, and utilities.

Skills differ from lessons:
- Lessons: concise behavioral guidance (30-50 lines), auto-activated by keywords
- Skills: executable workflows with bundled scripts, explicitly loaded

## Available Skills

Agent-specific skills go here. Shared/reusable skills live in `gptme-contrib/skills/`:

| Skill | Purpose |
|-------|---------|
| `gptme-contrib/skills/template-skill` | Starting point for new skills |
| `gptme-contrib/skills/code-review-helper` | Structured code review workflow |
| `gptme-contrib/skills/progressive-disclosure` | Managing information density |
| `gptme-contrib/skills/artifact-publishing` | Publishing artifacts (blog, twitter, github) |

## Creating a Skill

1. Create a directory: `skills/my-skill/`
2. Add `skills/my-skill/SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: One-line description of what this skill does
---
```

3. Add helper scripts, templates, or resources in the same directory

## Configuration

Skills are discovered via `gptme.toml`:

```toml
[lessons]
dirs = ["lessons", "skills", "gptme-contrib/lessons", "gptme-contrib/skills"]
```

The `skills/` directory is searched alongside `lessons/` for skill files.

## Related

- [gptme-contrib/skills/](../gptme-contrib/skills/README.md) — Shared skills
- [lessons/README.md](../lessons/README.md) — Lesson system
