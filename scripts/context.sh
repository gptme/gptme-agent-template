#!/bin/bash

# Build context for gptme
# Usage: ./scripts/context.sh [options]

set -e  # Exit on error

# Force UTF-8 encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make all component scripts executable
chmod +x "$SCRIPT_DIR"/context-*.sh

# Write context summary header
echo "# Context Summary"
echo
echo "Generated on: $(date)"
echo

# Add divider
echo "---"
echo

# Run each component script
"$SCRIPT_DIR"/context-journal.sh
echo
echo -e "# Tasks\n"
# gptodo is the task management CLI (replaces deprecated tasks.py)
if command -v gptodo &> /dev/null; then
    echo -e "Output of \`gptodo status --compact\` command:\n"
    gptodo status --compact
else
    echo -e "(Task management CLI not installed - install gptodo from gptme-contrib)\n"
    echo -e "See: uv tool install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptodo\n"
fi
echo
"$SCRIPT_DIR"/context-workspace.sh
echo
echo -e "# Git\n"
echo '```git status'
git status | head -200
echo '```'
