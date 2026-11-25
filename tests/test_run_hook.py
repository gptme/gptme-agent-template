"""Tests for .claude/hooks/run-hook.sh, the fail-open Claude Code hook launcher.

Claude Code treats exit status 2 from a hook as "block". `python3 MISSING.py`
exits 2, so a hook whose script is missing (submodule not checked out, dangling
symlink, renamed upstream script) would refuse every tool call, prompt or stop.
The launcher skips missing scripts and interpreters with exit 0, and passes
everything else through.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / ".claude" / "hooks"
LAUNCHER = HOOKS_DIR / "run-hook.sh"
SETTINGS = ROOT / ".claude" / "settings.json"
LAUNCHER_PREFIX = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/run-hook.sh '


def _run(args, tmp_path, stdin="", env=None):
    return subprocess.run(
        [str(LAUNCHER), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CLAUDE_HOOK_MISS_LOG": str(tmp_path / "miss.log"),
            **(env or {}),
        },
    )


def _script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body)
    return path


def _hook_commands():
    settings = json.loads(SETTINGS.read_text())
    return [
        (event, hook["command"])
        for event, groups in settings["hooks"].items()
        for group in groups
        for hook in group["hooks"]
        if hook.get("type") == "command"
    ]


def test_launcher_is_executable_regular_file():
    # A symlink into a submodule would go missing exactly when it is needed.
    assert not LAUNCHER.is_symlink()
    assert LAUNCHER.is_file()
    assert os.access(LAUNCHER, os.X_OK)


def test_missing_script_exits_zero_and_logs(tmp_path):
    result = _run([sys.executable, str(tmp_path / "nope.py")], tmp_path)
    assert result.returncode == 0
    assert "hook script not found" in result.stderr
    assert "nope.py" in (tmp_path / "miss.log").read_text()


def test_dangling_symlink_exits_zero(tmp_path):
    link = tmp_path / "hook.py"
    link.symlink_to(tmp_path / "gptme-contrib" / "missing.py")
    result = _run([sys.executable, str(link)], tmp_path)
    assert result.returncode == 0
    assert "hook script not found" in result.stderr


def test_missing_interpreter_exits_zero(tmp_path):
    script = _script(tmp_path, "ok.py", "print('hi')\n")
    result = _run(["no-such-interpreter-xyz", str(script)], tmp_path)
    assert result.returncode == 0
    assert "interpreter not found" in result.stderr


@pytest.mark.parametrize("no_block", [[], ["--no-block"]])
def test_stdin_stdout_and_args_pass_through(tmp_path, no_block):
    script = _script(
        tmp_path,
        "echo.py",
        "import sys\nprint(sys.stdin.read().upper() + ' ' + ' '.join(sys.argv[1:]))\n",
    )
    result = _run(
        [*no_block, sys.executable, str(script), "a", "b"], tmp_path, stdin="payload"
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "PAYLOAD a b"


@pytest.mark.parametrize("code", [0, 1, 2, 3])
def test_exit_code_passes_through(tmp_path, code):
    # Without --no-block, a hook that blocks on purpose (exit 2) still blocks.
    script = _script(tmp_path, "rc.py", f"raise SystemExit({code})\n")
    assert _run([sys.executable, str(script)], tmp_path).returncode == code


@pytest.mark.parametrize("code,expected", [(0, 0), (1, 1), (2, 1), (3, 3)])
def test_no_block_turns_two_into_one(tmp_path, code, expected):
    script = _script(tmp_path, "rc.py", f"raise SystemExit({code})\n")
    result = _run(["--no-block", sys.executable, str(script)], tmp_path)
    assert result.returncode == expected


def test_settings_has_hook_commands():
    assert _hook_commands(), "no command hooks found in .claude/settings.json"


@pytest.mark.parametrize("event,command", _hook_commands())
def test_every_settings_hook_goes_through_launcher(event, command):
    # Shell setup before the launcher is fine (e.g. choosing the interpreter
    # with `PY=...;`), but the hook script itself must only be run by it.
    *setup, invocation = command.split(";")
    assert invocation.strip().startswith(
        LAUNCHER_PREFIX
    ), f"{event} hook does not use run-hook.sh: {command}"
    assert not any(
        ".claude/hooks/" in part for part in setup
    ), f"{event} hook runs a hook script outside run-hook.sh: {command}"


@pytest.mark.parametrize("event,command", _hook_commands())
def test_settings_hooks_do_not_block_without_hook_scripts(tmp_path, event, command):
    # A checkout without submodules: settings.json and the launcher are there,
    # the hook scripts are not. Run each command the way Claude Code does.
    workspace = tmp_path / "agent with spaces"
    (workspace / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy2(LAUNCHER, workspace / ".claude" / "hooks" / "run-hook.sh")
    result = subprocess.run(
        command,
        shell=True,
        input="{}",
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(workspace),
            "CLAUDE_HOOK_MISS_LOG": str(tmp_path / "miss.log"),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "hook script not found" in result.stderr
    assert "hook script not found" in (tmp_path / "miss.log").read_text()


def test_unwritable_miss_log_still_exits_zero(tmp_path):
    # The miss log is best effort: if it cannot be written the hook is still skipped.
    log_dir = tmp_path / "is-a-directory"
    log_dir.mkdir()
    result = subprocess.run(
        [str(LAUNCHER), "--no-block", sys.executable, str(tmp_path / "missing.py")],
        input="{}",
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_HOOK_MISS_LOG": str(log_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert "hook script not found" in result.stderr


def test_no_block_passes_termination_on_to_the_script(tmp_path):
    # A hook that hits its timeout is killed by signal. In --no-block mode the script is a
    # child of the launcher and must not outlive it.
    pid_file = tmp_path / "child.pid"
    script = tmp_path / "slow.py"
    script.write_text(
        "import os, sys, time\n"
        "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    launcher = subprocess.Popen(
        [str(LAUNCHER), "--no-block", sys.executable, str(script), str(pid_file)],
        stdin=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 10
        while (
            not (pid_file.exists() and pid_file.read_text()) and time.time() < deadline
        ):
            time.sleep(0.05)
        child_pid = int(pid_file.read_text())
        launcher.send_signal(signal.SIGTERM)
        launcher.wait(timeout=10)
        deadline = time.time() + 10
        alive = True
        while alive and time.time() < deadline:
            try:
                os.kill(child_pid, 0)
                time.sleep(0.05)
            except ProcessLookupError:
                alive = False
        assert not alive, "hook script kept running after the launcher was terminated"
    finally:
        if launcher.poll() is None:
            launcher.kill()


def test_default_miss_log_is_per_user(tmp_path):
    """The default log lives in a private per-user state dir, not shared /tmp."""
    state = tmp_path / "state"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_HOOK_MISS_LOG"}
    env["XDG_STATE_HOME"] = str(state)
    result = subprocess.run(
        [str(LAUNCHER), "python3", str(tmp_path / "missing.py")],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0
    log_dir = state / "claude-hooks"
    assert "hook script not found" in (log_dir / "missing.log").read_text()
    assert (log_dir.stat().st_mode & 0o777) == 0o700


def test_miss_log_is_never_appended_through_a_symlink(tmp_path):
    """A planted symlink at the log path must not redirect the append."""
    victim = tmp_path / "victim"
    victim.write_text("original\n")
    link = tmp_path / "miss.log"
    link.symlink_to(victim)
    result = _run(["python3", str(tmp_path / "missing.py")], tmp_path)
    assert result.returncode == 0
    assert victim.read_text() == "original\n"
