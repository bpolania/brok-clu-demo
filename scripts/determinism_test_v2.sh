#!/bin/sh
# scripts/determinism_test_v2.sh — PoC v2 Determinism Validation
#
# Phase V2-5: Determinism Validation
#
# This script:
#   1. Executes the same input N times using unchanged V2-3 single-run path
#   2. Each iteration runs full verification and execution (no caching)
#   3. Compares stdout.raw.kv byte-for-byte across all runs
#   4. First successful run becomes the baseline
#   5. Any byte difference constitutes a determinism failure
#
# Usage:
#   scripts/determinism_test_v2.sh --input <PATH_TO_INPUT_FILE> --runs <N>
#
# Exit codes:
#   0   - PASS: All runs produced identical stdout.raw.kv
#   1   - FAIL: Output mismatch detected
#   2   - Usage error
#   3   - FAIL: Verification or execution error (mixed success/failure)
#
# Comparison target (authoritative):
#   - ONLY stdout.raw.kv is compared
#   - Byte-for-byte comparison (no normalization, no trimming)
#   - Any difference is a failure
#
# NOT compared:
#   - stderr.raw.txt
#   - exit_code.txt (beyond success/failure)
#   - execution.meta.json
#   - stdout.derived.json
#   - timestamps or paths
#
# Artifacts produced:
#   artifacts/determinism/test_<UTC_TIMESTAMP>/
#     baseline/stdout.raw.kv     - First successful run output
#     run_001/stdout.raw.kv      - Run 1 output
#     run_002/stdout.raw.kv      - Run 2 output
#     ...
#     summary.txt                - Human-readable summary
#     result.txt                 - PASS or FAIL with details

set -eu

# --- Compute paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_SCRIPT="$SCRIPT_DIR/run_poc_v2.sh"
ARTIFACTS_BASE="$REPO_ROOT/artifacts"

# --- Parse arguments ---
INPUT_FILE=""
RUN_COUNT=""

usage() {
    echo "Usage: $0 --input <PATH_TO_INPUT_FILE> --runs <N>"
    echo ""
    echo "Runs PoC v2 determinism validation."
    echo ""
    echo "Options:"
    echo "  --input <file>   Input file to test (required)"
    echo "  --runs <N>       Number of runs (required, minimum 2)"
    echo ""
    echo "Exit codes:"
    echo "  0  PASS: All runs produced identical stdout.raw.kv"
    echo "  1  FAIL: Output mismatch detected"
    echo "  2  Usage error"
    echo "  3  FAIL: Verification or execution error"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --input)
            [ $# -ge 2 ] || { usage >&2; exit 2; }
            INPUT_FILE="$2"
            shift 2
            ;;
        --runs)
            [ $# -ge 2 ] || { usage >&2; exit 2; }
            RUN_COUNT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# Validate arguments
if [ -z "$INPUT_FILE" ]; then
    echo "ERROR: --input is required" >&2
    usage >&2
    exit 2
fi

if [ -z "$RUN_COUNT" ]; then
    echo "ERROR: --runs is required" >&2
    usage >&2
    exit 2
fi

# Validate run count is a positive integer >= 2
case "$RUN_COUNT" in
    ''|*[!0-9]*)
        echo "ERROR: --runs must be a positive integer" >&2
        exit 2
        ;;
esac

if [ "$RUN_COUNT" -lt 2 ]; then
    echo "ERROR: --runs must be at least 2 for determinism testing" >&2
    exit 2
fi

# Convert input to absolute path
if [ "${INPUT_FILE#/}" = "$INPUT_FILE" ]; then
    INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: Input file not found: $INPUT_FILE" >&2
    exit 2
fi

if [ ! -r "$INPUT_FILE" ]; then
    echo "ERROR: Input file not readable: $INPUT_FILE" >&2
    exit 2
fi

# --- Create determinism test directory ---
UTC_TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TEST_DIR="$ARTIFACTS_BASE/determinism/test_$UTC_TIMESTAMP"
mkdir -p "$TEST_DIR"

echo "determinism_test: directory=$TEST_DIR"
echo "determinism_test: input=$INPUT_FILE"
echo "determinism_test: runs=$RUN_COUNT"

# --- Initialize summary ---
SUMMARY_FILE="$TEST_DIR/summary.txt"
RESULT_FILE="$TEST_DIR/result.txt"

cat > "$SUMMARY_FILE" << SUMMARYHEADER
Determinism Test Summary
========================
Test directory: $TEST_DIR
Input file: $INPUT_FILE
Run count: $RUN_COUNT
Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Comparison target: stdout.raw.kv (byte-for-byte, no normalization)
Comparison method: cmp (binary comparison)

SUMMARYHEADER

# --- Execute runs ---
BASELINE_FILE=""
FIRST_FAILURE_RUN=""
FIRST_FAILURE_REASON=""
ALL_RUNS_SUCCEEDED=true
MISMATCH_DETECTED=false

run_num=1
while [ "$run_num" -le "$RUN_COUNT" ]; do
    # Format run number with leading zeros
    RUN_NUM_PADDED=$(printf "%03d" "$run_num")
    RUN_SUBDIR="$TEST_DIR/run_$RUN_NUM_PADDED"
    mkdir -p "$RUN_SUBDIR"

    echo ""
    echo "determinism_test: run $run_num of $RUN_COUNT"

    # Execute using unchanged V2-3 path
    set +e
    "$RUN_SCRIPT" --input "$INPUT_FILE" > "$RUN_SUBDIR/wrapper_stdout.txt" 2> "$RUN_SUBDIR/wrapper_stderr.txt"
    RUN_EXIT_CODE=$?
    set -e

    echo "$RUN_EXIT_CODE" > "$RUN_SUBDIR/exit_code.txt"

    # Find the run directory created by run_poc_v2.sh
    # It outputs "run_directory: <path>" on stdout
    ACTUAL_RUN_DIR=$(grep "^run_directory:" "$RUN_SUBDIR/wrapper_stdout.txt" | head -1 | cut -d' ' -f2-)

    if [ -z "$ACTUAL_RUN_DIR" ] || [ ! -d "$ACTUAL_RUN_DIR" ]; then
        echo "determinism_test: run $run_num FAILED - could not locate run directory" >&2
        echo "Run $RUN_NUM_PADDED: FAILED (wrapper error - no run directory)" >> "$SUMMARY_FILE"
        ALL_RUNS_SUCCEEDED=false
        if [ -z "$FIRST_FAILURE_RUN" ]; then
            FIRST_FAILURE_RUN="$run_num"
            FIRST_FAILURE_REASON="wrapper error - no run directory"
        fi
        run_num=$((run_num + 1))
        continue
    fi

    # Check if execution was skipped or not run
    if [ -f "$ACTUAL_RUN_DIR/execution.SKIPPED" ]; then
        echo "determinism_test: run $run_num FAILED - verification failed" >&2
        echo "Run $RUN_NUM_PADDED: FAILED (verification failed)" >> "$SUMMARY_FILE"
        ALL_RUNS_SUCCEEDED=false
        if [ -z "$FIRST_FAILURE_RUN" ]; then
            FIRST_FAILURE_RUN="$run_num"
            FIRST_FAILURE_REASON="verification failed"
        fi
        run_num=$((run_num + 1))
        continue
    fi

    if [ -f "$ACTUAL_RUN_DIR/execution.NOT_RUN" ]; then
        echo "determinism_test: run $run_num FAILED - execution not run" >&2
        echo "Run $RUN_NUM_PADDED: FAILED (execution not run)" >> "$SUMMARY_FILE"
        ALL_RUNS_SUCCEEDED=false
        if [ -z "$FIRST_FAILURE_RUN" ]; then
            FIRST_FAILURE_RUN="$run_num"
            FIRST_FAILURE_REASON="execution not run"
        fi
        run_num=$((run_num + 1))
        continue
    fi

    # Check authoritative output exists
    STDOUT_RAW="$ACTUAL_RUN_DIR/stdout.raw.kv"
    if [ ! -f "$STDOUT_RAW" ]; then
        echo "determinism_test: run $run_num FAILED - stdout.raw.kv not found" >&2
        echo "Run $RUN_NUM_PADDED: FAILED (stdout.raw.kv not found)" >> "$SUMMARY_FILE"
        ALL_RUNS_SUCCEEDED=false
        if [ -z "$FIRST_FAILURE_RUN" ]; then
            FIRST_FAILURE_RUN="$run_num"
            FIRST_FAILURE_REASON="stdout.raw.kv not found"
        fi
        run_num=$((run_num + 1))
        continue
    fi

    # Copy authoritative output to determinism test directory
    cp "$STDOUT_RAW" "$RUN_SUBDIR/stdout.raw.kv"
    echo "$ACTUAL_RUN_DIR" > "$RUN_SUBDIR/source_run_dir.txt"

    # Record file hash for auditing
    STDOUT_HASH=$(shasum -a 256 "$RUN_SUBDIR/stdout.raw.kv" | awk '{print $1}')
    echo "$STDOUT_HASH" > "$RUN_SUBDIR/stdout.raw.kv.sha256"

    echo "determinism_test: run $run_num completed (exit_code=$RUN_EXIT_CODE)"
    echo "Run $RUN_NUM_PADDED: completed (exit_code=$RUN_EXIT_CODE, sha256=$STDOUT_HASH)" >> "$SUMMARY_FILE"

    # Set baseline from first successful run
    if [ -z "$BASELINE_FILE" ]; then
        BASELINE_FILE="$RUN_SUBDIR/stdout.raw.kv"
        mkdir -p "$TEST_DIR/baseline"
        cp "$BASELINE_FILE" "$TEST_DIR/baseline/stdout.raw.kv"
        cp "$RUN_SUBDIR/stdout.raw.kv.sha256" "$TEST_DIR/baseline/stdout.raw.kv.sha256"
        echo "determinism_test: baseline set from run $run_num"
        echo "" >> "$SUMMARY_FILE"
        echo "Baseline: run_$RUN_NUM_PADDED (sha256=$STDOUT_HASH)" >> "$SUMMARY_FILE"
        echo "" >> "$SUMMARY_FILE"
    else
        # Compare against baseline
        if ! cmp -s "$BASELINE_FILE" "$RUN_SUBDIR/stdout.raw.kv"; then
            MISMATCH_DETECTED=true
            BASELINE_HASH=$(cat "$TEST_DIR/baseline/stdout.raw.kv.sha256")
            echo "determinism_test: run $run_num MISMATCH detected" >&2
            echo "determinism_test: baseline sha256=$BASELINE_HASH" >&2
            echo "determinism_test: run $run_num sha256=$STDOUT_HASH" >&2
            echo "" >> "$SUMMARY_FILE"
            echo "MISMATCH DETECTED at run $RUN_NUM_PADDED" >> "$SUMMARY_FILE"
            echo "  Baseline sha256: $BASELINE_HASH" >> "$SUMMARY_FILE"
            echo "  Run $RUN_NUM_PADDED sha256: $STDOUT_HASH" >> "$SUMMARY_FILE"
            if [ -z "$FIRST_FAILURE_RUN" ]; then
                FIRST_FAILURE_RUN="$run_num"
                FIRST_FAILURE_REASON="output mismatch"
            fi
        fi
    fi

    run_num=$((run_num + 1))
done

# --- Determine final result ---
echo "" >> "$SUMMARY_FILE"
echo "Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

if [ "$ALL_RUNS_SUCCEEDED" = false ]; then
    # Mixed success/failure - determinism test fails
    echo "RESULT: FAIL" >> "$SUMMARY_FILE"
    echo "Reason: Verification or execution error (run $FIRST_FAILURE_RUN: $FIRST_FAILURE_REASON)" >> "$SUMMARY_FILE"
    echo "FAIL: Verification or execution error (run $FIRST_FAILURE_RUN: $FIRST_FAILURE_REASON)" > "$RESULT_FILE"
    echo ""
    echo "determinism_test: FAIL (verification/execution error at run $FIRST_FAILURE_RUN)"
    exit 3
fi

if [ "$MISMATCH_DETECTED" = true ]; then
    # Output mismatch
    echo "RESULT: FAIL" >> "$SUMMARY_FILE"
    echo "Reason: Output mismatch detected (first at run $FIRST_FAILURE_RUN)" >> "$SUMMARY_FILE"
    echo "FAIL: Output mismatch detected (first at run $FIRST_FAILURE_RUN)" > "$RESULT_FILE"
    echo ""
    echo "determinism_test: FAIL (output mismatch at run $FIRST_FAILURE_RUN)"
    exit 1
fi

# All runs succeeded and all outputs match
echo "RESULT: PASS" >> "$SUMMARY_FILE"
echo "All $RUN_COUNT runs produced identical stdout.raw.kv" >> "$SUMMARY_FILE"
echo "PASS: All $RUN_COUNT runs produced identical stdout.raw.kv" > "$RESULT_FILE"
echo ""
echo "determinism_test: PASS (all $RUN_COUNT runs identical)"
exit 0
