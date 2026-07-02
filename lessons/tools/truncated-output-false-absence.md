---
match:
  keywords:
    - "conclude it doesn't exist"
    - "appears untracked"
    - "no existing copy found"
    - "not in the list output"
    - "head truncated the listing"
  session_categories: [code, infrastructure, cleanup, cross-repo]
description: "Don't conclude a file, symbol, or config is absent from head- or limit-truncated search output — confirm absence by grepping for the specific target name, not by eyeballing a truncated list"
status: active
---

# Don't Conclude Absence From Truncated Output

## Rule
Never conclude "X doesn't exist / isn't tracked / has no copy" from output that was
truncated by `head`, `head_limit`, or tool-output trimming. Confirm absence by
searching for the **specific target name**, not by scanning a capped list.

## Context
Agent tool output is frequently truncated: `| head -N`, Grep tool's
default `head_limit`, Bash stdout/stderr trimming, or tool-output trimming.
A truncated listing produces **false negatives** — the item is present but past
the cutoff (e.g. alphabetically beyond `head -20`).

## Detection
- About to act on "not found" / "no existing X" after a `… | head -N` command
- Used `git ls-files '*.svc' | head` and concluded a file is untracked
- A listing was alphabetical/sorted and your target sorts late
- About to (re)create, re-track, or re-derive something you "confirmed" missing

## Pattern
```bash
# ❌ False negative: target may be past the head cutoff
git ls-files '*.service' | head -20        # target may sort late alphabetically
# → "not listed" ≠ "not tracked"

# ✅ Confirm absence by the specific name
git ls-files '*my-service-name*'           # authoritative present/absent
rg -l 'exact_symbol_name' path/            # not: rg ... | head, then eyeball
git ls-files | grep -c 'target'            # count, not truncated scan
```
Rule of thumb: a capped list answers "what are some matches?", never
"does this specific thing exist?". For existence, query the specific key.

## Outcome
- No wasted work re-creating/re-tracking something that already exists
- No duplicate files committed because the canonical copy was "missing"
- Absence claims are authoritative, not artifacts of a display limit

## Related
- [gh-body-heredoc-not-quotes.md](./gh-body-heredoc-not-quotes.md) — another "output not what you expect" class
