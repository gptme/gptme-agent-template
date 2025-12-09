#!/bin/bash
# Install dotfiles for gptme agent
# Creates symlinks for global git hooks and configuration
#
# Safety: This script includes checks to prevent accidentally running
# on non-agent systems and overwriting user configurations.

set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Safety Check: Detect if running on agent system ---
# Override with DOTFILES_FORCE=1 to bypass safety check
check_agent_environment() {
    # If forced, skip check
    if [ "$DOTFILES_FORCE" = "1" ]; then
        echo -e "${YELLOW}⚠️  Safety check bypassed (DOTFILES_FORCE=1)${NC}"
        return 0
    fi

    # Check for GPTME_AGENT environment variable (set by agent dotfiles)
    if [ -n "$GPTME_AGENT" ]; then
        return 0
    fi

    # Check reliable agent indicators
    local is_agent=false
    local indicators_found=""

    # Check 1: gptme.toml with agent configuration (most reliable)
    if [ -f "$DOTFILES_DIR/../gptme.toml" ]; then
        if grep -q '\[agent\]' "$DOTFILES_DIR/../gptme.toml" 2>/dev/null; then
            is_agent=true
            indicators_found="${indicators_found}  ✓ gptme.toml with [agent] section\n"
        fi
    fi

    # Check 2: Agent autonomous service running (very specific to agents)
    if systemctl --user is-active '*-autonomous.service' &>/dev/null || \
       systemctl --user list-units --type=service --all 2>/dev/null | grep -q 'autonomous.service'; then
        is_agent=true
        indicators_found="${indicators_found}  ✓ Agent autonomous service detected\n"
    fi

    # Check 3: Running in VM (common for agents, but not definitive)
    if [ -f "/sys/class/dmi/id/chassis_type" ]; then
        chassis_type=$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo "")
        # Type 1 = Other/VM
        if [ "$chassis_type" = "1" ]; then
            # VM alone is not sufficient, but contributes to detection
            indicators_found="${indicators_found}  ~ VM environment (chassis_type=1)\n"
        fi
    fi

    if [ "$is_agent" = false ]; then
        echo -e "${YELLOW}⚠️  Safety Warning: Agent environment not detected${NC}"
        echo ""
        echo "This script is designed for gptme agent workspaces."
        echo "It will modify global git configuration and may conflict"
        echo "with existing user configurations."
        echo ""
        echo "Indicators checked:"
        echo "  - gptme.toml with [agent] section: not found"
        echo "  - Agent autonomous service (*-autonomous.service): not found"
        echo "  - GPTME_AGENT environment variable: not set"
        echo ""
        echo "To proceed anyway, set environment variable:"
        echo "  GPTME_AGENT=1 $0"
        echo ""
        echo "Or force installation:"
        echo "  DOTFILES_FORCE=1 $0"
        echo ""
        echo "Or confirm you want to install on this system:"
        read -p "Continue installation? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Agent environment detected:${NC}"
        echo -e "$indicators_found"
    fi
}

# --- Handle existing hooks directory ---
handle_existing_hooks_dir() {
    local target="$HOME/.config/git/hooks"

    if [ -L "$target" ]; then
        # Existing symlink - remove and recreate
        echo "Removing existing symlink: $target"
        rm "$target"
    elif [ -d "$target" ]; then
        # Existing directory (not symlink) - back up
        local backup="$target.backup.$(date +%Y%m%d-%H%M%S)"
        echo -e "${YELLOW}⚠️  Existing hooks directory found (not a symlink)${NC}"
        echo "   Backing up to: $backup"
        mv "$target" "$backup"
    elif [ -e "$target" ]; then
        # Something else exists - error
        echo -e "${RED}❌ ERROR: $target exists but is not a directory or symlink${NC}"
        exit 1
    fi
}

# --- Main installation ---
echo "Installing dotfiles from $DOTFILES_DIR"
echo ""

# Run safety check
check_agent_environment

# Ensure target directories exist
mkdir -p ~/.config/git

# Handle existing hooks directory
handle_existing_hooks_dir

# Symlink git hooks directory
ln -sf "$DOTFILES_DIR/.config/git/hooks" ~/.config/git/hooks
echo -e "${GREEN}✓${NC} Linked ~/.config/git/hooks -> $DOTFILES_DIR/.config/git/hooks"

# Configure git to use global hooks
git config --global core.hooksPath ~/.config/git/hooks
echo -e "${GREEN}✓${NC} Set core.hooksPath to ~/.config/git/hooks"

# Set up template directory for pre-commit (create if needed)
mkdir -p ~/.git-templates
git config --global init.templateDir ~/.git-templates
echo -e "${GREEN}✓${NC} Set init.templateDir to ~/.git-templates"

echo ""
echo -e "${GREEN}✅ Dotfiles installed successfully!${NC}"
echo ""
echo "Global git hooks are now active:"
echo "  - pre-commit: Branch validation + pre-commit auto-staging"
echo "  - pre-push: Worktree tracking validation"
echo "  - post-checkout: Branch base warning on checkout"
echo ""
echo "Customize FORBIDDEN_PATTERNS in .config/git/hooks/pre-commit"
echo "to add repos where direct master commits should be blocked."
