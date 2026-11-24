"""fork.sh with a relative ``./name`` target (the form its --help shows).

gptme-contrib is redirected to a local stub repo via ``url.insteadOf`` so the
fork runs offline.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

FORK = Path(__file__).resolve().parents[1] / "scripts" / "fork.sh"


def _git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


def test_relative_target_wires_memory_bridge(tmp_path: Path) -> None:
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
    env = {
        **os.environ,
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

    work = tmp_path / "work"
    work.mkdir()
    result = subprocess.run(
        ["bash", str(FORK), "./rover", "Rover"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    target = work / "rover"
    tracked = _git("ls-files", cwd=target, env=env).split()
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
