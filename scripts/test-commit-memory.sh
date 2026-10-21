#!/usr/bin/env bash
# scripts/test-commit-memory.sh — regression tests for commit-memory.sh
#
# Covers:
#   1. Helper-unavailable route (fallback plain commit, no git-safe-commit)
#   2. Helper-present route (git-safe-commit stub present)
#   3. Staged rename where source tail matches a memory file (was exit 128 / silent corruption)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMIT_MEMORY="$SCRIPT_DIR/commit-memory.sh"
PASS=0
FAIL=0

run_test() {
    local name="$1"
    local fn="$2"
    # Capture exit code explicitly — don't call fn as an `if` condition (that disables set -e
    # inside the function, causing || return 1 assertions to silently pass).
    local rc=0
    { "$fn" 2>&1; rc=$?; } || true
    if [[ $rc -eq 0 ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (exit $rc)"
        FAIL=$((FAIL + 1))
    fi
}

setup_repo() {
    local dir="$1"
    # Use a non-master branch so the "no direct commits to master" hook doesn't block.
    git init -q -b work "$dir"
    git -C "$dir" config user.email "agent@example.com"
    git -C "$dir" config user.name "Agent"
    mkdir -p "$dir/memory" "$dir/scripts"
    touch "$dir/memory/.keep"
    # Copy the script under test into the repo so BASH_SOURCE[0] resolves to the right root.
    cp "$COMMIT_MEMORY" "$dir/scripts/commit-memory.sh"
    chmod +x "$dir/scripts/commit-memory.sh"
    git -C "$dir" add .
    ALLOW_GIT_IDENTITY=1 git -C "$dir" commit -q -m "init"
}

# Test 1: helper-unavailable — new memory file committed via plain fallback
test_no_helper() {
    local repo
    repo="$(mktemp -d)"
    setup_repo "$repo"
    echo "data" >"$repo/memory/new.md"
    (cd "$repo" && ALLOW_GIT_IDENTITY=1 MEMORY_DIR=memory bash scripts/commit-memory.sh) || return 1
    git -C "$repo" log --oneline --grep="periodic sweep" | grep -q . || { echo "  no sweep commit found"; return 1; }
    git -C "$repo" show HEAD -- memory/new.md | grep -q "data" || { echo "  new.md not in HEAD"; return 1; }
    rm -rf "$repo"
}

# Test 2: helper-present — delegates to git-safe-commit stub
test_with_helper() {
    local repo
    repo="$(mktemp -d)"
    setup_repo "$repo"
    mkdir -p "$repo/scripts"
    # Minimal git-safe-commit stub: same CLI contract as the real one
    cat >"$repo/scripts/git-safe-commit" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
files=(); msg=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -m) msg="$2"; shift 2 ;;
        --) shift; files+=("$@"); break ;;
        *) files+=("$1"); shift ;;
    esac
done
git add -- "${files[@]}"
ALLOW_GIT_IDENTITY=1 git commit -m "$msg" -- "${files[@]}"
STUB
    chmod +x "$repo/scripts/git-safe-commit"
    echo "helper-data" >"$repo/memory/via-helper.md"
    (cd "$repo" && ALLOW_GIT_IDENTITY=1 MEMORY_DIR=memory bash scripts/commit-memory.sh) || return 1
    git -C "$repo" log --oneline --grep="periodic sweep" | grep -q . || { echo "  no sweep commit found"; return 1; }
    git -C "$repo" show HEAD -- memory/via-helper.md | grep -q "helper-data" || { echo "  via-helper.md not in HEAD"; return 1; }
    rm -rf "$repo"
}

# Test 3: staged rename with outside-memory source whose tail matches a memory file.
# Before the fix: git status parsing mangled the old-path → exit 128 or silent corruption.
test_staged_rename_outside_source() {
    local repo
    repo="$(mktemp -d)"
    setup_repo "$repo"
    mkdir -p "$repo/docs"
    echo "outside" >"$repo/docs/notes.md"
    echo "inside" >"$repo/memory/notes.md"
    git -C "$repo" add .
    ALLOW_GIT_IDENTITY=1 git -C "$repo" commit -q -m "add files"
    # Stage a rename outside memory/ (docs/notes.md → docs/renamed.md)
    git -C "$repo" mv docs/notes.md docs/renamed.md
    # Add an uncommitted file in memory/
    echo "new" >"$repo/memory/new.md"
    # commit-memory.sh must commit only memory/new.md and not crash on the staged rename
    (cd "$repo" && ALLOW_GIT_IDENTITY=1 MEMORY_DIR=memory bash scripts/commit-memory.sh) || return 1
    git -C "$repo" log --oneline --grep="periodic sweep" | grep -q . || { echo "  no sweep commit found"; return 1; }
    git -C "$repo" show HEAD -- memory/new.md | grep -q "new" || { echo "  memory/new.md not in HEAD"; return 1; }
    # Staged rename must still be staged — commit-memory must not have touched it
    git -C "$repo" diff --cached --name-only | grep -q "docs/renamed.md" || { echo "  staged rename was lost"; return 1; }
    rm -rf "$repo"
}

run_test "helper-unavailable fallback" test_no_helper
run_test "helper-present route" test_with_helper
run_test "staged rename with outside-memory source-tail collision" test_staged_rename_outside_source

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
