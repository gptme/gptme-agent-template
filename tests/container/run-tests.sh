#!/bin/bash
# Container test runner for e2e agent validation
# Tests full fork + setup + script validation workflow

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Configure git (required for fork.sh)
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git config --global init.defaultBranch master

cd /home/testuser/gptme-agent-template

echo "========================================"
echo "E2E Agent Container Tests"
echo "========================================"
echo ""

# Test 1: Fork creates valid agent structure
log_test "Fork creates valid agent structure"
if ./scripts/fork.sh /home/testuser/test-agent testagent; then
    log_pass "Fork completed successfully"
else
    log_fail "Fork failed"
    exit 1
fi

cd /home/testuser/test-agent

# Test 2: Required directories exist
log_test "Required directories exist"
required_dirs=("tasks" "journal" "knowledge" "lessons" "people" "scripts")
all_dirs_exist=true
for dir in "${required_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log_fail "Missing directory: $dir"
        all_dirs_exist=false
    fi
done
if $all_dirs_exist; then
    log_pass "All required directories present"
fi

# Test 3: Required files exist
log_test "Required files exist"
required_files=("gptme.toml" "README.md" "ABOUT.md")
all_files_exist=true
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_fail "Missing file: $file"
        all_files_exist=false
    fi
done
if $all_files_exist; then
    log_pass "All required files present"
fi

# Test 4: Agent name substitution worked
log_test "Agent name substitution in gptme.toml"
if grep -q 'name = "testagent"' gptme.toml; then
    log_pass "Agent name correctly substituted"
else
    log_fail "Agent name not found in gptme.toml"
fi

# Test 5: Context script runs without error
log_test "Context script execution"
if [[ -f scripts/context.sh ]]; then
    if timeout 30 ./scripts/context.sh > /dev/null 2>&1; then
        log_pass "Context script runs successfully"
    else
        log_fail "Context script failed or timed out"
    fi
else
    log_fail "Context script not found"
fi

# Test 6: Systemd service files are valid (syntax check)
log_test "Systemd service file validation"
if [[ -d dotfiles/.config/systemd/user ]]; then
    service_files=$(find dotfiles/.config/systemd/user -name "*.service*" -o -name "*.timer*" 2>/dev/null)
    if [[ -n "$service_files" ]]; then
        all_valid=true
        while IFS= read -r service_file; do
            # Basic syntax check - ensure required sections exist
            if grep -qE '^\[Unit\]' "$service_file" && grep -qE '^\[Service\]|^\[Timer\]' "$service_file"; then
                :  # Valid
            else
                log_fail "Invalid service file format: $service_file"
                all_valid=false
            fi
        done <<< "$service_files"
        if $all_valid; then
            log_pass "All service files have valid format"
        fi
    else
        log_pass "No service files to validate (template uses examples)"
    fi
else
    log_pass "No dotfiles/systemd directory (optional)"
fi

# Test 7: Git repository is properly initialized
log_test "Git repository initialization"
if [[ -d .git ]] && git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    log_pass "Git repository properly initialized"
else
    log_fail "Git repository not initialized"
fi

# Test 8: Pre-commit config exists
log_test "Pre-commit configuration"
if [[ -f .pre-commit-config.yaml ]]; then
    log_pass "Pre-commit config present"
else
    log_fail "Pre-commit config missing"
fi

# Test 9: Submodule (gptme-contrib) initialized
log_test "Submodule initialization"
if [[ -d gptme-contrib/.git ]] || [[ -f gptme-contrib/.git ]]; then
    log_pass "Submodule initialized"
elif [[ -d gptme-contrib ]] && [[ -n "$(ls -A gptme-contrib 2>/dev/null)" ]]; then
    log_pass "Submodule directory populated"
else
    log_fail "Submodule not properly initialized"
fi

# Test 10: Scripts have execute permission
# Note: fork.sh is NOT copied to forked agents (stays in template only)
log_test "Script execute permissions"
scripts_with_exec=true
for script in scripts/context.sh; do
    if [[ -f "$script" ]] && [[ ! -x "$script" ]]; then
        log_fail "Missing execute permission: $script"
        scripts_with_exec=false
    fi
done
if $scripts_with_exec; then
    log_pass "Scripts have execute permissions"
fi

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "${RED}TESTS FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
fi
