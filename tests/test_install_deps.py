"""Tests for the python3 version gate in scripts/install-deps.sh.

A fake `python3` earlier on PATH reports a chosen version, so the script's real
version check runs without needing an old interpreter installed.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install-deps.sh"


def _run_with_python(
    tmp_path: Path, version: tuple[int, int, int]
) -> subprocess.CompletedProcess[str]:
    """Run install-deps.sh with a stub python3 that reports `version`."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "python3"
    # `--version` prints the version; `-c CODE` runs CODE under the real
    # interpreter with sys.version_info patched to the stub's version.
    fake.write_text(
        "#!/usr/bin/env bash\n"
        f'if [[ "$1" == "--version" ]]; then echo "Python {version[0]}.{version[1]}.{version[2]}"; exit 0; fi\n'
        f'exec "{sys.executable}" -I -c "import sys; sys.version_info = {version!r}; exec(sys.argv[1])" "${{@:2}}"\n'
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    # Isolate HOME/CLAUDE_HOME/WORKSPACE: the script ends by running
    # setup-memory.sh, which must never see (or relocate) the developer's real
    # Claude Code memory directory.
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "NO_COLOR": "1",
        "HOME": str(home),
        "CLAUDE_HOME": str(home / ".claude"),
        "WORKSPACE": str(tmp_path / "workspace"),
    }
    return subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("version", [(3, 10, 12), (3, 11, 4)])
def test_too_old_python_is_flagged(
    tmp_path: Path, version: tuple[int, int, int]
) -> None:
    result = _run_with_python(tmp_path, version)
    assert "too old" in result.stdout
    assert "python3>=3.11.5" in result.stdout
    assert result.returncode != 0


@pytest.mark.parametrize("version", [(3, 11, 5), (3, 12, 0)])
def test_new_enough_python_not_flagged(
    tmp_path: Path, version: tuple[int, int, int]
) -> None:
    result = _run_with_python(tmp_path, version)
    assert "too old" not in result.stdout
    assert "python3>=3.11.5" not in result.stdout
