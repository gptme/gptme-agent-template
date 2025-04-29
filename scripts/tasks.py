#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click>=8.0.0",
#     "rich>=13.0.0",
#     "python-frontmatter>=1.1.0",
#     "tabulate>=0.9.0",
# ]
# [tool.uv]
# exclude-newer = "2024-04-01T00:00:00Z"
# ///

"""Task verification and status CLI for gptme agents.

Features:
- Status views
- Task metadata verification
- Dependency validation
- Link checking
"""

import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import (
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
)

import click
import frontmatter
from rich.console import Console
from rich.table import Table
from tabulate import tabulate


@dataclass
class DirectoryConfig:
    """Configuration for a directory type."""

    type_name: str
    states: list[str]
    special_files: list[str]
    emoji: str  # Emoji for visual distinction


CONFIGS = {
    "tasks": DirectoryConfig(
        type_name="tasks",
        states=["new", "active", "paused", "done", "cancelled"],
        special_files=["README.md", "templates", "video-scripts"],
        emoji="📋",
    ),
    "tweets": DirectoryConfig(
        type_name="tweets",
        states=["new", "queued", "approved", "posted"],
        special_files=["README.md", "templates"],
        emoji="🐦",
    ),
    "email": DirectoryConfig(
        type_name="email",
        states=["inbox", "drafts", "sent", "archive"],
        special_files=["README.md", "templates", "config"],
        emoji="📧",
    ),
}


class SubtaskCount(NamedTuple):
    """Count of completed and total subtasks."""

    completed: int
    total: int

    def __str__(self) -> str:
        """Return string representation like (4/16)."""
        return f"({self.completed}/{self.total})" if self.total > 0 else ""


@dataclass
class TaskInfo:
    """Information about a task with metadata and validation.

    This class represents a task file with its metadata, content analysis,
    and validation status. It provides a unified interface for accessing
    task information across the codebase.

    Attributes:
        path: Path to the task file
        name: Filename without .md extension
        state: Current state from frontmatter (new, active, paused, etc.)
        created: Creation timestamp
        modified: Last modification timestamp
        priority: Task priority (high, medium, low)
        tags: List of tags
        depends: List of task dependencies
        subtasks: Count of completed and total subtasks
        issues: List of validation issues
        metadata: Raw frontmatter metadata
    """

    path: Path
    name: str
    state: Optional[str]
    created: datetime
    modified: datetime
    priority: Optional[str]
    tags: List[str]
    depends: List[str]
    subtasks: SubtaskCount
    issues: List[str]
    metadata: Dict

    @property
    def id(self) -> str:
        """Get task ID (filename without .md)."""
        return self.name

    @property
    def created_ago(self) -> str:
        """Get human-readable time since creation."""
        return format_time_ago(self.created)

    @property
    def modified_ago(self) -> str:
        """Get human-readable time since last modification."""
        return format_time_ago(self.modified)

    @property
    def has_issues(self) -> bool:
        """Check if task has any validation issues."""
        return len(self.issues) > 0

    @property
    def priority_rank(self) -> int:
        """Get numeric priority rank for sorting.

        Returns:
            int: Priority rank (3=high, 2=medium, 1=low, 0=none)
        """
        # Handle None case explicitly to satisfy type checker
        if self.priority is None:
            return PRIORITY_RANK[None]
        return PRIORITY_RANK.get(self.priority, 0)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = []
        if self.state:
            status.append(self.state)
        if self.priority:
            status.append(self.priority)
        if self.subtasks.total > 0:
            status.append(f"{self.subtasks.completed}/{self.subtasks.total}")

        status_str = f" ({', '.join(status)})" if status else ""
        return f"{self.name}{status_str}"


def count_subtasks(content: str) -> SubtaskCount:
    """Count completed and total subtasks in markdown content.

    Looks for markdown task list items in the format:
    - [ ] Incomplete task
    - [x] Completed task
    - ✅ Completed task
    - 🏃 In-progress task
    - [SKIP] Skipped task (not counted)

    Returns:
        SubtaskCount with completed and total counts
    """
    completed = len(re.findall(r"- (\[x\]|✅)", content))
    total = len(re.findall(r"- (\[ \]|🏃)", content)) + completed
    return SubtaskCount(completed, total)


def validate_task_file(file: Path, post: frontmatter.Post) -> List[str]:
    """Validate a task file's format and required fields.

    Args:
        file: Path to the task file
        post: Loaded frontmatter post

    Returns:
        List of validation issues
    """
    issues = []
    metadata = post.metadata

    # Check required fields
    required_fields: Dict[str, type | tuple[type, ...]] = {
        "state": str,
        "created": (str, datetime),  # Can be string or datetime
    }

    for field, expected_type in required_fields.items():
        if field not in metadata:
            issues.append(f"Missing required field: {field}")
        elif isinstance(expected_type, tuple):
            if not isinstance(metadata[field], expected_type):
                type_names = " or ".join(t.__name__ for t in expected_type)
                issues.append(f"Field {field} must be {type_names}")
        elif not isinstance(metadata[field], expected_type):
            issues.append(f"Field {field} must be {expected_type.__name__}")

    # Validate state value
    if "state" in metadata:
        state = metadata["state"]
        if state not in CONFIGS["tasks"].states:
            issues.append(f"Invalid state: {state}")

    # Validate created date format if string
    if "created" in metadata and isinstance(metadata["created"], str):
        try:
            datetime.fromisoformat(metadata["created"])
        except ValueError:
            issues.append(
                "Created date must be ISO format (YYYY-MM-DD[THH:MM:SS+HH:MM])"
            )

    # Optional field validation
    if "priority" in metadata:
        priority = metadata["priority"]
        if priority not in ("high", "medium", "low", None):
            issues.append("Priority must be 'high', 'medium', or 'low'")

    if "tags" in metadata and not isinstance(metadata["tags"], list):
        issues.append("Tags must be a list")

    if "depends" in metadata and not isinstance(metadata["depends"], list):
        issues.append("Dependencies must be a list")

    return issues


def load_tasks(
    tasks_dir: Path, recursive: bool = False, single_file: Optional[Path] = None
) -> List[TaskInfo]:
    """Load tasks from directory or single file with metadata.

    Args:
        tasks_dir: Directory containing task files
        recursive: Whether to search subdirectories
        single_file: Optional specific file to load

    Returns:
        List of TaskInfo objects
    """
    tasks = []

    # Directories to exclude
    excluded_dirs = {"templates", "video-scripts", "agent-setup-interview"}

    # Handle single file case
    if single_file:
        if not single_file.exists():
            logging.error(f"File not found: {single_file}")
            return []
        files = [single_file]
    else:
        # Determine glob pattern based on recursive flag
        pattern = "**/*.md" if recursive else "*.md"
        files = [
            f
            for f in tasks_dir.glob(pattern)
            if not recursive or not any(d in f.parts for d in excluded_dirs)
        ]

    for file in files:
        try:
            # Read frontmatter and content
            post = frontmatter.load(file)
            metadata = post.metadata

            # Validate file format and required fields
            issues = validate_task_file(file, post)

            # Count subtasks
            subtasks = count_subtasks(post.content)

            # Get state (default to new if missing)
            state = metadata.get("state")
            if not state:
                issues.append("No state in frontmatter")
                state = "new"  # Default state

            # Parse timestamps
            try:
                created = (
                    metadata["created"]
                    if isinstance(metadata.get("created"), datetime)
                    else datetime.fromisoformat(str(metadata.get("created", "")))
                )
                modified = (
                    metadata["modified"]
                    if isinstance(metadata.get("modified"), datetime)
                    else datetime.fromisoformat(str(metadata.get("modified", "")))
                )
            except (ValueError, TypeError):
                # Fallback to git timestamps
                try:
                    # Get last commit time
                    result = subprocess.run(
                        ["git", "log", "-1", "--format=%at", "--", str(file)],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    timestamp = int(result.stdout.strip())
                    modified = datetime.fromtimestamp(timestamp)

                    # Get first commit time (creation)
                    result = subprocess.run(
                        ["git", "log", "--reverse", "--format=%at", "--", str(file)],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    timestamp = int(result.stdout.strip().split("\n")[0])
                    created = datetime.fromtimestamp(timestamp)
                except (subprocess.CalledProcessError, ValueError, IndexError):
                    # Fallback to filesystem timestamps if git fails
                    stats = file.stat()
                    created = datetime.fromtimestamp(stats.st_ctime)
                    modified = datetime.fromtimestamp(stats.st_mtime)

            # Convert to naive datetime if timezone-aware
            if created.tzinfo:
                created = created.astimezone().replace(tzinfo=None)
            if modified.tzinfo:
                modified = modified.astimezone().replace(tzinfo=None)

            # Create TaskInfo object
            task = TaskInfo(
                path=file,
                name=file.stem,
                state=state,
                created=created,
                modified=modified,
                priority=metadata.get("priority"),
                tags=metadata.get("tags", []),
                depends=metadata.get("depends", []),
                subtasks=subtasks,
                issues=issues,
                metadata=metadata,
            )
            tasks.append(task)

        except Exception as e:
            logging.error(f"Error reading {file}: {e}")

    return tasks


def find_repo_root(start_path: Path) -> Path:
    """Find the repository root by looking for .git directory."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start_path.resolve()


def format_time_ago(dt: datetime) -> str:
    """Format a datetime as a human-readable time ago string."""
    # Convert to naive datetime if timezone-aware
    if dt.tzinfo:
        dt = dt.astimezone().replace(tzinfo=None)
    now = datetime.now()
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    elif delta < timedelta(days=30):
        days = delta.days
        return f"{days}d ago"
    else:
        return dt.strftime("%Y-%m-%d")


# State-specific styling
STATE_STYLES = {
    # Tasks
    "new": ("yellow", "new"),
    "active": ("blue", "active"),
    "paused": ("cyan", "paused"),
    "done": ("green", "done"),
    "cancelled": ("red", "cancelled"),
    # Tweets
    "queued": ("yellow", "queued"),
    "approved": ("blue", "approved"),
    "posted": ("green", "posted"),
    # Email
    "inbox": ("yellow", "inbox"),
    "drafts": ("blue", "draft"),
    "sent": ("green", "sent"),
    "archive": ("cyan", "archived"),
    # Special categories
    "issues": ("red", "!"),
    "untracked": ("dim", "?"),
}

# State emojis for consistent use
STATE_EMOJIS = {
    "new": "🆕",
    "active": "🏃",
    "paused": "⚪",
    "done": "✅",
    "cancelled": "❌",
    "issues": "⚠️",
    "untracked": "❓",
    # priorities
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}


@click.group()
@click.option("-v", "--verbose", is_flag=True)
def cli(verbose):
    """Task verification and status CLI."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)


def load_task(file: Path) -> Tuple[frontmatter.Post, SubtaskCount]:
    """Load a task file and count its subtasks."""
    post = frontmatter.load(file)
    subtasks = count_subtasks(post.content)
    return post, subtasks


@cli.command("show")
@click.argument("task_id", required=False)
def show_(task_id):
    """Show detailed information about a task.

    If task_id is not provided, it will show the first task found.
    """
    show(task_id)


def show(task_id):
    """Show detailed information about a task."""
    console = Console()
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    if not task_id:
        console.print("[red]Error: Task ID or filename required[/]")
        return

    # Load all tasks
    tasks = load_tasks(tasks_dir)
    if not tasks:
        console.print("[red]No tasks found[/]")
        return

    # Sort tasks by creation date for consistent ID mapping
    tasks.sort(key=lambda t: t.created)

    # Find requested task
    task = None
    if task_id.isdigit():
        # Get task by numeric ID
        idx = int(task_id) - 1
        if 0 <= idx < len(tasks):
            task = tasks[idx]
    else:
        # Get task by name
        task_name = task_id[:-3] if task_id.endswith(".md") else task_id
        matching = [t for t in tasks if t.name == task_name]
        if matching:
            task = matching[0]

    if not task:
        console.print(f"[red]Error: Task {task_id} not found[/]")
        return

    # Create rich table for metadata
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    # Add metadata rows
    table.add_row("File", str(task.path.relative_to(repo_root)))
    table.add_row("State", task.state or "unknown")
    table.add_row("Created", task.created_ago)
    table.add_row("Modified", task.modified_ago)
    if task.priority:
        table.add_row("Priority", STATE_EMOJIS.get(task.priority) or task.priority)
    if task.tags:
        table.add_row("Tags", ", ".join(task.tags))
    if task.depends:
        table.add_row("Dependencies", ", ".join(task.depends))
    if task.subtasks.total > 0:
        table.add_row(
            "Subtasks", f"{task.subtasks.completed}/{task.subtasks.total} completed"
        )
    if task.issues:
        table.add_row("Issues", ", ".join(task.issues))

    # Print metadata table
    console.print("\n[bold]Task Metadata:[/]")
    console.print(table)

    # Print content
    console.print("\n[bold]Content:[/]")
    post = frontmatter.load(task.path)  # Reload to get content
    console.out(post.content, highlight=True)


@cli.command("list")
@click.option(
    "--sort",
    type=click.Choice(["state", "date", "name", "completion"]),
    default="date",
    help="Sort by state, creation date, name, or completion percentage",
)
@click.option(
    "--active-only",
    is_flag=True,
    help="Only show new and active tasks",
)
def list_(sort, active_only):
    """List all tasks in a table format."""
    console = Console()
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    # Load all tasks
    all_tasks = load_tasks(tasks_dir)
    if not all_tasks:
        console.print("[red]No tasks found[/]")
        return

    # Create stable enumerated ID mapping based on creation date for ALL tasks
    tasks_by_date = sorted(all_tasks, key=lambda t: t.created)
    name_to_enum_id = {task.name: i for i, task in enumerate(tasks_by_date, 1)}
    # Keep a mapping of all task names for dependency resolution
    all_tasks_dict = {task.name: task for task in all_tasks}

    # Filter tasks if active-only flag is set
    tasks = all_tasks
    if active_only:
        tasks = [task for task in all_tasks if task.state in ["new", "active"]]
        if not tasks:
            console.print("[yellow]No new or active tasks found[/]")
            return
        console.print("[blue]Showing only new and active tasks[/]\n")

    # Sort tasks for display based on option
    if sort == "state":
        tasks.sort(key=lambda t: (t.state or "", t.created))
    elif sort == "name":
        tasks.sort(key=lambda t: t.name)
    elif sort == "completion":
        # Calculate completion percentage, grouping tasks with no subtasks at the bottom
        def completion_key(t):
            if t.subtasks.total == 0:
                return (0, t.created)  # Group at bottom, sort by date within group
            completion_pct = t.subtasks.completed / t.subtasks.total
            return (
                1,
                completion_pct,
                t.created,
            )  # Sort by completion %, newest first within same %

        # Sort in reverse order to get:
        # 1. Tasks with subtasks first (1 > 0)
        # 2. Higher completion percentages first
        # 3. Newer tasks first within same percentage
        tasks.sort(key=completion_key, reverse=True)
    else:  # default: date
        tasks.sort(key=lambda t: t.created)

    # Create display rows
    display_rows = []
    for task in tasks:
        # Get stable enumerated ID for task
        enum_id = name_to_enum_id[task.name]

        # Calculate completion info
        if task.subtasks.total > 0:
            completion_pct = (task.subtasks.completed / task.subtasks.total) * 100
            completion_str = f"{completion_pct:>3.0f}%"
            name_with_count = f"{task.name} {task.subtasks}"
        else:
            completion_str = "  -"
            name_with_count = task.name

        # Format dependencies with enumerated IDs or task info
        if task.depends:
            dep_ids = []
            for dep in task.depends:
                if dep in all_tasks_dict:
                    dep_task = all_tasks_dict[dep]
                    # If dependency is in filtered list, show its ID
                    if not active_only or dep_task.state in ["new", "active"]:
                        dep_ids.append(str(name_to_enum_id[dep]))
                    else:
                        # Show task name and state for filtered out dependencies
                        state_emoji = STATE_EMOJIS.get(
                            dep_task.state or "untracked", "•"
                        )
                        dep_ids.append(f"{dep} ({state_emoji})")
                else:
                    dep_ids.append(f"{dep} (missing)")
            deps_str = ", ".join(dep_ids)
        else:
            deps_str = ""

        # Add row with state emoji
        state_emoji = STATE_EMOJIS.get(task.state or "untracked", "•")
        display_rows.append(
            [
                state_emoji,
                f"{enum_id}. {name_with_count}",
                task.created_ago,
                STATE_EMOJIS.get(task.priority or "") or task.priority or "",
                completion_str,
                deps_str,
            ]
        )

    # Print table
    headers = ["", "Task", "Created", "Priority", "Complete", "Deps"]
    # Only show dependencies column if any task has dependencies
    has_deps = any(task.depends for task in tasks)
    if not has_deps:
        display_rows = [row[:-1] for row in display_rows]
        headers = headers[:-1]

    # Set column alignments and widths
    colaligns = ["left", "left", "left", "center"]
    colwidths = [2, None, None, None]
    if has_deps:
        colaligns.append("left")
        colwidths.append(20)

    console.print(
        "\n"
        + tabulate(
            display_rows,
            headers=headers,
            tablefmt="simple",
            maxcolwidths=colwidths,
            colalign=colaligns,
        )
    )

    # Print legend for tasks with dependencies
    if has_deps:
        tasks_with_deps = [
            (task, name_to_enum_id[task.name]) for task in tasks if task.depends
        ]
        if tasks_with_deps:
            console.print("\nDependencies:")
            for task, enum_id in tasks_with_deps:
                dep_strs = []
                for dep in task.depends:
                    if dep in all_tasks_dict:
                        dep_task = all_tasks_dict[dep]
                        # If dependency is in filtered list, show its ID
                        if not active_only or dep_task.state in ["new", "active"]:
                            dep_strs.append(f"{dep} ({name_to_enum_id[dep]})")
                        else:
                            # Show task name and state for filtered out dependencies
                            state_emoji = STATE_EMOJIS.get(
                                dep_task.state or "untracked", "•"
                            )
                            dep_strs.append(f"{dep} ({state_emoji})")
                    else:
                        dep_strs.append(f"{dep} (missing)")
                dep_str = ", ".join(dep_strs)
                console.print(f"  {task.name} ({enum_id}) -> {dep_str}")

    # Print summary
    state_counts: Dict[str, int] = {}
    for task in tasks:
        emoji = STATE_EMOJIS.get(task.state or "untracked", "•")
        state_counts[emoji] = state_counts.get(emoji, 0) + 1

    summary = [f"{count} {state}" for state, count in state_counts.items()]
    console.print(f"\nTotal: {len(tasks)} tasks ({', '.join(summary)})")


class StateChecker:
    """Check state directories for issues and status."""

    def __init__(self, repo_root: Path, config: DirectoryConfig):
        self.root = repo_root
        self.config = config
        self.base_dir = repo_root / config.type_name

    def check_all(self) -> Dict[str, List[TaskInfo]]:
        """Check all files and categorize by state."""
        results: Dict[str, List[TaskInfo]] = {
            "untracked": [],  # Files with no state
            "issues": [],  # Files with problems
        }
        # Initialize state lists
        for state in self.config.states:
            results[state] = []

        # Load all tasks from base directory
        tasks = load_tasks(self.base_dir)

        # Categorize tasks based on state and issues
        for task in tasks:
            # Skip special files
            if task.path.name in self.config.special_files:
                continue

            # Categorize based on status
            if task.issues:
                results["issues"].append(task)
            elif not task.state:
                results["untracked"].append(task)
            else:
                results[task.state].append(task)

        return results


def print_status_section(
    console: Console, title: str, items: List[TaskInfo], show_state: bool = False
):
    """Print a section of the status output."""
    if not items:
        return

    # Sort items by creation date (newest first)
    items = sorted(items, key=lambda x: x.created, reverse=True)

    # Get style for this section
    state_name = title.split()[-1].lower()
    style, emoji = STATE_STYLES.get(state_name, ("white", "•"))

    # Limit new tasks to 5, show count of remaining
    if state_name == "new":
        if len(items) > 5:
            display_items = items[:5]
            remaining = len(items) - 5
        else:
            display_items = items
            remaining = 0
    else:
        display_items = items
        remaining = 0

    # Print header with count and emoji
    emoji = STATE_EMOJIS.get(state_name, "•")
    console.print(f"\n{emoji} {title.upper()} ({len(items)}):")

    # Print items
    for task in display_items:
        # Format display string
        subtask_str = f" {task.subtasks}" if task.subtasks.total > 0 else ""
        priority_str = f" [{task.priority}]" if task.priority else ""

        # Get state info if needed
        state_info = ""
        if show_state:
            # Use "untracked" for None state, with fallback to default style
            state = task.state or "untracked"
            _, state_text = STATE_STYLES.get(state, ("white", "•"))
            state_info = f", {state_text}"

        # Print task info
        console.print(
            f"  {task.name}{subtask_str}{priority_str} ({task.created_ago}{state_info})"
        )

        # Show issues inline
        if task.issues:
            console.print(f"    ! {', '.join(task.issues)}")

    # Show remaining count for new tasks
    if remaining > 0:
        console.print(f"  ... and {remaining} more")


def print_summary(
    console: Console, results: Dict[str, List[TaskInfo]], config: DirectoryConfig
):
    """Print summary statistics."""
    total = 0
    state_counts: Dict[str, int] = {}

    # Count tasks by state
    for state, items in results.items():
        count = len(items)
        if count > 0:
            total += count
            state_counts[state] = count

    # Build summary strings
    summary_parts = []

    # Add regular states first
    for state in config.states:
        if count := state_counts.get(state, 0):
            style, state_text = STATE_STYLES.get(state, ("white", state))
            emoji = STATE_EMOJIS.get(state, "•")
            summary_parts.append(f"{count} {emoji}")

    # Add special categories
    if count := state_counts.get("untracked", 0):
        summary_parts.append(f"{count} ❓")
    if count := state_counts.get("issues", 0):
        summary_parts.append(f"{count} ⚠️")

    # Print compact summary
    if summary_parts:
        console.print(
            f"\n{config.emoji} Summary: {total} total ({', '.join(summary_parts)})"
        )


def check_directory(
    console: Console, dir_type: str, repo_root: Path, compact: bool = False
) -> Dict[str, List[TaskInfo]]:
    """Check and display status for a single directory type."""
    config = CONFIGS[dir_type]
    checker = StateChecker(repo_root, config)
    results = checker.check_all()

    # Print header with type-specific color
    style, _ = STATE_STYLES.get(config.states[0], ("white", "•"))
    console.print(
        f"\n[bold {style}]{config.emoji} {config.type_name.title()} Status[/]\n"
    )

    # Print sections in order
    if results["issues"]:
        print_status_section(
            console,
            "Issues Found",
            results["issues"],
            show_state=True,
        )

    if results["untracked"]:
        print_status_section(
            console,
            "Untracked Files",
            results["untracked"],
        )

    # Determine which states to show based on compact mode
    states_to_show = ["new", "active"] if compact else config.states

    # Print active states in order
    for state in states_to_show:
        if state in config.states and results.get(state):
            print_status_section(
                console,
                state,
                results[state],
            )

    # Print summary
    print_summary(console, results, config)

    return results


def print_total_summary(
    console: Console, all_results: Dict[str, Dict[str, List[TaskInfo]]]
):
    """Print summary of all directory types."""
    table = Table(title="\n📊 Total Summary", show_header=False, title_style="bold")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Details", justify="left")

    total_items = 0
    total_issues = 0

    # Process each directory type
    for dir_type, results in all_results.items():
        config = CONFIGS[dir_type]

        # Calculate totals
        type_total = sum(len(items) for items in results.values())
        type_issues = len(results.get("issues", []))
        total_items += type_total
        total_issues += type_issues

        if type_total == 0:
            continue

        # Build state summary
        state_summary = []
        for state in config.states:
            if count := len(results.get(state, [])):
                emoji = STATE_EMOJIS.get(state, "•")
                state_summary.append(f"{count} {emoji}")

        # Add special categories
        if count := len(results.get("untracked", [])):
            state_summary.append(f"{count} ❓")
        if type_issues:
            state_summary.append(f"{type_issues} ⚠️")

        # Add row to table
        table.add_row(
            config.emoji + " " + config.type_name,
            str(type_total),
            " ".join(state_summary),
        )

    # Add separator and total row
    if total_items > 0:
        table.add_row("", "", "")  # Empty row as separator
        table.add_row(
            "[bold]Total[/]",
            str(total_items),
            f"[yellow]{total_issues} issues[/]" if total_issues else "",
        )

        console.print(table)


@cli.command()
@click.option("--type", type=click.Choice(list(CONFIGS.keys())), default="tasks")
@click.option("--all", is_flag=True, help="Check all directory types")
@click.option("--compact", is_flag=True, help="Only show new and active tasks")
@click.option("--summary", is_flag=True, help="Only show summary")
@click.option("--issues", is_flag=True, help="Only show items with issues")
def status(type, all, compact, summary, issues):
    """Show status of tasks and other tracked items."""
    console = Console()
    repo_root = find_repo_root(Path.cwd())

    # Collect results from all directories
    all_results = {}

    if all:
        # Check all directory types
        for type_name in CONFIGS.keys():
            results = check_directory(console, type_name, repo_root, compact)
            if results:  # Only include directories with items
                all_results[type_name] = results

            # Add separator between types if not last
            if type_name != list(CONFIGS.keys())[-1]:
                console.print("\n" + "─" * 50)

        # Print total summary at the end
        if len(all_results) > 1:
            console.print("\n" + "─" * 50)
            print_total_summary(console, all_results)

    else:
        # Check single directory type
        results = check_directory(console, type, repo_root, compact)
        if results:
            all_results[type] = results

    # Additional filtering based on options
    if issues:
        # Show only items with issues across all types
        has_issues = False
        for dir_type, results in all_results.items():
            if issue_items := results.get("issues", []):
                has_issues = True
                config = CONFIGS[dir_type]
                console.print(f"\n{config.emoji} {dir_type.title()} Issues:")
                for item in issue_items:
                    console.print(f"  • {item.name}: {', '.join(item.issues)}")

        if not has_issues:
            console.print("\n[green]No issues found![/]")

    elif summary:
        # Show only the summary for each type
        for dir_type, results in all_results.items():
            config = CONFIGS[dir_type]
            print_summary(console, results, config)


@cli.command()
@click.option("--fix", is_flag=True, help="Try to fix simple issues")
@click.argument("task_files", nargs=-1, type=click.Path())
def check(fix: bool, task_files: list[str]):
    """Check task integrity and relationships.

    If task files are provided, only check those files.
    Otherwise, check all tasks in the tasks directory.
    """
    console = Console()

    # Find repo root and tasks directory
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    # Load specified tasks or all tasks
    tasks = []
    if task_files:
        for file in task_files:
            path = Path(file)
            if not path.absolute().stem != tasks_dir:
                path = tasks_dir / path
            try:
                file_tasks = load_tasks(path.parent, single_file=path)
                if file_tasks:
                    tasks.extend(file_tasks)
                else:
                    console.print(f"[yellow]Warning: No valid task found in {file}[/]")
            except Exception as e:
                console.print(f"[red]Error reading {file}: {e}[/]")
    else:
        # Load all tasks
        tasks = load_tasks(tasks_dir)
    if not tasks:
        console.print("[yellow]No tasks found![/]")
        return

    # Track task IDs and dependencies
    task_ids = {task.id for task in tasks}
    tasks_with_deps = [task for task in tasks if task.depends]

    def has_cycle(task_id: str, visited: Set[str], path: Set[str]) -> bool:
        """Check for circular dependencies."""
        if task_id in path:
            return True
        if task_id in visited:
            return False
        visited.add(task_id)
        path.add(task_id)
        # Find task object to get its dependencies
        task = next((t for t in tasks if t.id == task_id), None)
        if task:
            for dep in task.depends:
                if has_cycle(dep, visited, path):
                    return True
        path.remove(task_id)
        return False

    # Group issues by type
    validation_issues: list[str] = []
    dependency_issues: list[str] = []
    cycle_issues: list[str] = []

    # Collect validation issues from tasks
    for task in tasks:
        if task.issues:
            validation_issues.extend(f"{task.id}: {issue}" for issue in task.issues)

    # Check for missing dependencies
    for task in tasks_with_deps:
        for dep in task.depends:
            if dep not in task_ids:
                dependency_issues.append(f"{task.id}: Dependency '{dep}' not found")

    # Check for circular dependencies
    for task in tasks_with_deps:
        if has_cycle(task.id, set(), set()):
            cycle_issues.append(
                f"Circular dependency detected involving task {task.id}"
            )

    # TODO: Implement link checking
    # for task in tasks:
    #     check_links(task)

    # Report results by category
    has_issues = False

    if validation_issues:
        has_issues = True
        console.print("\n[bold red]Validation Issues:[/]")
        for issue in validation_issues:
            console.print(f"  • {issue}")

    if dependency_issues:
        has_issues = True
        console.print("\n[bold red]Dependency Issues:[/]")
        for issue in dependency_issues:
            console.print(f"  • {issue}")

    if cycle_issues:
        has_issues = True
        console.print("\n[bold red]Circular Dependencies:[/]")
        for issue in cycle_issues:
            console.print(f"  • {issue}")

    if has_issues:
        if fix:
            console.print("\n[yellow]Auto-fix not implemented yet[/]")
            console.print("Suggested fixes:")
            console.print("  • Add missing frontmatter fields")
            console.print("  • Fix invalid state values")
            console.print("  • Update or remove invalid dependencies")
            console.print("  • Break circular dependencies")
        sys.exit(1)
    else:
        total = len(tasks)
        with_subtasks = sum(1 for t in tasks if t.subtasks.total > 0)
        console.print(
            f"\n[bold green]✓ All {total} tasks verified successfully! "
            f"({with_subtasks} with subtasks)[/]"
        )


# Add priority ranking to the top of the file, after imports
PRIORITY_RANK: dict[str | None, int] = {
    "high": 3,
    "medium": 2,
    "low": 1,
    None: 0,  # Tasks without priority
}


def resolve_tasks(
    task_ids: List[str], tasks: List[TaskInfo], tasks_dir: Path
) -> List[TaskInfo]:
    """Resolve tasks by ID/path, supporting both task names and paths.

    Args:
        task_ids: List of task identifiers (names or paths)
        tasks: List of all tasks
        tasks_dir: Path to tasks directory

    Returns:
        List of matched tasks
    """
    matched_tasks = []
    for task_id in task_ids:
        # Handle both task names and paths
        task_path = Path(task_id)
        if task_path.suffix == ".md":
            # Compute repo root from tasks dir
            repo_root = tasks_dir.parent
            # Try different path resolutions
            paths_to_try = [
                task_path,  # As-is
                tasks_dir / task_path,  # Relative to tasks dir
                tasks_dir / task_path.name,  # Just the filename
                repo_root / task_path,  # Relative to repo root
            ]
            # Try to find task by any of the paths
            task = None
            for path in paths_to_try:
                task = next((t for t in tasks if t.path == path.resolve()), None)
                if task:
                    break
        else:
            # Find task by name
            task = next((t for t in tasks if t.name == task_id), None)

        if not task:
            raise ValueError(f"Task not found: {task_id}")
        matched_tasks.append(task)

    return matched_tasks


@cli.command("edit")
@click.argument("task_ids", nargs=-1, required=True)
@click.option(
    "--set",
    "set_fields",
    type=(str, str),
    multiple=True,
    help="Set a field value (state, priority)",
)
@click.option(
    "--add",
    "add_fields",
    type=(str, str),
    multiple=True,
    help="Add value to a list field (depends, tags)",
)
@click.option(
    "--remove",
    "remove_fields",
    type=(str, str),
    multiple=True,
    help="Remove value from a list field (depends, tags)",
)
def edit(task_ids, set_fields, add_fields, remove_fields):
    """Edit task metadata.

    Examples:
        tasks edit task-123 --set state active
        tasks edit task-123 --set priority high
        tasks edit task-123 --add depends other-task
        tasks edit task-123 --add tag feature
        tasks edit task-123 --remove tag wip
        tasks edit task-123 --set state active --add tag feature --add depends other-task
    """
    console = Console()
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    # Load all tasks
    tasks = load_tasks(tasks_dir)
    if not tasks:
        console.print("[red]No tasks found[/]")
        return

    # Find tasks to edit
    try:
        target_tasks = resolve_tasks(task_ids, tasks, tasks_dir)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        return

    # Validate all field operations before applying any changes
    changes = []

    # Validate set operations
    for field, value in set_fields:
        if field not in ("state", "priority"):
            console.print(
                f"[red]Cannot set field: {field}. Use --set with state or priority.[/]"
            )
            return

        if field == "state":
            if value not in CONFIGS["tasks"].states:
                console.print(f"[red]Invalid state: {value}[/]")
                return
        elif field == "priority":
            if value not in ("high", "medium", "low", "none"):
                console.print(f"[red]Invalid priority: {value}[/]")
                return

        changes.append(("set", field, value))

    # Validate add/remove operations
    for op, fields in [("add", add_fields), ("remove", remove_fields)]:
        for field, value in fields:
            if field not in ("deps", "tags", "tag", "dep"):
                console.print(
                    f"[red]Cannot {op} to field: {field}. Use --{op} with deps/tags.[/]"
                )
                return

            # Normalize field names (tag -> tags, dep -> depends, deps -> depends)
            field_map = {"tag": "tags", "dep": "depends", "deps": "depends"}
            field = field_map.get(field, field)
            changes.append((op, field, value))

    if not changes:
        console.print("[red]No changes specified. Use --set, --add, or --remove.[/]")
        return

    # Show changes to be made
    console.print("\nChanges to apply:")
    for task in target_tasks:
        task_changes = []

        # Group changes by field for cleaner display
        field_changes: dict[str, list[tuple[str, str]]] = {}
        for op, field, value in changes:
            if field not in field_changes:
                field_changes[field] = []
            field_changes[field].append((op, value))

        # Show changes for each field
        for field, field_ops in field_changes.items():
            if field in ("deps", "tags"):
                current = task.metadata.get(field, [])
                new = current.copy()

                # Apply all operations for this field
                for op, value in field_ops:
                    if op == "add":
                        new = list(set(new + [value]))
                    else:  # remove
                        new = [x for x in new if x != value]

                if new != current:
                    task_changes.append(
                        f"{field}: {', '.join(current)} -> {', '.join(new)}"
                    )
            else:
                # For set operations, only show the final value
                set_ops = [v for op, v in field_ops if op == "set"]
                if set_ops:
                    current = task.metadata.get(field)
                    new = set_ops[-1]  # Use the last set value
                    if new != current:
                        task_changes.append(f"{field}: {current} -> {new}")

        if task_changes:
            console.print(f"  {task.name}:")
            for change in task_changes:
                console.print(f"    {change}")

    # Apply changes
    for task in target_tasks:
        post = frontmatter.load(task.path)

        # Apply all changes
        for op, field, value in changes:
            if field in ("deps", "tags"):
                current = post.metadata.get(field, [])
                if op == "add":
                    post.metadata[field] = list(set(current + [value]))
                else:  # remove
                    post.metadata[field] = [x for x in current if x != value]
            else:  # set operation
                if value == "none":
                    post.metadata.pop(field, None)
                else:
                    post.metadata[field] = value

        # Save changes
        with open(task.path, "w") as f:
            f.write(frontmatter.dumps(post))

    # Show success message
    count = len(target_tasks)
    console.print(f"[green]✓ Updated {count} task{'s' if count > 1 else ''}[/]")


@cli.command("tags")
@click.option("--state", help="Filter by task state")
@click.option("--list", "show_tasks", is_flag=True, help="List tasks for each tag")
@click.argument("filter_tags", nargs=-1)
def tags(state: Optional[str], show_tasks: bool, filter_tags: tuple[str, ...]):
    """List all tags and their task counts.

    Examples:
        tasks tags                    # Show all tags and counts
        tasks tags --list            # Show tags with task lists
        tasks tags --state active    # Only count active tasks
        tasks tags automation ai     # Show specific tags
    """
    console = Console()
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    # Load all tasks
    tasks = load_tasks(tasks_dir)
    if not tasks:
        console.print("[yellow]No tasks found![/]")
        return

    # Filter by state if specified
    if state:
        if state not in CONFIGS["tasks"].states:
            console.print(f"[red]Invalid state: {state}[/]")
            return
        tasks = [t for t in tasks if t.state == state]
        if not tasks:
            console.print(f"[yellow]No tasks with state '{state}'[/]")
            return
        console.print(f"[blue]Showing tags for {state} tasks[/]\n")

    # Collect tags and count tasks
    tag_tasks: Dict[str, List[TaskInfo]] = {}
    for task in tasks:
        for tag in task.tags:
            if tag not in tag_tasks:
                tag_tasks[tag] = []
            tag_tasks[tag].append(task)

    if not tag_tasks:
        console.print("[yellow]No tags found![/]")
        return

    # Filter tags if specified
    if filter_tags:
        filtered_tags = {}
        for tag in filter_tags:
            if tag in tag_tasks:
                filtered_tags[tag] = tag_tasks[tag]
            else:
                console.print(f"[yellow]Warning: Tag '{tag}' not found[/]")
        tag_tasks = filtered_tags
        if not tag_tasks:
            console.print("[yellow]No matching tags found![/]")
            return

    # Sort tags by frequency (most used first)
    sorted_tags = sorted(tag_tasks.items(), key=lambda x: (-len(x[1]), x[0]))

    # Print header
    console.print("\n🏷️  Task Tags")

    # Create rows for tabulate
    rows = []
    for tag, tag_task_list in sorted_tags:
        count = len(tag_task_list)
        # Always show tasks if specific tags were requested
        if show_tasks or filter_tags:
            # Sort tasks by state and name
            tag_task_list.sort(key=lambda t: (t.state or "", t.name))
            # Format task list with state emojis
            task_list = []
            for task in tag_task_list:
                emoji = STATE_EMOJIS.get(task.state or "untracked", "•")
                task_list.append(f"{emoji} {task.name}")
            tasks_str = "\n".join(task_list)
            rows.append([tag, str(count), tasks_str])
        else:
            rows.append([tag, str(count)])

    # Print table using tabulate with simple format
    headers = (
        ["Tag", "Count", "Tasks"] if (show_tasks or filter_tags) else ["Tag", "Count"]
    )
    console.print(tabulate(rows, headers=headers, tablefmt="plain"))

    # Print summary
    total_tags = len(sorted_tags)
    total_tasks = len(tasks)
    tagged_tasks = len(set(task.name for tasks in tag_tasks.values() for task in tasks))
    console.print(
        f"\nFound {total_tags} tags across {tagged_tasks} tasks "
        f"({total_tasks - tagged_tasks} untagged)"
    )


@cli.command("next")
def next_():
    """Show the highest priority active task."""
    console = Console()
    repo_root = find_repo_root(Path.cwd())
    tasks_dir = repo_root / "tasks"

    # Load all tasks
    tasks = load_tasks(tasks_dir)
    if not tasks:
        console.print("[yellow]No tasks found![/]")
        return

    # Filter for active tasks
    active_tasks = [task for task in tasks if task.state == "active"]
    if not active_tasks:
        console.print("[yellow]No active tasks found![/]")
        return

    # Sort tasks by priority (high to low) and then by creation date (oldest first)
    active_tasks.sort(
        key=lambda t: (
            -PRIORITY_RANK.get(t.priority or "", 0),
            t.created,
        )
    )

    # Get the highest priority task
    next_task = active_tasks[0]

    # Show task using same format as show command
    console.print(
        f"\n[bold blue]🏃 Next Task:[/] (Priority: {next_task.priority or 'none'})"
    )
    # Call show command directly instead of using callback
    show(next_task.name)


if __name__ == "__main__":
    cli()
