#!/usr/bin/env python3
"""Pre-commit hook to verify relative links in markdown files.

Features:
- Validates all relative links in markdown files
- Handles both root-relative and directory-relative paths
- Follows symlinks correctly
- Ignores example files in projects/
- Skips URLs (http://, https://, ftp://, mailto:)
- Handles anchor links (#section-name)
- Self-contained with built-in tests (run with pytest)

Usage:
    Directly:
        python3 scripts/check_markdown_links.py [files...]

    With pytest:
        pytest scripts/check_markdown_links.py

    As pre-commit hook (.pre-commit-config.yaml):
        - repo: local
          hooks:
          - id: check-markdown-links
            name: Check markdown links
            entry: python3 scripts/check_markdown_links.py
            language: system
            types: [markdown]
            pass_filenames: true

Link Resolution Rules:
    1. Root-relative paths (starting with /):
       - Resolved from repository root
       - Example: /docs/README.md

    2. Directory-relative paths:
       - Starting with ./: Resolved from current file's directory
       - No prefix: Resolved from current file's directory
       - Example: ./setup.md or setup.md

    3. Parent directory paths:
       - Using ../ to navigate up
       - Example: ../docs/setup.md

Excluded Links:
    - URLs with protocols (http://, https://, ftp://, mailto:)
    - Pure anchor links (#section-name)
    - Files in projects/*/examples/ directories

Error Reporting:
    Reports broken links in format:
    path/to/file.md: Broken link: link/path.md -> /absolute/path/to/missing/file.md

Exit Codes:
    0: All links valid
    1: One or more broken links found
"""

import re
import sys
from pathlib import Path
from collections.abc import Sequence


def find_relative_links(content: str) -> list[tuple[str, str]]:
    """Find all relative links in markdown content, returns (text, link) tuples."""
    # Match [text](link) but exclude URLs with protocols and pure anchor links
    pattern = r"\[([^\]]+)\]\((?!https?://|ftp://|mailto:|#)([^)#\s]+)(?:#[^)]*)?\)"
    return [(match[1], match[2]) for match in re.finditer(pattern, content)]


def find_repo_root(start_path: Path) -> Path:
    """Find the repository root by looking for .git directory."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start_path.resolve()


def verify_links(file_path: Path, links: list[tuple[str, str]]) -> list[str]:
    """Verify each link resolves to an existing file."""
    errors = []
    repo_root = find_repo_root(file_path)

    # Skip example and template files
    if "examples" in str(file_path) or "templates" in str(file_path):
        return []

    for _link_text, link_path in links:
        try:
            # Handle both root-relative and directory-relative paths
            if link_path.startswith("/"):
                target = (repo_root / link_path.lstrip("/")).resolve()
            elif link_path.startswith("./"):
                target = (file_path.parent / link_path[2:]).resolve()
            else:
                target = (file_path.parent / link_path).resolve()

            # Handle links to projects directory specially
            if "projects/" in str(link_path):
                project_root = repo_root / "projects"
                try:
                    # Get the project name from the path
                    parts = Path(link_path).parts
                    proj_idx = parts.index("projects") + 1
                    if proj_idx < len(parts):
                        project_name = parts[proj_idx]
                        project_symlink = project_root / project_name

                        # If project symlink exists, verify the target
                        if project_symlink.exists() and project_symlink.is_symlink():
                            try:
                                resolved_target = target.resolve()
                                if not resolved_target.exists():
                                    errors.append(
                                        f"{file_path}: Broken link: {link_path} -> {resolved_target}"
                                    )
                            except Exception as e:
                                errors.append(
                                    f"{file_path}: Error resolving link {link_path}: {e}"
                                )
                        # If project not checked out (symlink doesn't exist), skip verification
                        continue
                except (ValueError, IndexError):
                    # Not actually under projects/ or invalid path, treat normally
                    pass

            # For non-projects links, follow symlinks and check final target
            while target.is_symlink():
                target = target.resolve()

            if not target.exists():
                errors.append(f"{file_path}: Broken link: {link_path} -> {target}")
                continue

            # Check that target is within repo_root or is a projects link
            try:
                target.relative_to(repo_root)
            except ValueError:
                # For links pointing outside repo, only allow if they go through projects/
                if not (
                    "projects/" in str(link_path)
                    and (repo_root / "projects").exists()
                    and any(
                        (repo_root / "projects" / p).is_symlink()
                        for p in Path(link_path).parts
                        if p != "projects"
                    )
                ):
                    errors.append(
                        f"{file_path}: Link {link_path} points outside repository"
                    )

        except Exception as e:
            errors.append(f"{file_path}: Error resolving link {link_path}: {e}")

    return errors


def main(argv: Sequence[str] = sys.argv) -> int:
    """Main function."""
    if len(argv) > 1:
        files = [Path(f) for f in argv[1:]]
    else:
        files = list(Path().rglob("*.md"))

    all_errors = []
    for file in files:
        if file.is_symlink():  # Skip symlinks to avoid duplicates
            continue

        content = file.read_text()
        links = find_relative_links(content)
        errors = verify_links(file, links)
        all_errors.extend(errors)

    if all_errors:
        print("\n".join(all_errors))
        return 1
    return 0


def test_find_relative_links() -> None:
    """Test the link finding function."""
    content = """# Test Document
[valid link](./file.md)
[external](https://example.com)
[mail](mailto:test@example.com)
[anchor](#section)
[combined](./file.md#section)
"""
    links = find_relative_links(content)
    assert len(links) == 2
    assert links[0] == ("valid link", "./file.md")
    assert links[1] == ("combined", "./file.md")


def test_verify_links() -> None:
    """Test the link verification function."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create test directory structure
        (root / "dir1").mkdir()
        (root / "dir2").mkdir()
        (root / "projects/example/examples").mkdir(parents=True)

        # Create test files
        (root / "target.md").write_text("target")
        (root / "dir1/file1.md").write_text("file1")
        (root / "dir2/file2.md").write_text("file2")
        (root / "dir1/symlink.md").symlink_to("../target.md")

        # Save current directory and change to test directory
        old_cwd = os.getcwd()
        os.chdir(str(root))

        try:
            # Test valid links
            test_file = root / "test.md"
            test_file.write_text("[link](./target.md)")
            errors = verify_links(test_file, find_relative_links(test_file.read_text()))
            assert len(errors) == 0

            # Test broken link
            test_file.write_text("[broken](./nonexistent.md)")
            errors = verify_links(test_file, find_relative_links(test_file.read_text()))
            assert len(errors) == 1
            assert "Broken link" in errors[0]

            # Test symlink
            test_file.write_text("[symlink](./dir1/symlink.md)")
            errors = verify_links(test_file, find_relative_links(test_file.read_text()))
            assert len(errors) == 0

            # Test example file (should be ignored)
            example_file = root / "projects/example/examples/test.md"
            example_file.write_text("[broken](./nonexistent.md)")
            errors = verify_links(
                example_file, find_relative_links(example_file.read_text())
            )
            assert len(errors) == 0

        finally:
            os.chdir(old_cwd)


if __name__ == "__main__":
    sys.exit(main())
