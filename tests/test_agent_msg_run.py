"""Hermetic tests for scripts/runs/agent-msg/agent-msg-run.sh.

gptmail, claude and build-system-prompt.sh are stubs, so no model session starts.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "runs"
    / "agent-msg"
    / "agent-msg-run.sh"
)

MSG = "20261117-120000-000001-erik-Hello.md"


def _exe(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _workspace(tmp_path: Path, pending: list[str]) -> dict:
    ws = tmp_path / "ws"
    d = ws / "scripts" / "runs" / "agent-msg"
    d.mkdir(parents=True)
    shutil.copy(SCRIPT, d / "agent-msg-run.sh")
    _exe(ws / "scripts" / "build-system-prompt.sh", "echo 'system prompt'\n")
    rows = "".join(f"  {f}  from erik: Hello\\n" for f in pending)
    out = (
        f"{len(pending)} message(s) awaiting reply:\\n{rows}"
        if pending
        else "No messages awaiting reply.\\n"
    )
    gptmail = _exe(tmp_path / "gptmail", f"printf '{out}'\n")
    launches = tmp_path / "launches.log"
    autonomous_lock = tmp_path / "autonomous.lock"
    claude = _exe(
        tmp_path / "claude",
        f'echo LAUNCH >> "{launches}"\necho "$@" >> "{launches}.args"\n'
        f'echo "$AGENT_DISPATCH_CAUSE" >> "{launches}.cause"\n'
        f'cat "{autonomous_lock}" >> "{launches}.lane" 2>/dev/null || true\n',
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("AGENT_DISPATCH_CAUSE", "INVOCATION_ID")
        and not k.startswith("AGENT_MSG_")
    }
    env.update(
        {
            "GPTMAIL_BIN": str(gptmail),
            "CLAUDE_BIN": str(claude),
            "AGENT_MSG_LOCKFILE": str(tmp_path / "slot.lock"),
            "AGENT_MSG_STATE_DIR": str(tmp_path / "state"),
            "AGENT_MSG_AUTONOMOUS_LOCKFILE": str(autonomous_lock),
        }
    )
    return {
        "script": d / "agent-msg-run.sh",
        "env": env,
        "launches": launches,
        "autonomous_lock": autonomous_lock,
    }


def _run(w: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(w["script"])],
        env=w["env"],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _launch_count(w: dict) -> int:
    p: Path = w["launches"]
    return p.read_text().splitlines().count("LAUNCH") if p.exists() else 0


def test_nothing_pending_starts_no_session(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [])
    r = _run(w)
    assert r.returncode == 0
    assert "nothing pending" in r.stdout
    assert _launch_count(w) == 0


def test_pending_message_launches_one_session_with_timestamps(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    before = int(time.time())
    r = _run(w)
    after = int(time.time())
    assert r.returncode == 0, r.stderr
    assert _launch_count(w) == 1
    assert f"dispatch: msg={MSG} msg_ts=20261117-120000" in r.stdout
    # pickup_s is launch time minus the send time in the file name, so an
    # inverted subtraction or a mis-parsed timestamp fails here.
    m = re.search(r"pickup_s=(-?\d+)", r.stdout)
    assert m, r.stdout
    sent = int(datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    assert before - sent <= int(m.group(1)) <= after - sent
    assert MSG in Path(f"{w['launches']}.args").read_text()


def test_busy_slot_exits_zero_without_launch(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    ready = tmp_path / "holder.ready"
    holder = subprocess.Popen(
        [
            "bash",
            "-c",
            f'exec 9>"{tmp_path / "slot.lock"}"; flock -n 9 && touch "{ready}"; sleep 20',
        ],
    )
    try:
        # The marker is written only after flock succeeds, so the lock is held.
        for _ in range(100):
            if ready.exists():
                break
            time.sleep(0.1)
        assert ready.exists(), "holder never acquired the slot lock"
        r = _run(w)
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 0
    assert "slot occupied" in r.stdout
    assert _launch_count(w) == 0


def test_attempt_cap_stops_relaunching_a_message_that_stays_pending(
    tmp_path: Path,
) -> None:
    w = _workspace(tmp_path, [MSG])
    for _ in range(3):
        assert _run(w).returncode == 0
    assert _launch_count(w) == 3
    r = _run(w)
    assert r.returncode == 0
    assert f"STUCK: {MSG}" in r.stdout
    assert _launch_count(w) == 3


def test_attempt_counter_dropped_when_message_leaves_pending(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    _run(w)
    counter = tmp_path / "state" / "attempts" / MSG
    assert counter.exists()
    # Message handled: a second pending message appears, the first is gone.
    other = "20261117-120100-000002-erik-Other.md"
    _exe(
        tmp_path / "gptmail",
        f"printf '1 message(s) awaiting reply:\\n  {other}  from erik: Other\\n'\n",
    )
    _run(w)
    assert not counter.exists()
    assert (tmp_path / "state" / "attempts" / other).exists()


def test_failed_prompt_build_leaves_attempts_unchanged(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    _exe(w["script"].parents[2] / "build-system-prompt.sh", "exit 1\n")
    for _ in range(4):
        r = _run(w)
        assert r.returncode == 1
        assert "attempt counters unchanged" in r.stdout
    assert _launch_count(w) == 0
    assert not (tmp_path / "state" / "attempts" / MSG).exists()


def test_attempt_counter_dropped_when_pending_list_is_empty(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    _run(w)
    counter = tmp_path / "state" / "attempts" / MSG
    assert counter.exists()
    _exe(tmp_path / "gptmail", "printf 'No messages awaiting reply.\\n'\n")
    r = _run(w)
    assert "nothing pending" in r.stdout
    assert not counter.exists()


def test_claude_that_cannot_start_leaves_attempts_unchanged(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["CLAUDE_BIN"] = str(tmp_path / "no-such-claude")
    for _ in range(4):
        r = _run(w)
        assert r.returncode == 127
        assert "attempt counters restored" in r.stdout
        assert "STUCK" not in r.stdout
    assert not (tmp_path / "state" / "attempts" / MSG).exists()


def test_claude_that_cannot_start_restores_an_existing_count(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    _run(w)  # one real dispatch
    counter = tmp_path / "state" / "attempts" / MSG
    assert counter.read_text().strip() == "1"
    w["env"]["CLAUDE_BIN"] = str(tmp_path / "no-such-claude")
    assert _run(w).returncode == 127
    assert counter.read_text().strip() == "1"


def _quota_gate(tmp_path: Path, allow: bool) -> Path:
    gate = tmp_path / "quota-gate.sh"
    gate.write_text(
        f'quota_gate_check() {{ echo "$@" > "{tmp_path / "gate.args"}"; '
        f"return {0 if allow else 1}; }}\n"
    )
    return gate


def test_quota_gate_blocks_launch_and_leaves_attempts_unchanged(
    tmp_path: Path,
) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_QUOTA_GATE_SCRIPT"] = str(_quota_gate(tmp_path, False))
    r = _run(w)
    assert r.returncode == 0, r.stderr
    assert "quota gate blocked" in r.stdout
    assert _launch_count(w) == 0
    assert not (tmp_path / "state" / "attempts" / MSG).exists()


def test_quota_gate_checks_the_session_model_and_allows_launch(
    tmp_path: Path,
) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_QUOTA_GATE_SCRIPT"] = str(_quota_gate(tmp_path, True))
    w["env"]["AGENT_MSG_MODEL"] = "haiku"
    assert _run(w).returncode == 0
    assert (tmp_path / "gate.args").read_text().split() == ["--model", "haiku"]
    assert _launch_count(w) == 1


def test_quota_gate_not_consulted_when_nothing_pending(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [])
    w["env"]["AGENT_MSG_QUOTA_GATE_SCRIPT"] = str(_quota_gate(tmp_path, True))
    assert _run(w).returncode == 0
    assert not (tmp_path / "gate.args").exists()


def test_session_is_attributed_to_the_inbox_trigger(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["INVOCATION_ID"] = "abc123"
    assert _run(w).returncode == 0
    cause = json.loads(Path(f"{w['launches']}.cause").read_text())
    assert cause == {"kind": "inbox", "id": "abc123"}


def _live_holder(lock: Path) -> subprocess.Popen[bytes]:
    holder = subprocess.Popen(["sleep", "20"])
    lock.write_text(f"{holder.pid}\n")
    return holder


def test_default_mode_ignores_the_autonomous_lock(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    holder = _live_holder(w["autonomous_lock"])
    try:
        assert _run(w).returncode == 0
    finally:
        holder.kill()
        holder.wait()
    assert _launch_count(w) == 1
    # The scheduled run's lock is untouched.
    assert w["autonomous_lock"].read_text().strip() == str(holder.pid)


def test_single_lane_waits_for_a_running_scheduled_session(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    holder = _live_holder(w["autonomous_lock"])
    try:
        r = _run(w)
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 0
    assert "holds the single lane" in r.stdout
    assert _launch_count(w) == 0
    assert w["autonomous_lock"].read_text().strip() == str(holder.pid)
    assert not (tmp_path / "state" / "attempts" / MSG).exists()


def test_single_lane_holds_the_autonomous_lock_during_the_session(
    tmp_path: Path,
) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    r = _run(w)
    assert r.returncode == 0, r.stderr
    assert _launch_count(w) == 1
    # The session ran under a PID lock a scheduled run would refuse, and the
    # lock was released afterwards.
    lane_pid = Path(f"{w['launches']}.lane").read_text().strip()
    assert lane_pid.isdigit()
    assert w["autonomous_lock"].read_text() == ""  # released: emptied, kept


def test_single_lane_replaces_a_stale_autonomous_lock(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    dead = subprocess.Popen(["true"])
    dead.wait()
    w["autonomous_lock"].write_text(f"{dead.pid}\n")
    assert _run(w).returncode == 0
    assert _launch_count(w) == 1
    assert w["autonomous_lock"].read_text() == ""  # released: emptied, kept


def test_single_lane_lock_refuses_a_real_scheduled_run(tmp_path: Path) -> None:
    """Controlled test: the real autonomous-run-cc.sh, started mid-session, is refused."""
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    runner_src = SCRIPT.parents[1] / "autonomous" / "autonomous-run-cc.sh"
    text = runner_src.read_text()
    marker = 'LOCKFILE="/tmp/${AGENT_NAME,,}-autonomous.lock"'
    assert marker in text, "runner lock path changed; update the single-lane adapter"
    # Own workspace, so a runner that got past the lock would find no git repo,
    # no prompt builder and only a stub `claude` (scripts/ is first on its PATH).
    runner_ws = tmp_path / "runner-ws"
    (runner_ws / "scripts" / "runs" / "autonomous").mkdir(parents=True)
    runner = runner_ws / "scripts" / "runs" / "autonomous" / "autonomous-run-cc.sh"
    runner.write_text(text.replace(marker, f'LOCKFILE="{w["autonomous_lock"]}"'))
    _exe(
        runner_ws / "scripts" / "claude",
        f'echo RUNNER-LAUNCHED >> "{tmp_path / "runner.out"}"\n',
    )
    home = tmp_path / "home"
    home.mkdir()
    out = tmp_path / "runner.out"
    # The stub "session" starts a scheduled run while the message session is live.
    _exe(
        Path(w["env"]["CLAUDE_BIN"]),
        f'echo LAUNCH >> "{w["launches"]}"\n'
        f'HOME="{home}" bash "{runner}" > "{out}" 2>&1; echo "rc=$?" >> "{out}"\n',
    )
    assert _run(w).returncode == 0
    assert _launch_count(w) == 1
    result = out.read_text()
    assert "Another autonomous run is active" in result, result
    assert "rc=1" in result
    assert w["autonomous_lock"].read_text() == ""  # released: emptied, kept


def test_single_lane_refuses_while_another_process_holds_the_flock(
    tmp_path: Path,
) -> None:
    """Simultaneous start: a runner that has the flock but has not written its
    PID yet must still win; the PID file alone would look free."""
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    ready = tmp_path / "flock.ready"
    lock = w["autonomous_lock"]
    holder = subprocess.Popen(
        ["bash", "-c", f'exec 8>>"{lock}"; flock -n 8 && touch "{ready}"; sleep 20']
    )
    try:
        for _ in range(100):
            if ready.exists():
                break
            time.sleep(0.1)
        assert ready.exists(), "holder never acquired the flock"
        r = _run(w)
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 0
    assert "slot occupied" in r.stdout
    assert _launch_count(w) == 0
    assert not (tmp_path / "state" / "attempts" / MSG).exists()


def test_single_lane_unopenable_lock_is_an_error_not_a_busy_slot(
    tmp_path: Path,
) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    w["env"]["AGENT_MSG_AUTONOMOUS_LOCKFILE"] = str(tmp_path / "missing" / "x.lock")
    r = _run(w)
    assert r.returncode == 1
    assert "cannot open the autonomous lock" in r.stdout
    assert "slot occupied" not in r.stdout
    assert _launch_count(w) == 0


def test_session_does_not_inherit_the_lock_fds(tmp_path: Path) -> None:
    """A background process left by the session must not hold the slot."""
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    fds = tmp_path / "fds"
    _exe(
        Path(w["env"]["CLAUDE_BIN"]),
        f'echo LAUNCH >> "{w["launches"]}"\nls /proc/$$/fd > "{fds}"\n',
    )
    assert _run(w).returncode == 0
    assert _launch_count(w) == 1
    open_fds = fds.read_text().split()
    assert "8" not in open_fds and "9" not in open_fds, open_fds


def test_single_lane_flock_error_is_not_a_busy_slot(tmp_path: Path) -> None:
    w = _workspace(tmp_path, [MSG])
    w["env"]["AGENT_MSG_SINGLE_LANE"] = "1"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    real_flock = shutil.which("flock")
    assert real_flock
    # Real flock for the slot lock (fd 9); a failing one for the lane (fd 8).
    _exe(
        bindir / "flock",
        f'case " $* " in *" 8 "*) exit 66;; esac\nexec "{real_flock}" "$@"\n',
    )
    w["env"]["PATH"] = f"{bindir}:{w['env']['PATH']}"
    r = _run(w)
    assert r.returncode == 1
    assert "flock on" in r.stdout and "failed (exit 66)" in r.stdout
    assert "slot occupied" not in r.stdout
    assert _launch_count(w) == 0
