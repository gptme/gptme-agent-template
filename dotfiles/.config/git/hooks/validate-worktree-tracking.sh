#!/bin/bash
# Validate worktree has correct upstream tracking before push
# Fails if no upstream or upstream not on origin

set -e

# Get current branch
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ -z "$current_branch" ]; then
    exit 0  # Not in a git repo
fi

# Skip check on master/main branches (usually tracked correctly)
if [ "$current_branch" = "master" ] || [ "$current_branch" = "main" ]; then
    exit 0
fi

# Get upstream tracking branch
upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")

if [ -z "$upstream" ]; then
    echo "❌ Error: Branch '$current_branch' has no upstream tracking branch"
    echo "   This can cause pushes to wrong location or branch."
    echo "   Fix with: git branch --set-upstream-to=origin/$current_branch"
    echo ""
    exit 1
fi

# Verify upstream is on origin (not a local branch)
if [[ ! "$upstream" =~ ^origin/ ]]; then
    echo "⚠️  Warning: Branch '$current_branch' upstream is '$upstream' (not on origin)"
    echo "   Expected: origin/$current_branch"
    echo "   Fix with: git branch --set-upstream-to=origin/$current_branch"
    echo ""
    # Don't fail, just warn - might be intentional
fi

exit 0
