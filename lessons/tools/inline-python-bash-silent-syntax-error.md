---
match:
  keywords:
    - "stderr swallowed around python3 -c"
    - "shell wrapper hid python syntaxerror"
    - "multi-line inline python drift"
    - "2>/dev/null python"
    - "inline python syntax"
  session_categories: [code, infrastructure]
description: "Inline python3 -c or heredoc Python in a shell script is piped to 2>/dev/null || true, so a SyntaxError fails silently and an expected field/file/commit never gets written"
status: active
---

# Inline Python in Bash Hides SyntaxErrors

## Rule
Don't pipe inline `python3 -c "..."` to `2>/dev/null || true`. Either let stderr
surface, or extract the script to a separate `.py` file so syntax errors fail
loudly the first time the script runs.

## Context
When embedding multi-line Python inside shell scripts (hooks, systemd ExecStart
wrappers, post-processing pipelines). Bash heredocs and `python3 -c` blocks
easily acquire indentation drift on edit, and the surrounding `2>/dev/null` +
`|| true` pattern swallows the resulting `SyntaxError`.

## Detection
- Inline `python3 -c '...'` or `python3 << EOF` blocks that suppress stderr
- `|| true` immediately after a python invocation
- A field, file, or commit that "should have" been written but wasn't, with no error visible
- **`@Q`/`${var}` interpolated into an *unquoted* heredoc body** (`json.loads(${item_json@Q})`):
  `@Q` emits a bash `$'...'` C-string when the value holds an apostrophe or newline — invalid Python.
  A title like `Erik's fix` then SyntaxErrors silently.

## Pattern
```bash
# ❌ Wrong — SyntaxError silently ignored, data never written
python3 -c "
for rec in records:
    if changed:    # mis-indented; SyntaxError
        update(rec)
        break
" 2>/dev/null || true

# ✅ Correct — extract to a real script file, let errors surface
python3 scripts/your_backfill.py "$session_id" || \
    echo "WARN: backfill failed for $session_id" >&2

# ✅ Also correct — keep inline but don't swallow stderr
python3 -c "
for rec in records:
    if changed:
        update(rec)
        break
"

# ✅ Passing values into a heredoc — quote the delimiter + use os.environ,
#    never interpolate bash (@Q / ${var}) into the Python body
out=$(ITEM_JSON="$item_json" python3 - <<'PY'
import json, os
print(json.loads(os.environ["ITEM_JSON"]))
PY
)
```

## Outcome
- SyntaxErrors fail on the first run instead of after N days of silent data loss
- Inline Python becomes a deliberate choice, not a default that hides bugs

## Related
- [markdown-codeblock-syntax.md](./markdown-codeblock-syntax.md) — similar silent-failure pattern with markdown code fences
