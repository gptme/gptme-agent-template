#!/usr/bin/env bash
# install-deps.sh - Check and install dependencies for gptme-agent-template
# Run this BEFORE forking to ensure all prerequisites are installed.
#
# Usage:
#   ./install-deps.sh          # Check all dependencies
#   ./install-deps.sh --install # Auto-install where possible

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_MODE=false
if [[ "$1" == "--install" ]]; then
    INSTALL_MODE=true
fi

echo -e "${BLUE}=== gptme-agent-template Dependency Check ===${NC}"
echo ""

# Track missing deps
MISSING=()

# Function to check if command exists
check_cmd() {
    local cmd=$1
    local name=${2:-$1}
    local install_hint=$3

    if command -v "$cmd" &> /dev/null; then
        local version=$("$cmd" --version 2>/dev/null | head -1 || echo "installed")
        echo -e "${GREEN}✓${NC} $name: $version"
        return 0
    else
        echo -e "${RED}✗${NC} $name: not found"
        if [[ -n "$install_hint" ]]; then
            echo -e "  ${YELLOW}→ $install_hint${NC}"
        fi
        MISSING+=("$name")
        return 1
    fi
}

# Detect OS for install hints
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/fedora-release ]]; then
        echo "fedora"
    elif [[ -f /etc/arch-release ]]; then
        echo "arch"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

echo -e "${BLUE}Detected OS:${NC} $OS"
echo ""
echo -e "${BLUE}Required Dependencies:${NC}"
echo ""

# Core tools
check_cmd "git" "git" "Install via package manager"
check_cmd "python3" "python3" "Install Python 3.10+"

# Python package managers
if ! check_cmd "pipx" "pipx" "python3 -m pip install --user pipx"; then
    if $INSTALL_MODE; then
        echo -e "${YELLOW}Installing pipx...${NC}"
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
    fi
fi

if ! check_cmd "uv" "uv" "curl -LsSf https://astral.sh/uv/install.sh | sh"; then
    if $INSTALL_MODE; then
        echo -e "${YELLOW}Installing uv...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
fi

# gptme
if ! check_cmd "gptme" "gptme" "pipx install gptme[server,browser,telemetry]"; then
    if $INSTALL_MODE; then
        echo -e "${YELLOW}Installing gptme...${NC}"
        pipx install gptme[server,browser,telemetry]
    fi
fi

# Optional but recommended
echo ""
echo -e "${BLUE}Recommended Dependencies:${NC}"
echo ""

case $OS in
    macos)
        check_cmd "tree" "tree" "brew install tree"
        check_cmd "jq" "jq" "brew install jq"
        check_cmd "gh" "GitHub CLI" "brew install gh"
        ;;
    debian)
        check_cmd "tree" "tree" "sudo apt install tree"
        check_cmd "jq" "jq" "sudo apt install jq"
        check_cmd "gh" "GitHub CLI" "See https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
        ;;
    fedora)
        check_cmd "tree" "tree" "sudo dnf install tree"
        check_cmd "jq" "jq" "sudo dnf install jq"
        check_cmd "gh" "GitHub CLI" "sudo dnf install gh"
        ;;
    arch)
        check_cmd "tree" "tree" "sudo pacman -S tree"
        check_cmd "jq" "jq" "sudo pacman -S jq"
        check_cmd "gh" "GitHub CLI" "sudo pacman -S github-cli"
        ;;
    *)
        check_cmd "tree" "tree" "Install via package manager"
        check_cmd "jq" "jq" "Install via package manager"
        check_cmd "gh" "GitHub CLI" "See https://cli.github.com/"
        ;;
esac

if ! check_cmd "pre-commit" "pre-commit" "pipx install pre-commit"; then
    if $INSTALL_MODE; then
        echo -e "${YELLOW}Installing pre-commit...${NC}"
        pipx install pre-commit
    fi
fi

# Summary
echo ""
echo -e "${BLUE}==============================${NC}"

if [[ ${#MISSING[@]} -eq 0 ]]; then
    echo -e "${GREEN}All dependencies installed!${NC}"
    echo ""
    echo "You're ready to fork. Run:"
    echo "  ./fork.sh <path> [<agent-name>]"
    exit 0
else
    echo -e "${YELLOW}Missing ${#MISSING[@]} dependencies:${NC} ${MISSING[*]}"
    echo ""
    if $INSTALL_MODE; then
        echo "Some dependencies were auto-installed. Please restart your shell and re-run this script."
    else
        echo "Run with --install to auto-install where possible:"
        echo "  ./install-deps.sh --install"
    fi
    exit 1
fi
