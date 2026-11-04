"""Tests for the onboarding-path config assertion used by CI.

The CI job asserted on `gptme-agent doctor` output and half of that assertion was
dead: doctor prints only the check message, so `Context command: not configured`
never appears. These tests pin the replacement — a direct `gptme.toml` structure
assertion — in both directions, so the job fails when either defect returns.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from check_onboarding_config import check_workspace

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_TOML = REPO_ROOT / "gptme.toml"


def _write(tmp_path: Path, text: str) -> Path:
    (tmp_path / "gptme.toml").write_text(text)
    return tmp_path


def test_template_config_passes(tmp_path: Path) -> None:
    """The template's own gptme.toml is the contract a created workspace must keep."""
    shutil.copy(TEMPLATE_TOML, tmp_path / "gptme.toml")
    assert check_workspace(tmp_path) == []


def test_missing_prompt_table_is_reported(tmp_path: Path) -> None:
    """Regression: `gptme-agent create` dropping [prompt] disabled auto-includes."""
    workspace = _write(
        tmp_path,
        '[agent]\nname = "MyAgent"\n',
    )
    problems = check_workspace(workspace)
    assert len(problems) == 1
    assert "[prompt] table" in problems[0]


def test_legacy_flat_form_is_reported(tmp_path: Path) -> None:
    """The flat form still loads, but it is not the template's contract."""
    workspace = _write(
        tmp_path,
        '[agent]\nname = "MyAgent"\n\nfiles = ["README.md"]\ncontext_cmd = "scripts/context.sh"\n',
    )
    problems = check_workspace(workspace)
    assert any("[prompt] table" in p for p in problems)


def test_missing_context_cmd_is_reported(tmp_path: Path) -> None:
    """Regression: the check the old doctor grep could never perform."""
    workspace = _write(
        tmp_path,
        '[agent]\nname = "MyAgent"\n\n[prompt]\nfiles = ["README.md"]\n',
    )
    problems = check_workspace(workspace)
    assert len(problems) == 1
    assert "context_cmd" in problems[0]


def test_empty_files_list_is_reported(tmp_path: Path) -> None:
    workspace = _write(
        tmp_path,
        '[agent]\nname = "MyAgent"\n\n[prompt]\nfiles = []\n'
        'context_cmd = "scripts/context.sh"\n',
    )
    problems = check_workspace(workspace)
    assert len(problems) == 1
    assert ".files" in problems[0]


def test_missing_toml_is_reported(tmp_path: Path) -> None:
    problems = check_workspace(tmp_path)
    assert len(problems) == 1
    assert "does not exist" in problems[0]
