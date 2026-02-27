#!/bin/bash
# Agent Workspace Readiness Check
#
# Validates that an agent workspace is properly configured for autonomous operation.
# Run after forking or setting up a new agent to ensure nothing is missing.
#
# Usage: ./scripts/check-readiness.sh [--fix]
#   --fix: Attempt to fix simple issues automatically

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FIX_MODE=false
[[ "${1:-}" == "--fix" ]] && FIX_MODE=true

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS + 1)); }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

# ========================================
# 1. Core Files
# ========================================
section "Core Identity Files"

check_file() {
    local path="$1"
    local desc="$2"
    local min_lines="${3:-5}"

    if [[ ! -f "$path" ]]; then
        fail "$desc: $path not found"
        return
    fi

    local lines
    lines=$(wc -l < "$path")
    if [[ "$lines" -lt "$min_lines" ]]; then
        warn "$desc: $path exists but only has $lines lines (expected >=$min_lines)"
    else
        pass "$desc: $path ($lines lines)"
    fi
}

check_file "ABOUT.md" "Agent identity" 10
check_file "gptme.toml" "gptme configuration" 3
check_file "ARCHITECTURE.md" "Architecture docs" 10

# Check for AGENTS.md or CLAUDE.md (at least one)
if [[ -f "AGENTS.md" ]] || [[ -f "CLAUDE.md" ]]; then
    pass "Agent instructions: AGENTS.md/CLAUDE.md present"
else
    fail "Agent instructions: neither AGENTS.md nor CLAUDE.md found"
fi

# ========================================
# 2. gptme.toml Configuration
# ========================================
section "gptme.toml Configuration"

if [[ -f "gptme.toml" ]]; then
    # Check for agent name
    if grep -q '^\[agent\]' gptme.toml && grep -q '^name\s*=' gptme.toml; then
        local_name=$(grep '^name\s*=' gptme.toml | head -1 | sed 's/.*=\s*"\(.*\)"/\1/')
        pass "Agent name configured: $local_name"
    else
        warn "No [agent] name configured in gptme.toml"
    fi

    # Check for prompt files
    if grep -q '^\[prompt\]' gptme.toml; then
        pass "Prompt configuration section present"
    else
        warn "No [prompt] section in gptme.toml"
    fi

    # Check for context_cmd
    if grep -q 'context_cmd' gptme.toml; then
        pass "Context command configured"
    else
        warn "No context_cmd in gptme.toml (dynamic context won't be generated)"
    fi
else
    info "Skipping gptme.toml checks (file not found)"
fi

# ========================================
# 3. Directory Structure
# ========================================
section "Directory Structure"

check_dir() {
    local path="$1"
    local desc="$2"
    local required="${3:-true}"

    if [[ -d "$path" ]]; then
        local count
        count=$(find "$path" -maxdepth 1 -type f -name "*.md" | wc -l)
        pass "$desc: $path/ ($count .md files)"
    elif [[ "$required" == "true" ]]; then
        fail "$desc: $path/ not found"
        if $FIX_MODE; then
            mkdir -p "$path"
            info "Created $path/"
        fi
    else
        warn "$desc: $path/ not found (optional)"
    fi
}

check_dir "tasks" "Task directory" true
check_dir "journal" "Journal directory" true
check_dir "knowledge" "Knowledge base" true
check_dir "lessons" "Lessons directory" true
check_dir "people" "People directory" false
check_dir "skills" "Skills directory" false

# ========================================
# 4. Git Configuration
# ========================================
section "Git Configuration"

if git rev-parse --git-dir >/dev/null 2>&1; then
    pass "Git repository initialized"
else
    fail "Not a git repository"
fi

# Check for remote
if git remote get-url origin >/dev/null 2>&1; then
    pass "Git remote 'origin' configured: $(git remote get-url origin)"
else
    warn "No git remote 'origin' configured"
fi

# Check for pre-commit hooks
if [[ -f ".pre-commit-config.yaml" ]]; then
    pass "Pre-commit configuration found"

    # Check if hooks are installed
    if [[ -f ".git/hooks/pre-commit" ]] && grep -q "pre-commit" ".git/hooks/pre-commit" 2>/dev/null; then
        pass "Pre-commit hooks installed"
    elif [[ -f ".git/hooks/pre-commit" ]] && grep -q "prek" ".git/hooks/pre-commit" 2>/dev/null; then
        pass "Pre-commit hooks installed (via prek)"
    else
        warn "Pre-commit hooks not installed (run: pre-commit install OR prek install)"
        if $FIX_MODE; then
            if command -v prek >/dev/null 2>&1; then
                prek install && info "Installed pre-commit hooks via prek"
            elif command -v pre-commit >/dev/null 2>&1; then
                pre-commit install && info "Installed pre-commit hooks"
            else
                info "Neither prek nor pre-commit found — install one first"
            fi
        fi
    fi
else
    warn "No .pre-commit-config.yaml found"
fi

# ========================================
# 5. Required Tools
# ========================================
section "Required Tools"

check_tool() {
    local cmd="$1"
    local desc="$2"
    local required="${3:-true}"

    if command -v "$cmd" >/dev/null 2>&1; then
        local version
        version=$("$cmd" --version 2>/dev/null | head -1 || echo "version unknown")
        pass "$desc: $cmd ($version)"
    elif [[ "$required" == "true" ]]; then
        fail "$desc: $cmd not found"
    else
        warn "$desc: $cmd not found (optional)"
    fi
}

check_tool "gptme" "gptme CLI" true
check_tool "git" "Git" true
check_tool "python3" "Python 3" true
check_tool "uv" "uv package manager" false
check_tool "gh" "GitHub CLI" false
check_tool "gptodo" "Task manager CLI" false

# ========================================
# 6. Python Environment
# ========================================
section "Python Environment"

if [[ -f "pyproject.toml" ]]; then
    pass "pyproject.toml found"

    if [[ -d ".venv" ]]; then
        pass "Virtual environment exists (.venv/)"
    else
        warn "No virtual environment (.venv/) — run: uv sync"
        if $FIX_MODE && command -v uv >/dev/null 2>&1; then
            uv sync && info "Created virtual environment"
        fi
    fi

    if [[ -f "uv.lock" ]]; then
        pass "Lock file exists (uv.lock)"
    else
        warn "No lock file (uv.lock) — run: uv sync"
    fi
else
    info "No pyproject.toml (no Python packages to manage)"
fi

# ========================================
# 7. Submodules
# ========================================
section "Submodules"

if [[ -f ".gitmodules" ]]; then
    local_subs="$(grep -c '\[submodule' .gitmodules || true)"
    : "${local_subs:=0}"
    pass "Git submodules configured ($local_subs)"

    # Check if submodules are initialized
    uninit="$(git submodule status 2>/dev/null | grep -c '^-' || true)"
    : "${uninit:=0}"
    if [[ "$uninit" -gt 0 ]]; then
        warn "$uninit uninitialized submodule(s) — run: git submodule update --init --recursive"
        if $FIX_MODE; then
            git submodule update --init --recursive && info "Initialized submodules"
        fi
    else
        pass "All submodules initialized"
    fi
else
    info "No submodules configured"
fi

# ========================================
# 8. Context Script
# ========================================
section "Context Generation"

if [[ -f "scripts/context.sh" ]]; then
    if [[ -x "scripts/context.sh" ]]; then
        pass "Context script executable: scripts/context.sh"
    else
        warn "Context script not executable: scripts/context.sh"
        if $FIX_MODE; then
            chmod +x scripts/context.sh && info "Made context.sh executable"
        fi
    fi
else
    warn "No context script (scripts/context.sh) — dynamic context won't be generated"
fi

# ========================================
# 9. Tasks
# ========================================
section "Task System"

if [[ -d "tasks" ]]; then
    task_count=$(find tasks/ -maxdepth 1 -name "*.md" -type f | wc -l)
    if [[ "$task_count" -gt 0 ]]; then
        pass "Tasks found: $task_count"
    else
        warn "Task directory exists but no tasks found"
    fi

    # Check for TASKS.md guide
    if [[ -f "TASKS.md" ]]; then
        pass "Task system documentation (TASKS.md)"
    else
        warn "No TASKS.md — task system undocumented"
    fi
else
    info "No tasks directory"
fi

# ========================================
# Summary
# ========================================
echo ""
echo "========================================="
echo "Agent Readiness Summary"
echo "========================================="

if [[ "$ERRORS" -eq 0 && "$WARNINGS" -eq 0 ]]; then
    echo -e "${GREEN}ALL CHECKS PASSED${NC} — workspace is ready for autonomous operation"
elif [[ "$ERRORS" -eq 0 ]]; then
    echo -e "${YELLOW}PASSED WITH WARNINGS${NC} — $WARNINGS warning(s), no critical issues"
else
    echo -e "${RED}ISSUES FOUND${NC} — $ERRORS error(s), $WARNINGS warning(s)"
    echo ""
    echo "Fix critical issues before running autonomous sessions."
    if ! $FIX_MODE; then
        echo "Run with --fix to attempt automatic fixes."
    fi
fi

echo ""
exit "$ERRORS"
