"""Tests for scripts/setup-memory.sh bridge migration."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup-memory.sh"


def _run(
    workspace: Path, claude_home: Path, memory_dir: str = "memory"
) -> subprocess.CompletedProcess[str]:
    # MEMORY_DIR is pinned so a caller's own MEMORY_DIR cannot leak into the tests.
    env = {
        **os.environ,
        "WORKSPACE": str(workspace),
        "CLAUDE_HOME": str(claude_home),
        "MEMORY_DIR": memory_dir,
    }
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
    second = _run(workspace, claude_home)
    assert second.returncode == 1

    # Both parked copies stay in the bridge dir until the user resolves them;
    # neither is migrated into the repo.
    assert (bridge / "MEMORY.md.bridge-backup").read_text() == "FIRST bridge index\n"
    assert (bridge / "MEMORY.md.bridge-backup.1").read_text() == "SECOND bridge index\n"
    assert sorted(p.name for p in (workspace / "memory").iterdir()) == ["MEMORY.md"]


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


def test_sibling_workspace_link_is_not_stolen(tmp_path: Path) -> None:
    """my-agent and my_agent mangle to the same project dir. Setting up the
    second must keep the first's live link rather than repoint it."""
    claude_home = tmp_path / ".claude"
    claude_home.mkdir()
    first = tmp_path / "my-agent"
    second = tmp_path / "my_agent"
    first.mkdir()
    second.mkdir()
    assert _bridge(first, claude_home) == _bridge(second, claude_home)
    assert _run(first, claude_home).returncode == 0

    result = _run(second, claude_home)
    assert result.returncode == 1
    assert str(first / "memory") in result.stderr, result.stderr
    bridge = _bridge(first, claude_home)
    assert bridge.resolve() == (first / "memory").resolve()


def test_dangling_link_is_repointed(tmp_path: Path) -> None:
    """A link left behind by a moved/deleted workspace is safe to repoint."""
    claude_home = tmp_path / ".claude"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    bridge = _bridge(workspace, claude_home)
    bridge.parent.mkdir(parents=True)
    bridge.symlink_to(tmp_path / "gone" / "memory")

    result = _run(workspace, claude_home)
    assert result.returncode == 0, result.stderr
    assert bridge.resolve() == (workspace / "memory").resolve()


def test_date_stamped_user_file_is_migrated(tmp_path: Path) -> None:
    """Only the script's own NAME.bridge-backup[.N] names stay parked; a user
    file that merely contains ".bridge-backup." is migrated like any other."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    claude_home = tmp_path / ".claude"
    bridge = _bridge(workspace, claude_home)
    bridge.mkdir(parents=True)
    name = "notes.bridge-backup.2026-11-24.md"
    (bridge / name).write_text("user notes\n")

    result = _run(workspace, claude_home)
    assert result.returncode == 0, result.stderr
    assert (workspace / "memory" / name).read_text() == "user notes\n"
    assert bridge.is_symlink()
    assert bridge.resolve() == (workspace / "memory").resolve()


def test_own_memory_link_to_other_disk_is_repointed(tmp_path: Path) -> None:
    """The bridge points at a memory dir inside this workspace that is itself a
    symlink to another disk. It resolves outside the workspace but is still
    this workspace's link, so changing MEMORY_DIR repoints it instead of
    reporting a sibling-workspace collision."""
    claude_home = tmp_path / ".claude"
    workspace = tmp_path / "ws"
    other_disk = tmp_path / "other-disk" / "claude-memory"
    other_disk.mkdir(parents=True)
    (workspace / "knowledge").mkdir(parents=True)
    (workspace / "knowledge" / "claude-memory").symlink_to(other_disk)
    bridge = _bridge(workspace, claude_home)
    bridge.parent.mkdir(parents=True)
    bridge.symlink_to(workspace / "knowledge" / "claude-memory")

    result = _run(workspace, claude_home, memory_dir="memory")
    assert result.returncode == 0, result.stderr
    assert bridge.resolve() == (workspace / "memory").resolve()
