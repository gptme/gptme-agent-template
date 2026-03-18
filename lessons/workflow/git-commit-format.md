---
match:
  keywords:
    - "conventional commits"
    - "commit message format"
    - "write commit message"
    - "commit type prefix"
    - "feat fix docs commit"
status: active
---

# Git Commit Message Format

## Rule
All commit messages must follow Conventional Commits format with a type prefix, optional scope, and short description.

## Context
When creating git commits in any workspace or repository.

## Detection
Observable signals indicating incorrect commit format:
- Commit message missing type prefix (feat, fix, docs, etc.)
- Vague descriptions ("update code", "fix stuff", "wip")
- Multiple unrelated changes in a single commit
- Missing scope when it would add clarity

## Pattern
```text
type(scope): short description

Optional longer description explaining why,
not just what changed.
```

**Common types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```text
feat(auth): add JWT-based authentication
fix(shell): preserve output when last line lacks trailing newline
docs(lessons): add absolute-paths lesson
refactor(context): migrate shell scripts to Python
test(tasks): add integration tests for task state machine
chore: update gptme-contrib submodule
```

**With scope** (preferred when the change is component-specific):
```text
fix(api): handle rate limit errors gracefully

Add exponential backoff for 429 responses.
Includes retry logic with configurable max attempts.
```

## Outcome
Following this pattern ensures:
- Automated versioning and changelog generation works correctly
- Clear, scannable git history
- Easy to identify the nature of a change at a glance
- Consistent format across all repositories

## Related
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
