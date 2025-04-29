#!/bin/bash

# Output journal context for gptme
# Usage: ./scripts/context-journal.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR=$(dirname "$SCRIPT_DIR")
pushd "$AGENT_DIR" > /dev/null

if [ ! -d journal ]; then
    echo "Journal folder not found, skipping journal section."
    popd > /dev/null
    exit 0
fi

# Add journal section header
echo "# Journal Context"
echo

# Get most recent journal file (sort by filename in reverse order)
JOURNAL=$(find journal -maxdepth 1 -name "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md" -type f | sort -r | head -n 1)

if [ ! -f "$JOURNAL" ]; then
    echo "No journal entries found."
    popd > /dev/null
    exit 0
fi

# Get the date from filename
DATE=$(basename "$JOURNAL" .md)

# Determine if this is today's or a past journal
if [ "$(date +%Y-%m-%d)" = "$DATE" ]; then
    HEADER="Today's Journal Entry"
elif [ "$(date -d yesterday +%Y-%m-%d)" = "$DATE" ]; then
    HEADER="Yesterday's Journal Entry"
else
    HEADER="Journal Entry from $DATE"
fi

echo "$HEADER:"
echo

# Output journal content
echo "\`\`\`journal/$(basename "$JOURNAL")"
    cat "$JOURNAL"
echo "\`\`\`"
echo

popd > /dev/null
