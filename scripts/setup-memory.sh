#!/bin/bash
# scripts/setup-memory.sh - Recreate the version-controlled memory bridge
#
# Claude Code stores its per-project memory under ~/.claude/projects/<mangled>/memory,
# OUTSIDE the brain repo. That directory is normally a symlink into the repo
# (memory/) so memories are version-controlled — but the symlink itself is not.
# A fresh clone on a new host therefore has NO memory wiring and fails silently:
# Claude Code just creates a plain empty directory and memories written there never
# reach git.
#
# This script recreates the bridge idempotently. Run it after a fresh clone or a
# host migration; it is safe to re-run any time (called from install-deps.sh and
# fork.sh, and assertable via --check).
#
# Harness-independent: on a pure-gptme host (no ~/.claude) it is a graceful no-op —
# memory still lives in the repo, there is just no Claude Code bridge to build.
#
# The in-repo memory location defaults to memory/ (the gptme/Claude Code convention,
# see gptme docs/memory.rst). Override with MEMORY_DIR for agents that keep memory
# elsewhere (e.g. MEMORY_DIR=knowledge/claude-memory).
#
# Behaviour:
#   - No ~/.claude on this host (pure-gptme, no Claude Code) -> graceful no-op.
#   - Bridge already a correct symlink                       -> no-op, report OK.
#   - Bridge a symlink pointing elsewhere                    -> repoint.
#   - Bridge a real EMPTY dir (the silent-fail case)         -> replace with symlink.
#   - Bridge a real NON-EMPTY dir (CC wrote memories there)  -> migrate new files
#                                                               into the repo, then
#                                                               replace with symlink.
#                                                               Never overwrites an
#                                                               existing repo file.
#
# Usage:
#   scripts/setup-memory.sh          # create/repair the bridge
#   scripts/setup-memory.sh --check  # verify only; exit 1 if the bridge is wrong
#   scripts/setup-memory.sh --help

set -euo pipefail

WORKSPACE="${WORKSPACE:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
MEMORY_DIR="${MEMORY_DIR:-memory}"
REPO_MEMORY="$WORKSPACE/$MEMORY_DIR"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"

usage() {
    sed -n '2,38p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

# Claude Code mangles the absolute workspace path into its project dir name by
# replacing '/' and '.' with '-'. e.g. /home/agent/workspace -> -home-agent-workspace
mangle_path() {
    printf '%s' "$1" | sed 's#[/.]#-#g'
}

CHECK_ONLY=0
case "${1:-}" in
    --help|-h) usage ;;
    --check) CHECK_ONLY=1 ;;
    "") ;;
    *) echo "setup-memory: unknown argument '$1' (try --help)" >&2; exit 2 ;;
esac

BRIDGE="$CLAUDE_HOME/projects/$(mangle_path "$WORKSPACE")/memory"

# Ensure the in-repo target exists with a committed stub so the bridge always has
# a real target to point at (a fresh fork must not depend on CC having run first).
ensure_repo_memory() {
    if [ ! -d "$REPO_MEMORY" ]; then
        mkdir -p "$REPO_MEMORY"
    fi
    if [ ! -f "$REPO_MEMORY/MEMORY.md" ]; then
        cat > "$REPO_MEMORY/MEMORY.md" <<'STUB'
# Auto Memory

One-line pointers to memory files live here (the index loaded each session).
STUB
    fi
}

bridge_is_correct() {
    [ -L "$BRIDGE" ] && [ "$(readlink -f "$BRIDGE")" = "$(readlink -f "$REPO_MEMORY")" ]
}

if [ "$CHECK_ONLY" -eq 1 ]; then
    if [ ! -d "$CLAUDE_HOME" ]; then
        echo "setup-memory: no $CLAUDE_HOME (pure-gptme host) — bridge not required"
        exit 0
    fi
    if bridge_is_correct; then
        echo "setup-memory: bridge OK ($BRIDGE -> $REPO_MEMORY)"
        exit 0
    fi
    echo "setup-memory: bridge MISSING or WRONG ($BRIDGE) — run scripts/setup-memory.sh" >&2
    exit 1
fi

ensure_repo_memory

# Pure-gptme host: no Claude Code, so no bridge to build. Memory still lives in the
# repo; this is a no-op, never an error (an unconditional mkdir would litter a
# non-CC host with a junk ~/.claude tree).
if [ ! -d "$CLAUDE_HOME" ]; then
    echo "setup-memory: no $CLAUDE_HOME (pure-gptme host) — memory lives in $REPO_MEMORY, no bridge needed"
    exit 0
fi

if bridge_is_correct; then
    echo "setup-memory: bridge already correct ($BRIDGE -> $REPO_MEMORY)"
    exit 0
fi

mkdir -p "$(dirname "$BRIDGE")"

if [ -L "$BRIDGE" ]; then
    # Wrong-target symlink: repoint.
    rm "$BRIDGE"
elif [ -d "$BRIDGE" ]; then
    # Real directory — the silent-fail case. Migrate any files CC wrote here into
    # the repo without overwriting existing repo files, then replace with a symlink.
    migrated=0
    shopt -s dotglob nullglob
    for src in "$BRIDGE"/*; do
        name="$(basename "$src")"
        dest="$REPO_MEMORY/$name"
        if [ -e "$dest" ]; then
            echo "setup-memory: WARNING keeping repo copy of '$name' (bridge copy parked as .bridge-backup)" >&2
            mv "$src" "$BRIDGE/$name.bridge-backup"
        else
            mv "$src" "$dest"
            migrated=$((migrated + 1))
        fi
    done
    shopt -u dotglob nullglob
    # Only remove the dir if nothing was left behind (no name collisions parked).
    if ! rmdir "$BRIDGE" 2>/dev/null; then
        echo "setup-memory: ERROR '$BRIDGE' not empty after migration (name collisions parked there) — resolve manually, not replacing with symlink" >&2
        exit 1
    fi
    [ "$migrated" -gt 0 ] && echo "setup-memory: migrated $migrated memory file(s) from bridge into $REPO_MEMORY"
elif [ -e "$BRIDGE" ]; then
    echo "setup-memory: ERROR '$BRIDGE' exists and is not a dir or symlink — resolve manually" >&2
    exit 1
fi

ln -s "$REPO_MEMORY" "$BRIDGE"
echo "setup-memory: bridge created ($BRIDGE -> $REPO_MEMORY)"
