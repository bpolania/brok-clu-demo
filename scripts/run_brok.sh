#!/usr/bin/env bash
#
# Phase M-2: Brok-CLU Orchestration Pipeline
#
# Orchestrates the full pipeline: proposals -> artifact -> optional execution.
# Does NOT modify any frozen runtime scripts.
#
# Usage:
#   ./scripts/run_brok.sh --input <file> --run-id <id>
#
# Options:
#   --input <file>       Input file path (required)
#   --run-id <id>        Run identifier (required)
#                        Allowed characters: A-Za-z0-9._- (max 64 chars)
#   --print-proposals    Print proposal_set.json to stdout
#   --print-artifact     Print artifact.json to stdout
#
# Pipeline steps:
#   1. Generate proposals (M-1): scripts/generate_proposals.sh
#   2. Build artifact (M-2): scripts/build_artifact.sh
#   3. If ACCEPT: invoke scripts/run_poc_v2.sh
#   4. If REJECT: print decision and exit 0 (no execution)
#
# Exit codes:
#   0  Pipeline completed (REJECT or ACCEPT with successful execution)
#   1  Usage error or path safety violation
#   N  Propagated exit code from run_poc_v2.sh (if ACCEPT)
#
# Constraints:
#   - Does NOT parse stdout.raw.kv
#   - Does NOT infer outcomes from PoC output
#   - Uses artifact only as gating decision record
#
# Authority:
#   Artifacts are wrapper-level decision records.
#   Execution truth remains solely in stdout.raw.kv from PoC v2.
#

set -euo pipefail

# Resolve repository root (relative path safe)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Path Safety Functions ---

# Validate run-id: only [A-Za-z0-9._-], max 64 chars
validate_run_id() {
    local run_id="$1"

    if [[ -z "$run_id" ]]; then
        echo "Error: --run-id cannot be empty" >&2
        return 1
    fi

    if [[ ${#run_id} -gt 64 ]]; then
        echo "Error: --run-id exceeds maximum length of 64 characters" >&2
        return 1
    fi

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
PRINT_PROPOSALS=false
PRINT_ARTIFACT=false

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
        --print-proposals)
            PRINT_PROPOSALS=true
            shift
            ;;
        --print-artifact)
            PRINT_ARTIFACT=true
            shift
            ;;
        -h|--help)
            head -50 "$0" | grep '^#' | sed 's/^# \?//'
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
    exit 1
fi

if [[ "$RUN_ID_PROVIDED" != "true" ]]; then
    echo "Error: --run-id is required" >&2
    exit 1
fi

if ! validate_run_id "$RUN_ID"; then
    exit 1
fi

# Check input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file not found: $INPUT_FILE" >&2
    exit 1
fi

# Compute repo-relative input_ref
INPUT_ABS="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"
if [[ "$INPUT_ABS" == "$REPO_ROOT"/* ]]; then
    INPUT_REF="${INPUT_ABS#$REPO_ROOT/}"
else
    # Use absolute path as-is for external files (will be recorded)
    INPUT_REF="$INPUT_FILE"
fi

# === Step 1: Generate Proposals (M-1) ===
echo "=== Step 1: Generating proposals ===" >&2

PROPOSAL_DIR="$REPO_ROOT/artifacts/proposals/$RUN_ID"
mkdir -p "$PROPOSAL_DIR"

# Run proposal generator
"$SCRIPT_DIR/generate_proposals.sh" --input "$INPUT_FILE" --run-id "$RUN_ID" > /dev/null

PROPOSAL_SET_PATH="$PROPOSAL_DIR/proposal_set.json"

if [[ ! -f "$PROPOSAL_SET_PATH" ]]; then
    echo "Error: Proposal generation failed - no proposal_set.json created" >&2
    exit 1
fi

if [[ "$PRINT_PROPOSALS" == "true" ]]; then
    cat "$PROPOSAL_SET_PATH"
fi

echo "  proposals: $PROPOSAL_SET_PATH" >&2

# === Step 2: Build Artifact (M-2) ===
echo "=== Step 2: Building artifact ===" >&2

ARTIFACT_JSON="$("$SCRIPT_DIR/build_artifact.sh" \
    --proposal-set "$PROPOSAL_SET_PATH" \
    --run-id "$RUN_ID" \
    --input-ref "$INPUT_REF")"

ARTIFACT_PATH="$REPO_ROOT/artifacts/artifacts/$RUN_ID/artifact.json"

if [[ ! -f "$ARTIFACT_PATH" ]]; then
    echo "Error: Artifact build failed - no artifact.json created" >&2
    exit 1
fi

if [[ "$PRINT_ARTIFACT" == "true" ]]; then
    echo "$ARTIFACT_JSON"
fi

echo "  artifact: $ARTIFACT_PATH" >&2

# Extract decision from artifact JSON
DECISION="$(echo "$ARTIFACT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['decision'])")"

# === Step 3: Execute based on decision ===
if [[ "$DECISION" == "REJECT" ]]; then
    # Extract reason_code
    REASON_CODE="$(echo "$ARTIFACT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['reject_payload']['reason_code'])")"

    echo "=== Decision: REJECT ===" >&2
    echo "decision=REJECT reason_code=$REASON_CODE"
    echo "  No PoC v2 execution (artifact gating)" >&2
    exit 0

elif [[ "$DECISION" == "ACCEPT" ]]; then
    echo "=== Decision: ACCEPT ===" >&2
    echo "  Invoking PoC v2 execution..." >&2

    # Invoke run_poc_v2.sh with the input file
    # This script creates its own timestamped run directory
    set +e
    "$SCRIPT_DIR/run_poc_v2.sh" --input "$INPUT_FILE"
    POC_EXIT_CODE=$?
    set -e

    echo "decision=ACCEPT"

    # Exit with same code as PoC v2
    exit $POC_EXIT_CODE
else
    echo "Error: Unknown decision in artifact: $DECISION" >&2
    exit 1
fi
