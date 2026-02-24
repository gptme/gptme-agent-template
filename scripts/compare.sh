#!/usr/bin/env bash
set -euo pipefail

# Compare this template harness to an existing agent workspace.
#
# Usage:
#   ./scripts/compare.sh <path_to_agent>
#   ./scripts/compare.sh --markdown <path_to_agent>
#
# Exit codes:
#   0: no differences
#   1: differences found
#   2: usage or path error

MARKDOWN=false

POSITIONAL=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --markdown)
            MARKDOWN=true
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Compare template harness files against an existing agent workspace.

Usage:
  ./scripts/compare.sh [--markdown] <path_to_agent>

Options:
  --markdown   Print each diff as a fenced code block for easy sharing
  -h, --help   Show this help

Examples:
  ./scripts/compare.sh ~/my-agent
  ./scripts/compare.sh --markdown ~/my-agent
  ./scripts/compare.sh ~/my-agent --markdown
EOF
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            exit 2
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

if [[ ${#POSITIONAL[@]} -ne 1 ]]; then
    echo "Usage: ./scripts/compare.sh [--markdown] <path_to_agent>" >&2
    exit 2
fi

TEMPLATE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_PATH="${POSITIONAL[0]}"

if [[ "$AGENT_PATH" == ~* ]]; then
    AGENT_PATH="${AGENT_PATH/#~/$HOME}"
fi

if [[ ! -d "$AGENT_PATH" ]]; then
    echo "Error: Agent path does not exist: $AGENT_PATH" >&2
    exit 2
fi

if command -v realpath >/dev/null 2>&1; then
    AGENT_PATH="$(realpath "$AGENT_PATH")"
fi

# Files/directories intended to stay mostly shared between template and forks.
# Keep identity/docs (ABOUT, README, journal, tasks content) out of this list.
declare -a HARNESS_PATHS=(
    "ARCHITECTURE.md"
    "TASKS.md"
    "TOOLS.md"
    ".pre-commit-config.yaml"
    "scripts"
)

found_diff=false

print_diff() {
    local relpath="$1"
    local left="$2"
    local right="$3"

    if [[ "$MARKDOWN" == true ]]; then
        echo
        echo '```shell'
        echo "diff -u -r '$left' '$right'"
        diff -u -r "$left" "$right" || true
        echo '```'
        echo
    else
        echo
        echo "=== $relpath ==="
        diff -u -r "$left" "$right" || true
    fi
}

echo "Comparing template harness at: $TEMPLATE_ROOT"
echo "Against agent workspace at:  $AGENT_PATH"

for rel in "${HARNESS_PATHS[@]}"; do
    left="$TEMPLATE_ROOT/$rel"
    right="$AGENT_PATH/$rel"

    if [[ ! -e "$left" ]]; then
        echo "Warning: Missing in template, skipping: $rel"
        continue
    fi

    if [[ ! -e "$right" ]]; then
        found_diff=true
        echo "Missing in agent: $rel"
        continue
    fi

    if ! diff -q -r "$left" "$right" >/dev/null 2>&1; then
        found_diff=true
        print_diff "$rel" "$left" "$right"
    fi
done

if [[ "$found_diff" == false ]]; then
    echo "No harness differences found."
    exit 0
fi

echo
cat <<EOF
Differences found.

Suggested next step:
- Keep agent-specific changes in the agent workspace.
- Upstream generic improvements to gptme-agent-template.
- Re-run this script after syncing to verify drift is resolved.
EOF

exit 1
