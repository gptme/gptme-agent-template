"""Hermetic tests for session-gate control flow in autonomous-run.sh.

Each test stubs session-gate.py to exercise one outcome branch — skip/run/error
— without spawning a real gptme session or git fetch. git and gptme are also
stubbed so the script can run to completion in a temporary workspace.
"""

from __future__ import annotations

import os
import pty
import stat
import subprocess
from pathlib import Path

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "runs"
    / "autonomous"
    / "autonomous-run.sh"
)


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
