---
match:
  keywords:
    - "can't build locally"
    - "cannot compile locally"
    - "type-correct by inspection"
    - "no webkit2gtk"
    - "rely on CI for the build"
    - "editing rust I can't compile"
  session_categories: [cross-repo, code]
description: "Editing compiled-language code (e.g. Rust) that can't be built locally, and claiming type-correctness by inspection — then a formatting/trait construct like {e} Display fails to compile"
status: active
---

# Don't Overclaim Correctness for Code You Can't Compile

## Rule
When editing a compiled language you can't build locally, do not claim
"type-correct by inspection" for trait-dependent constructs. Mirror the
surrounding error-handling exactly, and treat CI as the real gate.

## Context
When editing Rust (or any compiled language) in an environment missing system
libs (`gdk-3.0`, `webkit2gtk`, etc.), `cargo check`/clippy can't run. Inspection
catches logic but not trait-resolution failures.

## Detection
- `cargo check` fails at the system-dependency stage (missing `.pc` file)
- About to write `eprintln!("...: {e}")` / `format!("{e}")` on an error value
- The surrounding code discards that same error: `.map_err(|_| "...".into())`,
  or formats it with `{e:?}` (Debug) instead of `{e}` (Display)
- Journal/PR comment says "type-correct by inspection" for non-trivial edits

## Pattern
```rust
// Surrounding code is the type oracle. If it discards the error, the error
// type probably does NOT implement Display:
let p = dirs::db_path(testing).map_err(|_| "Failed to get db path")?;  // <-- signal

// ❌ Display on a non-Display error type → compile error you can't catch locally
Err(e) => { eprintln!("Error: failed to get db path: {e}"); exit(1); }

// ✅ Mirror the surrounding pattern: drop the value, or use Debug if needed
Err(_) => { eprintln!("Error: failed to get db path"); exit(1); }
// or, when the type is known to impl Debug:  eprintln!("...: {e:?}");
```

## Outcome
- No compile errors shipped on PRs that only CI (or a parallel session) catches
- Honest verification claims: "fmt clean + CI is the build authority", not
  "type-correct by inspection"
- Error formatting stays consistent with the file's existing conventions

## Related
- [exit-code-127-use-uv-run.md](./exit-code-127-use-uv-run.md) — another CI-gate-only failure class
