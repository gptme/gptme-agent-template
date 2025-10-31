# gptme-agent-template

[![built using gptme](https://img.shields.io/badge/built%20using-gptme%20%F0%9F%A4%96-5151f5?style=flat)](https://github.com/ErikBjare/gptme)
<!--template-->

[![Test](https://github.com/ErikBjare/gptme-agent-template/actions/workflows/test.yml/badge.svg)](https://github.com/ErikBjare/gptme-agent-template/actions/workflows/test.yml)

> [!NOTE]
> This is a template for a [gptme](https://gptme.org)-based agent. See the [agents documentation](https://gptme.org/docs/agents.html) for more information about gptme agents and how they work.
>
> [Fork it](#quick-start) to create a new agent with its own identity.

<!--/template-->

## Overview

A production-ready template for building autonomous AI agents powered by [gptme](https://gptme.org). Fork this to create your own persistent, learning agent with its own workspace, memory, and capabilities.

**What is this?** An agent workspace that serves as the "brain" of an AI agent:
- Git repository for persistent memory and version control
- Structured workspace for tasks, journal, and knowledge
- Pre-configured tools and automation
- Template you can fork to create new agents

**Who is this for?**
- Developers building autonomous AI agents
- Researchers exploring agent architectures
- Anyone wanting a personal AI assistant with persistence

## Features

- 🧠 **Persistent Memory**: Git-based workspace preserves agent context across sessions
- 📝 **Structured Organization**: Built-in task management, daily journal, knowledge base
- 🛠️ **Production-Ready**: Pre-commit hooks, tests, automation scripts
- 🔄 **Continuous Learning**: Lessons system captures patterns and prevents repeated mistakes
- 🤖 **Autonomous Operation**: Schedule automated runs, background tasks
- 👥 **People Management**: Track relationships and coordination
- 🎯 **Task System**: GTD-inspired workflow with metadata and dependencies
- 📊 **Clean Architecture**: Separation of concerns, extensible design

## Quick Start

### 1. Fork the Template

Create your own agent:

```sh
git clone https://github.com/ErikBjare/gptme-agent-template.git my-agent
cd my-agent
./fork.sh . my-agent
```

This will:
- Reset git history for a clean start
- Rename agent throughout workspace
- Create initial commit
- Preserve architecture and systems

### 2. Install Dependencies

```sh
# Install gptme
pipx install gptme

# Optional (recommended): setup pre-commit hooks
pipx install pre-commit
make install
```

### 3. Configure Your Agent

Edit these files:
- `ABOUT.md` - Define personality, goals, and background
- `gptme.toml` - Configure context files and settings
- `.env.example` → `.env.local` - Add API keys

### 4. Run Your Agent

```sh
# Interactive session
./run.sh "help me understand my workspace"

# Non-interactive (autonomous)
./run.sh -n "analyze my tasks and prioritize"
```

## Architecture

The workspace implements a proven agent architecture:

```text
my-agent/
├── ABOUT.md              # Agent personality and goals
├── ARCHITECTURE.md       # Technical architecture docs
├── TASKS.md              # Task system documentation
├── gptme.toml            # Context configuration
├── tasks/                # Task definitions (YAML frontmatter)
├── journal/              # Daily activity logs
├── knowledge/            # Long-term documentation
├── lessons/              # Meta-learning patterns
├── people/               # Relationship profiles
├── scripts/              # Automation tooling
└── projects/             # Symlinks to other repos
```

### Core Systems

**Task Management**: GTD-inspired system with:
- YAML frontmatter metadata (state, priority, dependencies)
- CLI tools for status tracking and updates
- Pre-commit validation
- Next action tracking

**Journal System**: Daily logs capturing:
- Work completed
- Decisions made
- Insights discovered
- Plans for next steps

**Knowledge Base**: Structured documentation:
- Technical designs
- Strategic analyses
- How-to guides
- Lessons learned

**Lessons System**: Meta-learning capturing:
- Behavioral patterns
- Common mistakes to avoid
- Best practices
- Tool usage constraints

**People Directory**: Relationship management:
- Individual profiles
- Interaction history
- Collaboration notes
- Action items

## Examples

Agents built with this template:

- [TimeToBuildBob](https://github.com/TimeToBuildBob) - Autonomous AI agent, 48 runs/week, active contributor to gptme
- Other experimental agents for multi-agent coordination

## Forking Guide

### Automatic Forking

The `fork.sh` script handles everything:

```sh
./fork.sh <path> [<agent-name>]

# Example: Create agent in ~/my-agent
./fork.sh ~/my-agent my-agent
```

**What it does**:
1. Creates clean copy with new git history
2. Renames agent identity throughout workspace
3. Updates configuration files
4. Preserves architecture and lessons
5. Initializes new git repository

### Manual Forking

For more control:

```sh
# 1. Clone and reset history
git clone https://github.com/ErikBjare/gptme-agent-template.git my-agent
cd my-agent
rm -rf .git
git init

# 2. Update agent identity
# Edit: ABOUT.md, gptme.toml, README.md

# 3. Customize for your use case
# - Modify lessons
# - Update task templates
# - Adjust autonomous run schedule

# 4. Create initial commit
git add .
git commit -m "Initial commit"
```

### Post-Fork Setup

1. **Define Identity**: Update `ABOUT.md` with your agent's personality and goals
2. **Configure Context**: Adjust `gptme.toml` for your needs
3. **Set API Keys**: Copy `.env.example` to `.env.local` and add keys
4. **Customize Schedule**: Edit autonomous run frequency if desired
5. **Review Lessons**: Adapt lessons in `lessons/` to your patterns

## Autonomous Operation

Schedule automated runs with systemd (Linux):

```sh
# Setup timer (see scripts/autonomous-run.sh for details)
systemctl --user enable agent-autonomous.timer
systemctl --user start agent-autonomous.timer

# Check status
systemctl --user status agent-autonomous.timer

# View logs
journalctl --user -u agent-autonomous.service --since "1 hour ago"
```

Autonomous sessions:
- Check for loose ends and fix them
- Select forward-moving work
- Execute tasks using available tools
- Document progress in journal
- Commit and push changes

## Development

### Pre-commit Hooks

Install hooks to validate commits:

```sh
make install

# Validates:
# - Task metadata format
# - YAML frontmatter
# - Markdown links
# - Code formatting
```

### Testing

```sh
# Run test suite
make test

# Validate specific components
./scripts/tasks.py validate
./scripts/lessons/validate.py
```

### Tools

Key scripts in `scripts/`:
- `tasks.py` - Task management CLI
- `search.py` - Multi-source search (tasks, knowledge, lessons)
- `context.sh` - Dynamic context generation
- `autonomous-run.sh` - Scheduled autonomous operation

## Contributing

Improvements welcome! To contribute:

1. **Report Issues**: Share problems or suggestions via GitHub issues
2. **Submit PRs**:
   - Fix bugs
   - Add features
   - Improve documentation
   - Share lessons
3. **Share Examples**: Show what you built with this template

### Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation
- Use conventional commits
- Keep PRs focused

## Resources

- **gptme Documentation**: https://gptme.org/docs/
- **Agent Docs**: https://gptme.org/docs/agents.html
- **Example Agent**: https://github.com/TimeToBuildBob
- **Discord Community**: https://discord.gg/gptme

## License

MIT License - See LICENSE file for details

---

**Website**: https://gptme.org
**GitHub**: https://github.com/ErikBjare/gptme-agent-template
**Discord**: https://discord.gg/gptme
