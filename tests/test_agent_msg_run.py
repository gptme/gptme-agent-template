"""Hermetic tests for scripts/runs/agent-msg/agent-msg-run.sh.

gptmail, claude and build-system-prompt.sh are stubs, so no model session starts.
"""

from __future__ import annotations

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
    claude = _exe(
        tmp_path / "claude",
        f'echo LAUNCH >> "{launches}"\necho "$@" >> "{launches}.args"\n',
    )
    env = {
        **os.environ,
        "GPTMAIL_BIN": str(gptmail),
        "CLAUDE_BIN": str(claude),
        "AGENT_MSG_LOCKFILE": str(tmp_path / "slot.lock"),
        "AGENT_MSG_STATE_DIR": str(tmp_path / "state"),
    }
    return {"script": d / "agent-msg-run.sh", "env": env, "launches": launches}


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
