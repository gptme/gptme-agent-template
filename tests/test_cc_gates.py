"""Hermetic tests for gate control flow in autonomous-run-cc.sh.

Each test stubs out quota-gate.sh and/or session-gate.py to exercise one
outcome branch — skip/run/error — without spawning a real Claude session or
git fetch. git and claude are also stubbed so the script can run to completion
in a temporary workspace.
"""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
from pathlib import Path

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "runs"
    / "autonomous"
    / "autonomous-run-cc.sh"
)


def _setup_workspace(tmp_path: Path) -> None:
    """Scaffold a minimal workspace so the runner resolves correctly.

    The runner computes WORKSPACE as three directories above its own location
    ($0 → dirname → ../../..). Copy the runner into the expected place inside
    tmp_path, customizing its agent name so each test has a private lock.
    """
    # Place runner at the depth the script expects
    scripts_dir = tmp_path / "scripts" / "runs" / "autonomous"
    scripts_dir.mkdir(parents=True)
    agent_name = "TestAgent" + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    (scripts_dir / "autonomous-run-cc.sh").write_text(
        RUNNER.read_text().replace(
            'AGENT_NAME="YourAgent"', f'AGENT_NAME="{agent_name}"'
        )
    )

    # Stub executables: git and claude must exit 0 for non-gate tests
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("git", "claude"):
        p = bin_dir / name
        p.write_text("#!/bin/bash\nexit 0\n")
        p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Stub build-system-prompt.sh (called after gates when session runs)
    bsp = tmp_path / "scripts" / "build-system-prompt.sh"
    bsp.write_text("#!/bin/bash\necho 'stub system prompt'\n")
    bsp.chmod(bsp.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Contrib gate-scripts directory (empty by default → degrade-gracefully path)
    (tmp_path / "gptme-contrib" / "scripts" / "runs" / "autonomous").mkdir(parents=True)


def _run(tmp_path: Path, env_extra: dict[str, str] | None = None) -> int:
    script = tmp_path / "scripts" / "runs" / "autonomous" / "autonomous-run-cc.sh"
    env = {
        "PATH": f"{tmp_path}/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        # Stop the script from sourcing the real ~/.profile
        "BASH_ENV": "",
    }
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["bash", str(script)],
        env=env,
        capture_output=True,
        timeout=15,
    )
    return result.returncode


def _capture_session(tmp_path: Path, env_extra: dict[str, str]) -> dict:
    """Capture only the runner's identity contract at the Claude boundary."""
    _setup_workspace(tmp_path)
    (tmp_path / "bin" / "claude").write_text(
        "#!/usr/bin/python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "keys = ('AGENT_SESSION_ID', 'GIT_COMMITTER_SESSION_ID', "
        "'AGENT_JOURNAL_PATH', 'AGENT_SESSION_LABEL', 'AGENT_DISPATCH_CAUSE')\n"
        "capture = {key: os.environ.get(key) for key in keys}\n"
        "capture['args'] = sys.argv[1:]\n"
        "Path(os.environ['HOME'], 'session.json').write_text(json.dumps(capture))\n"
    )
    assert _run(tmp_path, env_extra) == 0
    return json.loads((tmp_path / "session.json").read_text())


def test_identity_opt_out_clears_inherited_commit_trailer(tmp_path: Path) -> None:
    captured = _capture_session(
        tmp_path,
        {
            "AGENT_SESSION_IDENTITY": "0",
            "GIT_COMMITTER_SESSION_ID": "11111111-1111-4111-8111-111111111111",
        },
    )
    assert "--session-id" not in captured["args"]
    assert captured["GIT_COMMITTER_SESSION_ID"] is None


def test_journal_path_is_reserved_and_in_prompt(tmp_path: Path) -> None:
    captured = _capture_session(tmp_path, {})
    journal = Path(captured["AGENT_JOURNAL_PATH"] or "")
    assert journal.is_absolute()
    assert journal.is_file()
    assert journal.parent.parent == tmp_path / "journal"
    assert str(journal) in captured["args"][-1]
    session_id = captured["AGENT_SESSION_ID"]
    args = captured["args"]
    assert args[args.index("--session-id") + 1] == session_id
    assert captured["GIT_COMMITTER_SESSION_ID"] == session_id
    assert json.loads(captured["AGENT_DISPATCH_CAUSE"])["kind"] == "manual"


def test_journal_reservation_is_unique_per_run(tmp_path: Path) -> None:
    first = _capture_session(tmp_path, {})
    journal = Path(first["AGENT_JOURNAL_PATH"] or "")
    assert journal.is_file()
    journal.write_text("previous session\n")
    assert _run(tmp_path) == 0
    second = json.loads((tmp_path / "session.json").read_text())
    assert second["AGENT_JOURNAL_PATH"] != str(journal)
    assert journal.read_text() == "previous session\n"


def test_explicit_journal_path_is_preserved_without_truncation(tmp_path: Path) -> None:
    journal = tmp_path / "journal" / "reserved entry.md"
    journal.parent.mkdir()
    journal.write_text("existing entry\n")
    captured = _capture_session(tmp_path, {"AGENT_JOURNAL_PATH": str(journal)})
    assert captured["AGENT_JOURNAL_PATH"] == str(journal)
    assert str(journal) in captured["args"][-1]
    assert journal.read_text() == "existing entry\n"


def test_journal_is_available_with_identity_opt_out(tmp_path: Path) -> None:
    captured = _capture_session(tmp_path, {"AGENT_SESSION_IDENTITY": "0"})
    journal = Path(captured["AGENT_JOURNAL_PATH"] or "")
    assert journal.is_file()
    assert str(journal) in captured["args"][-1]
    assert "--session-id" not in captured["args"]


def test_force_session_bypasses_gates(tmp_path: Path) -> None:
    """FORCE_SESSION=1 skips both gate scripts entirely."""
    _setup_workspace(tmp_path)
    rc = _run(tmp_path, {"FORCE_SESSION": "1"})
    assert rc == 0


def test_gate_scripts_absent_degrades_gracefully(tmp_path: Path) -> None:
    """No contrib gate scripts → runner logs 'not found' and runs anyway."""
    _setup_workspace(tmp_path)
    rc = _run(tmp_path)
    assert rc == 0


def test_quota_gate_blocks_run(tmp_path: Path) -> None:
    """quota_gate_check returning non-zero → runner exits 0 (skip, don't run)."""
    _setup_workspace(tmp_path)
    quota_stub = tmp_path / "gptme-contrib" / "scripts" / "quota-gate.sh"
    quota_stub.write_text("quota_gate_check() { return 1; }\n")
    rc = _run(tmp_path)
    assert rc == 0


def test_session_gate_skip_exits_zero(tmp_path: Path) -> None:
    """session-gate.py exits 0 (no trigger) → runner exits 0 (skip)."""
    _setup_workspace(tmp_path)
    gate = (
        tmp_path
        / "gptme-contrib"
        / "scripts"
        / "runs"
        / "autonomous"
        / "session-gate.py"
    )
    gate.write_text("import sys; sys.exit(0)\n")
    rc = _run(tmp_path)
    assert rc == 0


def test_session_gate_error_fails_open(tmp_path: Path) -> None:
    """session-gate.py exits 2 (error) → runner logs and runs anyway (fail open)."""
    _setup_workspace(tmp_path)
    gate = (
        tmp_path
        / "gptme-contrib"
        / "scripts"
        / "runs"
        / "autonomous"
        / "session-gate.py"
    )
    gate.write_text("import sys; sys.exit(2)\n")
    rc = _run(tmp_path)
    assert rc == 0
