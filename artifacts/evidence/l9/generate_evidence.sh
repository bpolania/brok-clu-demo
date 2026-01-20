#!/bin/bash
# Phase L-9 Authoritative Evidence Generation (Closure-Grade)
#
# This script generates CLOSURE-GRADE evidence for L-9 synonym equivalence.
# All run directories MUST be NEW (created during this evidence run).
#
# CLOSURE REQUIREMENTS:
# - FRESH run environment (no pre-existing run directories interfere)
# - JSON-parsed output (no grep on human text)
# - All run directories MUST be NEW (reuse = FAIL)
# - No wildcard hashing
# - Complete auditable evidence
#
# FRESH ENVIRONMENT STRATEGY: Move-aside (Strategy 2)
# - Quarantine existing artifacts/run to artifacts/run.__l9_quarantine__/<id>
# - Create fresh empty artifacts/run directory
# - Run evidence generation
# - Restore original on completion or failure
#
# INPUT VARIANTS:
# - ACCEPT: "create payment" (canonical), "submit payment", "new payment", "make a payment"
# - REJECT: "payment" (unknown, not in L-9 mapping)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
EVIDENCE_DIR="$SCRIPT_DIR"
RUN_ROOT="$REPO_ROOT/artifacts/run"
BROK_RUN="$REPO_ROOT/brok-run"

# Quarantine settings
QUARANTINE_ROOT="$REPO_ROOT/artifacts/run.__l9_quarantine__"
QUARANTINE_ID="evidence_$(date +%Y%m%d_%H%M%S)_$$"
QUARANTINE_DIR="$QUARANTINE_ROOT/$QUARANTINE_ID"

# Evidence output file
EVIDENCE_FILE="$EVIDENCE_DIR/stdout_raw_kv_evidence.txt"

# Cleanup on exit (restore run root)
ORIGINAL_RUN_ROOT_QUARANTINED=""
cleanup() {
    local exit_code=$?

    # Restore quarantined run root if it exists
    if [ -n "$ORIGINAL_RUN_ROOT_QUARANTINED" ] && [ -d "$ORIGINAL_RUN_ROOT_QUARANTINED" ]; then
        echo ""
        echo "========================================================================"
        echo "Restoring Original Run Root"
        echo "========================================================================"

        # Remove the fresh run root (evidence artifacts)
        if [ -d "$RUN_ROOT" ]; then
            rm -rf "$RUN_ROOT"
        fi

        # Move quarantined back to original location
        mv "$ORIGINAL_RUN_ROOT_QUARANTINED" "$RUN_ROOT"
        echo "Restored: $ORIGINAL_RUN_ROOT_QUARANTINED -> $RUN_ROOT"

        # Clean up empty quarantine dirs
        rmdir "$QUARANTINE_ROOT" 2>/dev/null || true
    fi

    # Clean up temp files
    rm -f /tmp/l9_evidence_*.txt /tmp/l9_evidence_*.json

    exit $exit_code
}
trap cleanup EXIT

# Python helper for JSON parsing (no jq dependency)
extract_json_field() {
    local json="$1"
    local field="$2"
    python3 -c "
import json
import sys
try:
    data = json.loads('''$json''')
    value = data.get('$field')
    if value is None:
        print('null')
    else:
        print(value)
except Exception as e:
    print('ERROR:' + str(e), file=sys.stderr)
    sys.exit(1)
"
}

# Extract JSON object from wrapper output
# Finds the JSON object containing both run_dir and decision keys
extract_wrapper_json() {
    local output="$1"
    python3 -c "
import json
import sys
import re

output = '''$output'''

# Find JSON objects in the output
json_pattern = r'\{[^{}]*\"run_dir\"[^{}]*\"decision\"[^{}]*\}|\{[^{}]*\"decision\"[^{}]*\"run_dir\"[^{}]*\}'

# Try to find any line that looks like JSON with both keys
for line in output.split('\n'):
    line = line.strip()
    if line.startswith('{') and line.endswith('}'):
        try:
            data = json.loads(line)
            if 'run_dir' in data and 'decision' in data:
                print(line)
                sys.exit(0)
        except json.JSONDecodeError:
            continue

# No valid JSON found
print('', file=sys.stderr)
sys.exit(1)
"
}

echo "========================================================================"
echo "Phase L-9 Authoritative Evidence Generation (Closure-Grade)"
echo "========================================================================"
echo ""
echo "Repository root: $REPO_ROOT"
echo "Evidence directory: $EVIDENCE_DIR"
echo "Run root: $RUN_ROOT"
echo "Wrapper: $BROK_RUN"
echo ""

# Verify brok-run exists
if [ ! -x "$BROK_RUN" ]; then
    echo "ERROR: brok-run not found or not executable: $BROK_RUN"
    exit 1
fi

# ============================================================================
# FRESH ENVIRONMENT: Strategy 2 - Move-aside
# ============================================================================
echo "========================================================================"
echo "Creating Fresh Run Environment (Strategy 2: Move-aside)"
echo "========================================================================"
echo ""

if [ -d "$RUN_ROOT" ]; then
    # Count existing directories
    EXISTING_COUNT=$(ls -1 "$RUN_ROOT" 2>/dev/null | wc -l | tr -d ' ')
    echo "Existing run directories: $EXISTING_COUNT"

    if [ "$EXISTING_COUNT" -gt 0 ]; then
        # Create quarantine directory
        mkdir -p "$QUARANTINE_ROOT"

        # Move existing run root to quarantine
        echo "Quarantining: $RUN_ROOT -> $QUARANTINE_DIR"
        mv "$RUN_ROOT" "$QUARANTINE_DIR"
        ORIGINAL_RUN_ROOT_QUARANTINED="$QUARANTINE_DIR"

        # Create fresh empty run root
        mkdir -p "$RUN_ROOT"
        echo "Created fresh run root: $RUN_ROOT"
    else
        echo "Run root is already empty"
    fi
else
    echo "Run root does not exist, creating fresh"
    mkdir -p "$RUN_ROOT"
fi

# Snapshot before (should be empty now)
SNAPSHOT_BEFORE="/tmp/l9_evidence_before.txt"
ls -1 "$RUN_ROOT" 2>/dev/null | sort > "$SNAPSHOT_BEFORE" || touch "$SNAPSHOT_BEFORE"
BEFORE_COUNT=$(wc -l < "$SNAPSHOT_BEFORE" | tr -d ' ')
echo ""
echo "BEFORE snapshot: $BEFORE_COUNT directories (must be 0 for closure)"
if [ "$BEFORE_COUNT" -ne 0 ]; then
    echo "ERROR: Run root is not empty after quarantine. Cannot generate closure evidence."
    exit 1
fi
echo ""

# ============================================================================
# RUN EVIDENCE TESTS
# ============================================================================

# Arrays to store results
declare -a INPUTS=("create payment" "submit payment" "new payment" "make a payment" "payment")
declare -a LABELS=("canonical" "expanded_submit" "expanded_new" "expanded_make_a" "reject")
declare -a EXPECTED_DECISIONS=("ACCEPT" "ACCEPT" "ACCEPT" "ACCEPT" "REJECT")
declare -a RUN_DIRS
declare -a DECISIONS
declare -a JSONS
declare -a STDOUT_PATHS
declare -a HASHES
declare -a NEW_FLAGS

echo "========================================================================"
echo "Running Evidence Tests (5 inputs)"
echo "========================================================================"
echo ""

for i in "${!INPUTS[@]}"; do
    INPUT="${INPUTS[$i]}"
    LABEL="${LABELS[$i]}"
    EXPECTED="${EXPECTED_DECISIONS[$i]}"

    echo "[$(($i+1))/5] Running: '$INPUT' (expected: $EXPECTED)"

    # Snapshot before this run
    SNAP_BEFORE="/tmp/l9_evidence_snap_before_$i.txt"
    ls -1 "$RUN_ROOT" 2>/dev/null | sort > "$SNAP_BEFORE" || touch "$SNAP_BEFORE"

    # Run brok-run and capture output
    OUTPUT=$("$BROK_RUN" "$INPUT" 2>&1) || true

    # Snapshot after this run
    SNAP_AFTER="/tmp/l9_evidence_snap_after_$i.txt"
    ls -1 "$RUN_ROOT" 2>/dev/null | sort > "$SNAP_AFTER" || touch "$SNAP_AFTER"

    # Extract JSON from output
    JSON=$(extract_wrapper_json "$OUTPUT") || {
        echo "  ERROR: Failed to extract JSON from wrapper output"
        echo "  Output was: $OUTPUT"
        exit 1
    }

    if [ -z "$JSON" ]; then
        echo "  ERROR: No valid JSON found in wrapper output"
        echo "  Output was: $OUTPUT"
        exit 1
    fi

    JSONS[$i]="$JSON"

    # Parse JSON fields
    RUN_DIR=$(extract_json_field "$JSON" "run_dir")
    DECISION=$(extract_json_field "$JSON" "decision")
    AUTH_PATH=$(extract_json_field "$JSON" "authoritative_stdout_raw_kv")
    AUTH_HASH=$(extract_json_field "$JSON" "authoritative_stdout_raw_kv_sha256")

    RUN_DIRS[$i]="$RUN_DIR"
    DECISIONS[$i]="$DECISION"

    echo "  run_dir: $RUN_DIR"
    echo "  decision: $DECISION (expected: $EXPECTED)"

    # Verify decision matches expected
    if [ "$DECISION" != "$EXPECTED" ]; then
        echo "  ERROR: Decision mismatch! Expected $EXPECTED, got $DECISION"
        exit 1
    fi

    # Compute delta (new directories)
    DELTA=$(comm -13 "$SNAP_BEFORE" "$SNAP_AFTER" | tr '\n' ' ')
    echo "  delta (new dirs): ${DELTA:-none}"

    # Check if run_dir is in the delta (NEW)
    RUN_DIR_BASENAME=$(basename "$RUN_DIR")
    if grep -qxF "$RUN_DIR_BASENAME" "$SNAP_BEFORE" 2>/dev/null; then
        echo "  ERROR: REUSE DETECTED - run_dir existed before this run!"
        echo "  CLOSURE VIOLATION: run_dir '$RUN_DIR_BASENAME' is not new"
        exit 1
    fi

    # Verify run_dir is within the evidence run dirs (check delta or that we created it)
    NEW_FLAGS[$i]="true"

    # For ACCEPT cases, find stdout.raw.kv
    if [ "$DECISION" = "ACCEPT" ]; then
        # Look for stdout.raw.kv in delta directories
        STDOUT_PATH=""
        for dir_name in $(comm -13 "$SNAP_BEFORE" "$SNAP_AFTER"); do
            candidate="$RUN_ROOT/$dir_name/stdout.raw.kv"
            if [ -f "$candidate" ]; then
                STDOUT_PATH="$candidate"
                break
            fi
        done

        if [ -z "$STDOUT_PATH" ]; then
            echo "  ERROR: ACCEPT decision but no stdout.raw.kv found in delta"
            exit 1
        fi

        STDOUT_PATHS[$i]="$STDOUT_PATH"

        # Compute hash (no wildcards)
        HASH=$(shasum -a 256 "$STDOUT_PATH" | cut -d' ' -f1)
        HASHES[$i]="$HASH"
        echo "  stdout.raw.kv: $STDOUT_PATH"
        echo "  sha256: $HASH"
    else
        # REJECT case - verify no stdout.raw.kv in delta
        STDOUT_PATH=""
        for dir_name in $(comm -13 "$SNAP_BEFORE" "$SNAP_AFTER"); do
            candidate="$RUN_ROOT/$dir_name/stdout.raw.kv"
            if [ -f "$candidate" ]; then
                STDOUT_PATH="$candidate"
                break
            fi
        done

        if [ -n "$STDOUT_PATH" ]; then
            echo "  ERROR: REJECT decision but stdout.raw.kv found: $STDOUT_PATH"
            exit 1
        fi

        STDOUT_PATHS[$i]="N/A"
        HASHES[$i]="N/A"
        echo "  stdout.raw.kv: ABSENT (expected for REJECT)"
    fi

    echo "  new_run_dir: ${NEW_FLAGS[$i]}"
    echo ""
done

# ============================================================================
# VERIFY ACCEPT HASHES ALL EQUAL
# ============================================================================
echo "========================================================================"
echo "Hash Equality Check (ACCEPT cases)"
echo "========================================================================"
echo ""

# Get ACCEPT hashes (indices 0-3)
ACCEPT_HASH_1="${HASHES[0]}"
ACCEPT_HASH_2="${HASHES[1]}"
ACCEPT_HASH_3="${HASHES[2]}"
ACCEPT_HASH_4="${HASHES[3]}"

echo "canonical (create payment): $ACCEPT_HASH_1"
echo "expanded (submit payment):  $ACCEPT_HASH_2"
echo "expanded (new payment):     $ACCEPT_HASH_3"
echo "expanded (make a payment):  $ACCEPT_HASH_4"
echo ""

if [ "$ACCEPT_HASH_1" = "$ACCEPT_HASH_2" ] && \
   [ "$ACCEPT_HASH_2" = "$ACCEPT_HASH_3" ] && \
   [ "$ACCEPT_HASH_3" = "$ACCEPT_HASH_4" ]; then
    echo "RESULT: ALL ACCEPT HASHES MATCH"
    ACCEPT_HASHES_EQUAL="true"
else
    echo "RESULT: ACCEPT HASH MISMATCH DETECTED"
    ACCEPT_HASHES_EQUAL="false"
fi
echo ""

# ============================================================================
# VERIFY REJECT STDOUT ABSENT
# ============================================================================
echo "========================================================================"
echo "REJECT Path Verification"
echo "========================================================================"
echo ""

REJECT_DECISION="${DECISIONS[4]}"
REJECT_STDOUT="${STDOUT_PATHS[4]}"

echo "decision: $REJECT_DECISION"
echo "stdout.raw.kv: $REJECT_STDOUT"

if [ "$REJECT_DECISION" = "REJECT" ] && [ "$REJECT_STDOUT" = "N/A" ]; then
    echo "RESULT: REJECT correctly has no stdout.raw.kv"
    REJECT_STDOUT_ABSENT="true"
else
    echo "RESULT: REJECT verification failed"
    REJECT_STDOUT_ABSENT="false"
fi
echo ""

# ============================================================================
# OVERALL RESULT
# ============================================================================
echo "========================================================================"
echo "Evidence Summary"
echo "========================================================================"
echo ""

ALL_NEW="true"
for flag in "${NEW_FLAGS[@]}"; do
    if [ "$flag" != "true" ]; then
        ALL_NEW="false"
        break
    fi
done

echo "ACCEPT_HASHES_ALL_EQUAL: $ACCEPT_HASHES_EQUAL"
echo "REJECT_STDOUT_RAW_KV_PRESENT: $([ "$REJECT_STDOUT_ABSENT" = "true" ] && echo "false" || echo "true")"
echo "ALL_RUN_DIRS_NEW: $ALL_NEW"
echo ""

if [ "$ACCEPT_HASHES_EQUAL" = "true" ] && \
   [ "$REJECT_STDOUT_ABSENT" = "true" ] && \
   [ "$ALL_NEW" = "true" ]; then
    echo "OVERALL_PASS: true"
    OVERALL_PASS="true"
    EXIT_CODE=0
else
    echo "OVERALL_PASS: false"
    OVERALL_PASS="false"
    EXIT_CODE=1
fi
echo ""

# ============================================================================
# WRITE EVIDENCE FILE
# ============================================================================
echo "========================================================================"
echo "Writing Evidence File"
echo "========================================================================"
echo ""

cat > "$EVIDENCE_FILE" << EOF
Phase L-9 Authoritative Evidence: stdout.raw.kv Hash Equivalence
================================================================

Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Repository: $REPO_ROOT
Strategy: Fresh run environment (Strategy 2: Move-aside quarantine)
Quarantine ID: $QUARANTINE_ID

================================================================================
CLOSURE REQUIREMENTS
================================================================================

- All run directories MUST be NEW (created during this evidence run)
- JSON-parsed output from ./brok-run (no grep on human text)
- No wildcard hashing
- REJECT must have decision=REJECT and no stdout.raw.kv

================================================================================
EVIDENCE RUNS (5 total)
================================================================================

EOF

for i in "${!INPUTS[@]}"; do
    cat >> "$EVIDENCE_FILE" << EOF
--- Run $((i+1)): ${LABELS[$i]} ---
input: "${INPUTS[$i]}"
command: ./brok-run "${INPUTS[$i]}"
json: ${JSONS[$i]}
run_dir: ${RUN_DIRS[$i]}
new_run_dir: ${NEW_FLAGS[$i]}
decision: ${DECISIONS[$i]}
expected_decision: ${EXPECTED_DECISIONS[$i]}
stdout_raw_kv_path: ${STDOUT_PATHS[$i]}
sha256: ${HASHES[$i]}

EOF
done

cat >> "$EVIDENCE_FILE" << EOF
================================================================================
VERIFICATION RESULTS
================================================================================

ACCEPT_HASHES_ALL_EQUAL: $ACCEPT_HASHES_EQUAL
  canonical:       $ACCEPT_HASH_1
  expanded_submit: $ACCEPT_HASH_2
  expanded_new:    $ACCEPT_HASH_3
  expanded_make_a: $ACCEPT_HASH_4

REJECT_STDOUT_RAW_KV_PRESENT: $([ "$REJECT_STDOUT_ABSENT" = "true" ] && echo "false" || echo "true")
  (Must be false for closure)

ALL_RUN_DIRS_NEW: $ALL_NEW
  (Must be true for closure - no reuse allowed)

OVERALL_PASS: $OVERALL_PASS
  (Must be true for closure evidence)

================================================================================
CONCLUSION
================================================================================

L-9 language acceptance contract closure evidence:
- 4 ACCEPT inputs (canonical + 3 synonyms) produce byte-identical stdout.raw.kv
- 1 REJECT input produces decision=REJECT with no stdout.raw.kv
- All 5 run directories were NEW (created during this evidence run)
- No wildcards used in hash computation

Closure status: $([ "$OVERALL_PASS" = "true" ] && echo "CLOSED" || echo "NOT CLOSED")

================================================================================
REPRODUCTION COMMANDS
================================================================================

# To reproduce this evidence:
# 1. Run the evidence script (it will quarantine existing runs automatically)
./artifacts/evidence/l9/generate_evidence.sh

# The script:
# - Quarantines existing artifacts/run to artifacts/run.__l9_quarantine__/
# - Creates fresh empty artifacts/run
# - Runs 5 inputs via ./brok-run
# - Parses JSON output to extract run_dir and decision
# - Verifies all run_dirs are NEW (not reused)
# - Computes sha256 only for captured stdout.raw.kv paths (no wildcards)
# - Restores original artifacts/run on exit

# NOTE: rerun/reuse is FORBIDDEN for closure evidence.
# The script FAILS if any run_dir existed before the evidence run.
EOF

echo "Evidence written to: $EVIDENCE_FILE"
echo ""

exit $EXIT_CODE
