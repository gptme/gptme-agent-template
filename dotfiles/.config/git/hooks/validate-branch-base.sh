#!/bin/bash
# Validate that current branch is based on origin/master
# Warns if branch has unmerged commits from local work

set -e

# Get current branch
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ -z "$current_branch" ]; then
    exit 0  # Not in a git repo
fi

# Skip check on master/main branches
if [ "$current_branch" = "master" ] || [ "$current_branch" = "main" ]; then
    exit 0
fi

# Get merge base with origin/master (try both master and main)
merge_base=""
for remote_branch in origin/master origin/main; do
    if git rev-parse --verify "$remote_branch" >/dev/null 2>&1; then
        merge_base=$(git merge-base HEAD "$remote_branch" 2>/dev/null || echo "")
        if [ -n "$merge_base" ]; then
            origin_default="$remote_branch"
            break
        fi
    fi
done

if [ -z "$merge_base" ]; then
    # Can't determine merge base, skip check
    exit 0
fi

# Get latest commit on origin/master or origin/main
origin_commit=$(git rev-parse "$origin_default" 2>/dev/null || echo "")
if [ -z "$origin_commit" ]; then
    exit 0
fi

# Check if merge base is origin/master/main
if [ "$merge_base" != "$origin_commit" ]; then
    echo "⚠️  Warning: Branch '$current_branch' not based on latest $origin_default"
    echo "   Merge base: $(git rev-parse --short $merge_base)"
    echo "   $origin_default: $(git rev-parse --short $origin_commit)"
    echo "   This means your branch includes unmerged commits from other local work."
    echo "   Consider: git rebase $origin_default"
    echo ""
    # Don't fail, just warn (can be noisy during rebases)
fi

exit 0
