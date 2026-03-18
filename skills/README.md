# Skills

Use skills to extend your capabilities with executable workflows, bundled scripts, and reusable utilities. Reach for a skill when you need a multi-step workflow with helper scripts — use a lesson when you need concise behavioral guidance that activates automatically via keywords.

## When to Use Each

| Situation | Use |
|-----------|-----|
| Need step-by-step workflow guidance | Skill |
| Need bundled scripts for a task | Skill |
| Need to remember a pattern or rule | Lesson |
| Guidance should auto-activate on keywords | Lesson |

## Available Skills

Shared skills in `gptme-contrib/skills/` are ready to use:

| Skill | When to use |
|-------|-------------|
| `template-skill` | Starting point when creating a new skill |
| `code-review-helper` | Structured PR review workflow |
| `progressive-disclosure` | Managing context/information density |
| `artifact-publishing` | Publishing blog posts, tweets, GitHub releases |

Agent-specific skills go in this directory (`skills/`).

## Creating a Skill

1. Create `skills/my-skill/SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: One-line description of what this skill does and when to invoke it
---

# My Skill

Instructions for executing the skill...
```

2. Add helper scripts, templates, or resources in `skills/my-skill/`

Skills are discovered automatically via `gptme.toml` — no extra config needed once the `skills/` dir is in `[lessons] dirs`.

## Related

- [gptme-contrib/skills/](../gptme-contrib/skills/README.md) — Shared skills library
- [lessons/README.md](../lessons/README.md) — Lesson system
