#!/bin/sh
# semantic/scripts/semantic_equivalence.sh
# Phase S-5: Semantic Equivalence Evaluation (DERIVED, NON-AUTHORITATIVE)
#
# Compares multiple existing stdout.raw.kv files under Rule V1.
# Read-only. Does not execute PoC v2. Does not modify any files.
#
# Exit codes:
#   0 = Evaluation completed (result produced, regardless of outcome)
#   1 = Operational failure (invalid input, missing files, parse error)
#
# This tool is DERIVED and NON-AUTHORITATIVE.
# Equivalence here is defined by rule, not by meaning.
#
# Limitation: Paths must not contain spaces.

set -eu

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

TOOL_VERSION="0.1.1"
RULE_NAME="RULE_V1"

# Compared keys (Rule V1: Coarse Functional Equivalence)
COMPARED_KEYS_DISPLAY="status, intent_id, n_slots"

# Ignored keys (explicitly listed)
IGNORED_KEYS_DISPLAY="dispatch, all other keys"

# Comparison method
COMPARISON_METHOD="exact string equality of compared key values"

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: $(basename "$0") <run_ref_1> <run_ref_2> [run_ref_3 ...]

Compare multiple stdout.raw.kv files under Rule V1 (Coarse Functional Equivalence).

A run reference may be:
  - A path directly to a stdout.raw.kv file
  - A path to a run directory containing stdout.raw.kv
  - A run ID (e.g., run_20260107T222101Z) resolved via artifacts/run/

Requires at least 2 run references.

Limitation: Paths must not contain spaces.

Rule V1 compares: ${COMPARED_KEYS_DISPLAY} (${COMPARISON_METHOD})
Only the explicitly listed keys are compared. All other keys are ignored.

Exit 0 on successful evaluation (even if NOT_EQUIVALENT or UNDECIDABLE).
Exit non-zero only on operational failure.

DERIVED, NON-AUTHORITATIVE. Does not imply correctness of meaning.
EOF
}

error_exit() {
    echo "ERROR: $1" >&2
    exit 1
}

# Resolve a run reference to an actual stdout.raw.kv path
resolve_run_ref() {
    ref="$1"

    # Case 1: Direct path to stdout.raw.kv
    if [ -f "$ref" ] && [ "$(basename "$ref")" = "stdout.raw.kv" ]; then
        echo "$ref"
        return 0
    fi

    # Case 2: Path to a directory containing stdout.raw.kv
    if [ -d "$ref" ] && [ -f "$ref/stdout.raw.kv" ]; then
        echo "$ref/stdout.raw.kv"
        return 0
    fi

    # Case 3: Run ID with prefix - resolve via artifacts/run/
    if echo "$ref" | grep -qE '^run_[0-9]{8}T[0-9]{6}Z$'; then
        candidate="$REPO_ROOT/artifacts/run/$ref/stdout.raw.kv"
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    fi

    # Case 4: Bare run ID without prefix - resolve via artifacts/run/
    if echo "$ref" | grep -qE '^[0-9]{8}T[0-9]{6}Z$'; then
        candidate="$REPO_ROOT/artifacts/run/run_$ref/stdout.raw.kv"
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    fi

    # Could not resolve
    return 1
}

# Extract a key value from stdout.raw.kv
# Prints value to stdout (empty if not found)
# Returns exit 0 on success (including key not found)
# Returns exit 1 on duplicate key (prints nothing)
extract_key() {
    file="$1"
    key="$2"

    # Find all lines matching key=
    matches=$(grep -n "^${key}=" "$file" 2>/dev/null || true)

    if [ -z "$matches" ]; then
        # Key not found - valid, return empty
        echo ""
        return 0
    fi

    # Count matches
    match_count=$(echo "$matches" | wc -l | tr -d ' ')

    if [ "$match_count" -gt 1 ]; then
        # Duplicate keys - operational failure, print nothing
        return 1
    fi

    # Extract value (everything after first =)
    value=$(echo "$matches" | sed 's/^[0-9]*://' | sed "s/^${key}=//")
    echo "$value"
    return 0
}

# Print the structured report
print_report() {
    result_label="$1"
    shift
    # Remaining args are: path1 sig1 path2 sig2 ...

    echo "========================================================================"
    echo "SEMANTIC EQUIVALENCE RESULT: $result_label"
    echo "========================================================================"
    echo ""
    echo "Rule: $RULE_NAME"
    echo "Tool Version: $TOOL_VERSION"
    echo "Compared Keys: $COMPARED_KEYS_DISPLAY"
    echo "Ignored: $IGNORED_KEYS_DISPLAY"
    echo "Comparison: $COMPARISON_METHOD"
    echo ""
    echo "------------------------------------------------------------------------"
    echo "Per-Run Details"
    echo "------------------------------------------------------------------------"

    run_num=1
    while [ $# -ge 2 ]; do
        path="$1"
        sig="$2"
        shift 2

        echo ""
        echo "Run $run_num:"
        echo "  Authoritative path: $path"

        # Parse signature: status|intent_id|n_slots or MISSING:key
        if echo "$sig" | grep -q "^MISSING:"; then
            missing_key=$(echo "$sig" | sed 's/^MISSING://')
            echo "  Missing compared key: $missing_key"
            echo "  Compared values: unavailable"
        else
            status_val=$(echo "$sig" | cut -d'|' -f1)
            intent_val=$(echo "$sig" | cut -d'|' -f2)
            nslots_val=$(echo "$sig" | cut -d'|' -f3)

            echo "  Compared values:"
            echo "    status    = $status_val"
            echo "    intent_id = $intent_val"
            echo "    n_slots   = $nslots_val"
        fi

        run_num=$((run_num + 1))
    done

    echo ""
    echo "------------------------------------------------------------------------"
    echo "Interpretation Disclaimer"
    echo "------------------------------------------------------------------------"
    echo ""
    echo "Equivalence here is defined by rule, not by meaning."
    echo "Derived, non-authoritative. Does not imply correctness."
    echo ""
    echo "Determinism means the same input produces the same bytes."
    echo "Semantic equivalence means different inputs produce the same derived"
    echo "signature under this rule."
    echo ""
    echo "========================================================================"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

# Check minimum arguments
if [ $# -lt 2 ]; then
    usage >&2
    error_exit "At least 2 run references required."
fi

# Resolve all run references
resolved_args=""
for ref in "$@"; do
    resolved=$(resolve_run_ref "$ref") || error_exit "Cannot resolve run reference: $ref"

    if [ ! -f "$resolved" ]; then
        error_exit "Resolved path does not exist: $resolved"
    fi

    if [ ! -r "$resolved" ]; then
        error_exit "Cannot read file: $resolved"
    fi

    resolved_args="$resolved_args $resolved"
done

# Extract signatures for all runs
signatures=""
report_data=""
has_missing=0

for path in $resolved_args; do
    # Extract each compared key, checking exit codes for duplicate detection
    if ! status_val=$(extract_key "$path" "status"); then
        error_exit "Duplicate 'status' key in $path"
    fi

    if ! intent_val=$(extract_key "$path" "intent_id"); then
        error_exit "Duplicate 'intent_id' key in $path"
    fi

    if ! nslots_val=$(extract_key "$path" "n_slots"); then
        error_exit "Duplicate 'n_slots' key in $path"
    fi

    # Check for missing keys
    if [ -z "$status_val" ]; then
        has_missing=1
        sig="MISSING:status"
    elif [ -z "$intent_val" ]; then
        has_missing=1
        sig="MISSING:intent_id"
    elif [ -z "$nslots_val" ]; then
        has_missing=1
        sig="MISSING:n_slots"
    else
        sig="${status_val}|${intent_val}|${nslots_val}"
    fi

    signatures="$signatures $sig"
    report_data="$report_data $path $sig"
done

# Determine result
if [ "$has_missing" -eq 1 ]; then
    result="UNDECIDABLE_UNDER_RULE_V1"
else
    # Check if all signatures match under the rule
    first_sig=""
    all_match=1

    for sig in $signatures; do
        if [ -z "$first_sig" ]; then
            first_sig="$sig"
        elif [ "$sig" != "$first_sig" ]; then
            all_match=0
            break
        fi
    done

    if [ "$all_match" -eq 1 ]; then
        result="EQUIVALENT_UNDER_RULE_V1"
    else
        result="NOT_EQUIVALENT_UNDER_RULE_V1"
    fi
fi

# Print report
# shellcheck disable=SC2086
print_report "$result" $report_data

# Exit 0 - evaluation completed successfully
exit 0
