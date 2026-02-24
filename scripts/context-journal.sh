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
# Supports both formats:
#   - Legacy flat: journal/2025-12-24-topic.md
#   - New subdirectory: journal/2025-12-24/topic.md

# Find all journal files (both formats)
ALL_JOURNALS=$(
    # Legacy flat format
    find journal -maxdepth 1 -name "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.md" -type f 2>/dev/null
    # New subdirectory format
    find journal -mindepth 2 -maxdepth 2 -name "*.md" -type f 2>/dev/null | while read -r f; do
        parent=$(basename "$(dirname "$f")")
        if echo "$parent" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
            echo "$f"
        fi
    done
)

LATEST_JOURNAL=$(echo "$ALL_JOURNALS" | sort -r | head -n 1)

if [ -z "$LATEST_JOURNAL" ]; then
    echo "No journal entries found."
    popd > /dev/null
    exit 0
fi

# Extract date from path (supports both formats)
# - Legacy: journal/2025-12-24-topic.md -> extract from filename
# - Subdirectory: journal/2025-12-24/topic.md -> extract from parent dir
extract_date_from_path() {
    local path="$1"
    local parent
    parent=$(basename "$(dirname "$path")")
    # Check if parent dir is a date (subdirectory format)
    if echo "$parent" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
        echo "$parent"
    else
        # Legacy format: extract from filename
        basename "$path" .md | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    fi
}

DATE=$(extract_date_from_path "$LATEST_JOURNAL")

# Get all journal files for this date, sorted by modification time (most recent first)
# Supports both formats
JOURNALS_BY_MTIME=$(
    {
        # Legacy flat format
        find journal -maxdepth 1 -name "${DATE}*.md" -type f 2>/dev/null
        # New subdirectory format
        if [ -d "journal/${DATE}" ]; then
            find "journal/${DATE}" -maxdepth 1 -name "*.md" -type f 2>/dev/null
        fi
    } | while read -r f; do stat -c '%Y %n' "$f" 2>/dev/null; done | sort -rn | cut -d' ' -f2
)

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
    echo "Create a NEW journal entry for today at: \`journal/$(date +%Y-%m-%d)/<description>.md\`"
    echo
fi

# Configuration: Number of most recent entries to include in full
MAX_FULL_ENTRIES=10

# Get the most recent N entries (by mtime), then re-sort chronologically for display
RECENT_JOURNALS=$(echo "$JOURNALS_BY_MTIME" | head -n $MAX_FULL_ENTRIES | while read -r f; do stat -c '%Y %n' "$f"; done | sort -n | cut -d' ' -f2)
OLDER_JOURNALS=$(echo "$JOURNALS_BY_MTIME" | tail -n +$((MAX_FULL_ENTRIES + 1)))

# Output most recent journal files in full
for JOURNAL in $RECENT_JOURNALS; do
    BASENAME=$(basename "$JOURNAL" .md)
    PARENT_DIR=$(basename "$(dirname "$JOURNAL")")
    DESCRIPTION=""

    # Extract description based on format
    if echo "$PARENT_DIR" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
        # Subdirectory format: journal/2025-12-24/topic.md - description is just the filename
        DESCRIPTION="$BASENAME"
    elif [[ "$BASENAME" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-(.+)$ ]]; then
        # Legacy flat format: journal/2025-12-24-topic.md - extract after date prefix
        DESCRIPTION="${BASH_REMATCH[1]}"
    fi

    if [ -n "$DESCRIPTION" ] && [ "$JOURNAL_COUNT" -gt 1 ]; then
        echo "## Session: $DESCRIPTION"
        echo
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
