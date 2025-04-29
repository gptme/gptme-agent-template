#!/bin/bash

# Build context for gptme
# Usage: ./scripts/context.sh [options]

set -e  # Exit on error

# Force UTF-8 encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make all component scripts executable
chmod +x $SCRIPT_DIR/context-*.sh

# Write context summary header
echo "# Context Summary"
echo
echo "Generated on: $(date)"
echo

# Add divider
echo "---"
echo

# Run each component script
$SCRIPT_DIR/context-journal.sh
echo
echo -e "# Tasks\n"
echo -e "Output of \`$SCRIPT_DIR/tasks.py status --compact\` command:\n"
$SCRIPT_DIR/tasks.py status --compact
echo
$SCRIPT_DIR/context-workspace.sh
echo
echo -e "# Git\n"
echo '```git status -vv'
git status -vv
echo '```'
