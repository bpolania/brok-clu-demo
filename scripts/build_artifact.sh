#!/usr/bin/env bash
#
# Phase M-2: Artifact Builder CLI
#
# Builds an authoritative wrapper-level decision record (Artifact) from
# a non-authoritative ProposalSet (M-1 output).
#
# Usage:
#   ./scripts/build_artifact.sh --proposal-set <path> --run-id <id> --input-ref <path>
#
# Options:
#   --proposal-set <path>  Path to proposal_set.json (required)
#   --run-id <id>          Run identifier (required)
#                          Allowed characters: A-Za-z0-9._- (max 64 chars)
#   --input-ref <path>     Repo-relative path to input file (required)
#
# Output:
#   Artifact JSON to stdout
#   If --run-id provided, also writes to artifacts/artifacts/<run-id>/artifact.json
#
# Exit codes:
#   0  Success (Artifact emitted, decision may be ACCEPT or REJECT)
#   1  Usage error, invalid arguments, or path safety violation
#   2  Internal error
#
# Constraints:
#   - All generated outputs MUST live under artifacts/
#   - No absolute paths allowed in artifact content
#   - No timestamps in artifact content
#
# Authority:
#   Artifacts are wrapper-level decision records only.
#   They do NOT override execution truth (stdout.raw.kv remains authoritative).
#

set -euo pipefail

# Resolve repository root (relative path safe)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARTIFACT_SRC="$REPO_ROOT/artifact/src"

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
PROPOSAL_SET=""
RUN_ID=""
INPUT_REF=""
RUN_ID_PROVIDED=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --proposal-set)
            PROPOSAL_SET="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            RUN_ID_PROVIDED=true
            shift 2
            ;;
        --input-ref)
            INPUT_REF="$2"
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
if [[ -z "$PROPOSAL_SET" ]]; then
    echo "Error: --proposal-set is required" >&2
    exit 1
fi

if [[ -z "$INPUT_REF" ]]; then
    echo "Error: --input-ref is required" >&2
    exit 1
fi

if [[ "$RUN_ID_PROVIDED" != "true" ]]; then
    echo "Error: --run-id is required" >&2
    exit 1
fi

# Validate run-id
if ! validate_run_id "$RUN_ID"; then
    exit 1
fi

# Check proposal-set file exists
if [[ ! -f "$PROPOSAL_SET" ]]; then
    echo "Error: Proposal set file not found: $PROPOSAL_SET" >&2
    exit 1
fi

# Compute repo-relative proposal_set_ref
# Convert absolute path to repo-relative if needed
PROPOSAL_SET_ABS="$(cd "$(dirname "$PROPOSAL_SET")" && pwd)/$(basename "$PROPOSAL_SET")"
if [[ "$PROPOSAL_SET_ABS" == "$REPO_ROOT"/* ]]; then
    PROPOSAL_SET_REF="${PROPOSAL_SET_ABS#$REPO_ROOT/}"
else
    PROPOSAL_SET_REF="$PROPOSAL_SET"
fi

# Build artifact using Python builder
ARTIFACT_JSON="$(cd "$REPO_ROOT" && python3 -c "
import sys
import json
sys.path.insert(0, '${ARTIFACT_SRC}')
from builder import build_artifact, artifact_to_json, load_proposal_set

proposal_set_path = '${PROPOSAL_SET}'
run_id = '${RUN_ID}'
input_ref = '${INPUT_REF}'
proposal_set_ref = '${PROPOSAL_SET_REF}'

# Load proposal set
proposal_set, load_error = load_proposal_set(proposal_set_path)

if load_error:
    # Build artifact with load error
    from builder import _build_reject_artifact
    artifact = _build_reject_artifact(
        run_id=run_id,
        input_ref=input_ref,
        proposal_set_ref=proposal_set_ref,
        reason_code='INVALID_PROPOSALS',
        proposal_count=0,
        validator_errors=[load_error]
    )
else:
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id=run_id,
        input_ref=input_ref,
        proposal_set_ref=proposal_set_ref
    )

print(artifact_to_json(artifact))
")"

# Write artifact to artifacts directory
ARTIFACT_DIR="$REPO_ROOT/artifacts/artifacts/$RUN_ID"
mkdir -p "$ARTIFACT_DIR"
echo "$ARTIFACT_JSON" > "$ARTIFACT_DIR/artifact.json"

# Optionally compute SHA256 for auditing
if command -v sha256sum > /dev/null 2>&1; then
    echo "$ARTIFACT_JSON" | sha256sum | cut -d' ' -f1 > "$ARTIFACT_DIR/artifact.json.sha256"
elif command -v shasum > /dev/null 2>&1; then
    echo "$ARTIFACT_JSON" | shasum -a 256 | cut -d' ' -f1 > "$ARTIFACT_DIR/artifact.json.sha256"
fi

# Output to stdout
echo "$ARTIFACT_JSON"
