# Skills Directory

This directory contains **skills** — enhanced lessons that bundle workflows, scripts, and utilities for gptme agents.

## Skills vs. Lessons

| Feature | Lesson | Skill |
|---------|--------|-------|
| **Purpose** | Behavioral guidance | Executable workflows |
| **Content** | Patterns, rules, examples | Instructions + bundled scripts |
| **Activation** | Automatic via keywords | Explicit loading |
| **Length** | 30-50 lines (primary) | Hundreds of lines |
| **Scripts** | None | Bundled helper utilities |

## Creating a Skill

Skills use a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

# My Skill

## Overview
...
```

### Directory structure

```text
skills/
└── my-skill/
    ├── SKILL.md        # Required: instructions + frontmatter
    └── scripts/        # Optional: supporting scripts
        └── helper.py
```

## Shared Skills (gptme-contrib)

Additional shared skills are available in `gptme-contrib/skills/`:

- `template-skill` — Starting point for creating new skills
- `progressive-disclosure` — Pattern for progressive context loading
- `code-review-helper` — Code review workflow
- `artifact-publishing` — Publishing blog posts and content

## Configuration

Skills are automatically crawled by gptme when listed in `gptme.toml`:

```toml
[lessons]
dirs = ["lessons", "skills", "gptme-contrib/lessons", "gptme-contrib/skills"]
```

## Related

- [gptme-contrib/skills/](../gptme-contrib/skills/) — Shared skills
- [lessons/README.md](../lessons/README.md) — Lesson system
- [gptme skill marketplace](https://github.com/gptme/gptme/issues/1566) — Publishing skills
