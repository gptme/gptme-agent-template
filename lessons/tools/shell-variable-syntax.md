---
match:
  keywords:
    - "missing dollar sign in shell"
    - "bare variable in shell"
    - "forgot the dollar prefix"
    - "command not found variable"
  session_categories: [code, infrastructure]
description: "A shell command fails with 'VARIABLE_NAME: command not found' because a variable was referenced as a bare word without the $ prefix"
status: active
---

# Shell Variable Syntax

## Rule
Always use `$` prefix when referencing variables in shell commands.

## Context
When constructing shell commands programmatically or writing shell scripts.

## Detection
Observable signals indicating missing `$` prefix:
- Error: `bash: VARIABLE_NAME: command not found`
- Variable names appearing as bare words in commands
- All-caps identifiers used as commands (e.g. `TIMEOUT: command not found`)
- A numeric literal treated as a command (`300.0: command not found`)

## Pattern
```shell
# ❌ Wrong: bare variable name — bash tries to run it as a command
REPO_ROOT

# ✅ Correct: with $ prefix
echo $REPO_ROOT

# ❌ Wrong: numeric literal as command
300.0

# ✅ Correct: use in proper context
timeout 300 mycommand

# ❌ Wrong: variable inside assignment with missing $ on the right
DEST=HOME/projects    # HOME never expanded

# ✅ Correct
DEST=$HOME/projects
```

## Outcome
- No spurious "command not found" errors from bare variable names
- Shell scripts run predictably without hidden expansion failures

## Related
- [shell-heredoc.md](./shell-heredoc.md) — other common shell trap in gptme agent scripts
