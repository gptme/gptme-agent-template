"""Exercise CI's branch-exposure step with real push and PR checkout shapes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"


@pytest.mark.parametrize("detached", [False, True], ids=["push-master", "pull-request"])
def test_onboarding_branch_can_be_cloned(tmp_path: Path, detached: bool) -> None:
    repo = tmp_path / "checkout"
    subprocess.run(["git", "init", "-b", "master", str(repo)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
    )
    if detached:
        subprocess.run(["git", "-C", str(repo), "checkout", "--detach"], check=True)
    expected = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    # Execute the workflow's actual shell, not a separately maintained copy.
    step = (
        WORKFLOW.read_text()
        .split(
            "    - name: Expose the checked-out commit as a branch the clone can see\n",
            1,
        )[1]
        .split("\n    - name:", 1)[0]
    )
    script = "\n".join(
        line.removeprefix("        ")
        for line in step.split("      run: |\n", 1)[1].splitlines()
    )
    script = script.replace("${{ github.head_ref || github.ref_name }}", "master")
    github_env = tmp_path / "github-env"
    subprocess.run(
        ["bash", "-eu", "-c", script],
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(repo),
            "GITHUB_ENV": str(github_env),
        },
        check=True,
    )
    branch = github_env.read_text().strip().removeprefix("TEMPLATE_BRANCH=")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--branch", branch, repo.as_uri(), str(clone)], check=True
    )
    assert (
        subprocess.check_output(
            ["git", "-C", str(clone), "rev-parse", "HEAD"], text=True
        ).strip()
        == expected
    )
    assert (
        subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        == expected
    )
