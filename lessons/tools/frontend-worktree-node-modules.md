---
match:
  keywords:
    - "worktree has no node_modules"
    - "npx resolves a surprising tool version"
    - "missing local binaries in worktree"
description: "In a JS/TS frontend worktree, npx resolves a surprising tool version or npm test/lint reports missing local binaries because the worktree has no node_modules"
status: active
---

# Frontend Worktree Node Modules

## Rule
When using a git worktree for a JS/TS frontend repo, make sure the worktree has access to the repo's real `node_modules` before running `npx`, tests, or pre-commit hooks.

## Context
This applies in repos that keep dependencies in the main checkout while the worktree is a fresh linked directory without installed packages.

## Detection
- `npx` resolves a surprising tool version in the worktree
- pre-commit or lint fails with config-version errors that don't match the repo
- `npm test` or `npm run lint` says local binaries are missing

## Pattern
```bash
ln -s /path/to/base-checkout/node_modules /tmp/worktrees/repo/branch/node_modules
```

Run the command before verification or commit hooks. Remove the symlink before final status checks if you want a clean untracked tree.

## Outcome
- Hooks use the repo's actual toolchain instead of a random global/latest `npx` fallback
- Frontend worktrees behave like the base checkout without a full reinstall

## Related
- [exit-code-127-use-uv-run.md](./exit-code-127-use-uv-run.md) — similar "tools missing in worktree" class
