#!/usr/bin/env python3
"""Post-session hook: record session metrics to gptme-sessions.

Claude Code `Stop` hook — fires when a session ends (user exits or /stop).
Reads `transcript_path` from the hook input, runs `post_session()` to extract
productivity metrics, and appends a session record to `state/sessions/`.

Without records there is no noop rate, no outcome tracking, no bandit input,
and no way to answer "is this agent still alive?". This hook is what makes an
agent forked from the template observable by default.

Portability (shared-core tiers):
  Tier 0 — always safe. Any failure (no gptme-sessions, no transcript, import
  error) logs to `logs/post-session.log` and exits 0. A recording failure must
  never break the session itself.
  Tier 1 — records when possible. It finds `gptme_sessions` in three ways, in
  order: (1) the invoking Python already has it; (2) the vendored copy under
  `gptme-contrib/packages/gptme-sessions/src`; (3) a `uv tool install`ed
  gptme-sessions, by re-exec'ing into that tool's interpreter.

Environment (all optional):
  GPTME_SESSIONS_DIR        Where records are written. Defaults to
                            `<workspace>/state/sessions`. The autonomous
                            runners export this so bare `gptme-sessions` CLI
                            calls resolve to the same store.
  AGENT_SESSION_TYPE        Tag records by source: "autonomous" (default),
                            "monitoring", "email", "interactive".
  AGENT_RECOMMENDED_CATEGORY  Category the session was launched for (bandit input).
  START_COMMIT              HEAD before the session (set by the run script);
                            end_commit is resolved from HEAD when the session stops.
"""

from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]  # .claude/hooks/ → workspace root
SESSIONS_DIR = Path(
    os.environ.get("GPTME_SESSIONS_DIR") or (WORKSPACE / "state" / "sessions")
)
LOG_FILE = WORKSPACE / "logs" / "post-session.log"
CONTRIB_SRC = WORKSPACE / "gptme-contrib" / "packages" / "gptme-sessions" / "src"

# Guard against an infinite re-exec loop when hunting for a usable interpreter.
_REEXEC_GUARD = "_POST_SESSION_REEXEC"


def log(msg: str) -> None:
    """Append to the post-session log (non-fatal)."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        import datetime

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _find_uv_tool_python() -> Path | None:
    """Locate a `uv tool install`ed gptme-sessions interpreter, if present.

    uv installs tool venvs under $XDG_DATA_HOME/uv/tools (or ~/.local/share/uv/tools).
    Returns the tool's python, or None.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    roots = [Path(xdg) / "uv" / "tools"] if xdg else []
    roots.append(Path.home() / ".local" / "share" / "uv" / "tools")
    for root in roots:
        py = root / "gptme-sessions" / "bin" / "python3"
        if py.is_file():
            return py
    return None


def _import_sessions():
    """Return (SessionStore, post_session), or (None, None) if unavailable.

    Tries the invoking interpreter, then the vendored contrib src. If neither
    works and a `uv tool` install exists, re-exec into it (once).
    """
    try:
        from gptme_sessions import SessionStore, post_session

        return SessionStore, post_session
    except ImportError:
        pass

    if CONTRIB_SRC.is_dir():
        sys.path.insert(0, str(CONTRIB_SRC))
        try:
            from gptme_sessions import SessionStore, post_session

            return SessionStore, post_session
        except ImportError:
            sys.path.pop(0)

    # Last resort: re-exec into a uv-tool-installed gptme-sessions interpreter.
    if not os.environ.get(_REEXEC_GUARD):
        tool_py = _find_uv_tool_python()
        if tool_py:
            os.environ[_REEXEC_GUARD] = "1"
            log(f"re-exec into uv tool python: {tool_py}")
            os.execv(str(tool_py), [str(tool_py), __file__])  # never returns

    return None, None


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    event = hook_input.get("hook_event_name", "")
    if event not in ("Stop", "StopSession"):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    session_id = hook_input.get("session_id", "unknown")
    model = hook_input.get("model", "unknown")

    if not transcript_path or not Path(transcript_path).is_file():
        log(f"no transcript at {transcript_path!r}, skipping")
        sys.exit(0)

    session_type = os.environ.get("AGENT_SESSION_TYPE") or "autonomous"
    recommended_category = os.environ.get("AGENT_RECOMMENDED_CATEGORY") or None

    # Commit tracking: START_COMMIT is set by the run script before the session;
    # end_commit is the current HEAD when the session stops.
    start_commit = os.environ.get("START_COMMIT") or None
    try:
        import subprocess

        end_commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(WORKSPACE),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
            or None
        )
    except Exception:
        end_commit = None

    SessionStore, post_session = _import_sessions()
    if post_session is None or SessionStore is None:
        log(
            "gptme_sessions unavailable — no session record written. "
            "Install with: uv tool install ./gptme-contrib/packages/gptme-sessions"
        )
        sys.exit(0)

    try:
        store = SessionStore(SESSIONS_DIR)

        # Dedup guard: the Stop hook can fire more than once for the same session
        # (e.g. interrupted then resumed). Skip if session_id already recorded.
        if store.path.exists() and session_id != "unknown":
            with open(store.path, encoding="utf-8") as f:
                tail = collections.deque(f, maxlen=20)
            for line in tail:
                if session_id in line:
                    log(f"skipped duplicate session {session_id[:8]}")
                    sys.exit(0)

        result = post_session(
            store=store,
            harness="claude-code",
            model=model,
            run_type=session_type,
            trajectory_path=Path(transcript_path),
            recommended_category=recommended_category,
            session_id=session_id,
            start_commit=start_commit,
            end_commit=end_commit,
        )
        log(
            f"appended session {session_id[:8]}: "
            f"outcome={result.record.outcome} "
            f"duration={result.record.duration_seconds}s "
            f"deliverables={len(result.record.deliverables or [])} "
            f"run_type={session_type!r}"
        )
    except Exception as e:
        log(f"post_session exception: {e}")
        import traceback

        log(traceback.format_exc())

    sys.exit(0)


if __name__ == "__main__":
    main()
