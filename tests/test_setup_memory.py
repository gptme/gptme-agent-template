"""Tests for scripts/setup-memory.sh bridge migration."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup-memory.sh"


def _run(workspace: Path, claude_home: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "WORKSPACE": str(workspace), "CLAUDE_HOME": str(claude_home)}
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def _bridge(workspace: Path, claude_home: Path) -> Path:
    # Claude Code: every non-alphanumeric path character becomes "-"
    mangled = re.sub(r"[^A-Za-z0-9]", "-", str(workspace))
    return claude_home / "projects" / mangled / "memory"


def test_rerun_does_not_overwrite_parked_backup(tmp_path: Path) -> None:
    """A colliding bridge file is parked; a later run that parks another copy
    of the same file must not overwrite the first parked copy."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    claude_home = tmp_path / ".claude"
    bridge = _bridge(workspace, claude_home)
    bridge.mkdir(parents=True)

    (bridge / "MEMORY.md").write_text("FIRST bridge index\n")
    first = _run(workspace, claude_home)
    assert first.returncode == 1  # collision parked, dir left in place

    # Claude Code keeps writing into the still-real dir.
    (bridge / "MEMORY.md").write_text("SECOND bridge index\n")
    _run(workspace, claude_home)

    contents = [
        p.read_text()
        for root in (bridge, workspace / "memory")
        if root.is_dir() and not root.is_symlink()
        for p in root.iterdir()
    ]
    assert any("FIRST" in c for c in contents), contents
    assert any("SECOND" in c for c in contents), contents


def test_bridge_dir_matches_claude_code_mangling_for_underscores(
    tmp_path: Path,
) -> None:
    """Claude Code maps every non-alphanumeric path character to "-" (observed:
    cwd /home/agent/.review-__4m33zb -> project -home-agent--review---4m33zb).
    A workspace path with "_" must get its bridge in that same directory."""
    workspace = tmp_path / "my_agent"
    workspace.mkdir()
    claude_home = tmp_path / ".claude"
    claude_home.mkdir()
    result = _run(workspace, claude_home)
    assert result.returncode == 0, result.stderr
    expected = _bridge(workspace, claude_home)
    assert expected.is_symlink(), sorted(
        p.name for p in (claude_home / "projects").iterdir()
    )
