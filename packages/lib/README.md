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

These are implemented in agent-specific repositories (e.g., Bob's workspace).

## See Also

- Task Scheduler: `packages/tasks_loop/` - Scheduled autonomous execution
- Work Queue: `state/queue-*.md` - Task prioritization
- Scripts: `scripts/` - Queue generation and utilities
