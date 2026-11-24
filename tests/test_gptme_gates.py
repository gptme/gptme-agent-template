"""Hermetic tests for session-gate control flow in autonomous-run.sh.

Each test stubs session-gate.py to exercise one outcome branch — skip/run/error
— without spawning a real gptme session or git fetch. git and gptme are also
stubbed so the script can run to completion in a temporary workspace.
"""

from __future__ import annotations

import json
import os
import pty
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "runs"
    / "autonomous"
    / "autonomous-run.sh"
)
HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "post-session.py"


def _setup_workspace(tmp_path: Path) -> Path:
    """Scaffold a workspace and a runner copy with WORKSPACE rewritten.

    The gptme runner uses a template placeholder for WORKSPACE rather than
    auto-detecting from $0, so tests copy the script and substitute tmp_path.
    """
    scripts_dir = tmp_path / "scripts" / "runs" / "autonomous"
    scripts_dir.mkdir(parents=True)
    source = RUNNER.read_text()
    rewritten = source.replace(
        'WORKSPACE="/path/to/your/workspace"',
        f'WORKSPACE="{tmp_path}"',
        1,
    )
    if rewritten == source:
        raise AssertionError("failed to rewrite WORKSPACE placeholder in runner")
    runner = scripts_dir / "autonomous-run.sh"
    runner.write_text(rewritten)
    runner.chmod(runner.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "gptme-ran"
    gptme = bin_dir / "gptme"
    gptme.write_text(f"#!/bin/bash\ntouch '{marker}'\nexit 0\n")
    gptme.chmod(gptme.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    git = bin_dir / "git"
    git.write_text("#!/bin/bash\nexit 0\n")
    git.chmod(git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    (tmp_path / "gptme-contrib" / "scripts" / "runs" / "autonomous").mkdir(parents=True)
    return marker


def _run(
    tmp_path: Path, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "scripts" / "runs" / "autonomous" / "autonomous-run.sh"
    env = {
        "PATH": f"{tmp_path}/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(script)],
        env=env,
        stdin=subprocess.DEVNULL,  # non-TTY: scheduled/CI path still hits the gate
        capture_output=True,
        text=True,
        timeout=15,
    )


def _run_tty(
    tmp_path: Path, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the runner with a PTY on stdin so `[ -t 0 ]` is true (manual path)."""
    script = tmp_path / "scripts" / "runs" / "autonomous" / "autonomous-run.sh"
    env = {
        "PATH": f"{tmp_path}/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    if env_extra:
        env.update(env_extra)
    master_fd, slave_fd = pty.openpty()
    try:
        return subprocess.run(
            ["bash", str(script)],
            env=env,
            stdin=slave_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def _write_session_gate(tmp_path: Path, exit_code: int) -> None:
    gate = (
        tmp_path
        / "gptme-contrib"
        / "scripts"
        / "runs"
        / "autonomous"
        / "session-gate.py"
    )
    gate.write_text(f"import sys; sys.exit({exit_code})\n")


def test_force_session_bypasses_gate(tmp_path: Path) -> None:
    """FORCE_SESSION=1 skips the session gate entirely and still runs."""
    marker = _setup_workspace(tmp_path)
    _write_session_gate(tmp_path, 0)
    result = _run(tmp_path, {"FORCE_SESSION": "1"})
    assert result.returncode == 0
    assert "FORCE_SESSION=1" in result.stdout
    assert marker.exists()


def test_tty_stdin_bypasses_gate(tmp_path: Path) -> None:
    """Direct manual run (TTY stdin) skips the session gate and still runs."""
    marker = _setup_workspace(tmp_path)
    _write_session_gate(tmp_path, 0)
    result = _run_tty(tmp_path)
    assert result.returncode == 0
    assert "TTY stdin" in result.stdout
    assert marker.exists()


def test_gate_script_absent_degrades_gracefully(tmp_path: Path) -> None:
    """No contrib session-gate.py → runner logs 'not found' and runs anyway."""
    marker = _setup_workspace(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "session-gate.py not found" in result.stdout
    assert marker.exists()


def test_session_gate_skip_does_not_run_gptme(tmp_path: Path) -> None:
    """session-gate.py exits 0 (no trigger) → runner exits 0 without gptme."""
    marker = _setup_workspace(tmp_path)
    _write_session_gate(tmp_path, 0)
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "no trigger" in result.stdout
    assert not marker.exists()


def test_session_gate_run_proceeds(tmp_path: Path) -> None:
    """session-gate.py exits 1 (trigger) → runner proceeds to gptme."""
    marker = _setup_workspace(tmp_path)
    _write_session_gate(tmp_path, 1)
    result = _run(tmp_path)
    assert result.returncode == 0
    assert marker.exists()


def test_session_gate_error_fails_open(tmp_path: Path) -> None:
    """session-gate.py exits 2 (error) → runner logs and runs anyway."""
    marker = _setup_workspace(tmp_path)
    _write_session_gate(tmp_path, 2)
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "failing open" in result.stdout
    assert marker.exists()


def _capture_identity(tmp_path: Path, env_extra: dict[str, str]) -> dict:
    """Run with a gptme stub that records its argv/env and writes a log.

    The stub writes conversation.jsonl under the default gptme log root, named
    by --name, as real gptme does; the real post-session hook is installed and
    a fake gptme_sessions captures what it would record.
    """
    _setup_workspace(tmp_path)
    (tmp_path / "bin" / "gptme").write_text(
        "#!/usr/bin/python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "keys = ('AGENT_SESSION_ID', 'GIT_COMMITTER_SESSION_ID', "
        "'AGENT_SESSION_LABEL', 'AGENT_DISPATCH_CAUSE')\n"
        "capture = {key: os.environ.get(key) for key in keys}\n"
        "capture['args'] = args\n"
        "home = Path(os.environ['HOME'])\n"
        "(home / 'gptme.json').write_text(json.dumps(capture))\n"
        "if '--name' in args:\n"
        "    log = home / '.local/share/gptme/logs' / args[args.index('--name') + 1]\n"
        "    log.mkdir(parents=True)\n"
        "    (log / 'conversation.jsonl').write_text('{}\\n')\n"
    )
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / "post-session.py")
    fake = tmp_path / "fake-sessions" / "gptme_sessions"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "class SessionStore:\n"
        "    def __init__(self, *a, **k): pass\n"
        "def post_session(*, store, harness, session_id, trajectory_path, "
        "model=None, **rest):\n"
        "    record = {'harness': harness, 'session_id': session_id, "
        "'trajectory_path': str(trajectory_path)}\n"
        "    Path(os.environ['HOME'], 'record.json').write_text(json.dumps(record))\n"
        "    raise RuntimeError('captured')  # hook logs it and exits 0\n"
    )
    env = {"PYTHONPATH": str(fake.parent), "FORCE_SESSION": "1", **env_extra}
    result = _run(tmp_path, env)
    assert result.returncode == 0, result.stdout + result.stderr
    captured = json.loads((tmp_path / "gptme.json").read_text())
    record = tmp_path / "record.json"
    captured["record"] = json.loads(record.read_text()) if record.exists() else None
    return captured


def test_identity_links_conversation_trailer_and_record(tmp_path: Path) -> None:
    """One id names the gptme conversation, the commit trailer and the record."""
    captured = _capture_identity(tmp_path, {})
    args = captured["args"]
    session_id = captured["AGENT_SESSION_ID"]
    assert session_id
    assert args[args.index("--name") + 1] == session_id
    assert captured["GIT_COMMITTER_SESSION_ID"] == session_id
    assert captured["AGENT_SESSION_LABEL"] == session_id[:4]
    assert json.loads(captured["AGENT_DISPATCH_CAUSE"])["kind"] == "manual"

    record = captured["record"]
    assert record is not None
    assert record["harness"] == "gptme"
    assert record["session_id"] == session_id
    assert record["trajectory_path"] == str(
        tmp_path / ".local/share/gptme/logs" / session_id / "conversation.jsonl"
    )


def test_identity_opt_out_clears_inherited_trailer(tmp_path: Path) -> None:
    """AGENT_SESSION_IDENTITY=0: no --name, no inherited trailer, no record."""
    captured = _capture_identity(
        tmp_path,
        {
            "AGENT_SESSION_IDENTITY": "0",
            "GIT_COMMITTER_SESSION_ID": "11111111-1111-4111-8111-111111111111",
        },
    )
    assert "--name" not in captured["args"]
    assert captured["GIT_COMMITTER_SESSION_ID"] is None
    assert captured["record"] is None


def test_parent_session_is_passed_through(tmp_path: Path) -> None:
    parent = "22222222-2222-4222-8222-222222222222"
    captured = _capture_identity(tmp_path, {"AGENT_PARENT_SESSION_ID": parent})
    assert json.loads(captured["AGENT_DISPATCH_CAUSE"])["parent_session_id"] == parent


@pytest.mark.parametrize("ignores_term", [False, True])
def test_terminated_runner_stops_gptme(tmp_path: Path, ignores_term: bool) -> None:
    """SIGTERM to the runner (manual or cron run, outside systemd's cgroup kill)
    must stop gptme. gptme's parent is `timeout`, not the runner, so cleanup's
    `pkill -P $$ gptme` used to match nothing and leave gptme orphaned. A gptme
    that ignores SIGTERM is force-stopped after the grace period."""
    import time

    _setup_workspace(tmp_path)
    pidfile = tmp_path / "gptme.pid"
    gptme = tmp_path / "bin" / "gptme"
    trap = "trap '' TERM\n" if ignores_term else ""
    gptme.write_text(f"#!/bin/bash\n{trap}echo $$ > '{pidfile}'\nexec sleep 30\n")
    script = tmp_path / "scripts" / "runs" / "autonomous" / "autonomous-run.sh"
    env = {
        "PATH": f"{tmp_path}/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FORCE_SESSION": "1",
    }
    runner = subprocess.Popen(
        ["bash", str(script)],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    gptme_pid = 0
    try:
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            time.sleep(0.1)
        gptme_pid = int(pidfile.read_text())
        runner.terminate()
        runner.wait(timeout=15)
        for _ in range(50):
            try:
                os.kill(gptme_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("gptme still running after runner was terminated")
    finally:
        if runner.poll() is None:
            runner.kill()
        if gptme_pid:
            try:
                os.kill(gptme_pid, 9)
            except ProcessLookupError:
                pass


def test_pull_conflict_does_not_leave_unmerged_files(tmp_path: Path) -> None:
    """With pull configured to merge, a conflicting `git pull` must not leave
    unmerged files behind for every later pull and commit to trip on."""
    _setup_workspace(tmp_path)
    (tmp_path / "bin" / "git").unlink()  # this test needs real git
    genv = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "T",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "T",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }

    def git(*args: str, cwd: Path = tmp_path) -> None:
        subprocess.run(
            ["git", *args], cwd=cwd, env=genv, check=True, capture_output=True
        )

    git("init", "-q", "-b", "master")
    git("config", "pull.rebase", "false")
    (tmp_path / "state.md").write_text("base\n")
    git("add", "-A")
    git("commit", "-qm", "init")
    origin = tmp_path.parent / f"{tmp_path.name}-origin.git"
    git("clone", "-q", "--bare", str(tmp_path), str(origin))
    git("remote", "add", "origin", str(origin))
    git("fetch", "-q", "origin")
    git("branch", "-q", "--set-upstream-to=origin/master")
    other = tmp_path.parent / f"{tmp_path.name}-other"
    git("clone", "-q", str(origin), str(other), cwd=tmp_path.parent)
    (other / "state.md").write_text("upstream edit\n")
    git("commit", "-qam", "upstream", cwd=other)
    git("push", "-q", "origin", "master", cwd=other)
    (tmp_path / "state.md").write_text("local edit\n")
    git("commit", "-qam", "local")

    upstream = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=other,
        env=genv,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = _run(
        tmp_path,
        {**genv, "PATH": f"{tmp_path}/bin:/usr/bin:/bin", "FORCE_SESSION": "1"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONFLICT" in result.stdout, "the pull never hit the conflict"
    assert "Git pull failed" in result.stdout
    fetched = subprocess.run(
        ["git", "rev-parse", "origin/master"],
        cwd=tmp_path,
        env=genv,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert fetched == upstream
    assert not (tmp_path / ".git" / "MERGE_HEAD").exists(), "left mid-merge"
    assert (tmp_path / "state.md").read_text() == "local edit\n"
