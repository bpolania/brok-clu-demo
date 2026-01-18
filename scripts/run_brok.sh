#!/usr/bin/env bash
#
# Brok-CLU Pipeline (Legacy Shell Wrapper)
#
# This script is maintained for backward compatibility.
# All invocations are routed through the M-3 Python orchestrator.
#
# Usage:
#   ./scripts/run_brok.sh --input <file> --run-id <id>
#
# For the canonical CLI, use:
#   ./brok --input <file> [--run-id <id>]
#
# Note: The --print-proposals and --print-artifact flags are no longer
# supported. Use the canonical ./brok CLI which provides structured
# output with authority boundary labels.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check for deprecated flags
for arg in "$@"; do
    case "$arg" in
        --print-proposals|--print-artifact)
            echo "Warning: $arg is deprecated. Use ./brok for structured output." >&2
            ;;
    esac
done

# Filter out deprecated flags and pass remaining args to M-3 orchestrator
FILTERED_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --print-proposals|--print-artifact)
            shift
            ;;
        *)
            FILTERED_ARGS+=("$1")
            shift
            ;;
    esac
done

# Route through M-3 orchestrator
exec python3 "$REPO_ROOT/m3/src/orchestrator.py" \
    --repo-root "$REPO_ROOT" \
    "${FILTERED_ARGS[@]}"
