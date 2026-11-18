#!/bin/sh
# run-hook.sh: run a Claude Code hook script without letting a missing file block the session.
#
# Usage (in .claude/settings.json):
#   "$CLAUDE_PROJECT_DIR"/.claude/hooks/run-hook.sh [--no-block] INTERPRETER SCRIPT [ARGS...]
#
# Why: a hook command such as `python3 path/to/hook.py` exits 2 when the file does not exist
# (dangling symlink, submodule not checked out, script moved). Claude Code treats exit 2 from a
# hook as "block", so every tool call, prompt or stop is refused and the session cannot repair
# itself. This launcher is a real file in the workspace (never a symlink into a submodule), so it
# is present whenever settings.json is.
#
# Behaviour:
#   - SCRIPT or INTERPRETER missing: write one line to stderr and to the miss log, exit 0.
#   - otherwise exec INTERPRETER SCRIPT ARGS with stdin/stdout untouched; the exit code is the
#     script's own, so hooks that block on purpose (exit 2) still block.
#   - --no-block: for advisory hooks (lesson matching, logging). A script exit of 2 becomes 1:
#     the error stays visible but can never block. TERM, INT and HUP are passed on to the script.
#
# Miss log: ${CLAUDE_HOOK_MISS_LOG:-${TMPDIR:-/tmp}/claude-hook-missing.log}

no_block=0
if [ "${1:-}" = "--no-block" ]; then
    no_block=1
    shift
fi

if [ "$#" -lt 2 ]; then
    echo "run-hook.sh: usage: run-hook.sh [--no-block] INTERPRETER SCRIPT [ARGS...]" >&2
    exit 0
fi

interp="$1"
script="$2"
shift 2

miss() {
    msg="run-hook.sh: $1; hook skipped"
    echo "$msg" >&2
    log="${CLAUDE_HOOK_MISS_LOG:-${TMPDIR:-/tmp}/claude-hook-missing.log}"
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$msg" >>"$log" 2>/dev/null || true
    exit 0
}

[ -f "$script" ] || miss "hook script not found: $script"
command -v "$interp" >/dev/null 2>&1 || miss "interpreter not found: $interp"

if [ "$no_block" -eq 0 ]; then
    exec "$interp" "$script" "$@"
fi

# Run the script as a child so its exit code can be rewritten, but keep it tied to this
# process: a hook that hits its timeout is killed by signal, and the script must not outlive
# the launcher. `<&0` keeps the hook's stdin (a background command would otherwise read
# /dev/null).
"$interp" "$script" "$@" <&0 &
child=$!
trap 'kill -TERM "$child" 2>/dev/null' TERM INT HUP
wait "$child"
rc=$?
if [ "$rc" -gt 128 ]; then
    # wait was interrupted by a trapped signal, or the script died from one: reap it.
    wait "$child" 2>/dev/null
fi
if [ "$rc" -eq 2 ]; then
    exit 1
fi
exit "$rc"
