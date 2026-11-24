"""The setup task fork.sh seeds into tasks/ must keep its relative links working.

tasks/templates/initial-agent-setup.md links ../../docs/first-task-walkthrough.md,
which is right for the template location but points outside the workspace once
fork.sh copies the file one level up to tasks/.
"""

import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\((?!https?://|#|mailto:)([^)#\s]+)")


def test_seeded_setup_task_links_resolve(tmp_path: Path) -> None:
    target = tmp_path / "agent"
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(
        [
            str(REPO / "scripts" / "fork.sh"),
            "--minimal",
            "--no-dotfiles",
            str(target),
            "Testy",
        ],
        cwd=REPO,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=300,
    )
    seeded = target / "tasks" / "initial-agent-setup.md"
    assert seeded.is_file(), "fork.sh did not seed tasks/initial-agent-setup.md"

    links = LINK.findall(seeded.read_text())
    assert any("first-task-walkthrough.md" in link for link in links)
    broken = [link for link in links if not (seeded.parent / link).resolve().exists()]
    assert broken == [], f"broken links in seeded setup task: {broken}"
