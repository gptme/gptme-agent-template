#!/usr/bin/env bash
# Event-driven inbox pickup: one bounded session for pending agent messages.
#
# Triggered by agent-msg-run.path (a message landed in messages/inbox/) and by
# agent-msg-run.timer (retry while a session held the slot). Both start the
# oneshot service that runs this script, so there is one code path.
#
# Contract:
#   - One agent-message session at a time (non-blocking flock). A second
#     trigger exits 0 immediately; the retry timer picks the message up later.
#   - Nothing pending -> exit 0 without starting a model session.
#   - A message is dispatched at most AGENT_MSG_MAX_ATTEMPTS times. A handler
#     that ends without `reply` or `ack` (see TOOLS.md) would otherwise be
#     relaunched on every retry forever.
#   - Every dispatch logs msg_ts (from the file name) and launched_at so the
#     send->pickup latency can be read from the journal. See README.md.
#
# SETUP: set AGENT_NAME, then install the three agent-msg-run.*.example units
# (see README.md in this directory).

set -euo pipefail

# === CONFIGURATION (CUSTOMIZE THESE) ===
AGENT_NAME="YourAgent"
WORKSPACE="$(cd "$(dirname "$0")/../../.." && pwd)"
MODEL="${AGENT_MSG_MODEL:-sonnet}"
SCRIPT_TIMEOUT="${AGENT_MSG_TIMEOUT:-1200}" # 20 minutes
MAX_ATTEMPTS="${AGENT_MSG_MAX_ATTEMPTS:-3}"
GPTMAIL_BIN="${GPTMAIL_BIN:-gptmail}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
# =======================================

NAME_LC="${AGENT_NAME,,}"
STATE_DIR="${AGENT_MSG_STATE_DIR:-$WORKSPACE/state/agent-msg}"
LOCKFILE="${AGENT_MSG_LOCKFILE:-/tmp/${NAME_LC}-agent-msg.lock}"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"; }

cd "$WORKSPACE"
mkdir -p "$STATE_DIR/attempts"

# --- Single slot -----------------------------------------------------------
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    log "slot occupied: another agent-message session is running; the retry timer will re-check"
    exit 0
fi

# --- Discovery -------------------------------------------------------------
# `pending` applies messages/no-reply-subject-patterns and the reply window, so
# this script and an interactive session agree on what is owed.
PENDING_OUT="$(AGENT_NAME="$AGENT_NAME" "$GPTMAIL_BIN" agent pending 2>&1)" || {
    log "ERROR: '$GPTMAIL_BIN agent pending' failed: $PENDING_OUT"
    exit 1
}
# Rows look like: "  <file>.md  from <sender>: <subject>"
mapfile -t PENDING < <(printf '%s\n' "$PENDING_OUT" | sed -nE 's/^[[:space:]]+([^[:space:]]+\.md)[[:space:]]+from .*/\1/p')

# --- Attempt cap -----------------------------------------------------------
# Forget attempt counters for messages that are no longer pending. This runs
# before the empty-list return so the last handled message's counter goes too.
for f in "$STATE_DIR"/attempts/*; do
    [ -e "$f" ] || continue
    keep=0
    for p in "${PENDING[@]}"; do [ "$(basename "$f")" = "$p" ] && keep=1; done
    [ "$keep" -eq 1 ] || rm -f "$f"
done

if [ "${#PENDING[@]}" -eq 0 ]; then
    log "nothing pending"
    exit 0
fi

# Read-only here: counters are only written after the prompt is built, so a
# failing build cannot burn attempts for messages that never reached a session.
DISPATCH=()
for p in "${PENDING[@]}"; do
    n=0
    [ -f "$STATE_DIR/attempts/$p" ] && n="$(cat "$STATE_DIR/attempts/$p")"
    if [ "$n" -ge "$MAX_ATTEMPTS" ]; then
        log "STUCK: $p was dispatched $n times and is still pending; reply or ack it by hand"
        continue
    fi
    DISPATCH+=("$p")
done

if [ "${#DISPATCH[@]}" -eq 0 ]; then
    log "all pending messages hit the attempt cap; not launching"
    exit 0
fi

SYSPROMPT_FILE="$(mktemp "/tmp/${NAME_LC}-agent-msg-sysprompt-XXXXXX")"
trap 'rm -f "$SYSPROMPT_FILE"' EXIT
if ! "$WORKSPACE/scripts/build-system-prompt.sh" >"$SYSPROMPT_FILE"; then
    log "ERROR: build-system-prompt.sh failed; no session launched and attempt counters unchanged"
    exit 1
fi

for p in "${DISPATCH[@]}"; do
    n=0
    [ -f "$STATE_DIR/attempts/$p" ] && n="$(cat "$STATE_DIR/attempts/$p")"
    echo $((n + 1)) >"$STATE_DIR/attempts/$p"
done

# --- Launch ----------------------------------------------------------------
LAUNCHED_AT="$(date -u +%s)"
for p in "${DISPATCH[@]}"; do
    # Message files start with YYYYMMDD-HHMMSS (UTC), the send time.
    ts="${p:0:15}"
    send_epoch="$(date -u -d "${ts:0:8} ${ts:9:2}:${ts:11:2}:${ts:13:2}" +%s 2>/dev/null || echo "")"
    if [ -n "$send_epoch" ]; then
        log "dispatch: msg=$p msg_ts=$ts launched_at=$(date -u -d "@$LAUNCHED_AT" +%Y%m%dT%H%M%SZ) pickup_s=$((LAUNCHED_AT - send_epoch))"
    else
        log "dispatch: msg=$p msg_ts=unknown launched_at=$(date -u -d "@$LAUNCHED_AT" +%Y%m%dT%H%M%SZ)"
    fi
done

FILE_LIST="$(printf -- '- %s\n' "${DISPATCH[@]}")"
PROMPT="You are $AGENT_NAME. Your identity files are injected as system context.

New agent messages are waiting in messages/inbox/:
$FILE_LIST
For each one: read it (gptmail agent read <file>), do what it asks if it is within
your remit, then end it in exactly one of two ways:
- reply:  gptmail agent reply <file> \"<answer>\"
- ack:    gptmail agent ack <file>   (no answer is owed)
A message that ends in neither stays pending and is relaunched. Do not start other
work; this session exists only to handle these messages."

unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

EXIT_CODE=0
timeout "$SCRIPT_TIMEOUT" "$CLAUDE_BIN" -p \
    --dangerously-skip-permissions \
    --model "$MODEL" \
    --append-system-prompt-file "$SYSPROMPT_FILE" \
    "$PROMPT" </dev/null || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 124 ]; then
    log "session timed out after ${SCRIPT_TIMEOUT}s"
fi
log "agent-message session finished (exit: $EXIT_CODE)"
exit "$EXIT_CODE"
