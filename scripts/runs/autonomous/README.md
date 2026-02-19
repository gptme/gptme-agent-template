# Autonomous Run System

This directory contains infrastructure for running your agent autonomously on a schedule.

## Overview

Autonomous runs enable your agent to work independently without human intervention:
- Scheduled execution (e.g., every 2-4 hours)
- Systematic workflow (Loose Ends → Task Selection → Execution)
- Safety guardrails and operational guidelines
- Session documentation and state management

## Backends

Two backends are supported:

| Backend | Script | Best For |
|---------|--------|----------|
| **gptme** | `autonomous-run.sh` | gptme-native agents, local models |
| **Claude Code** | `autonomous-run-cc.sh` | Claude Max subscription, Claude-native tooling |

Both backends use the same identity files (from `gptme.toml`) and follow the same CASCADE workflow.

## Quick Start

### 1. Choose Your Backend

**gptme backend**: Edit `autonomous-run.sh` and update the configuration section:

```bash
AGENT_NAME="YourAgent"
WORKSPACE="/path/to/your/workspace"
REPO_OWNER="your-github-username"
REPO_NAME="your-agent-workspace"
SCRIPT_TIMEOUT=3000
```

**Claude Code backend**: Edit `autonomous-run-cc.sh`:

```bash
AGENT_NAME="YourAgent"
# WORKSPACE auto-detects from script location
MODEL="sonnet"  # or "opus"
```

### 2. Customize the Prompt

Edit the prompt template in your chosen script to:
- Add your agent's specific goals and values
- Adjust safety guidelines for your use case
- Modify the workflow to match your needs
- Add domain-specific instructions

### 3. Test Manually

Run the script directly to verify it works:

```bash
cd /path/to/your/workspace

# gptme backend
./scripts/runs/autonomous/autonomous-run.sh

# Claude Code backend
./scripts/runs/autonomous/autonomous-run-cc.sh
```

### 4. Schedule with systemd (Linux)

Create a systemd timer to run automatically:

```bash
# Copy the example service and timer for your backend
# gptme backend:
cp ../../systemd/user/agent-autonomous.service ~/.config/systemd/user/
# Claude Code backend:
cp ../../systemd/user/agent-autonomous-cc.service ~/.config/systemd/user/

cp ../../systemd/user/agent-autonomous.timer ~/.config/systemd/user/

# Edit to match your configuration
# Update WorkingDirectory, ExecStart paths, and schedule
# For CC backend: also update the PATH to include your node installation

# Enable and start
systemctl --user daemon-reload
systemctl --user enable agent-autonomous.timer
systemctl --user start agent-autonomous.timer
```

## CASCADE Workflow

The autonomous run follows a three-step workflow:

### Step 1: Quick Loose Ends Check (2-5 min)
- Check git status for uncommitted work
- Scan for critical notifications
- Fix only immediate blockers
- Don't spend excessive time here

### Step 2: Task Selection via CASCADE (5-10 min)
1. **PRIMARY**: Read `state/queue-manual.md` "Planned Next" section
   - Manual queue contains session context and strategic notes
   - Fall back to `state/queue-generated.md` if manual queue empty
2. **SECONDARY**: Check notifications for direct assignments
3. **TERTIARY**: Check workspace tasks if PRIMARY/SECONDARY blocked
4. **COMMIT** to a specific task before completing Step 2

**Important**: All three sources must be blocked before declaring a real blocker.

### Step 3: Execution (20-30 min - THE MAIN FOCUS)
- Execute the selected task
- Make concrete, verifiable progress
- Commit work incrementally
- Document progress in journal

## Work Queue System

The template supports a two-queue system:

### Manual Queue (`state/queue-manual.md`)
- **PRIMARY source** for task selection
- Manually maintained with rich context
- Contains session reasoning, dependencies, strategic notes
- Format:
  ```markdown
  ## Current Run
  Session XXX: Brief status

  ## Planned Next
  1. Task name (priority, status, next action)
  2. Task name (priority, status, next action)
  3. Task name (priority, status, next action)
  ```

### Generated Queue (`state/queue-generated.md`)
- **FALLBACK source** when manual queue empty
- Auto-generated from task files and GitHub issues
- Refreshed before each autonomous run
- Provides objective, fresh priorities

## Safety Guidelines

The script includes safety classifications for operations:
- **GREEN**: Code, tests, docs, refactoring → Execute autonomously
- **YELLOW**: Social media, email → Follow established patterns
- **RED**: Financial, major decisions → Escalate to human

Customize these classifications for your use case.

## Session Completion

Each autonomous run should:
1. Return to workspace directory
2. Update work queue with session status
3. Commit journal entry and queue updates
4. Use `complete` tool to signal completion

Keep documentation brief (2-5 minutes max).

## Monitoring

View logs with systemd:
```bash
# Check timer status
systemctl --user status agent-autonomous.timer

# View recent logs
journalctl --user -u agent-autonomous.service --since "1 hour ago"

# Follow live logs
journalctl --user -u agent-autonomous.service -f
```

## Customization Tips

### Adjust Schedule
Edit the timer's `OnCalendar` setting:
- `*:0/15` = Every 15 minutes
- `*-*-* 06,10,14:00:00` = 6am, 10am, 2pm daily
- `Mon-Fri *-*-* 08:00:00` = 8am on weekdays

### Modify Timeout
Adjust `SCRIPT_TIMEOUT` in the script based on your schedule:
- Hourly runs: 3000 seconds (50 minutes)
- Every 2 hours: 6000 seconds (100 minutes)

### Add Pre-Run Checks
Add validation scripts before `gptme` execution:
```bash
# Run checks
if "$SCRIPT_DIR/validate-workspace.sh"; then
    log "✅ Workspace validation passed"
else
    log "❌ Workspace validation failed"
    exit 1
fi
```

## Troubleshooting

### Script Exits Immediately
- Check that `WORKSPACE` path exists
- Verify `gptme` is installed and in PATH
- Review logs for error messages

### Git Pull Fails
- Ensure SSH keys are configured
- Check network connectivity
- Verify remote repository access

### Timeout Issues
- Increase `SCRIPT_TIMEOUT` if runs consistently timeout
- Review task complexity (may need simpler tasks)
- Check for infinite loops or hanging operations

### Multiple Runs Conflicting
- The CC script includes built-in lock management
- For the gptme script, implement a lock mechanism or use systemd's `After=` directive

### Claude Code Binary Not Found (CC backend)
- Ensure node/npm is installed (Claude Code is a Node binary)
- The systemd service needs the node PATH explicitly set
- Find your path: `dirname $(which node)`
- Update `Environment="PATH=..."` in the service file

### Profile Sourcing Fails (CC backend)
- Version managers (nvm, pyenv) may return non-zero in non-interactive shells
- The CC script uses `source ~/.profile 2>/dev/null || true` to handle this
- If authentication fails, run `claude /login` interactively first

### Process Gets SIGSTOP in tmux/systemd
- Claude Code requires `</dev/null` stdin redirect in non-interactive contexts
- The CC script handles this automatically

## Examples

See production autonomous agent implementations on GitHub for advanced patterns:
- Lock management and coordination
- Monitoring and failure recovery
- Complex prompt templates
