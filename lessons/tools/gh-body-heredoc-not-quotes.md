---
match:
  keywords:
    - "gh pr comment --body"
    - "gh issue comment --body"
    - "backtick in body"
    - "comment body mangled"
    - "github comment stripped"
    - "gh pr comment"
    - "gh issue comment"
    - "gh pr create"
  session_categories: [social, cross-repo, code]
description: "A posted gh comment or PR body is missing its backtick code spans because backticks inside a double-quoted --body were interpreted as command substitution"
target_grade: trajectory_grade
status: active
---

# Use Heredoc (not quotes) for gh --body with backticks

## Rule
When the `--body` text contains backticks, use a heredoc or `$'...'` syntax — never
double-quoted strings — or bash will interpret backticks as command substitution
and silently strip the content.

## Context
Whenever posting GitHub comments, PR descriptions, or review replies via `gh`
that include Markdown inline code (backtick-wrapped text like \`v1.2.3\`).

## Detection
- About to write `gh ... --body "... \`code\` ..."` with backticks inside double quotes
- Posted a comment and the version names / code spans are missing from the result
- Shell emits "command not found" stderr lines for the backtick content

## Pattern
```bash
# ❌ Wrong: bash interprets backticks as command substitution
gh pr comment 123 --repo owner/repo \
  --body "Yes, `ubuntu-22.04` runners are faster. Use `python3.11`."
# → stderr: bash: ubuntu-22.04: command not found
# → comment posted as: "Yes,  runners are faster. Use ."

# ✅ Correct: heredoc preserves backticks literally
gh pr comment 123 --repo owner/repo --body "$(cat <<'EOF'
Yes, `ubuntu-22.04` runners are faster. Use `python3.11`.
EOF
)"

# ✅ Also correct: $'...' with escaped backticks
gh pr comment 123 --body $'Yes, `ubuntu-22.04` runners are faster.'
```

## Outcome
- GitHub comment posts with the exact Markdown the reader expects
- No silent stripping of code spans from public-facing text
- No confusing "command not found" stderr noise

## Related
- [unquoted-heredoc-backtick-command-substitution.md](./shell-heredoc.md)
  — same trap when appending to files via an unquoted heredoc
