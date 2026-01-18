#!/usr/bin/env bash
#
# Phase M-1: Proposal Generation CLI
#
# Generates non-authoritative proposals from user input.
# This script is upstream-only and does NOT invoke PoC v2 execution.
#
# Usage:
#   ./scripts/generate_proposals.sh --input <file>
#   ./scripts/generate_proposals.sh --input -              # read from stdin
#   echo "restart alpha subsystem gracefully" | ./scripts/generate_proposals.sh --input -
#
# Options:
#   --input <file>   Input file path, or "-" for stdin (required)
#   --run-id <id>    Optional: deterministic run ID for artifact storage
#                    Writes to artifacts/proposals/<run-id>/proposal_set.json
#                    Allowed characters: A-Za-z0-9._- (max 64 chars)
#
# Output:
#   Validated ProposalSet JSON to stdout
#   If --run-id provided, also writes to artifacts/proposals/<run-id>/proposal_set.json
#
# Exit codes:
#   0  Success (ProposalSet emitted, may have zero proposals)
#   1  Usage error, invalid input, or path safety violation
#   2  Internal error
#
# Constraints:
#   - All generated outputs MUST live under artifacts/
#   - No absolute paths allowed for output
#   - No path traversal allowed
#
# Authority:
#   This script produces NON-AUTHORITATIVE proposals only.
#   Proposals do not imply execution outcomes or decisions.
#   Execution truth remains solely in stdout.raw.kv from PoC v2.
#

set -euo pipefail

# Resolve repository root (relative path safe)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROPOSAL_SRC="$REPO_ROOT/proposal/src"

# --- Path Safety Functions ---

# Validate run-id: only [A-Za-z0-9._-], max 64 chars
validate_run_id() {
    local run_id="$1"

    # Check empty
    if [[ -z "$run_id" ]]; then
        echo "Error: --run-id cannot be empty" >&2
        return 1
    fi

    # Check max length (64)
    if [[ ${#run_id} -gt 64 ]]; then
        echo "Error: --run-id exceeds maximum length of 64 characters" >&2
        return 1
    fi

    # Check allowed characters: A-Za-z0-9._-
    if [[ ! "$run_id" =~ ^[A-Za-z0-9._-]+$ ]]; then
        echo "Error: --run-id contains invalid characters. Allowed: A-Za-z0-9._-" >&2
        return 1
    fi

    return 0
}

# Defaults
INPUT_FILE=""
RUN_ID=""
RUN_ID_PROVIDED=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            RUN_ID_PROVIDED=true
            shift 2
            ;;
        -h|--help)
            head -45 "$0" | grep '^#' | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            echo "Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$INPUT_FILE" ]]; then
    echo "Error: --input is required" >&2
    echo "Use --help for usage information." >&2
    exit 1
fi

# Validate run-id if provided
if [[ "$RUN_ID_PROVIDED" == "true" ]]; then
    if ! validate_run_id "$RUN_ID"; then
        exit 1
    fi
fi

# Read input
if [[ "$INPUT_FILE" == "-" ]]; then
    INPUT_RAW="$(cat)"
else
    if [[ ! -f "$INPUT_FILE" ]]; then
        echo "Error: Input file not found: $INPUT_FILE" >&2
        exit 1
    fi
    INPUT_RAW="$(cat "$INPUT_FILE")"
fi

# Generate proposals using Python generator
PROPOSAL_JSON="$(cd "$REPO_ROOT" && python3 -c "
import sys
sys.path.insert(0, '${PROPOSAL_SRC}')
from generator import generate_proposal_set, proposal_set_to_json
from validator import validate_and_normalize

input_raw = sys.stdin.read()
proposal_set = generate_proposal_set(input_raw)
validated = validate_and_normalize(proposal_set)
print(proposal_set_to_json(validated))
" <<< "$INPUT_RAW")"

# Handle run-id artifact storage (only allowed output path)
if [[ -n "$RUN_ID" ]]; then
    # Path is guaranteed safe: artifacts/proposals/<validated-run-id>/proposal_set.json
    ARTIFACT_DIR="$REPO_ROOT/artifacts/proposals/$RUN_ID"
    mkdir -p "$ARTIFACT_DIR"
    echo "$PROPOSAL_JSON" > "$ARTIFACT_DIR/proposal_set.json"
fi

# Always output to stdout
echo "$PROPOSAL_JSON"
