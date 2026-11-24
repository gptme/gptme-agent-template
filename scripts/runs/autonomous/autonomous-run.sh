#!/bin/bash
# Autonomous operation runner template for gptme agents
# This script runs gptme in autonomous mode with conversation history and safety guidelines
#
# CUSTOMIZATION REQUIRED:
# 1. Update AGENT_NAME with your agent's name
# 2. Update WORKSPACE with your workspace path
# 3. Update REPO_OWNER/REPO_NAME if using GitHub integration
# 4. Customize the prompt template in the "Create autonomous operation prompt" section
# 5. Adjust SCRIPT_TIMEOUT based on your scheduling needs
#
# CONCURRENT EXECUTION:
# This script does NOT support concurrent execution.
# Multiple simultaneous runs can cause git conflicts and file operation race conditions.
# Implement a lock mechanism if scheduling frequent runs.

set -e  # Exit on error

# === CONFIGURATION (CUSTOMIZE THESE) ===
AGENT_NAME="YourAgent"  # Replace with your agent's name
WORKSPACE="/path/to/your/workspace"  # Replace with your workspace path
# shellcheck disable=SC2034  # These are template placeholders for users to customize
REPO_OWNER="your-github-username"  # Replace with your GitHub username
# shellcheck disable=SC2034  # These are template placeholders for users to customize
REPO_NAME="your-agent-workspace"  # Replace with your workspace repo name
SCRIPT_TIMEOUT=3000  # 50 minutes in seconds (allows hourly scheduling with buffer)
# ========================================

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Cleanup function
cleanup() {
    # shellcheck disable=SC2317  # Called by trap, not directly
    log "Cleaning up..."
    # Stop any remaining children. gptme runs under `timeout`, so it is a
    # grandchild: signal our direct children and `timeout` forwards the TERM.
    # shellcheck disable=SC2317  # Called by trap, not directly
    pkill -TERM -P $$ 2>/dev/null || true
    # shellcheck disable=SC2317  # Called by trap, not directly
    sleep 1
    # Clean up temporary prompt file. Guard the unset case so an early skip
    # (session gate, before PROMPT_FILE is assigned) still exits 0 under set -e.
    # shellcheck disable=SC2317  # Called by trap, not directly
    if [ -n "${PROMPT_FILE:-}" ] && [ -f "$PROMPT_FILE" ]; then
        rm -f "$PROMPT_FILE"
    fi
}

# Ensure cleanup on exit
trap cleanup EXIT
trap 'log "ERROR: Script failed at line $LINENO"' ERR

# Detect scheduled vs manual before any gate. systemd sets INVOCATION_ID on
# service processes; a direct terminal run does not. Identify the invocation
# here so a TTY/manual run skips the session gate instead of no-op'ing the
# README "Test Manually" path. RUN_TYPE also feeds the gptme prompt later.
if [ -n "${INVOCATION_ID:-}" ]; then
    RUN_TYPE="Scheduled (systemd)"
else
    RUN_TYPE="Manual"
fi

# --- Pre-run session gate (from gptme-contrib) ---
# Skip quiet scheduled runs when there's no trigger. Lives in gptme-contrib and
# degrades gracefully when absent: a fresh fork with no contrib checkout still
# runs. Quota gate is intentionally not wired here — it is a Claude-subscription
# check, and this gptme runner is the failover when that subscription is exhausted.
# Bypass: FORCE_SESSION=1, or a TTY stdin (direct manual run). Scheduled
# systemd/cron invocations have no TTY and still go through the gate.
CONTRIB_DIR="$WORKSPACE/gptme-contrib/scripts"
if [ "${FORCE_SESSION:-0}" = "1" ]; then
    log "FORCE_SESSION=1 — skipping session gate"
elif [ -t 0 ]; then
    log "Manual run (TTY stdin) — skipping session gate"
else
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

# Pull latest changes from remote
log "Pulling latest changes from git..."
cd "$WORKSPACE"
# Compute REPO_DIR after cd so scripts/ always resolves to the workspace repo
REPO_DIR="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$REPO_DIR/scripts"
export PATH="$REPO_DIR/scripts:$PATH"
if ! git pull; then
    log "WARNING: Git pull failed, continuing with current state"
fi

# Generate work queue from task files (if script exists)
if [ -f "$SCRIPT_DIR/generate-work-queue.py" ]; then
    log "Generating work queue from task files..."
    "$SCRIPT_DIR/generate-work-queue.py" 2>&1 || log "⚠️  Work queue generation encountered issues"
fi

# Enable chat history for context continuity
export GPTME_CHAT_HISTORY=true

log "Starting autonomous run (timeout: ${SCRIPT_TIMEOUT}s / 50 minutes)..."
log "Workspace: $WORKSPACE"
log "Run type: $RUN_TYPE"

# Queue file paths (customize queue system as needed)
# shellcheck disable=SC2034  # Template placeholders for agent customization
MANUAL_QUEUE="$WORKSPACE/state/queue-manual.md"
# shellcheck disable=SC2034  # Template placeholders for agent customization
GENERATED_QUEUE="$WORKSPACE/state/queue-generated.md"

PROMPT_FILE=/tmp/autonomous-prompt-$$.txt

# Create autonomous operation prompt
# CUSTOMIZE THIS SECTION with your agent's specific workflow and guidelines
cat > "$PROMPT_FILE" <<EOF
You are $AGENT_NAME, running autonomously.

**Current Time**: $(date --iso=minutes)
**Run Type**: $RUN_TYPE
**Context Budget**: 200k tokens (use ~160k for work, save ~40k margin for completion)

**Recent Activity**: You have summaries of recent conversations via GPTME_CHAT_HISTORY.

## Required Workflow

Focus on EXECUTION over planning. Three-step workflow optimized for doing work:

**Step 1**: Quick Loose Ends Check (2-5 min max)
- Check git status, critical notifications only
- Fix only immediate blockers

**Step 2**: Task Selection via CASCADE (5-10 min max)
1. **PRIMARY**: Read state/queue-manual.md "Planned Next" section
   - If empty or missing: Fall back to state/queue-generated.md
2. **SECONDARY**: Check notifications for direct assignments
3. **TERTIARY**: Check workspace tasks if PRIMARY/SECONDARY blocked
4. **COMMIT to task** before completing Step 2

**Step 3**: EXECUTION (20-30 min - the main focus!)
- This is where the real work happens
- Don't stop early - keep working until real blocker or token hint
- Make substantial progress on the selected task
- Verify your work (tests, CI checks, etc.)

**Real Blocker Criteria** (STRICT - all three sources must be blocked):
- Checked PRIMARY → All blocked
- Checked SECONDARY → Nothing actionable
- Checked TERTIARY → All blocked

## Key Principles

- **Verifiable Tasks**: Prioritize tasks with tests/CI/verification
- **Efficient Selection**: <10 tool calls OR 20k tokens for Step 2
- **Token Efficiency**:
  - Read full files when <1000 lines (not partial with head/tail)
  - Filter shell output with grep when expecting large dumps
  - Concise session summaries (5-10 lines) without repeating work queue
- **Absolute Paths**: Always use $WORKSPACE for workspace files

## Git Workflow

**For External Repos**:
- MUST use worktrees for PRs
- MUST read/create/update/comment on PRs
- Never commit directly to master/main on external repos

**For Workspace Repo**:
- Can commit directly to master
- Follow Conventional Commits format

## Critical File Operations

**Always use ABSOLUTE PATHS** for workspace files:
- Correct: \`$WORKSPACE/journal/2025-10-19-topic.md\`
- Wrong: \`journal/2025-10-19-topic.md\` (breaks when cwd changes)

**Journal Location**:
- Create in workspace: \`$WORKSPACE/journal/YYYY-MM-DD-topic.md\`
- NEW topics = NEW files with descriptive names
- NEVER create journal/ in external repos

## Session Completion

Keep documentation BRIEF (2-5 min max):
1. Return to workspace: \`cd $WORKSPACE\`
2. **Update work queue**: \`state/queue-manual.md\`
   - One-line "Current Run" status
   - Refresh "Planned Next" (3 tasks)
   - Update timestamp
3. Commit: \`git-safe-commit journal/<today>/*.md state/queue-manual.md -m "docs: session updates" && git push\`
4. Use \`complete\` tool when finished

Begin your autonomous work session now.
EOF

# --- Session identity and lineage ---
# Same contract as autonomous-run-cc.sh: the `Git-Session-Id` trailer on a
# commit and the session record for the run that made it must carry the same
# value. gptme has no --session-id; its conversation id is --name, which also
# names the log directory holding the trajectory. So the runner mints one id,
# uses it as the conversation name, exports it as the trailer, and records the
# session under it after gptme exits (gptme has no Stop hook to do that).
# Opt out with AGENT_SESSION_IDENTITY=0 (records and commits stay unlinked).
GPTME_NAME_ARGS=()
# Never attribute this run's commits to a session inherited from its launcher.
unset GIT_COMMITTER_SESSION_ID
if [ "${AGENT_SESSION_IDENTITY:-1}" = "1" ]; then
    AGENT_SESSION_ID="${AGENT_SESSION_ID:-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')}"
    if [ -n "$AGENT_SESSION_ID" ]; then
        export AGENT_SESSION_ID
        GPTME_NAME_ARGS=(--name "$AGENT_SESSION_ID")
        export GIT_COMMITTER_SESSION_ID="$AGENT_SESSION_ID"
        export AGENT_SESSION_LABEL="${AGENT_SESSION_LABEL:-${AGENT_SESSION_ID:0:4}}"
        # Dispatch cause: `post_session` reads these names from the environment.
        if [ -n "${INVOCATION_ID:-}" ]; then
            export AGENT_DISPATCH_KIND="${AGENT_DISPATCH_KIND:-systemd}"
            export AGENT_DISPATCH_ID="${AGENT_DISPATCH_ID:-$INVOCATION_ID}"
        else
            export AGENT_DISPATCH_KIND="${AGENT_DISPATCH_KIND:-manual}"
            export AGENT_DISPATCH_ID="${AGENT_DISPATCH_ID:-$$}"
        fi
        # AGENT_PARENT_SESSION_ID is passed through, never defaulted: inventing
        # a parent would fabricate lineage.
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
export AGENT_SESSION_TYPE="${AGENT_SESSION_TYPE:-autonomous}"
export START_COMMIT
START_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"

# Record the session under AGENT_SESSION_ID via the shared post-session hook,
# pointing it at gptme's trajectory for the conversation named above. Searches
# gptme's log roots for that exact name; the id is a fresh UUID, so a match is
# this run's log. Never fails the run: a missing hook, log, or gptme-sessions
# only costs the record.
record_session() {
    [ -n "${AGENT_SESSION_ID:-}" ] && [ "${#GPTME_NAME_ARGS[@]}" -gt 0 ] || return 0
    local hook="$WORKSPACE/.claude/hooks/post-session.py"
    [ -f "$hook" ] || { log "post-session hook not found — no session record"; return 0; }
    local root transcript=""
    for root in "${GPTME_LOGS_HOME:-}" "${XDG_DATA_HOME:+$XDG_DATA_HOME/gptme/logs}" \
        "$HOME/.local/share/gptme/logs" "$HOME/Library/Application Support/gptme/logs"; do
        if [ -n "$root" ] && [ -f "$root/$AGENT_SESSION_ID/conversation.jsonl" ]; then
            transcript="$root/$AGENT_SESSION_ID/conversation.jsonl"
            break
        fi
    done
    if [ -z "$transcript" ]; then
        log "WARN: no gptme log for conversation $AGENT_SESSION_ID — no session record"
        return 0
    fi
    python3 -c '
import json, sys

session_id, transcript = sys.argv[1:3]
print(json.dumps({
    "hook_event_name": "Stop",
    "harness": "gptme",
    "session_id": session_id,
    "transcript_path": transcript,
}))
' "$AGENT_SESSION_ID" "$transcript" | python3 "$hook" || true
}

# Run gptme with the autonomous prompt (with timeout)
log "Starting gptme session..."
timeout "$SCRIPT_TIMEOUT" gptme --non-interactive "${GPTME_NAME_ARGS[@]}" "$PROMPT_FILE" 2>&1 || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}
record_session

# Check exit status
if [ "$EXIT_CODE" -eq 0 ]; then
    log "Autonomous run completed successfully"
    exit 0
elif [ "$EXIT_CODE" -eq 124 ]; then
    log "WARNING: Autonomous run timed out after ${SCRIPT_TIMEOUT}s"
    exit 124
else
    log "ERROR: Autonomous run failed with exit code $EXIT_CODE"
    exit "$EXIT_CODE"
fi
