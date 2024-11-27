#!/bin/bash

# get most recent journal/YYYY-MM-DD.md file
JOURNAL=journal/$(ls -t journal/ | head -n 1)

# Parse arguments
DRY_RUN=false
INTERACTIVE=true
PROMPT="continue\n\nHere is today's journal: $JOURNAL"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --non-interactive)
            INTERACTIVE=false
            shift
            ;;
        *)
            PROMPT="$1"
            shift
            ;;
    esac
done

# TODO: read from gptme.toml
HARNESS_FILES="README.md ARCHITECTURE.md ABOUT.md"

# Generate tree of workspace structure
TREE_HARNESS="$(ls -l $HARNESS_FILES | awk '{print $9}')"
TREE_TASKS_CURRENT=$(ls -l CURRENT_TASK.md | awk '{print $9 " -> " $11}')
TREE_TASKS_ACTIVE="$(tree -a --dirsfirst --noreport ./tasks -L 3 -I 'all|cancelled')"
TREE_TASKS="$(echo -e "$TREE_TASKS_CURRENT\n$TREE_TASKS_ACTIVE")"
TREE_PROJECTS="$(tree -a --dirsfirst --noreport ./projects -L 1)"
TREE_JOURNAL="$(tree -a --dirsfirst --noreport ./journal)"
TREE_KNOWLEDGE="$(tree -a --dirsfirst --noreport ./knowledge)"
TREE_PEOPLE="$(tree -a --dirsfirst --noreport ./people)"
TREE=$(echo -e "# Workspace structure\n\n\`\`\`tree\n$TREE_HARNESS\n$TREE_TASKS\n$TREE_PROJECTS\n$TREE_JOURNAL\n$TREE_KNOWLEDGE\n$TREE_PEOPLE\n\`\`\`")

# Prepare full prompt
FULL_PROMPT="$TREE"

# if git status isn't clean, add git status and diff information
if [[ $(git status --porcelain) ]]; then
    FULL_PROMPT=$(echo -e "$FULL_PROMPT\n\n\`\`\`git status\n$(git status)\n\`\`\`")
    # staged changes (if any)
    if [[ $(git diff --cached) ]]; then
        FULL_PROMPT=$(echo -e "$FULL_PROMPT\n\n\`\`\`git diff --cached\n$(git diff --cached)\n\`\`\`")
    fi
    # unstaged changes (if any)
    if [[ $(git diff) ]]; then
        FULL_PROMPT=$(echo -e "$FULL_PROMPT\n\n\`\`\`git diff\n$(git diff)\n\`\`\`")
    fi
fi

if [ "$DRY_RUN" = true ]; then
    # In dry-run mode, just print the prompts
    echo -e "$PROMPT\n\n$FULL_PROMPT"
else
    # Normal mode: run gptme with or without interactive mode
    if [ "$INTERACTIVE" = false ]; then
        gptme --non-interactive "$PROMPT" "$FULL_PROMPT"
    else
        gptme "$PROMPT" "$FULL_PROMPT"
    fi
fi
