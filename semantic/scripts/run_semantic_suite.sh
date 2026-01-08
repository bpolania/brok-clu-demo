#!/bin/sh
# semantic/scripts/run_semantic_suite.sh
#
# Phase S-1: Semantic Suite Execution
#
# Executes Semantic Equivalence Sets (SES) against PoC v2 and produces
# derived comparison reports. All semantic artifacts are non-authoritative.
#
# Usage:
#   ./semantic/scripts/run_semantic_suite.sh                    # Run all SES files
#   ./semantic/scripts/run_semantic_suite.sh SES_001            # Run specific SES
#   ./semantic/scripts/run_semantic_suite.sh --ses <SES_FILE>   # Run specific file
#
# Exit codes:
#   0 - Script completed (SES divergence is NOT a failure)
#   1 - Script internal error (missing files, parse error, etc.)
#   2 - Usage error
#
# IMPORTANT: This script produces DERIVED, NON-AUTHORITATIVE artifacts.
# The only authoritative output is stdout.raw.kv from PoC v2.

set -eu

# --- Compute paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEMANTIC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SEMANTIC_ROOT/.." && pwd)"

SUITES_DIR="$SEMANTIC_ROOT/suites"
ARTIFACTS_DIR="$SEMANTIC_ROOT/artifacts"
RUN_SCRIPT="$REPO_ROOT/scripts/run_poc_v2.sh"

# --- Timestamp for this suite run ---
SUITE_RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"

# --- Temp file cleanup ---
TEMP_FILES=""
cleanup() {
    for f in $TEMP_FILES; do
        rm -f "$f" 2>/dev/null || true
    done
}
trap cleanup EXIT

add_temp() {
    TEMP_FILES="$TEMP_FILES $1"
}

# --- Usage ---
usage() {
    echo "Usage: $0 [SES_ID | --ses <SES_FILE> | --all]"
    echo ""
    echo "Runs Semantic Equivalence Sets against PoC v2."
    echo ""
    echo "Options:"
    echo "  (none)        Run all SES files in semantic/suites/"
    echo "  SES_ID        Run specific SES by ID (e.g., SES_001)"
    echo "  --ses FILE    Run specific SES YAML file"
    echo "  --all         Run all SES files"
    echo ""
    echo "All outputs are DERIVED and NON-AUTHORITATIVE."
}

# --- Parse arguments ---
TARGET_SES=""
RUN_ALL=1

if [ $# -gt 0 ]; then
    case "$1" in
        --ses)
            [ $# -ge 2 ] || { usage >&2; exit 2; }
            TARGET_SES="$2"
            RUN_ALL=0
            ;;
        --all)
            RUN_ALL=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        SES_*)
            # Find matching file
            if [ -f "$SUITES_DIR/${1}.yaml" ]; then
                TARGET_SES="$SUITES_DIR/${1}.yaml"
            elif [ -f "$SUITES_DIR/${1}_*.yaml" ]; then
                TARGET_SES="$(ls "$SUITES_DIR/${1}_"*.yaml 2>/dev/null | head -1)"
            else
                echo "ERROR: No SES file found for ID: $1" >&2
                exit 1
            fi
            RUN_ALL=0
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
fi

# --- Verify prerequisites ---
if [ ! -x "$RUN_SCRIPT" ]; then
    echo "ERROR: PoC v2 run script not found or not executable: $RUN_SCRIPT" >&2
    exit 1
fi

if [ ! -d "$SUITES_DIR" ]; then
    echo "ERROR: Suites directory not found: $SUITES_DIR" >&2
    exit 1
fi

# --- Parse SES YAML (simple grep-based parser) ---
# Returns: id, title, description, inputs (newline-separated)
parse_ses_yaml() {
    _yaml_file="$1"

    # Extract id
    SES_ID="$(grep '^id:' "$_yaml_file" | head -1 | sed 's/^id:[[:space:]]*//')"

    # Extract title (remove quotes)
    SES_TITLE="$(grep '^title:' "$_yaml_file" | head -1 | sed 's/^title:[[:space:]]*//; s/^"//; s/"$//')"

    # Extract description (first line only for simplicity)
    SES_DESC="$(grep -A1 '^description:' "$_yaml_file" | tail -1 | sed 's/^[[:space:]]*//')"

    # Extract inputs (lines starting with "  - " after inputs:)
    SES_INPUTS_FILE="$(mktemp)"
    add_temp "$SES_INPUTS_FILE"

    _in_inputs=0
    while IFS= read -r _line || [ -n "$_line" ]; do
        case "$_line" in
            "inputs:")
                _in_inputs=1
                ;;
            "  - "*)
                if [ "$_in_inputs" -eq 1 ]; then
                    # Remove "  - " prefix and quotes
                    echo "$_line" | sed 's/^[[:space:]]*-[[:space:]]*//; s/^"//; s/"$//' >> "$SES_INPUTS_FILE"
                fi
                ;;
            *)
                # Non-input line after inputs started - stop
                if [ "$_in_inputs" -eq 1 ] && [ -n "$_line" ] && ! echo "$_line" | grep -q '^[[:space:]]*$'; then
                    case "$_line" in
                        [a-z]*:*|[A-Z]*:*)
                            _in_inputs=0
                            ;;
                    esac
                fi
                ;;
        esac
    done < "$_yaml_file"
}

# --- Run single SES ---
run_ses() {
    _ses_file="$1"

    echo "========================================"
    echo "SES: $_ses_file"
    echo "========================================"

    # Parse YAML
    parse_ses_yaml "$_ses_file"

    if [ -z "$SES_ID" ]; then
        echo "ERROR: Could not parse SES ID from $_ses_file" >&2
        return 1
    fi

    echo "ID: $SES_ID"
    echo "Title: $SES_TITLE"

    # Count inputs
    INPUT_COUNT="$(wc -l < "$SES_INPUTS_FILE" | tr -d ' ')"
    echo "Inputs: $INPUT_COUNT"

    if [ "$INPUT_COUNT" -lt 2 ]; then
        echo "ERROR: SES requires at least 2 inputs for comparison" >&2
        return 1
    fi

    # Create artifact directory
    SES_ID_LOWER="$(echo "$SES_ID" | tr '[:upper:]' '[:lower:]')"
    SES_ARTIFACT_DIR="$ARTIFACTS_DIR/$SES_ID_LOWER"
    RUNS_DIR="$SES_ARTIFACT_DIR/runs"
    mkdir -p "$RUNS_DIR"

    # Track run paths for comparison
    RUN_PATHS_FILE="$(mktemp)"
    add_temp "$RUN_PATHS_FILE"

    # Execute each input
    INPUT_INDEX=0
    while IFS= read -r INPUT_STRING || [ -n "$INPUT_STRING" ]; do
        INPUT_INDEX=$((INPUT_INDEX + 1))
        INPUT_NN="$(printf "%02d" "$INPUT_INDEX")"

        echo ""
        echo "--- Input $INPUT_NN ---"
        echo "String: $INPUT_STRING"

        # Create temp input file
        INPUT_TMP="$(mktemp)"
        add_temp "$INPUT_TMP"
        printf '%s\n' "$INPUT_STRING" > "$INPUT_TMP"

        # Invoke PoC v2
        RUN_OUTPUT="$(mktemp)"
        add_temp "$RUN_OUTPUT"

        set +e
        "$RUN_SCRIPT" --input "$INPUT_TMP" > "$RUN_OUTPUT" 2>&1
        EXEC_EXIT_CODE=$?
        set -e

        # Extract run_directory from output
        RUN_DIR="$(grep '^run_directory:' "$RUN_OUTPUT" | head -1 | sed 's/^run_directory:[[:space:]]*//')"

        if [ -z "$RUN_DIR" ]; then
            echo "ERROR: Could not extract run_directory from PoC v2 output" >&2
            RUN_DIR="UNKNOWN"
        fi

        echo "Run directory: $RUN_DIR"
        echo "Exit code: $EXEC_EXIT_CODE"

        # Extract verification exit code
        VERIFY_EXIT_CODE="unknown"
        VERIFY_EXIT_FILE="$RUN_DIR/verify/exit_code.txt"
        if [ -f "$VERIFY_EXIT_FILE" ]; then
            VERIFY_EXIT_CODE="$(cat "$VERIFY_EXIT_FILE")"
        fi

        # Determine authoritative output path
        AUTH_OUTPUT="$RUN_DIR/stdout.raw.kv"
        if [ ! -f "$AUTH_OUTPUT" ]; then
            AUTH_OUTPUT="NOT_FOUND"
        fi

        # Create runtime_ref.txt
        INPUT_REF_DIR="$RUNS_DIR/input_$INPUT_NN"
        mkdir -p "$INPUT_REF_DIR"

        cat > "$INPUT_REF_DIR/runtime_ref.txt" << REFEOF
# Runtime Reference (Phase S-1)
# DERIVED, NON-AUTHORITATIVE - For traceability only

ses_id: $SES_ID
input_index: $INPUT_INDEX
input_string: $INPUT_STRING
runtime_run_path: $RUN_DIR
authoritative_output: stdout.raw.kv
verification_exit_code: $VERIFY_EXIT_CODE
execution_exit_code: $EXEC_EXIT_CODE
suite_run_timestamp: $SUITE_RUN_TS
REFEOF

        # Record for comparison
        echo "$AUTH_OUTPUT" >> "$RUN_PATHS_FILE"

    done < "$SES_INPUTS_FILE"

    echo ""
    echo "--- Comparison (cmp byte-for-byte) ---"

    # Compare all outputs against baseline (first run)
    BASELINE=""
    COMPARISON_RESULTS_FILE="$(mktemp)"
    add_temp "$COMPARISON_RESULTS_FILE"

    ALL_MATCH=1
    COMP_INDEX=0

    while IFS= read -r OUTPUT_PATH || [ -n "$OUTPUT_PATH" ]; do
        COMP_INDEX=$((COMP_INDEX + 1))
        COMP_NN="$(printf "%02d" "$COMP_INDEX")"

        if [ -z "$BASELINE" ]; then
            BASELINE="$OUTPUT_PATH"
            echo "input_$COMP_NN: BASELINE" >> "$COMPARISON_RESULTS_FILE"
            echo "Input $COMP_NN: BASELINE"
        else
            if [ "$OUTPUT_PATH" = "NOT_FOUND" ] || [ "$BASELINE" = "NOT_FOUND" ]; then
                echo "input_$COMP_NN: DIFFER (missing output)" >> "$COMPARISON_RESULTS_FILE"
                echo "Input $COMP_NN: DIFFER (missing output)"
                ALL_MATCH=0
            elif cmp -s "$BASELINE" "$OUTPUT_PATH"; then
                echo "input_$COMP_NN: MATCH" >> "$COMPARISON_RESULTS_FILE"
                echo "Input $COMP_NN: MATCH"
            else
                echo "input_$COMP_NN: DIFFER" >> "$COMPARISON_RESULTS_FILE"
                echo "Input $COMP_NN: DIFFER"
                ALL_MATCH=0
            fi
        fi
    done < "$RUN_PATHS_FILE"

    # Classify
    if [ "$ALL_MATCH" -eq 1 ]; then
        CLASSIFICATION="CONSISTENT"
    else
        CLASSIFICATION="DIVERGENT"
    fi

    echo ""
    echo "Classification: $CLASSIFICATION"

    # Write execution_index.md
    cat > "$SES_ARTIFACT_DIR/execution_index.md" << INDEXEOF
# $SES_ID: Execution Index

**DERIVED, NON-AUTHORITATIVE VIEW**

> Authoritative output is \`stdout.raw.kv\` only.
> This report is for illustration and traceability purposes.
> Do not use this report to assert correctness.

---

## SES Metadata

| Field | Value |
|-------|-------|
| SES ID | $SES_ID |
| Title | $SES_TITLE |
| Input Count | $INPUT_COUNT |
| Suite Run | $SUITE_RUN_TS |

## Description

$SES_DESC

---

## Input Runs

| Input | String | Runtime Reference |
|-------|--------|-------------------|
INDEXEOF

    # Add input rows
    INPUT_INDEX=0
    while IFS= read -r INPUT_STRING || [ -n "$INPUT_STRING" ]; do
        INPUT_INDEX=$((INPUT_INDEX + 1))
        INPUT_NN="$(printf "%02d" "$INPUT_INDEX")"
        echo "| $INPUT_NN | \`$INPUT_STRING\` | [runtime_ref.txt](runs/input_$INPUT_NN/runtime_ref.txt) |" >> "$SES_ARTIFACT_DIR/execution_index.md"
    done < "$SES_INPUTS_FILE"

    cat >> "$SES_ARTIFACT_DIR/execution_index.md" << INDEXEOF2

---

## Comparison Results (cmp byte-for-byte)

Comparison method: \`cmp -s\` (byte-for-byte equality on \`stdout.raw.kv\`)

| Input | Result vs Baseline |
|-------|-------------------|
INDEXEOF2

    # Add comparison rows
    while IFS= read -r COMP_LINE || [ -n "$COMP_LINE" ]; do
        COMP_INPUT="$(echo "$COMP_LINE" | cut -d: -f1)"
        COMP_RESULT="$(echo "$COMP_LINE" | cut -d: -f2 | sed 's/^[[:space:]]*//')"
        echo "| $COMP_INPUT | $COMP_RESULT |" >> "$SES_ARTIFACT_DIR/execution_index.md"
    done < "$COMPARISON_RESULTS_FILE"

    cat >> "$SES_ARTIFACT_DIR/execution_index.md" << INDEXEOF3

---

## Classification

**$CLASSIFICATION**

$(if [ "$CLASSIFICATION" = "CONSISTENT" ]; then
    echo "All inputs produced byte-identical \`stdout.raw.kv\` outputs."
else
    echo "Inputs produced differing \`stdout.raw.kv\` outputs."
fi)

---

*Generated: $SUITE_RUN_TS*
*Phase S-1 Semantic Suite Execution*
INDEXEOF3

    echo ""
    echo "Artifacts written to: $SES_ARTIFACT_DIR"

    # Return classification for summary
    echo "$SES_ID:$CLASSIFICATION:$INPUT_COUNT" >> "$SUMMARY_DATA_FILE"
}

# --- Main ---

# Prepare summary data file
SUMMARY_DATA_FILE="$(mktemp)"
add_temp "$SUMMARY_DATA_FILE"

# Collect SES files to run
SES_FILES=""
if [ "$RUN_ALL" -eq 1 ]; then
    SES_FILES="$(ls "$SUITES_DIR"/*.yaml 2>/dev/null || true)"
    if [ -z "$SES_FILES" ]; then
        echo "ERROR: No SES YAML files found in $SUITES_DIR" >&2
        exit 1
    fi
else
    if [ ! -f "$TARGET_SES" ]; then
        echo "ERROR: SES file not found: $TARGET_SES" >&2
        exit 1
    fi
    SES_FILES="$TARGET_SES"
fi

# Run each SES
TOTAL_SES=0
for SES_FILE in $SES_FILES; do
    TOTAL_SES=$((TOTAL_SES + 1))
    run_ses "$SES_FILE"
    echo ""
done

# Write SES_SUMMARY.md
cat > "$ARTIFACTS_DIR/SES_SUMMARY.md" << SUMMARYEOF
# Semantic Equivalence Set Summary

**DERIVED, NON-AUTHORITATIVE VIEW**

> All classifications are illustrative only.
> Authoritative output is \`stdout.raw.kv\` only.
> This summary does not constitute a system guarantee.

---

## Suite Run

| Field | Value |
|-------|-------|
| Timestamp | $SUITE_RUN_TS |
| Total SES | $TOTAL_SES |

---

## Results

| SES ID | Classification | Input Count |
|--------|----------------|-------------|
SUMMARYEOF

while IFS= read -r SUMMARY_LINE || [ -n "$SUMMARY_LINE" ]; do
    S_ID="$(echo "$SUMMARY_LINE" | cut -d: -f1)"
    S_CLASS="$(echo "$SUMMARY_LINE" | cut -d: -f2)"
    S_COUNT="$(echo "$SUMMARY_LINE" | cut -d: -f3)"
    echo "| $S_ID | $S_CLASS | $S_COUNT |" >> "$ARTIFACTS_DIR/SES_SUMMARY.md"
done < "$SUMMARY_DATA_FILE"

cat >> "$ARTIFACTS_DIR/SES_SUMMARY.md" << SUMMARYEOF2

---

## Non-Claims

This semantic suite explicitly does **NOT** claim:

- General language understanding
- Paraphrase completeness
- Production readiness
- Multilingual robustness
- Typo tolerance
- Domain invariance

Classifications are curated, bounded, and illustrative only.

---

*Generated: $SUITE_RUN_TS*
*Phase S-1 Semantic Suite Execution*
SUMMARYEOF2

echo "========================================"
echo "Summary written to: $ARTIFACTS_DIR/SES_SUMMARY.md"
echo "========================================"
echo ""
echo "Phase S-1 semantic suite execution complete."
echo "Exit code: 0 (SES divergence is not a script failure)"

exit 0
