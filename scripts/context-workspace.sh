#!/bin/bash

# Output workspace structure context for gptme
# Usage: ./scripts/context-workspace.sh

set -e  # Exit on error

# Force UTF-8 encoding
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR=$(dirname "$SCRIPT_DIR")
pushd "$AGENT_DIR" > /dev/null

# Add workspace structure section
echo -e "# Workspace structure\n"

# Get tree structure for each directory, force ASCII output
TREE_HARNESS="$(LANG=C tree -a --dirsfirst --noreport . -L 1)"
TREE_TASKS="$(LANG=C tree -a --dirsfirst --noreport ./tasks)"
TREE_PROJECTS="$(LANG=C tree -a --dirsfirst --noreport ./projects -L 1)"
TREE_JOURNAL="$(LANG=C tree -a --dirsfirst --noreport ./journal)"
TREE_KNOWLEDGE="$(LANG=C tree -a -L 2 --dirsfirst --noreport ./knowledge)"
TREE_PEOPLE="$(LANG=C tree -a --dirsfirst --noreport ./people)"

cat << EOF
\`\`\`tree $AGENT_DIR
$TREE_HARNESS
$TREE_TASKS
$TREE_PROJECTS
$TREE_JOURNAL
$TREE_KNOWLEDGE
$TREE_PEOPLE
\`\`\`
EOF

popd > /dev/null
