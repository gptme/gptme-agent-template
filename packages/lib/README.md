# Input Orchestrator Library

Coordinates polling of external input sources (GitHub, Email, Webhooks, Scheduler) for autonomous agent operation.

## Overview

The input orchestrator enables agents to respond to external events by:
- Polling multiple input sources at configured intervals
- Tracking processed items to avoid duplicate work
- Creating prioritized work items from external sources
- Coordinating with the task scheduler for autonomous execution

## Architecture

```txt
┌─────────────────────────────────────────────┐
│         Input Source Orchestrator           │
│  (Polls sources, tracks state, processes)   │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬────────────┐
        │           │           │            │
   ┌────▼───┐  ┌───▼────┐  ┌───▼────┐  ┌────▼─────┐
   │ GitHub │  │ Email  │  │Webhook │  │Scheduler │
   │ Source │  │ Source │  │ Source │  │  Source  │
   └────────┘  └────────┘  └────────┘  └──────────┘
```

## Components

### `orchestrator.py`
Main coordination logic:
- Manages multiple input sources
- Polls at configured intervals
- Processes items by priority
- Tracks state across sessions

### `input_sources.py`
Base classes and interfaces:
- `InputSource`: Abstract base for all sources
- `InputItem`: Standardized work item representation
- Common polling interface

### `state.py`
Persistent state tracking:
- Tracks which items have been processed
- Prevents duplicate work
- JSON-based persistence

## Usage

### Basic Setup

```python
from lib.orchestrator import InputSourceOrchestrator
from lib.input_sources import InputSource
from pathlib import Path

# Create custom input source
class CustomSource(InputSource):
    async def poll(self):
        # Return list of InputItem objects
        pass

    async def acknowledge(self, item_id):
        # Mark item as handled
        pass

# Initialize orchestrator
orchestrator = InputSourceOrchestrator(
    sources={"custom": CustomSource({})},
    state_file=Path("state.json"),
    poll_intervals={"custom": 300},  # 5 minutes
)

# Run continuously
import asyncio
asyncio.run(orchestrator.run())
```

### Custom Input Sources

Implement the `InputSource` abstract base class:

```python
from lib.input_sources import InputSource, InputItem

class MySource(InputSource):
    async def poll(self):
        # Query external system
        external_items = await fetch_items()

        # Convert to InputItem format
        return [
            InputItem(
                source="mysource",
                item_id=item.id,
                priority="high",
                title=item.title,
                description=item.description,
            )
            for item in external_items
        ]

    async def acknowledge(self, item_id):
        # Optional: notify external system
        pass
```

## Configuration

### Poll Intervals

Configure how often each source is polled:

```python
poll_intervals = {
    "github": 300,      # 5 minutes
    "email": 600,       # 10 minutes
    "webhook": 60,      # 1 minute
    "scheduler": 60,    # 1 minute
}
```

### Priority Levels

Items support four priority levels:
- `urgent`: Critical issues requiring immediate attention
- `high`: Important work to prioritize
- `medium`: Standard priority (default)
- `low`: Can be deferred

## Systemd Integration

Run as a continuous service using systemd:

```bash
# Copy service file
cp systemd/user/agent-input-orchestrator.service ~/.config/systemd/user/

# Enable and start
systemctl --user enable agent-input-orchestrator.service
systemctl --user start agent-input-orchestrator.service

# Check status
systemctl --user status agent-input-orchestrator.service

# View logs
journalctl --user -u agent-input-orchestrator.service -f
```

## State Management

The orchestrator maintains persistent state to prevent duplicate processing:

```python
from lib.state import StateTracker

tracker = StateTracker(Path("state.json"))

# Check if item was processed
if tracker.is_processed("github", "issue-123"):
    return  # Skip already handled

# Mark as processed
tracker.mark_processed("github", "issue-123")

# Get processing statistics
count = tracker.get_processed_count("github")
```

State is automatically saved to JSON after each update.

## Testing

Run tests using pytest:

```bash
pytest packages/lib/tests/
```

Tests cover:
- State persistence and loading
- Source polling and filtering
- Priority-based processing
- Duplicate detection

## Development

Install development dependencies:

```bash
pip install -e "packages/lib[dev]"
```

Run type checking:

```bash
mypy packages/lib/src
```

## Integration

The orchestrator integrates with:
- **Task Scheduler**: Triggers scheduled work
- **Work Queue**: Adds items to processing queue
- **Autonomous Runs**: Can trigger immediate execution for urgent items

## Future Enhancements

Potential additions (not in template):
- Rate limiting per source
- Webhook HTTP server
- Email integration (IMAP/SMTP)
- GitHub API client
- Metrics and monitoring
- Retry logic for failed processing

These are implemented in agent-specific repositories (e.g., production agent workspaces).

## See Also

- Task Scheduler: `packages/tasks_loop/` - Scheduled autonomous execution
- Work Queue: `state/queue-*.md` - Task prioritization
- Scripts: `scripts/` - Queue generation and utilities

## Journal Module

The `journal` module provides utilities for managing agent journal entries with support for two formats.

### Supported Formats

**Legacy (flat)**: `journal/2025-12-24-topic.md`
**New (subdirectories)**: `journal/2025-12-24/topic.md`

The module automatically detects and handles both formats, making migration seamless.

### Key Functions

```python
from lib.journal import (
    find_journal_directory,
    generate_journal_context,
    get_journals_for_date,
    get_recent_journal_date,
)

# Find journal directory in workspace
journal_dir = find_journal_directory(agent_dir)

# Get most recent journal date
recent_date = get_recent_journal_date(journal_dir)

# Get all journal files for a specific date
journals = get_journals_for_date(journal_dir, "2025-12-24")

# Generate formatted context for gptme
context = generate_journal_context(agent_dir)
```

### Migration

To migrate existing journals from flat to subdirectory format:

```bash
# Preview migration
./scripts/migrate-journals.py

# Execute migration
./scripts/migrate-journals.py --execute
```

### Benefits of Subdirectory Format

- **Better organization**: Files grouped by date
- **Reduced clutter**: Large journal directories become manageable
- **Improved performance**: Filesystem operations on date directories
- **Parallel agent support**: Multiple session files per day with unique names
