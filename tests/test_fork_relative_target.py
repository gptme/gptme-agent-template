"""fork.sh with a relative ``./name`` target (the form its --help shows).

gptme-contrib is redirected to a local stub repo via ``url.insteadOf`` so the
fork runs offline.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

FORK = Path(__file__).resolve().parents[1] / "scripts" / "fork.sh"


def _git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


def _fork_env(tmp_path: Path) -> dict[str, str]:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    stub = tmp_path / "contrib-stub"
    stub.mkdir()
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(
        "[user]\n  name = T\n  email = t@example.com\n"
        '[protocol "file"]\n  allow = always\n'
        f'[url "{stub}"]\n  insteadOf = https://github.com/gptme/gptme-contrib.git\n'
        "[init]\n  defaultBranch = master\n"
    )
    # fork.sh runs prek/pre-commit when on PATH, and real hooks can fetch
    # repos; shadow both with no-op stubs so the fork stays offline.
    stub_bin = tmp_path / "stub-bin"
    stub_bin.mkdir()
    for tool in ("prek", "pre-commit"):
        (stub_bin / tool).write_text("#!/bin/sh\nexit 0\n")
        (stub_bin / tool).chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{stub_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    env.pop("CLAUDE_HOME", None)
    env.pop("WORKSPACE", None)
    _git("init", "-q", cwd=stub, env=env)
    (stub / "README.md").write_text("stub\n")
    _git("add", ".", cwd=stub, env=env)
    _git("commit", "-qm", "stub", cwd=stub, env=env)
    return env


def _fork(
    tmp_path: Path, env: dict[str, str], target: str, name: str
) -> subprocess.CompletedProcess[str]:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(FORK), target, name],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_relative_target_wires_memory_bridge(tmp_path: Path) -> None:
    env = _fork_env(tmp_path)
    home = Path(env["HOME"])
    result = _fork(tmp_path, env, "./rover", "Rover")
    assert result.returncode == 0, result.stdout + result.stderr
    target = tmp_path / "work" / "rover"
    # Inspect the commit, not the index: a failed commit leaves files staged.
    tracked = _git(
        "ls-tree", "-r", "--name-only", "HEAD", cwd=target, env=env
    ).splitlines()
    assert "memory/MEMORY.md" in tracked, result.stdout + result.stderr
    assert "rover/memory/MEMORY.md" not in tracked, result.stdout + result.stderr

    bridge = (
        home
        / ".claude"
        / "projects"
        / re.sub(r"[^A-Za-z0-9]", "-", str(target))
        / "memory"
    )
    assert bridge.is_symlink(), sorted(
        p.name for p in (home / ".claude" / "projects").iterdir()
    )
    assert bridge.resolve() == (target / "memory").resolve()


def test_agent_name_with_perl_metacharacters_is_literal(tmp_path: Path) -> None:
    """The agent name was spliced into a perl s/// replacement: "/" aborted the
    fork and "@x" interpolated as an empty array, truncating the name."""
    env = _fork_env(tmp_path)
    name = "R2@D2/x$y"
    result = _fork(tmp_path, env, str(tmp_path / "work" / "droid"), name)
    assert result.returncode == 0, result.stdout + result.stderr
    toml = (tmp_path / "work" / "droid" / "gptme.toml").read_text()
    assert f'"{name}"' in toml, toml[:400]
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        return
    assert tomllib.loads(toml)["agent"]["name"] == name


@pytest.mark.parametrize("name", ["back\\slash", 'dq"uote', "tab\tname"])
def test_agent_name_that_breaks_toml_is_rejected(tmp_path: Path, name: str) -> None:
    """The name is copied verbatim into a quoted TOML string; a backslash or
    quote would yield a config gptme can't read (or reads as another name)."""
    env = _fork_env(tmp_path)
    target = tmp_path / "work" / "bad"
    result = _fork(tmp_path, env, str(target), name)
    assert result.returncode != 0
    assert "invalid agent name" in result.stderr, result.stdout + result.stderr
    assert not target.exists()
