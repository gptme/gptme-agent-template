# Task Scheduler

A simple, flexible task scheduler for autonomous agents with cron-like scheduling and priority-based execution.

## Features

- **Cron-like Scheduling**: Standard cron syntax for job scheduling
- **Priority Levels**: Urgent, High, Medium, Low job priorities
- **State Management**: Track job execution state and results
- **Retry Support**: Configure automatic retries for failed jobs
- **Timeout Control**: Set execution timeouts per job or globally
- **YAML Configuration**: Simple job definitions in YAML format

## Quick Start

### 1. Installation

```bash
# Install the package
uv pip install -e packages/tasks_loop

# Or add to workspace pyproject.toml
```

### 2. Create Job Definition

Create a YAML file in `jobs/` directory:

```yaml
# jobs/example-daily.yaml
id: example-daily
name: Daily Health Check
description: Check system health every day at 2am
command: echo "Health check complete"
schedule: "0 2 * * *"  # Cron: 2am daily
priority: medium
enabled: true
max_retries: 2
timeout_seconds: 300
```

### 3. Run Scheduler

```python
from tasks_loop import TaskScheduler, SchedulerConfig

# Create scheduler with config
config = SchedulerConfig(
    jobs_dir="jobs",
    poll_interval_seconds=60,
)

scheduler = TaskScheduler(config)
scheduler.run()  # Runs as daemon
```

Or use the CLI:

```bash
python3 -m tasks_loop.scheduler
```

## Configuration

### Scheduler Configuration

Create `config/scheduler.yaml`:

```yaml
jobs_dir: jobs
poll_interval_seconds: 60
default_timeout_seconds: 300
max_concurrent_jobs: 1
log_level: INFO
log_file: logs/scheduler.log  # Optional
```

### Job Configuration

Each job is defined in a YAML file in the `jobs/` directory:

**Required Fields**:
- `id`: Unique job identifier
- `name`: Human-readable job name
- `command`: Shell command to execute
- `schedule`: Cron schedule expression

**Optional Fields**:
- `priority`: `urgent`, `high`, `medium`, `low` (default: `medium`)
- `description`: Job description
- `enabled`: Enable/disable job (default: `true`)
- `max_retries`: Number of retry attempts on failure (default: `0`)
- `timeout_seconds`: Job execution timeout (uses default if not set)

## Cron Schedule Syntax

Standard cron syntax is supported:

```text
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Examples**:
- `0 2 * * *` - Daily at 2am
- `*/15 * * * *` - Every 15 minutes
- `0 9 * * 1-5` - Weekdays at 9am
- `0 0 1 * *` - First day of month at midnight

## Priority Levels

Jobs are executed in priority order when multiple jobs are due:

1. **Urgent**: Critical tasks requiring immediate execution
2. **High**: Important tasks that should run soon
3. **Medium**: Regular scheduled tasks (default)
4. **Low**: Background tasks that can wait

## Job States

Jobs progress through these states:

- `pending`: Waiting to be scheduled
- `running`: Currently executing
- `completed`: Successfully finished
- `failed`: Execution failed

Failed jobs can retry if `max_retries > 0`.

## Systemd Integration

The scheduler can run as a systemd user service for persistent operation.

See `systemd/user/agent-scheduler.service` for the service template.

**Setup**:

```bash
# Copy service file
cp systemd/user/agent-scheduler.service ~/.config/systemd/user/

# Edit paths in service file as needed
nano ~/.config/systemd/user/agent-scheduler.service

# Enable and start
systemctl --user daemon-reload
systemctl --user enable agent-scheduler.service
systemctl --user start agent-scheduler.service

# Check status
systemctl --user status agent-scheduler.service

# View logs
journalctl --user -u agent-scheduler.service -f
```

## Example Jobs

See `jobs/` directory for example job definitions:
- `example-daily.yaml`: Daily health check
- `example-weekly.yaml`: Weekly cleanup task

## API Usage

### Basic Scheduler

```python
from tasks_loop import TaskScheduler

scheduler = TaskScheduler()
scheduler.load_jobs()  # Load from jobs/ directory
scheduler.run_once()   # Execute one scheduler cycle
```

### Custom Configuration

```python
from pathlib import Path
from tasks_loop import TaskScheduler, SchedulerConfig

config = SchedulerConfig(
    jobs_dir=Path("custom/jobs"),
    poll_interval_seconds=30,
    max_concurrent_jobs=2,
)

scheduler = TaskScheduler(config)
scheduler.run()  # Run as daemon
```

### Programmatic Job Creation

```python
from tasks_loop import Job, Priority

job = Job(
    id="custom-job",
    name="Custom Task",
    command="echo 'Hello from scheduler'",
    schedule="*/5 * * * *",  # Every 5 minutes
    priority=Priority.HIGH,
    max_retries=3,
)

scheduler = TaskScheduler()
scheduler.jobs[job.id] = job
scheduler.run_once()
```

## Testing

```bash
# Run tests
cd packages/tasks_loop
pytest

# With coverage
pytest --cov=tasks_loop --cov-report=term-missing
```

## Architecture

### Components

- **Job**: Job definition and state management
- **SchedulerConfig**: Configuration management
- **TaskScheduler**: Core scheduler daemon

### Execution Flow

1. Scheduler loads job definitions from YAML files
2. Every `poll_interval_seconds`, checks for due jobs
3. Due jobs are sorted by priority
4. Jobs execute up to `max_concurrent_jobs` limit
5. Results are logged and job state updated
6. Failed jobs retry if configured

### State Persistence

Job execution state (last run time, results) is maintained in memory during scheduler operation but not persisted to disk. Each scheduler restart starts fresh from job definitions.

## Customization

### Adding Custom Job Types

Extend the `Job` class for specialized behavior:

```python
from tasks_loop import Job

class NotificationJob(Job):
    def __init__(self, *args, notification_email: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.notification_email = notification_email
```

### Custom Execution Logic

Subclass `TaskScheduler` to customize execution:

```python
from tasks_loop import TaskScheduler, Job, JobResult

class CustomScheduler(TaskScheduler):
    def execute_job(self, job: Job) -> JobResult:
        # Add pre-execution logic
        self.send_notification(f"Starting {job.name}")

        # Execute job
        result = super().execute_job(job)

        # Add post-execution logic
        if not result.success:
            self.alert_admin(job, result)

        return result
```

## Troubleshooting

### Jobs Not Executing

1. Check job is enabled: `enabled: true`
2. Verify cron schedule syntax
3. Check scheduler logs for errors
4. Ensure job command is valid

### Permission Errors

- Ensure scheduler has execute permissions for job commands
- Check file paths are accessible
- Verify systemd service user has required permissions

### Schedule Issues

- Test cron expressions at [crontab.guru](https://crontab.guru/)
- Check system timezone matches expected schedule
- Verify `poll_interval_seconds` is appropriate for schedule frequency

## License

Part of the gptme-agent-template project.
