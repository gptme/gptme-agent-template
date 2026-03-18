---
match:
  keywords:
    - "save file to"
    - "write journal entry"
    - "mkdir -p journal"
    - "file path"
    - "wrong directory"
    - "file ended up in wrong"
    - "journal created in external repo"
status: active
---

# Always Use Absolute Paths for Workspace Files

## Rule
Always use absolute paths when saving/appending to workspace files, especially journal entries.

## Context
When working across multiple repositories or when current directory might change during operation.

## Detection
- Files ending up in wrong directory (e.g., journal entry created in a checked-out external repo)
- "File not found" errors when appending to a previously written file
- Relative paths used with save/append tools
- Journal entries created outside the agent workspace

## Pattern
```text
# ❌ Wrong: relative path depends on cwd
cd ~/projects/gptme
echo "..." >> journal/2025-10-14-topic.md  # creates in wrong repo!

# ✅ Correct: absolute path works from any directory
WORKSPACE=$(git rev-parse --show-toplevel)
echo "..." >> "$WORKSPACE/journal/2025-10-14-topic.md"
```

For tools that write files directly (save, append), always use the absolute path:
```text
# ❌ Wrong
save journal/2025-10-14/session.md

# ✅ Correct
save /home/agent/workspace/journal/2025-10-14/session.md
```

## Outcome
- **Reliability**: Works regardless of current working directory
- **Prevents data loss**: Files always go to the intended location
- **No confusion**: Explicit about which repo/workspace receives the file

## Related
- Full context: knowledge/lessons/workflow/absolute-paths-for-workspace-files.md
