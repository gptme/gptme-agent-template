#!/usr/bin/env python3
"""Generate journal context for gptme.

Provides recent journal entries with intelligent truncation of verbose sections.
Supports both legacy flat format (YYYY-MM-DD-topic.md) and new subdirectory format
(YYYY-MM-DD/topic.md).
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional


def find_journal_directory(agent_dir: Path) -> Optional[Path]:
    """Find journal directory in agent workspace.

    Args:
        agent_dir: Path to agent workspace root

    Returns:
        Path to journal directory if exists, None otherwise
    """
    journal_dir = agent_dir / "journal"
    return journal_dir if journal_dir.is_dir() else None


def is_date_directory(path: Path) -> bool:
    """Check if a path is a YYYY-MM-DD date directory.

    Args:
        path: Path to check

    Returns:
        True if path is a directory with YYYY-MM-DD name
    """
    return path.is_dir() and bool(re.match(r"^\d{4}-\d{2}-\d{2}$", path.name))


def extract_date_from_path(path: Path) -> Optional[str]:
    """Extract YYYY-MM-DD date from journal path.

    Supports both formats:
    - New: journal/2025-12-24/topic.md (date from parent directory)
    - Legacy: journal/2025-12-24-topic.md (date from filename prefix)

    Args:
        path: Journal file path

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    # Try parent directory name first (new format)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", path.parent.name):
        return path.parent.name

    # Fallback to filename prefix (legacy format)
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else None


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract YYYY-MM-DD date from journal filename (legacy format).

    Args:
        filename: Journal filename (e.g., "2025-11-04-session.md")

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None


def get_all_journal_dates(journal_dir: Path) -> List[str]:
    """Get all dates that have journal entries, checking both formats.

    Args:
        journal_dir: Path to journal directory

    Returns:
        List of date strings in YYYY-MM-DD format, sorted descending (most recent first)
    """
    dates = set()

    # Check new format: date subdirectories
    for entry in journal_dir.iterdir():
        if is_date_directory(entry):
            # Only include if it has markdown files
            if any(f.suffix == ".md" for f in entry.iterdir() if f.is_file()):
                dates.add(entry.name)

    # Check legacy format: date-prefixed files
    pattern = r"^(\d{4}-\d{2}-\d{2})"
    for f in journal_dir.glob("*.md"):
        if f.is_file():
            match = re.match(pattern, f.name)
            if match:
                dates.add(match.group(1))

    return sorted(dates, reverse=True)


def get_recent_journal_date(journal_dir: Path) -> Optional[str]:
    """Get most recent journal date from journal files.

    Supports both legacy flat format and new subdirectory format.

    Args:
        journal_dir: Path to journal directory

    Returns:
        Most recent date string in YYYY-MM-DD format, or None if no journals
    """
    dates = get_all_journal_dates(journal_dir)
    return dates[0] if dates else None


def get_journals_for_date(journal_dir: Path, target_date: str) -> List[Path]:
    """Get all journal files for a specific date, sorted by modification time.

    Supports both formats:
    - New: journal/YYYY-MM-DD/*.md
    - Legacy: journal/YYYY-MM-DD-*.md

    Args:
        journal_dir: Path to journal directory
        target_date: Date string in YYYY-MM-DD format

    Returns:
        List of journal file paths sorted by mtime (most recent first)
    """
    journal_files: List[Path] = []

    # Check new format: subdirectory
    date_dir = journal_dir / target_date
    if date_dir.is_dir():
        journal_files.extend(f for f in date_dir.glob("*.md") if f.is_file())

    # Check legacy format: date-prefixed files in root
    legacy_pattern = f"{target_date}*.md"
    journal_files.extend(f for f in journal_dir.glob(legacy_pattern) if f.is_file())

    # Sort by modification time (most recent first)
    journal_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return journal_files


def get_date_header(journal_date: str) -> str:
    """Get appropriate header for journal date.

    Args:
        journal_date: Date string in YYYY-MM-DD format

    Returns:
        Human-readable header string
    """
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    if journal_date == today:
        return "Today's Journal Entry"
    elif journal_date == yesterday:
        return "Yesterday's Journal Entry"
    else:
        return f"Journal Entry from {journal_date}"


def extract_description(journal_path: Path) -> Optional[str]:
    """Extract description from journal filename or path.

    Supports both formats:
    - New: journal/2025-12-24/topic.md -> "topic"
    - Legacy: journal/2025-12-24-topic.md -> "topic"

    Args:
        journal_path: Path to journal file

    Returns:
        Description string, or None if not extractable
    """
    # New format: filename is the description
    if re.match(r"^\d{4}-\d{2}-\d{2}$", journal_path.parent.name):
        return journal_path.stem

    # Legacy format: extract from filename
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", journal_path.stem)
    return match.group(1) if match else None


def truncate_journal_sections(content: str, max_lines: int = 20) -> str:
    """Truncate verbose sections in journal content.

    Truncates sections that match patterns like 'Session X' or tool outputs
    to reduce context size while preserving structure.

    Args:
        content: Journal content string
        max_lines: Maximum lines before truncation per section

    Returns:
        Truncated content string
    """
    lines = content.split("\n")
    result = []
    section_lines: List[str] = []
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            if in_code_block:
                # Starting code block - flush section
                if section_lines:
                    result.extend(_truncate_section(section_lines, max_lines))
                    section_lines = []
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Check for section headers
        if re.match(r"^##\s+", line):
            # Flush previous section
            if section_lines:
                result.extend(_truncate_section(section_lines, max_lines))
            section_lines = [line]
        else:
            section_lines.append(line)

    # Handle remaining lines
    if section_lines:
        result.extend(_truncate_section(section_lines, max_lines))

    return "\n".join(result)


def _truncate_section(lines: List[str], max_lines: int) -> List[str]:
    """Truncate a single section if too long.

    Args:
        lines: Lines in the section
        max_lines: Maximum lines before truncation

    Returns:
        Truncated lines
    """
    if len(lines) <= max_lines:
        return lines

    # Keep first few and last few lines
    keep_start = max_lines // 2
    keep_end = max_lines // 2
    truncated_count = len(lines) - keep_start - keep_end

    return (
        lines[:keep_start]
        + [f"\n[... {truncated_count} lines truncated ...]\n"]
        + lines[-keep_end:]
    )


def generate_journal_context(
    agent_dir: Path,
    max_full_entries: int = 10,
) -> str:
    """Generate journal context string for gptme.

    Args:
        agent_dir: Path to agent workspace root
        max_full_entries: Maximum number of entries to include in full

    Returns:
        Formatted journal context string
    """
    output: List[str] = ["# Journal Context", ""]

    # Find journal directory
    journal_dir = find_journal_directory(agent_dir)
    if not journal_dir:
        output.append("Journal folder not found, skipping journal section.")
        return "\n".join(output)

    # Get most recent journal date
    recent_date = get_recent_journal_date(journal_dir)
    if not recent_date:
        output.append("No journal entries found.")
        return "\n".join(output)

    # Get all journals for this date
    journals = get_journals_for_date(journal_dir, recent_date)
    if not journals:
        output.append("No journal entries found.")
        return "\n".join(output)

    # Determine header
    header = get_date_header(recent_date)
    journal_count = len(journals)

    if journal_count == 1:
        output.append(f"{header}:")
    else:
        output.append(f"{header} ({journal_count} sessions):")
    output.append("")

    # Add instructions if not today
    today = date.today().isoformat()
    if recent_date != today:
        output.extend(
            [
                f"**IMPORTANT**: This journal is from {recent_date} (not today: {today}).",
                f"Create a NEW journal entry for today at: `journal/{today}/<description>.md`",
                "",
            ]
        )

    # Sort journals chronologically for display (oldest first)
    recent_journals = journals[:max_full_entries]
    recent_journals.sort(key=lambda f: f.stat().st_mtime)

    older_journals = journals[max_full_entries:]

    # Output recent journal files with truncation
    for journal_path in recent_journals:
        description = extract_description(journal_path)

        if description and journal_count > 1:
            output.extend([f"## Session: {description}", ""])

        # Read and truncate content
        content = journal_path.read_text(encoding="utf-8")
        truncated = truncate_journal_sections(content)

        output.extend([f"```{journal_path}", truncated, "```", ""])

    # List older journals
    if older_journals:
        output.extend(["## Older Sessions (read with cat if relevant)", ""])
        for journal_path in older_journals:
            output.append(f"- `{journal_path}`")
        output.append("")

    return "\n".join(output)


def find_workspace_root(start_path: Path) -> Optional[Path]:
    """Find the workspace root by looking for identifying files.

    Args:
        start_path: Path to start searching from

    Returns:
        Path to workspace root if found, None otherwise
    """
    current = start_path.resolve()
    while current != current.parent:
        # Check for workspace identifiers
        if (current / "gptme.toml").exists():
            return current
        if (current / ".git").exists() and (current / "journal").is_dir():
            return current
        current = current.parent
    return None


def main() -> int:
    """Main entry point for journal context generation."""
    try:
        # Find workspace root from current directory or script location
        agent_dir = find_workspace_root(Path.cwd())
        if not agent_dir:
            agent_dir = find_workspace_root(Path(__file__).parent)

        if not agent_dir:
            print("Error: Could not find workspace root", file=sys.stderr)
            return 1

        # Generate and print context
        context = generate_journal_context(agent_dir)
        print(context)

        return 0
    except Exception as e:
        print(f"Error generating journal context: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
