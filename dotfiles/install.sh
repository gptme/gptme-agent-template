#!/bin/bash
# Install dotfiles for gptme agent
# Creates symlinks for global git hooks and configuration

set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Installing dotfiles from $DOTFILES_DIR"

# Ensure target directories exist
mkdir -p ~/.config/git

# Symlink git hooks directory
if [ -L ~/.config/git/hooks ]; then
    echo "Removing existing symlink: ~/.config/git/hooks"
    rm ~/.config/git/hooks
fi
ln -sf "$DOTFILES_DIR/.config/git/hooks" ~/.config/git/hooks
echo "✓ Linked ~/.config/git/hooks -> $DOTFILES_DIR/.config/git/hooks"

# Configure git to use global hooks
git config --global core.hooksPath ~/.config/git/hooks
echo "✓ Set core.hooksPath to ~/.config/git/hooks"

# Set up template directory for pre-commit
git config --global init.templateDir ~/.git-templates
echo "✓ Set init.templateDir to ~/.git-templates"

echo ""
echo "✅ Dotfiles installed successfully!"
echo ""
echo "Global git hooks are now active:"
echo "  - pre-commit: Branch validation + pre-commit auto-staging"
echo "  - pre-push: Worktree tracking validation"
echo "  - post-checkout: Branch base warning on checkout"
echo ""
echo "Customize FORBIDDEN_PATTERNS in .config/git/hooks/pre-commit"
echo "to add repos where direct master commits should be blocked."
