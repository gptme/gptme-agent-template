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

# Get most recent journal date (from any journal file)
LATEST_JOURNAL=$(find journal -maxdepth 1 -name "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.md" -type f | sort -r | head -n 1)

if [ -z "$LATEST_JOURNAL" ]; then
    echo "No journal entries found."
    popd > /dev/null
    exit 0
fi

# Extract date from filename (before any description)
DATE=$(basename "$LATEST_JOURNAL" .md | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}')

# Get all journal files for this date, sorted by modification time (most recent first)
JOURNALS_BY_MTIME=$(find journal -maxdepth 1 -name "${DATE}*.md" -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2)

# Determine if this is today's or a past journal
if [ "$(date +%Y-%m-%d)" = "$DATE" ]; then
    HEADER="Today's Journal Entry"
elif [ "$(date -d yesterday +%Y-%m-%d)" = "$DATE" ]; then
    HEADER="Yesterday's Journal Entry"
else
    HEADER="Journal Entry from $DATE"
fi

# Count journal files
JOURNAL_COUNT=$(echo "$JOURNALS_BY_MTIME" | wc -l)

if [ "$JOURNAL_COUNT" -eq 1 ]; then
    echo "$HEADER:"
else
    echo "$HEADER ($JOURNAL_COUNT sessions):"
fi
echo

# Add instructions based on journal date
if [ "$(date +%Y-%m-%d)" != "$DATE" ]; then
    echo "**IMPORTANT**: This journal is from $DATE (not today: $(date +%Y-%m-%d))."
    echo "Create a NEW journal entry for today at: \`journal/$(date +%Y-%m-%d)-<description>.md\`"
    echo
fi

# Configuration: Number of most recent entries to include in full
MAX_FULL_ENTRIES=10

# Get the most recent N entries (by mtime), then re-sort chronologically for display
RECENT_JOURNALS=$(echo "$JOURNALS_BY_MTIME" | head -n $MAX_FULL_ENTRIES | while read f; do stat -c '%Y %n' "$f"; done | sort -n | cut -d' ' -f2)
OLDER_JOURNALS=$(echo "$JOURNALS_BY_MTIME" | tail -n +$((MAX_FULL_ENTRIES + 1)))

# Output most recent journal files in full
for JOURNAL in $RECENT_JOURNALS; do
    BASENAME=$(basename "$JOURNAL" .md)
    # Extract description if present
    if [[ "$BASENAME" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-(.+)$ ]]; then
        DESCRIPTION="${BASH_REMATCH[1]}"
        if [ "$JOURNAL_COUNT" -gt 1 ]; then
            echo "## Session: $DESCRIPTION"
            echo
        fi
    fi

    echo "\`\`\`$JOURNAL"
    cat "$JOURNAL"
    echo "\`\`\`"
    echo
done

# List older journal entries (paths only)
if [ -n "$OLDER_JOURNALS" ]; then
    echo "## Older Sessions (read with cat if relevant)"
    echo
    for JOURNAL in $OLDER_JOURNALS; do
        echo "- \`$JOURNAL\`"
    done
    echo
fi

popd > /dev/null
