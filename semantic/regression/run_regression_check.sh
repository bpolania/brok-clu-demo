#!/bin/sh
# Phase S-3: Optional Semantic Regression Gate
# DERIVED, NON-AUTHORITATIVE
#
# This script re-runs curated inputs and compares against baselines
# using byte-for-byte SHA-256 comparison.
#
# Exit codes:
#   0 = Success (regressions may or may not be detected - observational only)
#   1 = Operational failure (missing baselines, failed commands, zero eligible baselines)
#
# Contract: semantic/contract/PHASE_S_0_SCOPE_LOCK.md

set -eu

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINES_FILE="$SCRIPT_DIR/baselines/BASELINES.json"
RUNS_DIR="$SCRIPT_DIR/runs"
REPORTS_DIR="$SCRIPT_DIR/reports"

# Runtime entrypoint
POC_RUNNER="$REPO_ROOT/scripts/run_poc_v2.sh"

# Timestamp for this run
RUN_TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
RUN_DIR="$RUNS_DIR/run_$RUN_TIMESTAMP"
PER_INPUT_DIR="$RUN_DIR/per_input"

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------

if [ ! -f "$BASELINES_FILE" ]; then
    echo "ERROR: Baselines file not found: $BASELINES_FILE" >&2
    exit 1
fi

if [ ! -x "$POC_RUNNER" ]; then
    echo "ERROR: PoC v2 runner not found or not executable: $POC_RUNNER" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# Create run directory structure
# -----------------------------------------------------------------------------

mkdir -p "$PER_INPUT_DIR"

echo "=== Phase S-3: Regression Check ==="
echo "Run timestamp: $RUN_TIMESTAMP"
echo "Baselines file: $BASELINES_FILE"
echo ""

# -----------------------------------------------------------------------------
# Parse baselines and run checks
# -----------------------------------------------------------------------------

# Initialize counters
total_inputs=0
regression_count=0
no_regression_count=0
error_count=0

# Process each input from baselines
process_input() {
    input_id="$1"
    input_string="$2"
    baseline_source="$3"

    echo "Processing: $input_id"
    echo "  Input: $input_string"
    echo "  Baseline: $baseline_source"

    total_inputs=$((total_inputs + 1))

    # Check baseline exists
    if [ ! -f "$baseline_source" ]; then
        echo "  ERROR: Baseline file not found"
        error_count=$((error_count + 1))
        write_per_input_result "$input_id" "$input_string" "$baseline_source" "" "ERROR" "Baseline file not found"
        return
    fi

    # Compute baseline checksum (opaque bytes - no content inspection)
    baseline_sha256="$(shasum -a 256 "$baseline_source" | cut -d' ' -f1)"
    echo "  Baseline SHA-256: $baseline_sha256"

    # Create temp file for input
    input_file="$(mktemp)"
    printf '%s' "$input_string" > "$input_file"

    # Run through PoC v2
    echo "  Running through PoC v2..."

    if ! "$POC_RUNNER" --input "$input_file" > /dev/null 2>&1; then
        echo "  ERROR: PoC v2 execution failed"
        rm -f "$input_file"
        error_count=$((error_count + 1))
        write_per_input_result "$input_id" "$input_string" "$baseline_source" "" "ERROR" "Execution failed"
        return
    fi

    rm -f "$input_file"

    # Find the most recent run directory
    latest_run="$(ls -1dt "$REPO_ROOT/artifacts/run/run_"* 2>/dev/null | head -1)"

    if [ -z "$latest_run" ] || [ ! -f "$latest_run/stdout.raw.kv" ]; then
        echo "  ERROR: Could not find output file"
        error_count=$((error_count + 1))
        write_per_input_result "$input_id" "$input_string" "$baseline_source" "" "ERROR" "Output not found"
        return
    fi

    current_path="$latest_run/stdout.raw.kv"
    # Compute current checksum (opaque bytes - no content inspection)
    current_sha256="$(shasum -a 256 "$current_path" | cut -d' ' -f1)"
    echo "  Current SHA-256: $current_sha256"

    # Compare checksums (byte-for-byte via SHA-256)
    if [ "$baseline_sha256" = "$current_sha256" ]; then
        status="NO-REGRESSION"
        no_regression_count=$((no_regression_count + 1))
        echo "  Status: NO-REGRESSION"
    else
        status="REGRESSION"
        regression_count=$((regression_count + 1))
        echo "  Status: REGRESSION"
    fi

    write_per_input_result "$input_id" "$input_string" "$baseline_source" "$current_path" "$status" "" "$baseline_sha256" "$current_sha256"
    echo ""
}

write_per_input_result() {
    _id="$1"
    _input="$2"
    _baseline="$3"
    _current="$4"
    _status="$5"
    _error="${6:-}"
    _baseline_sha="${7:-}"
    _current_sha="${8:-}"

    result_file="$PER_INPUT_DIR/${_id}.json"

    cat > "$result_file" << JSONEOF
{
  "input_id": "$_id",
  "input_string": "$_input",
  "baseline_source": "$_baseline",
  "current_path": "$_current",
  "baseline_sha256": "$_baseline_sha",
  "current_sha256": "$_current_sha",
  "status": "$_status",
  "error": "$_error",
  "run_timestamp": "$RUN_TIMESTAMP"
}
JSONEOF
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------

echo "Reading baselines..."
echo ""

# Process demo_input_01
id_01="$(grep -o '"id"[[:space:]]*:[[:space:]]*"demo_input_01"' "$BASELINES_FILE" | head -1 || true)"
if [ -n "$id_01" ]; then
    input_01="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_01"/,/}/p' "$BASELINES_FILE" | grep '"input_string"' | sed 's/.*"input_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    baseline_01="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_01"/,/}/p' "$BASELINES_FILE" | grep '"baseline_source"' | sed 's/.*"baseline_source"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    process_input "demo_input_01" "$input_01" "$baseline_01"
fi

# Process demo_input_02
id_02="$(grep -o '"id"[[:space:]]*:[[:space:]]*"demo_input_02"' "$BASELINES_FILE" | head -1 || true)"
if [ -n "$id_02" ]; then
    input_02="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_02"/,/}/p' "$BASELINES_FILE" | grep '"input_string"' | sed 's/.*"input_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    baseline_02="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_02"/,/}/p' "$BASELINES_FILE" | grep '"baseline_source"' | sed 's/.*"baseline_source"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    process_input "demo_input_02" "$input_02" "$baseline_02"
fi

# Process demo_input_03
id_03="$(grep -o '"id"[[:space:]]*:[[:space:]]*"demo_input_03"' "$BASELINES_FILE" | head -1 || true)"
if [ -n "$id_03" ]; then
    input_03="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_03"/,/}/p' "$BASELINES_FILE" | grep '"input_string"' | sed 's/.*"input_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    baseline_03="$(sed -n '/"id"[[:space:]]*:[[:space:]]*"demo_input_03"/,/}/p' "$BASELINES_FILE" | grep '"baseline_source"' | sed 's/.*"baseline_source"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)"
    process_input "demo_input_03" "$input_03" "$baseline_03"
fi

# Check for zero eligible baselines
if [ "$total_inputs" -eq 0 ]; then
    echo "ERROR: Zero eligible baselines found" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# Generate summary
# -----------------------------------------------------------------------------

echo "=== Summary ==="
echo "Total inputs: $total_inputs"
echo "NO-REGRESSION: $no_regression_count"
echo "REGRESSION: $regression_count"
echo "ERRORS: $error_count"
echo ""

# Write SUMMARY.json
cat > "$RUN_DIR/SUMMARY.json" << SUMEOF
{
  "run_timestamp": "$RUN_TIMESTAMP",
  "total_inputs": $total_inputs,
  "no_regression_count": $no_regression_count,
  "regression_count": $regression_count,
  "error_count": $error_count,
  "overall_status": "$([ $regression_count -eq 0 ] && [ $error_count -eq 0 ] && echo 'PASS' || echo 'REGRESSION_DETECTED')"
}
SUMEOF

# Write INDEX.md
cat > "$RUN_DIR/INDEX.md" << IDXEOF
# Regression Check Run: $RUN_TIMESTAMP

**DERIVED, NON-AUTHORITATIVE**

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

---

## Run Summary

| Metric | Value |
|--------|-------|
| Timestamp | $RUN_TIMESTAMP |
| Total Inputs | $total_inputs |
| NO-REGRESSION | $no_regression_count |
| REGRESSION | $regression_count |
| Errors | $error_count |

---

## Per-Input Results

| Input ID | Status |
|----------|--------|
IDXEOF

# Add per-input results to INDEX.md
for result_file in "$PER_INPUT_DIR"/*.json; do
    if [ -f "$result_file" ]; then
        _rid="$(grep '"input_id"' "$result_file" | sed 's/.*"input_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rstatus="$(grep '"status"' "$result_file" | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        echo "| $_rid | $_rstatus |" >> "$RUN_DIR/INDEX.md"
    fi
done

cat >> "$RUN_DIR/INDEX.md" << IDXEOF2

---

## Artifacts

- Summary: \`SUMMARY.json\`
- Per-input results: \`per_input/*.json\`

---

## Note

Byte-level change detected between baseline and current \`stdout.raw.kv\`. No further analysis is performed.

---

*Phase S-3: Optional Semantic Regression Gate*
IDXEOF2

# -----------------------------------------------------------------------------
# Generate reports
# -----------------------------------------------------------------------------

echo "Generating reports..."

# per_input_comparison.md
cat > "$REPORTS_DIR/per_input_comparison.md" << REPEOF
# Per-Input Comparison Report

**DERIVED, NON-AUTHORITATIVE**

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

Generated: $RUN_TIMESTAMP

---

## Comparison Results

| Input ID | Input String | Status | Baseline SHA-256 | Current SHA-256 |
|----------|--------------|--------|------------------|-----------------|
REPEOF

for result_file in "$PER_INPUT_DIR"/*.json; do
    if [ -f "$result_file" ]; then
        _rid="$(grep '"input_id"' "$result_file" | sed 's/.*"input_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rinput="$(grep '"input_string"' "$result_file" | sed 's/.*"input_string"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rstatus="$(grep '"status"' "$result_file" | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rbsha="$(grep '"baseline_sha256"' "$result_file" | sed 's/.*"baseline_sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rcsha="$(grep '"current_sha256"' "$result_file" | sed 's/.*"current_sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        # Truncate SHA for readability
        _rbsha_short="$(echo "$_rbsha" | cut -c1-16)..."
        _rcsha_short="$(echo "$_rcsha" | cut -c1-16)..."
        echo "| $_rid | \`$_rinput\` | $_rstatus | \`$_rbsha_short\` | \`$_rcsha_short\` |" >> "$REPORTS_DIR/per_input_comparison.md"
    fi
done

cat >> "$REPORTS_DIR/per_input_comparison.md" << REPEOF2

---

## Notes

Byte-level change detected between baseline and current \`stdout.raw.kv\`. No further analysis is performed.

---

*Phase S-3: Optional Semantic Regression Gate*
REPEOF2

# regression_matrix.md
cat > "$REPORTS_DIR/regression_matrix.md" << MATEOF
# Regression Matrix

**DERIVED, NON-AUTHORITATIVE**

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

Generated: $RUN_TIMESTAMP

---

## Matrix

| Input | Baseline Run | Current Run | Status |
|-------|--------------|-------------|--------|
MATEOF

for result_file in "$PER_INPUT_DIR"/*.json; do
    if [ -f "$result_file" ]; then
        _rid="$(grep '"input_id"' "$result_file" | sed 's/.*"input_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        _rstatus="$(grep '"status"' "$result_file" | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')"
        # Extract run directory names
        _rbase_dir="$(grep '"baseline_source"' "$result_file" | sed 's/.*run_\([0-9TZ]*\).*/run_\1/' | head -1)"
        _rcurr_dir="$(grep '"current_path"' "$result_file" | sed 's/.*run_\([0-9TZ]*\).*/run_\1/' | head -1)"
        echo "| $_rid | $_rbase_dir | $_rcurr_dir | $_rstatus |" >> "$REPORTS_DIR/regression_matrix.md"
    fi
done

cat >> "$REPORTS_DIR/regression_matrix.md" << MATEOF2

---

## Summary

| Metric | Count |
|--------|-------|
| Total Inputs | $total_inputs |
| NO-REGRESSION | $no_regression_count |
| REGRESSION | $regression_count |
| Errors | $error_count |

---

## Note

Byte-level change detected between baseline and current \`stdout.raw.kv\`. No further analysis is performed.

---

*Phase S-3: Optional Semantic Regression Gate*
MATEOF2

echo ""
echo "=== Regression check complete ==="
echo "Run directory: $RUN_DIR"
echo "Reports: $REPORTS_DIR"
echo ""
echo "Exit code: 0 (observational only)"

# Exit 0 for regressions detected (observational only)
# Exit 1 only for operational failures (handled above)
exit 0
