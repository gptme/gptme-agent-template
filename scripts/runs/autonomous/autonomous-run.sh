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
REPO_OWNER="your-github-username"  # Replace with your GitHub username
REPO_NAME="your-agent-workspace"  # Replace with your workspace repo name
SCRIPT_TIMEOUT=3000  # 50 minutes in seconds (allows hourly scheduling with buffer)
# ========================================

# Determine script directory for relative paths
REPO_DIR="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="$REPO_DIR/scripts"

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    # Kill any gptme child processes
    pkill -P $$ gptme 2>/dev/null || true
    sleep 1
    # Clean up temporary prompt file
    [ -f "$PROMPT_FILE" ] && rm -f "$PROMPT_FILE"
}

# Ensure cleanup on exit
trap cleanup EXIT
trap 'log "ERROR: Script failed at line $LINENO"' ERR

# Pull latest changes from remote
log "Pulling latest changes from git..."
cd "$WORKSPACE"
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

# Detect if this is a scheduled run or manual trigger
if [ -n "$INVOCATION_ID" ]; then
    RUN_TYPE="Scheduled (systemd)"
else
    RUN_TYPE="Manual"
fi

# Queue file paths (customize queue system as needed)
MANUAL_QUEUE="$WORKSPACE/state/queue-manual.md"
GENERATED_QUEUE="$WORKSPACE/state/queue-generated.md"

PROMPT_FILE=/tmp/autonomous-prompt-$$.txt

# Create autonomous operation prompt
# CUSTOMIZE THIS SECTION with your agent's specific workflow and guidelines
cat > $PROMPT_FILE <<EOF
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
3. Commit: \`git add journal/\*.md state/queue-manual.md && git commit -m "docs: session updates" && git push\`
4. Use \`complete\` tool when finished

Begin your autonomous work session now.
EOF

# Run gptme with the autonomous prompt (with timeout)
log "Starting gptme session..."
timeout $SCRIPT_TIMEOUT gptme --non-interactive "$PROMPT_FILE" 2>&1 || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}

# Check exit status
if [ $EXIT_CODE -eq 0 ]; then
    log "Autonomous run completed successfully"
    exit 0
elif [ $EXIT_CODE -eq 124 ]; then
    log "WARNING: Autonomous run timed out after ${SCRIPT_TIMEOUT}s"
    exit 124
else
    log "ERROR: Autonomous run failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
