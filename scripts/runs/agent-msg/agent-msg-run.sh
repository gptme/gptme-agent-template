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
# Single-lane mode (opt-in): share the scheduled autonomous run's lock, so a
# message session and a scheduled session never overlap. See README.md.
SINGLE_LANE="${AGENT_MSG_SINGLE_LANE:-0}"
AUTONOMOUS_LOCKFILE="${AGENT_MSG_AUTONOMOUS_LOCKFILE:-/tmp/${NAME_LC}-autonomous.lock}"
QUOTA_GATE_SCRIPT="${AGENT_MSG_QUOTA_GATE_SCRIPT:-$WORKSPACE/gptme-contrib/scripts/quota-gate.sh}"

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

# --- Budget gate -----------------------------------------------------------
# The inbox forces discovery, not the budget: a message session is a paid
# session like any other, so it passes the same quota gate as the scheduled run
# (fails open when gptme-contrib is absent, as that runner does). A blocked run
# leaves the attempt counters alone; the retry timer re-checks.
if [ -f "$QUOTA_GATE_SCRIPT" ]; then
    # shellcheck source=/dev/null
    QUOTA_GATE_LOG_PREFIX="[${NAME_LC}-agent-msg]" \
    source "$QUOTA_GATE_SCRIPT"
    if ! quota_gate_check --model "$MODEL"; then
        log "quota gate blocked: ${#DISPATCH[@]} message(s) stay pending; the retry timer will re-check"
        exit 0
    fi
else
    log "quota-gate.sh not found at $QUOTA_GATE_SCRIPT; skipping quota gate"
fi

SYSPROMPT_FILE=""
OWN_AUTONOMOUS_LOCK=0
# shellcheck disable=SC2317  # called by the EXIT trap
cleanup() {
    [ -n "$SYSPROMPT_FILE" ] && rm -f "$SYSPROMPT_FILE"
    # Clear only a PID this run wrote, and truncate rather than delete, as
    # autonomous-run-cc.sh does. Exiting closes fd 8 and releases the flock.
    if [ "$OWN_AUTONOMOUS_LOCK" -eq 1 ] && [ "$(cat "$AUTONOMOUS_LOCKFILE" 2>/dev/null)" = "$$" ]; then
        : >"$AUTONOMOUS_LOCKFILE"
    fi
}
trap cleanup EXIT

# --- Single lane (opt-in) --------------------------------------------------
# Take the same flock as autonomous-run-cc.sh (fd 8, opened with >> so the
# runner's PID is never truncated). While this session holds it, a scheduled
# run refuses to start; while a scheduled run holds it, this exits and the
# retry timer re-checks. One session, no chaining.
if [ "$SINGLE_LANE" = "1" ]; then
    if ! { exec 8>>"$AUTONOMOUS_LOCKFILE"; } 2>/dev/null; then
        log "ERROR: cannot open the autonomous lock $AUTONOMOUS_LOCKFILE; check AGENT_MSG_AUTONOMOUS_LOCKFILE"
        exit 1
    fi
    if ! flock -n 8; then
        log "slot occupied: a scheduled autonomous run holds the single lane; the retry timer will re-check"
        exit 0
    fi
    # A live PID without the flock is a runner from before the flock change.
    holder="$(cat "$AUTONOMOUS_LOCKFILE" 2>/dev/null || true)"
    if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
        log "slot occupied: scheduled autonomous run (PID $holder) holds the single lane; the retry timer will re-check"
        exit 0
    fi
    echo $$ >"$AUTONOMOUS_LOCKFILE"
    OWN_AUTONOMOUS_LOCK=1
fi

SYSPROMPT_FILE="$(mktemp "/tmp/${NAME_LC}-agent-msg-sysprompt-XXXXXX")"
if ! "$WORKSPACE/scripts/build-system-prompt.sh" >"$SYSPROMPT_FILE"; then
    log "ERROR: build-system-prompt.sh failed; no session launched and attempt counters unchanged"
    exit 1
fi

# PREV remembers each pre-launch count so a launch that never started a
# session (see below) can put the counters back.
declare -A PREV=()
for p in "${DISPATCH[@]}"; do
    n=0
    [ -f "$STATE_DIR/attempts/$p" ] && n="$(cat "$STATE_DIR/attempts/$p")"
    PREV["$p"]="$n"
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

# Attribute the session to its trigger. The post-session hook reads this
# variable; without it the record cannot tell an inbox session from a timer one.
if [ -z "${AGENT_DISPATCH_CAUSE:-}" ]; then
    export AGENT_DISPATCH_CAUSE="{\"kind\": \"inbox\", \"id\": \"${INVOCATION_ID:-$$}\"}"
fi

unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

# 8>&- 9>&-: keep the lock fds out of the session, so a background process it
# leaves behind cannot hold a lock and block every later pickup.

EXIT_CODE=0
timeout "$SCRIPT_TIMEOUT" "$CLAUDE_BIN" -p \
    --dangerously-skip-permissions \
    --model "$MODEL" \
    --append-system-prompt-file "$SYSPROMPT_FILE" \
    "$PROMPT" </dev/null 8>&- 9>&- || EXIT_CODE=$?

# timeout exits 126/127 when it cannot run $CLAUDE_BIN at all (not executable /
# not found). No session ran, so those dispatches must not count toward the cap:
# otherwise a broken install would mark every pending message STUCK.
if [ "$EXIT_CODE" -eq 126 ] || [ "$EXIT_CODE" -eq 127 ]; then
    for p in "${DISPATCH[@]}"; do
        if [ "${PREV[$p]}" -eq 0 ]; then
            rm -f "$STATE_DIR/attempts/$p"
        else
            echo "${PREV[$p]}" >"$STATE_DIR/attempts/$p"
        fi
    done
    log "ERROR: could not start '$CLAUDE_BIN' (exit: $EXIT_CODE); no session ran and attempt counters restored"
    exit "$EXIT_CODE"
fi
if [ "$EXIT_CODE" -eq 124 ]; then
    log "session timed out after ${SCRIPT_TIMEOUT}s"
fi
log "agent-message session finished (exit: $EXIT_CODE)"
exit "$EXIT_CODE"
