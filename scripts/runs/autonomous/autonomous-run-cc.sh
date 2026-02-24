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
- Follow the git workflow: conventional commits, respect pre-commit hooks
- Update task state when done
- Log progress in the journal (append-only)

## Rules
- You have ~50 minutes. Focus on shipping, not perfecting.
- Commit early and often. Small, well-described commits.
- Push commits to origin before ending the session.
- If stuck on something for more than 10 minutes, move on.
- Don't ask questions — make reasonable decisions and document them.
- Use absolute paths for all file operations."

log "Starting Claude Code session..."

# Unset nested-session protection vars
unset CLAUDECODE 2>/dev/null || true
unset CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

# Run Claude Code
# IMPORTANT: </dev/null prevents SIGSTOP in non-interactive contexts (tmux, systemd)
timeout "$SCRIPT_TIMEOUT" claude -p \
    --dangerously-skip-permissions \
    --model "$MODEL" \
    --append-system-prompt-file "$SYSPROMPT_FILE" \
    "$PROMPT" </dev/null

EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    log "Session timed out after ${SCRIPT_TIMEOUT}s"
fi

# Safety net: push any uncommitted work
git push origin master 2>/dev/null || true

log "=== $AGENT_NAME autonomous run finished (exit: $EXIT_CODE) ==="
exit $EXIT_CODE
