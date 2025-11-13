# Job Definitions

This directory contains YAML job definitions for the task scheduler.

## Job File Format

Each job is defined in a separate YAML file with the following structure:

```yaml
# Required fields
id: unique-job-id               # Unique identifier for the job
name: Job Display Name          # Human-readable name
command: echo "task output"     # Shell command to execute
schedule: "0 2 * * *"           # Cron schedule expression

# Optional fields
description: Job description    # Detailed description (optional)
priority: medium                # urgent, high, medium, low (default: medium)
enabled: true                   # Enable/disable job (default: true)
max_retries: 1                  # Number of retry attempts (default: 0)
timeout_seconds: 300            # Execution timeout in seconds (default: config default)
```

## Cron Schedule Format

Standard cron syntax is used for scheduling:

```text
┌─────────── minute (0 - 59)
│ ┌───────── hour (0 - 23)
│ │ ┌─────── day of month (1 - 31)
│ │ │ ┌───── month (1 - 12)
│ │ │ │ ┌─── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

### Common Schedule Examples

```yaml
# Every minute
schedule: "* * * * *"

# Every 5 minutes
schedule: "*/5 * * * *"

# Daily at 2:00 AM
schedule: "0 2 * * *"

# Weekdays at 9:00 AM
schedule: "0 9 * * 1-5"

# First day of month at midnight
schedule: "0 0 1 * *"

# Every Sunday at 3:00 AM
schedule: "0 3 * * 0"

# Twice daily (6 AM and 6 PM)
schedule: "0 6,18 * * *"
```

Test your cron expressions at [crontab.guru](https://crontab.guru/).

## Priority Levels

Jobs execute in priority order when multiple jobs are due:

- **urgent**: Critical tasks requiring immediate execution
- **high**: Important tasks that should run soon
- **medium**: Regular scheduled tasks (default)
- **low**: Background tasks that can wait

## Creating New Jobs

1. Create a new YAML file in this directory
2. Use a descriptive filename: `my-task-name.yaml`
3. Define the job using the format above
4. Restart the scheduler to load the new job

**Example**:

```yaml
# backup-database.yaml
id: backup-database
name: Database Backup
description: Create daily backup of application database
command: /path/to/backup-script.sh
schedule: "0 1 * * *"  # 1:00 AM daily
priority: high
enabled: true
max_retries: 2
timeout_seconds: 1800  # 30 minutes
```

## Job Execution

- Jobs run in a shell environment
- Commands can use shell features (pipes, redirects, etc.)
- stdout/stderr are captured in job results
- Failed jobs retry if `max_retries > 0`
- Long-running commands should respect `timeout_seconds`

## Testing Jobs

Test job commands manually before scheduling:

```bash
# Test the command works
echo "Health check complete - $(date)"

# Test with timeout
timeout 300 echo "test"

# Check exit code
echo $?  # 0 = success
```

## Disabling Jobs

Temporarily disable a job without deleting it:

```yaml
# Set enabled to false
enabled: false
```

Or remove the YAML file entirely to permanently delete the job.

## Best Practices

1. **Use absolute paths** in commands for reliability
2. **Set appropriate timeouts** to prevent hanging
3. **Configure retries** for flaky commands
4. **Test commands** manually before scheduling
5. **Use descriptive IDs** that indicate the job's purpose
6. **Document complex commands** in the description field
7. **Start with low priority** and increase if needed

## Examples

See the example jobs in this directory:
- `example-daily.yaml`: Daily health check
- `example-weekly.yaml`: Weekly cleanup task

Customize these examples or use them as templates for your own jobs.
