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
#   --output <file>  Optional: write output to file instead of stdout
#   --run-id <id>    Optional: deterministic run ID for artifact storage
#                    If provided, writes to artifacts/proposals/<run-id>/proposal_set.json
#
# Output:
#   Validated ProposalSet JSON to stdout (or --output file)
#
# Exit codes:
#   0  Success (ProposalSet emitted, may have zero proposals)
#   1  Usage error or missing input
#   2  Internal error
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

# Defaults
INPUT_FILE=""
OUTPUT_FILE=""
RUN_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        -h|--help)
            head -40 "$0" | grep '^#' | sed 's/^# \?//'
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

# Handle output
if [[ -n "$OUTPUT_FILE" ]]; then
    echo "$PROPOSAL_JSON" > "$OUTPUT_FILE"
fi

# Handle run-id artifact storage
if [[ -n "$RUN_ID" ]]; then
    ARTIFACT_DIR="$REPO_ROOT/artifacts/proposals/$RUN_ID"
    mkdir -p "$ARTIFACT_DIR"
    echo "$PROPOSAL_JSON" > "$ARTIFACT_DIR/proposal_set.json"
fi

# Always output to stdout unless suppressed
if [[ -z "$OUTPUT_FILE" ]] || [[ -n "$RUN_ID" ]]; then
    echo "$PROPOSAL_JSON"
fi
