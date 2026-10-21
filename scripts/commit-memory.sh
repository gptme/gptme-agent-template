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
# Each non-rename entry from `git status --porcelain -z` is "XY path\0".
# Rename/copy entries emit two NUL-terminated tokens: "R  new-path\0old-path\0".
#
# We build two lists:
#   add_files    — paths to stage with git add (new/modified; NOT rename sources, which
#                  are already gone from the working tree and can't be re-added)
#   commit_paths — all paths for the git commit pathspec, including rename source paths
#                  so the staged deletion lands in the same commit as the new file.
add_files=()
commit_paths=()
prev_was_rename=false
while IFS= read -r -d '' entry; do
    if $prev_was_rename; then
        # Rename/copy source token: the file is already gone from the working tree and
        # already staged for deletion. Include in commit pathspec only — git add would
        # fail with "pathspec did not match any files".
        commit_paths+=("$entry")
        prev_was_rename=false
        continue
    fi
    # Status entries have a 2-char code + space at positions 0-2.
    [[ ${#entry} -lt 3 || "${entry:2:1}" != " " ]] && continue
    code="${entry:0:2}"
    path="${entry:3}"
    # D in index: staged deletion — file is gone from the working tree, git add
    # would fail with "pathspec did not match any files". Add to commit_paths only
    # so the staged deletion lands in the sweep commit without a git add attempt.
    if [[ "${code:0:1}" == "D" ]]; then
        commit_paths+=("$path")
        continue
    fi
    add_files+=("$path")
    commit_paths+=("$path")
    # R or C in the index column means the next NUL token is the source path.
    [[ "${code:0:1}" == "R" || "${code:0:1}" == "C" ]] && prev_was_rename=true || prev_was_rename=false
done < <(git status --porcelain -z -- "$MEMORY_PATH")

if [ ${#commit_paths[@]} -eq 0 ]; then
    echo "commit-memory: no uncommitted files in $MEMORY_DIR/ — nothing to do"
    exit 0
fi

echo "commit-memory: committing ${#commit_paths[@]} file(s) in $MEMORY_DIR/"

MSG="chore(memory): periodic sweep — commit ${#commit_paths[@]} file(s)"

# Prefer git-safe-commit (flock + hot-worktree guards + #642 safeguard). Resolve
# it by absolute path, NOT via PATH: a systemd user unit inherits a minimal PATH
# that usually lacks ~/bin, so a PATH lookup would silently exit 127 while still
# logging "committing N file(s)" — looking like it worked when it did nothing.
#
# git-safe-commit calls git add internally, so it cannot safely receive rename
# source paths (already gone from the working tree — git add would fail with
# "pathspec did not match any files"). Fall back to the plain path when rename
# sources are present; our own flock (above) already serializes against other sweeps.
SAFE_COMMIT="$REPO_ROOT/scripts/git-safe-commit"
has_rename_sources=$(( ${#commit_paths[@]} - ${#add_files[@]} ))
if [ -x "$SAFE_COMMIT" ] && [ "$has_rename_sources" -eq 0 ]; then
    # No rename/deletion-only sources — git-safe-commit handles the full add+commit
    # cycle under its own commit.lock (serializes against concurrent session commits).
    # Scope the dirty-worktree guard to off: a hot worktree may legitimately carry
    # unrelated unstaged edits from a live session that this sweep must not block on.
    GIT_SAFE_COMMIT_DIRTY_GUARD=off "$SAFE_COMMIT" "${add_files[@]}" -m "$MSG"
else
    # Fallback path (rename/deletion sources present, or git-safe-commit absent).
    # Must also serialize against session commits that hold commit.lock via
    # git-safe-commit — our commit-memory.lock only serializes sweeps against each
    # other, not against session commits. Use non-blocking so we skip rather than stall.
    exec 10>"$GIT_DIR/commit.lock"
    if ! flock -n 10; then
        echo "commit-memory: session commit in flight — skipping"
        exit 0
    fi
    if [ ${#add_files[@]} -gt 0 ]; then
        git add -- "${add_files[@]}"
    fi
    git commit -m "$MSG" -- "${commit_paths[@]}"
fi

echo "commit-memory: done"
