#!/bin/bash
set -euo pipefail

# Get ISO 8601 datetime with seconds with support for BSD date (MacOS)
iso_datetime() {
  date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z"
}

# Default options: everything included
WITH_DOTFILES=false
WITH_AUTONOMOUS=true
WITH_PEOPLE=true
WITH_PROJECTS=true
WITH_STATE=true

# Two-pass parsing: process --minimal first so --with-* flags override it
# regardless of argument order (e.g. --with-autonomous --minimal works)
for arg in "$@"; do
    if [[ "$arg" == "--minimal" ]]; then
        WITH_AUTONOMOUS=false
        WITH_PEOPLE=false
        WITH_PROJECTS=false
        WITH_STATE=false
        break
    fi
done

# Parse options (second pass: --with-* and --without-* override --minimal)
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-dotfiles)
            WITH_DOTFILES=true
            shift
            ;;
        --with-autonomous)
            WITH_AUTONOMOUS=true
            shift
            ;;
        --without-autonomous)
            WITH_AUTONOMOUS=false
            shift
            ;;
        --with-people)
            WITH_PEOPLE=true
            shift
            ;;
        --without-people)
            WITH_PEOPLE=false
            shift
            ;;
        --with-projects)
            WITH_PROJECTS=true
            shift
            ;;
        --without-projects)
            WITH_PROJECTS=false
            shift
            ;;
        --with-state)
            WITH_STATE=true
            shift
            ;;
        --without-state)
            WITH_STATE=false
            shift
            ;;
        --minimal)
            # Already handled in first pass
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] <new_agent_workspace> [<new_agent_name>]"
            echo ""
            echo "Create a new agent workspace from the template."
            echo ""
            echo "Arguments:"
            echo "  <new_agent_workspace>  Path for the new agent workspace"
            echo "  [<new_agent_name>]     Optional: Agent name (defaults to directory name)"
            echo ""
            echo "Options:"
            echo "  --minimal              Minimal agent (journal, tasks, knowledge, lessons only)"
            echo "  --without-autonomous   Exclude autonomous run scripts"
            echo "  --without-people       Exclude people directory and templates"
            echo "  --without-projects     Exclude projects directory"
            echo "  --without-state        Exclude state/queue system"
            echo "  --with-autonomous      Include autonomous run scripts (use with --minimal, any order)"
            echo "  --with-people          Include people directory (use with --minimal, any order)"
            echo "  --with-projects        Include projects directory (use with --minimal, any order)"
            echo "  --with-state           Include state/queue system (use with --minimal, any order)"
            echo "  --with-dotfiles        Include dotfiles (global git hooks)"
            echo "  --help, -h             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 alice-agent Alice                             # Full-featured agent"
            echo "  $0 --minimal simple-bot SimpleBot                # Minimal agent"
            echo "  $0 --minimal --with-state ./bob Bob             # Minimal + state/queues"
            echo "  $0 --minimal --with-autonomous ./bob Bob        # Minimal + autonomous runs"
            echo "  $0 --without-autonomous ./bob Bob               # No autonomous runs"
            echo "  $0 --with-dotfiles ./bob Bob                    # Include git hooks"
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Check arguments
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 [OPTIONS] <new_agent_workspace> [<new_agent_name>]"
    echo "Example: $0 alice-agent Alice"
    echo "Use --help for more options."
    exit 1
fi



# Get the directory containing this script
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$1"

# If target starts with ~, expand it
if [[ "$TARGET_DIR" == ~* ]]; then
    TARGET_DIR="${TARGET_DIR/#~/$HOME}"
fi

# If target is not an absolute path and doesn't start with ./ or ../
if [[ "$TARGET_DIR" != /* ]] && [[ "$TARGET_DIR" != ./* ]] && [[ "$TARGET_DIR" != ../* ]]; then
    TARGET_DIR="$(realpath .)/${TARGET_DIR}"
fi

# Create parent directories if needed
mkdir -p "$(dirname "$TARGET_DIR")"

# If a name is provided, use it
# Else, extract agent name from the last directory component, whether it has -agent suffix or not
NEW_AGENT="${2:-$(basename "$TARGET_DIR" | sed 's/-agent$//')}"
# Name of agent in template, to be replaced
NAME_TEMPLATE="gptme-agent"

# Check if directory exists
if [ -d "$TARGET_DIR" ]; then
    # Check if directory is empty
    if [ -n "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]; then
        echo "Error: Target directory exists and is not empty: $TARGET_DIR"
        exit 1
    fi
    echo "Warning: Target directory exists but is empty, continuing..."
fi

echo -e "\nCreating new agent '$NEW_AGENT' in directory '$TARGET_DIR'..."

# Create core directory structure
echo "Creating directory structure..."
mkdir -p "${TARGET_DIR}"/{journal,tasks/templates,knowledge,lessons,scripts}
[ "$WITH_PROJECTS" = true ] && mkdir -p "${TARGET_DIR}/projects"
[ "$WITH_PEOPLE" = true ] && mkdir -p "${TARGET_DIR}/people/templates"
[ "$WITH_STATE" = true ] && mkdir -p "${TARGET_DIR}/state"

# Copy core files and directories
echo "Copying core files..."

function copy_file() {
    local src="${SOURCE_DIR}/$1"
    local dst="${TARGET_DIR}/$1"

    # Create target directory if copying a directory
    if [ -d "$src" ]; then
        mkdir -p "$dst"
        cp -r "$src/"* "$dst/"
    else
        # Ensure parent directory exists for files
        mkdir -p "$(dirname "$dst")"
        cp -r "$src" "$dst"
    fi

    # Process all files, whether dst is a file or directory
    find "$dst" -type f -print0 | while IFS= read -r -d '' file; do
        # Strip template sections FIRST (before name replacement)
        # This prevents replacing "gptme-agent" in template-only content
        # (e.g. CLI tool references like "gptme-agent create" that should not be renamed)
        perl -i -pe 'BEGIN{undef $/;} s/<!--template-->.*?<!--\/template-->\n?//gs' "$file"
        # Replace template strings in remaining content
        perl -i -pe "s/${NAME_TEMPLATE}-template/${NEW_AGENT}/g" "$file"
        perl -i -pe "s/${NAME_TEMPLATE}/${NEW_AGENT}/g" "$file"
        # Collapse 3+ consecutive blank lines to 2 (cleanup after template stripping)
        perl -i -pe 'BEGIN{undef $/;} s/\n{4,}/\n\n\n/gs' "$file"
    done

    # Make shell scripts executable
    find "$dst" -type f -name "*.sh" -exec chmod +x {} \;
}

function copy_files() {
    for file in "$@"; do
        copy_file "$file"
    done
}

# Core documentation and configuration (always included)
copy_file README.md
cp "${SOURCE_DIR}/Makefile" "${TARGET_DIR}/Makefile"  # copy without replacing NAME_TEMPLATE
copy_file ABOUT.md
copy_file ARCHITECTURE.md
copy_file TOOLS.md
copy_file TASKS.md
copy_file gptme.toml
copy_file .pre-commit-config.yaml
copy_file .gitignore
copy_file .gitmodules

# Core scripts (context generation is always needed)
# Copy scripts directory, then optionally remove autonomous runs
copy_file scripts

if [ "$WITH_AUTONOMOUS" = false ]; then
    echo "  Skipping: autonomous run scripts"
    rm -rf "${TARGET_DIR}/scripts/runs"
    # Create stub so doc links resolve
    mkdir -p "${TARGET_DIR}/scripts/runs/autonomous"
    {
        echo "# Autonomous Runs (not included)"
        echo ""
        echo "This agent was created without autonomous run infrastructure."
        echo "To add it, re-fork without \`--without-autonomous\`, or copy from the template."
    } > "${TARGET_DIR}/scripts/runs/autonomous/README.md"
    # Strip autonomous sections from README
    perl -i -0pe 's/<!--autonomous-->.*?<!--\/autonomous-->\n?//gs' "${TARGET_DIR}/README.md"
fi

# Copy base knowledge
copy_file knowledge/agent-forking.md
copy_file knowledge/forking-workspace.md

# Copy lessons (always included — core learning system)
copy_file lessons/README.md
copy_file lessons/TEMPLATE.md
copy_file lessons/tools/shell-heredoc.md

# Optional: state/queue system
if [ "$WITH_STATE" = true ]; then
    copy_file state
else
    echo "  Skipping: state/queue system"
    # Create stub so doc links resolve
    mkdir -p "${TARGET_DIR}/state"
    {
        echo "# State (not included)"
        echo ""
        echo "This agent was created without the state/queue system."
        echo "To add it, re-fork without the \`--without-state\` flag, or copy from the template."
    } > "${TARGET_DIR}/state/README.md"
    # Strip state sections from README
    perl -i -0pe 's/<!--state-->.*?<!--\/state-->\n?//gs' "${TARGET_DIR}/README.md"
fi

# Optional: projects directory
if [ "$WITH_PROJECTS" = true ]; then
    copy_file projects/README.md
else
    echo "  Skipping: projects directory"
    # Create stub so gptme.toml reference to projects/README.md doesn't fail
    mkdir -p "${TARGET_DIR}/projects"
    {
        echo "# Projects (not included)"
        echo ""
        echo "This agent was created without the projects directory."
        echo "To add it, re-fork without the \`--without-projects\` flag, or copy from the template."
    } > "${TARGET_DIR}/projects/README.md"
fi

# Optional: people directory
if [ "$WITH_PEOPLE" = true ]; then
    copy_file people/templates/person.md
else
    echo "  Skipping: people directory"
    # Create stub so doc links resolve
    mkdir -p "${TARGET_DIR}/people"
    {
        echo "# People (not included)"
        echo ""
        echo "This agent was created without the people directory."
        echo "To add it, re-fork without the \`--without-people\` flag, or copy from the template."
    } > "${TARGET_DIR}/people/README.md"
    # Strip people sections from README
    perl -i -0pe 's/<!--people-->.*?<!--\/people-->\n?//gs' "${TARGET_DIR}/README.md"
fi

# Clean up remaining conditional comment tags (keep content, remove markers)
perl -i -pe 's/<!--(?:autonomous|people|state|projects)-->//g; s/<!--\/(?:autonomous|people|state|projects)-->//g' "${TARGET_DIR}/README.md"

# Copy templates (always included)
copy_file journal/templates/daily.md
copy_file tasks/templates/initial-agent-setup.md

# Initialize git
(cd "${TARGET_DIR}" && git init)

# Clone and initialize the gptme-contrib submodule
(cd "${TARGET_DIR}" && git submodule add https://github.com/gptme/gptme-contrib.git gptme-contrib)
(cd "${TARGET_DIR}" && git submodule update --init --recursive)

# Setup dotfiles if requested
if [ "$WITH_DOTFILES" = true ]; then
    echo "Setting up dotfiles with symlinks to gptme-contrib..."

    # Create dotfiles directory structure
    mkdir -p "${TARGET_DIR}/dotfiles/.config/git/hooks"

    # Create symlinks to individual files (allows selective ejection)
    ln -sf ../gptme-contrib/dotfiles/install.sh "${TARGET_DIR}/dotfiles/install.sh"
    ln -sf ../gptme-contrib/dotfiles/README.md "${TARGET_DIR}/dotfiles/README.md"
    ln -sf ../../../../gptme-contrib/dotfiles/.config/git/hooks/pre-commit "${TARGET_DIR}/dotfiles/.config/git/hooks/pre-commit"
    ln -sf ../../../../gptme-contrib/dotfiles/.config/git/hooks/pre-push "${TARGET_DIR}/dotfiles/.config/git/hooks/pre-push"
    ln -sf ../../../../gptme-contrib/dotfiles/.config/git/hooks/post-checkout "${TARGET_DIR}/dotfiles/.config/git/hooks/post-checkout"
    ln -sf ../../../../gptme-contrib/dotfiles/.config/git/hooks/validate-branch-base.sh "${TARGET_DIR}/dotfiles/.config/git/hooks/validate-branch-base.sh"
    ln -sf ../../../../gptme-contrib/dotfiles/.config/git/hooks/validate-worktree-tracking.sh "${TARGET_DIR}/dotfiles/.config/git/hooks/validate-worktree-tracking.sh"

    echo "✓ Dotfiles symlinks created (use dotfiles/install.sh to activate)"
fi

# Create initial setup task from template
cp "${TARGET_DIR}/tasks/templates/initial-agent-setup.md" "${TARGET_DIR}/tasks/"
# Set creation timestamp if gptodo is available (optional tool)
if command -v gptodo > /dev/null 2>&1; then
    (cd "${TARGET_DIR}" && gptodo edit initial-agent-setup --set created "$(iso_datetime)")
else
    echo "Note: gptodo not installed - skipping timestamp update"
    echo "Install with: uv tool install git+https://github.com/gptme/gptme-contrib#subdirectory=packages/gptodo"
fi

# If pre-commit is installed
# Install pre-commit hooks (may fail if core.hooksPath is set)
# shellcheck disable=SC2015  # A && B || C is intentional: ignore install failure
command -v pre-commit > /dev/null && (cd "${TARGET_DIR}" && pre-commit install) || true

# Stage files first, then run pre-commit to format them
(cd "${TARGET_DIR}" && git add .)

# Run pre-commit to format staged files, then restage any changes
if command -v pre-commit > /dev/null; then
    # shellcheck disable=SC2015  # pre-commit run failures are intentionally swallowed
    (cd "${TARGET_DIR}" && pre-commit run || true)
    (cd "${TARGET_DIR}" && git add .)
fi

# Commit initial files (--no-verify: hooks may require tools like uv not yet available;
# the explicit pre-commit run above already handled formatting)
(cd "${TARGET_DIR}" && git commit --no-verify -m "feat: initialize ${NEW_AGENT} agent workspace")

# Make the target directory relative to the current directory (prettier output)
TARGET_DIR_RELATIVE=$(python3 -c "import os, sys; print(os.path.relpath('${TARGET_DIR}', start='$(pwd)'))")

# Build success message
EXTRAS_MSG=""
if [ "$WITH_DOTFILES" = true ]; then
    EXTRAS_MSG="${EXTRAS_MSG}
Dotfiles included! To activate git hooks:
  cd ${TARGET_DIR_RELATIVE}/dotfiles && ./install.sh
"
fi

# Show what systems were included
SYSTEMS_INCLUDED="journal, tasks, knowledge, lessons"
[ "$WITH_STATE" = true ] && SYSTEMS_INCLUDED="${SYSTEMS_INCLUDED}, state/queues"
[ "$WITH_AUTONOMOUS" = true ] && SYSTEMS_INCLUDED="${SYSTEMS_INCLUDED}, autonomous runs"
[ "$WITH_PEOPLE" = true ] && SYSTEMS_INCLUDED="${SYSTEMS_INCLUDED}, people"
[ "$WITH_PROJECTS" = true ] && SYSTEMS_INCLUDED="${SYSTEMS_INCLUDED}, projects"
[ "$WITH_DOTFILES" = true ] && SYSTEMS_INCLUDED="${SYSTEMS_INCLUDED}, dotfiles"

echo "
Agent workspace created successfully!

Systems included: ${SYSTEMS_INCLUDED}

Next steps:
1. cd ${TARGET_DIR_RELATIVE}
2. Start the agent with: gptme \"hello\"
3. The agent will guide you through the setup interview
4. Follow the agent's instructions to establish its identity
${EXTRAS_MSG}
The new agent workspace is ready in: ${TARGET_DIR}"
