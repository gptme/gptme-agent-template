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

    # Check common agent indicators
    local is_agent=false

    # Check 1: Agent-specific directories
    if [ -d "$HOME/bob" ] || [ -d "$HOME/alice" ]; then
        is_agent=true
    fi

    # Check 2: gptme.toml with agent configuration
    if [ -f "$DOTFILES_DIR/../gptme.toml" ]; then
        if grep -q '\[agent\]' "$DOTFILES_DIR/../gptme.toml" 2>/dev/null; then
            is_agent=true
        fi
    fi

    # Check 3: Running in VM (common for agents)
    if [ -f "/sys/class/dmi/id/chassis_type" ]; then
        chassis_type=$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo "")
        # Type 1 = Other/VM
        if [ "$chassis_type" = "1" ]; then
            is_agent=true
        fi
    fi

    # Check 4: Explicit agent username patterns
    if [[ "$USER" =~ ^(bob|alice|agent)$ ]]; then
        is_agent=true
    fi

    if [ "$is_agent" = false ]; then
        echo -e "${YELLOW}⚠️  Safety Warning: Agent environment not detected${NC}"
        echo ""
        echo "This script is designed for gptme agent workspaces."
        echo "It will modify global git configuration and may conflict"
        echo "with existing user configurations."
        echo ""
        echo "Indicators checked:"
        echo "  - Agent directories (~/bob, ~/alice): not found"
        echo "  - gptme.toml with [agent] section: not found"
        echo "  - VM chassis type: not detected"
        echo "  - Agent username pattern: '$USER' doesn't match"
        echo ""
        echo "To proceed anyway, run with:"
        echo "  DOTFILES_FORCE=1 $0"
        echo ""
        echo "Or confirm you want to install on this system:"
        read -p "Continue installation? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 1
        fi
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
