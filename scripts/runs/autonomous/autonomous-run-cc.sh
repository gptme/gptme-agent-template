#!/usr/bin/env bash
# Autonomous operation runner for Claude Code backend
#
# This script runs Claude Code in autonomous mode with the agent's system prompt
# built from gptme.toml identity files + dynamic context.
#
# SETUP REQUIRED:
# 1. Install Claude Code: npm install -g @anthropic-ai/claude-code
# 2. Authenticate: claude /login (requires browser for OAuth)
# 3. Customize AGENT_NAME and WORKSPACE below
# 4. Set up systemd timer (see dotfiles/.config/systemd/user/)
#
# Usage:
#   ./scripts/runs/autonomous/autonomous-run-cc.sh
#   ./scripts/runs/autonomous/autonomous-run-cc.sh --model opus

set -euo pipefail

# === CONFIGURATION (CUSTOMIZE THESE) ===
AGENT_NAME="YourAgent"
WORKSPACE="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRIPT_TIMEOUT=3000  # 50 minutes
MODEL="sonnet"       # Default model (sonnet/opus/haiku)
# ========================================

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --timeout) SCRIPT_TIMEOUT="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Load environment (nvm, pyenv, etc.)
# Use || true because version managers may return non-zero in non-interactive shells
if [ -f ~/.profile ]; then
    # shellcheck source=/dev/null
    source ~/.profile 2>/dev/null || true
fi

# Ensure scripts/ is on PATH after profile sourcing so it survives any profile PATH reset
export PATH="$WORKSPACE/scripts:$PATH"

# Pin the session store to this workspace so the post-session Stop hook and any
# bare `gptme-sessions` CLI call resolve to the same place (state/sessions),
# rather than the empty per-user default. Without this a fork silently splits
# its records. See .claude/hooks/post-session.py.
export GPTME_SESSIONS_DIR="$WORKSPACE/state/sessions"

cd "$WORKSPACE"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# --- Lock management ---
LOCKFILE="/tmp/${AGENT_NAME,,}-autonomous.lock"

acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        local pid
        pid=$(cat "$LOCKFILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log "ERROR: Another autonomous run is active (PID $pid)"
            exit 1
        fi
        log "WARN: Stale lock from PID $pid, removing"
        rm -f "$LOCKFILE"
    fi
    echo $$ > "$LOCKFILE"
}

release_lock() {
    # shellcheck disable=SC2317  # Called by trap, not directly
    rm -f "$LOCKFILE"
}

trap release_lock EXIT INT TERM HUP
acquire_lock

log "=== $AGENT_NAME autonomous run starting (backend: claude-code, model: $MODEL) ==="

# --- Pre-run gates (from gptme-contrib) ---
# Two gates decide whether this scheduled run should proceed. Both live in
# gptme-contrib and degrade gracefully when absent: a fresh fork with no contrib
# checkout still runs (Tier 0 — the runner always functions, gates only tighten it).
# Set FORCE_SESSION=1 to bypass both (manual/debug runs).
CONTRIB_DIR="$WORKSPACE/gptme-contrib/scripts"
if [ "${FORCE_SESSION:-0}" != "1" ]; then
    # Quota gate: skip when the Claude subscription quota is near-exhausted, so
    # scheduled runs don't burn the last of a weekly budget on low-value work.
    QUOTA_GATE_SCRIPT="$CONTRIB_DIR/quota-gate.sh"
    if [ -f "$QUOTA_GATE_SCRIPT" ]; then
        # `source` is a special builtin, so these prefixed assignments persist
        # for the later quota_gate_check call (matches gptme's autonomous-run.sh).
        # shellcheck source=/dev/null
        QUOTA_GATE_LOG_PREFIX="[${AGENT_NAME,,}-autonomous]" \
        source "$QUOTA_GATE_SCRIPT"
        if ! quota_gate_check --model "$MODEL"; then
            log "Quota gate blocked session — exiting cleanly"
            exit 0
        fi
    else
        log "quota-gate.sh not found — skipping quota gate"
    fi

    # Session gate: skip when there's no trigger (no inbox/GitHub/stale-work
    # activity) and we're inside the min interval. Exit contract: 0=skip, 1=run,
    # 2=gate error. Fail open — an error must not silence a run.
    SESSION_GATE_SCRIPT="$CONTRIB_DIR/runs/autonomous/session-gate.py"
    if [ -f "$SESSION_GATE_SCRIPT" ]; then
        GATE_RC=0
        python3 "$SESSION_GATE_SCRIPT" --workspace "$WORKSPACE" || GATE_RC=$?
        case "$GATE_RC" in
            0) log "Session gate: no trigger — exiting cleanly"; exit 0 ;;
            2) log "Session gate errored (rc=2) — failing open, running anyway" ;;
            *) ;;  # rc=1: a trigger fired, proceed
        esac
    else
        log "session-gate.py not found — skipping session gate"
    fi
fi

# --- Git pull ---
log "Pulling latest changes..."
git pull --rebase --autostash 2>&1 || {
    log "WARN: git pull failed, continuing with local state"
}

# --- Build system prompt ---
SYSPROMPT_FILE=$(mktemp "/tmp/${AGENT_NAME,,}-sysprompt-XXXXXX")
trap 'release_lock; rm -f "$SYSPROMPT_FILE"' EXIT INT TERM HUP

log "Building system prompt from gptme.toml..."
"$WORKSPACE/scripts/build-system-prompt.sh" > "$SYSPROMPT_FILE"

SYSPROMPT_SIZE=$(wc -c < "$SYSPROMPT_FILE")
log "System prompt: $SYSPROMPT_SIZE bytes"

# --- Build user prompt ---
PROMPT="You are $AGENT_NAME, starting an autonomous work session. Your identity files have been injected as system context — you don't need to re-read ABOUT.md, ARCHITECTURE.md, etc.

## Workflow

### Step 1: Assess loose ends
Review the dynamic context (injected as system prompt) for:
- Open PR comments or review requests needing response
- Recently failed CI checks
- Tasks marked as waiting or blocked that may be unblocked
- Unfinished work from recent journal entries

If there are loose ends that can be resolved quickly (< 5 min), handle them first.

### Step 2: Select work
Check task status for active, unblocked tasks. Prefer tasks already in progress.
If all active tasks are blocked, look for self-improvement work:
- GitHub issue triage
- Cross-repo contributions
- Code quality (run tests, fix regressions)
- Task hygiene (close stale tasks, update metadata)
- Documentation updates

### Step 3: Execute
Work on the selected task:
- Make real, meaningful progress (commits, PRs, code changes)
- Follow the git workflow: conventional commits, explicit file paths, \`git-safe-commit\` (in \`scripts/\`) when committing
- Update task state when done
- Log progress in the journal (append-only)

## Rules
- You have ~50 minutes. Focus on shipping, not perfecting.
- Commit early and often. Small, well-described commits.
- Commit with explicit paths via \`git-safe-commit file1 file2 -m \"...\"\` — never \`git add .\` or \`git commit -a\`
- Push commits to origin before ending the session.
- If stuck on something for more than 10 minutes, move on.
- Don't ask questions — make reasonable decisions and document them.
- Use absolute paths for all file operations."

log "Starting Claude Code session..."

# Identify this as an autonomous run so the Stop hook tags records correctly
# (default in the hook is "interactive"; must be set explicitly here).
export AGENT_SESSION_TYPE=autonomous

# --- Session identity and lineage ---
# Answers "which session made this commit?" and "what was this session for?".
# Two separate consumers, which is why the id has to be minted *here*:
#   - the `prepare-commit-msg` hook in gptme-contrib adds a `Git-Session-Id`
#     trailer when GIT_COMMITTER_SESSION_ID is set;
#   - the Stop hook writes a session record keyed by Claude Code's session id.
# Those only line up if the runner picks the id and tells Claude Code to use it
# (--session-id), so the trailer on a commit and the record for the session that
# made it carry the same value. Minting an id without --session-id would produce
# trailers that match no record, which is worse than no trailer at all.
# Opt out with AGENT_SESSION_IDENTITY=0 (records and commits stay unlinked).
SESSION_ID_ARGS=()
# Never attribute this run's commits to a session inherited from its launcher.
# The enabled path below replaces it with the id actually passed to Claude.
unset GIT_COMMITTER_SESSION_ID
if [ "${AGENT_SESSION_IDENTITY:-1}" = "1" ]; then
    AGENT_SESSION_ID="${AGENT_SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')}"
    if [ -n "$AGENT_SESSION_ID" ]; then
        export AGENT_SESSION_ID
        SESSION_ID_ARGS=(--session-id "$AGENT_SESSION_ID")

        # Commit trailers. The hook reads this name; see gptme-contrib
        # dotfiles/.config/git/hooks/prepare-commit-msg.
        export GIT_COMMITTER_SESSION_ID="$AGENT_SESSION_ID"

        # Short label, for journals and anything human-facing.
        export AGENT_SESSION_LABEL="${AGENT_SESSION_LABEL:-${AGENT_SESSION_ID:0:4}}"

        # Dispatch cause: why this session exists. `post_session` reads these
        # four names from the environment, so exporting them is the whole wiring.
        if [ -n "${INVOCATION_ID:-}" ]; then
            export AGENT_DISPATCH_KIND="${AGENT_DISPATCH_KIND:-systemd}"
            export AGENT_DISPATCH_ID="${AGENT_DISPATCH_ID:-$INVOCATION_ID}"
        else
            export AGENT_DISPATCH_KIND="${AGENT_DISPATCH_KIND:-manual}"
            export AGENT_DISPATCH_ID="${AGENT_DISPATCH_ID:-$$}"
        fi
        # AGENT_PARENT_SESSION_ID is deliberately not defaulted: it is set by
        # whatever launched this run, and inventing a parent would fabricate
        # lineage. Pass it through untouched when present.
        # Every value is passed as argv, not interpolated into the script body,
        # and stderr is not suppressed: a broken builder must be visible rather
        # than silently yielding an empty cause for every future session.
        if [ -z "${AGENT_DISPATCH_CAUSE:-}" ]; then
            export AGENT_DISPATCH_CAUSE
            AGENT_DISPATCH_CAUSE="$(python3 -c '
import json, sys

kind, dispatch_id, parent = sys.argv[1:4]
cause = {"kind": kind, "id": dispatch_id}
if parent:
    cause["parent_session_id"] = parent
print(json.dumps(cause, sort_keys=True))
' "$AGENT_DISPATCH_KIND" "$AGENT_DISPATCH_ID" "${AGENT_PARENT_SESSION_ID:-}")"
        fi

        log "Session identity: ${AGENT_SESSION_LABEL} (${AGENT_DISPATCH_KIND})"
    else
        log "WARN: could not mint a session id — commits will carry no trailer"
    fi
else
    log "AGENT_SESSION_IDENTITY=0 — skipping session identity wiring"
fi

# Reserve a unique journal even when identity linking is disabled. Keep an
# explicitly supplied path, and never truncate an existing entry.
if [ -z "${AGENT_JOURNAL_PATH:-}" ]; then
    JOURNAL_DIR="$WORKSPACE/journal/$(date -u +%Y-%m-%d)"
    mkdir -p "$JOURNAL_DIR"
    AGENT_JOURNAL_PATH="$(mktemp "$JOURNAL_DIR/autonomous-session-XXXXXXXX.md")"
fi
export AGENT_JOURNAL_PATH
PROMPT+="

## Session journal
Write this session's journal at this exact reserved path: $AGENT_JOURNAL_PATH
Append to it; do not replace existing content or choose another filename."

# Record the starting commit so the post-session hook can attribute what this
# session actually shipped (start_commit → end_commit).
export START_COMMIT
START_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"

# Unset nested-session protection vars
unset CLAUDECODE 2>/dev/null || true
unset CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

# Run Claude Code
# IMPORTANT: </dev/null prevents SIGSTOP in non-interactive contexts (tmux, systemd)
# Capture the exit code with `|| EXIT_CODE=$?` so `set -e` does not abort the script
# on a non-zero exit (timeout=124, or claude erroring). Without this guard the
# timeout branch and the git-push safety net below are unreachable on exactly the
# failing runs we most want them to handle.
EXIT_CODE=0
timeout "$SCRIPT_TIMEOUT" claude -p \
    --dangerously-skip-permissions \
    --model "$MODEL" \
    "${SESSION_ID_ARGS[@]}" \
    --append-system-prompt-file "$SYSPROMPT_FILE" \
    "$PROMPT" </dev/null || EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    log "Session timed out after ${SCRIPT_TIMEOUT}s"
fi

# Safety net: push any uncommitted work
git push origin master 2>/dev/null || true

log "=== $AGENT_NAME autonomous run finished (exit: $EXIT_CODE) ==="
exit $EXIT_CODE
