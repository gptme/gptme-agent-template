#!/usr/bin/env bash
# scripts/commit-memory.sh — periodic sweep that commits uncommitted memory/ files.
#
# Why this exists:
#   Memory is written mid-session (by a Claude Code hook, a gptme tool, or by hand).
#   If the session ends before anything commits, those edits sit uncommitted and are
#   lost on the next clean checkout or host migration. Memory is the highest
#   write-loss directory an agent has (measured ~0.68% in production) precisely
#   because hook-writes die with the session that made them.
#
#   setup-memory.sh fixes *delivery* (the ~/.claude bridge so writes reach memory/);
#   this fixes *durability* (writes that reached memory/ but were never committed).
#
# What it does:
#   - Finds uncommitted files under memory/ (tracked-modified + untracked).
#     Untracked detection respects .gitignore, so memory/pending-*.md scratch
#     files are skipped automatically.
#   - Commits them with explicit paths (never `git add .`), via git-safe-commit
#     when present (flock-serialized, hot-worktree safe) or a flock'd plain commit.
#   - Silent no-op when there is nothing to commit.
#
# This is OPT-IN. It is not wired into install-deps.sh/fork.sh because not every
# host has systemd or wants an auto-committing timer. Enable it deliberately with
# the matching dotfiles/.config/systemd/user/agent-commit-memory.{service,timer}.example
# (or any cron/launchd equivalent).
#
# Usage:
#   scripts/commit-memory.sh          # run one sweep
#   MEMORY_DIR=knowledge/claude-memory scripts/commit-memory.sh
#
# Override MEMORY_DIR to match setup-memory.sh for agents that keep memory
# elsewhere. Defaults to memory/.
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
MEMORY_DIR="${MEMORY_DIR:-memory}"
MEMORY_PATH="$REPO_ROOT/$MEMORY_DIR"

cd "$REPO_ROOT"

if [ ! -d "$MEMORY_PATH" ]; then
    echo "commit-memory: no $MEMORY_DIR/ directory — nothing to do"
    exit 0
fi

# Non-blocking lock: if another sweep (or session commit) is mid-flight, skip
# silently rather than stack up. Keyed to the repo's git dir so multiple clones
# don't share a lock.
GIT_DIR="$(git rev-parse --git-dir)"
exec 9>"$GIT_DIR/commit-memory.lock"
if ! flock -n 9; then
    echo "commit-memory: another sweep is running — skipping"
    exit 0
fi

# Collect uncommitted memory files (modified + untracked), newline-safe.
# --others --exclude-standard honors .gitignore (skips memory/pending-*.md).
files=()
while IFS= read -r -d '' f; do
    files+=("$f")
done < <(git status --porcelain -z -- "$MEMORY_PATH" | \
         while IFS= read -r -d '' entry; do printf '%s\0' "${entry:3}"; done)

if [ ${#files[@]} -eq 0 ]; then
    echo "commit-memory: no uncommitted files in $MEMORY_DIR/ — nothing to do"
    exit 0
fi

echo "commit-memory: committing ${#files[@]} file(s) in $MEMORY_DIR/"

MSG="chore(memory): periodic sweep — commit ${#files[@]} file(s)"

# Prefer git-safe-commit (flock + hot-worktree guards + #642 safeguard). Resolve
# it by absolute path, NOT via PATH: a systemd user unit inherits a minimal PATH
# that usually lacks ~/bin, so a PATH lookup would silently exit 127 while still
# logging "committing N file(s)" — looking like it worked when it did nothing.
SAFE_COMMIT="$REPO_ROOT/scripts/git-safe-commit"
if [ -x "$SAFE_COMMIT" ]; then
    # Scope the dirty-worktree guard to off: we commit an explicit memory-only
    # pathspec, and a hot worktree may legitimately carry unrelated unstaged
    # edits from a live session that this sweep must not block on.
    GIT_SAFE_COMMIT_DIRTY_GUARD=off "$SAFE_COMMIT" "${files[@]}" -m "$MSG"
else
    # Fallback: the lock above already serializes us against other sweeps.
    git add -- "${files[@]}"
    git commit -- "${files[@]}" -m "$MSG"
fi

echo "commit-memory: done"
