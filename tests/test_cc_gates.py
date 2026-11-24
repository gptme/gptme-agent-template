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

import pytest

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
    source = RUNNER.read_text()
    rewritten = source.replace(
        'AGENT_NAME="YourAgent"', f'AGENT_NAME="{agent_name}"'
    ).replace(
        'LOCKFILE="/tmp/${AGENT_NAME,,}-autonomous.lock"',
        f'LOCKFILE="{_lockfile(tmp_path)}"',
    )
    if _lockfile(tmp_path).name not in rewritten:
        raise AssertionError("failed to rewrite LOCKFILE in runner")
    (scripts_dir / "autonomous-run-cc.sh").write_text(rewritten)

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


def _lockfile(tmp_path: Path) -> Path:
    """Each test's private lock, inside tmp_path rather than shared /tmp."""
    return tmp_path / "autonomous.lock"


def _run(tmp_path: Path, env_extra: dict[str, str] | None = None) -> int:
    return _run_result(tmp_path, env_extra).returncode


def _run_result(
    tmp_path: Path, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "scripts" / "runs" / "autonomous" / "autonomous-run-cc.sh"
    env = {
        "PATH": f"{tmp_path}/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        # Stop the script from sourcing the real ~/.profile
        "BASH_ENV": "",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


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


def test_refused_run_keeps_live_runs_lock(tmp_path: Path) -> None:
    """A run refused by a live lock must not delete that lock on its way out,
    or the next run starts alongside the live one."""
    _setup_workspace(tmp_path)
    lock = _lockfile(tmp_path)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        lock.write_text(f"{holder.pid}\n")
        rc = _run(tmp_path, {"FORCE_SESSION": "1"})
        assert rc == 1
        assert lock.exists(), "refused run removed the live run's lock"
        assert lock.read_text().strip() == str(holder.pid)
    finally:
        holder.kill()
        holder.wait()
        lock.unlink(missing_ok=True)


_GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "T",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "T",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(tmp_path: Path, *args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or tmp_path,
        env={**_GIT_ENV, "HOME": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _diverged_repo(tmp_path: Path, *, local_commit: bool) -> str:
    """Make tmp_path a clone whose origin changed state.md upstream.

    With local_commit, a conflicting local commit exists; otherwise the local
    edit is left uncommitted. Returns the upstream commit sha.
    """
    _setup_workspace(tmp_path)
    (tmp_path / "bin" / "git").unlink()  # these tests need real git
    _git(tmp_path, "init", "-q", "-b", "master")
    (tmp_path / "state.md").write_text("base\n")
    _git(tmp_path, "add", "state.md")
    _git(tmp_path, "commit", "-qm", "init")
    origin = tmp_path.parent / f"{tmp_path.name}-origin.git"
    _git(tmp_path, "clone", "-q", "--bare", str(tmp_path), str(origin))
    _git(tmp_path, "remote", "add", "origin", str(origin))
    _git(tmp_path, "fetch", "-q", "origin")
    _git(tmp_path, "branch", "-q", "--set-upstream-to=origin/master")
    other = tmp_path.parent / f"{tmp_path.name}-other"
    _git(tmp_path, "clone", "-q", str(origin), str(other), cwd=tmp_path.parent)
    (other / "state.md").write_text("upstream edit\n")
    _git(tmp_path, "commit", "-qam", "upstream", cwd=other)
    _git(tmp_path, "push", "-q", "origin", "master", cwd=other)
    (tmp_path / "state.md").write_text("local edit\n")
    if local_commit:
        _git(tmp_path, "commit", "-qam", "local")
    return _git(tmp_path, "rev-parse", "HEAD", cwd=other).strip()


def test_pull_conflict_does_not_leave_repo_mid_rebase(tmp_path: Path) -> None:
    """A conflicting `git pull --rebase` must not wedge the workspace: every
    later run's pull and the session's commits would fail on unmerged files."""
    upstream = _diverged_repo(tmp_path, local_commit=True)

    result = _run_result(tmp_path, {"FORCE_SESSION": "1"})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONFLICT" in result.stdout, "the pull never hit the conflict"
    assert "git pull failed" in result.stdout
    assert _git(tmp_path, "rev-parse", "origin/master").strip() == upstream
    gitdir = tmp_path / ".git"
    assert not (gitdir / "rebase-merge").exists(), "left mid-rebase"
    assert not (gitdir / "rebase-apply").exists(), "left mid-rebase"
    assert (tmp_path / "state.md").read_text() == "local edit\n"


@pytest.mark.parametrize("operation", ["rebase", "merge"])
def test_pull_leaves_existing_rebase_untouched(tmp_path: Path, operation: str) -> None:
    """A staged resolution survives, and no agent starts during the operation."""
    _diverged_repo(tmp_path, local_commit=True)
    marker = tmp_path / "claude-ran"
    (tmp_path / "bin" / "claude").write_text(f"#!/bin/bash\ntouch '{marker}'\n")
    _git(tmp_path, "fetch", "-q", "origin")
    rebase = subprocess.run(
        ["git", operation, "origin/master"],
        cwd=tmp_path,
        env={**_GIT_ENV, "HOME": str(tmp_path)},
        capture_output=True,
    )
    assert rebase.returncode != 0, "setup: rebase should conflict"
    (tmp_path / "state.md").write_text("resolved\n")
    _git(tmp_path, "add", "state.md")

    result = _run_result(tmp_path, {"FORCE_SESSION": "1"})

    assert result.returncode == 1, result.stdout + result.stderr
    assert "already in progress" in result.stdout, result.stdout
    op_path = "rebase-merge" if operation == "rebase" else "MERGE_HEAD"
    assert (tmp_path / ".git" / op_path).exists(), "operation was aborted"
    assert _git(tmp_path, "show", ":state.md") == "resolved\n"
    assert not marker.exists(), "agent started during an unfinished git operation"


def test_pull_with_autostash_conflict_stops_run(tmp_path: Path) -> None:
    """`git pull --autostash` exits 0 when re-applying the stash conflicts; the
    run must stop rather than start a session that cannot commit."""
    _diverged_repo(tmp_path, local_commit=False)

    result = _run_result(tmp_path, {"FORCE_SESSION": "1"})

    assert _git(
        tmp_path, "diff", "--name-only", "--diff-filter=U"
    ).strip(), "setup: the autostash should conflict"
    assert result.returncode == 1, result.stdout + result.stderr
    assert "unmerged files" in result.stdout
