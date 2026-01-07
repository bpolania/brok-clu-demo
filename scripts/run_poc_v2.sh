#!/bin/sh
# scripts/run_poc_v2.sh — PoC v2 Execution Wrapper
#
# Phase V2-3: Execution Wiring
# Phase V2-4: Output Capture & Presentation
#
# This script:
#   1. Invokes V2-2 verification (scripts/verify_poc_v2.sh) as authoritative black box
#   2. Only after verification success, extracts bundle and discovers run entrypoint
#   3. Invokes run entrypoint exactly once with user-provided input
#   4. Captures stdout/stderr/exit_code verbatim
#   5. Writes execution.meta.json (allowed fields only, no semantic interpretation)
#   6. Optionally generates derived output (non-authoritative)
#
# Usage:
#   scripts/run_poc_v2.sh --input <PATH_TO_INPUT_FILE>
#
# Exit codes:
#   0   - Execution succeeded
#   1   - Wrapper-internal failure (entrypoint discovery)
#   2   - Usage error
#   N   - PoC v2 verification or execution exit code (propagated verbatim)
#
# Verification gating:
#   Execution is IMPOSSIBLE unless V2-2 verification succeeds.
#   V2-2 is the single source of truth for verification.
#
# Output artifacts (Phase V2-4):
#   Authoritative: stdout.raw.kv (verbatim PoC stdout)
#   Supporting: stderr.raw.txt, exit_code.txt
#   Metadata: execution.meta.json (non-authoritative, allowed fields only)
#   Verification: verify/ subdirectory
#   Sentinel: execution.SKIPPED (verification failed) or execution.NOT_RUN (wrapper failed)

set -eu

# --- Compute repo root reliably ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Constants ---
VERIFY_SCRIPT="$SCRIPT_DIR/verify_poc_v2.sh"
VENDOR_DIR="$REPO_ROOT/vendor/poc_v2"
TARBALL="$VENDOR_DIR/poc_v2.tar.gz"
ARTIFACTS_BASE="$REPO_ROOT/artifacts"

# --- Generate UTC timestamp (filesystem-safe) ---
UTC_TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CREATED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- Directories for this run ---
RUN_DIR="$ARTIFACTS_BASE/run/run_$UTC_TIMESTAMP"
EXTRACT_DIR="$ARTIFACTS_BASE/exec_bundle/run_$UTC_TIMESTAMP"
VERIFY_DIR="$RUN_DIR/verify"

# --- Parse arguments ---
INPUT_FILE=""

usage() {
    echo "Usage: $0 --input <PATH_TO_INPUT_FILE>"
    echo ""
    echo "Runs PoC v2 verification followed by single-run execution."
    echo "Verification is mandatory and blocking (via V2-2)."
}

while [ $# -gt 0 ]; do
    case "$1" in
        --input)
            [ $# -ge 2 ] || { usage >&2; exit 2; }
            INPUT_FILE="$2"
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

# Validate input file
if [ -z "$INPUT_FILE" ]; then
    echo "ERROR: --input is required" >&2
    usage >&2
    exit 2
fi

# Convert to absolute path
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

# --- Helper: Write execution.meta.json ---
write_execution_meta() {
    _verification_passed="$1"
    _execution_attempted="$2"
    _exit_code="$3"
    _stdout_path="$4"
    _stderr_path="$5"
    _derived_path="$6"
    _notes="$7"

    cat > "$RUN_DIR/execution.meta.json" << METAJSON
{
  "run_dir": "$RUN_DIR",
  "created_at_utc": "$CREATED_AT_UTC",
  "verification_passed": $_verification_passed,
  "execution_attempted": $_execution_attempted,
  "exit_code": $_exit_code,
  "stdout_path": $_stdout_path,
  "stderr_path": $_stderr_path,
  "derived_stdout_json_path": $_derived_path,
  "notes": "$_notes"
}
METAJSON
}

# --- Helper: Generate derived stdout.derived.json ---
generate_derived_json() {
    _raw_file="$1"
    _derived_file="$2"

    # Create DERIVED_VIEW_NOTICE.txt first
    cat > "$RUN_DIR/DERIVED_VIEW_NOTICE.txt" << 'DERIVEDNOTICE'
DERIVED VIEW NOTICE

The file stdout.derived.json is a DERIVED, NON-AUTHORITATIVE view.

- Source: stdout.raw.kv (the single authoritative output)
- Purpose: Convenience parsing only
- Usage restriction: Derived views MUST NOT be used for determinism checks

The authoritative output is always stdout.raw.kv, which contains the exact
bytes emitted by PoC v2 to stdout, in order, without modification.

Any discrepancy between stdout.derived.json and stdout.raw.kv must be
resolved in favor of stdout.raw.kv.
DERIVEDNOTICE

    # Generate the derived JSON
    printf '{\n'
    printf '  "derived": true,\n'
    printf '  "authoritative_source": "stdout.raw.kv",\n'
    printf '  "note": "This file is derived for convenience only. Authoritative output is stdout.raw.kv.",\n'
    printf '  "items": [\n'

    _first=true
    while IFS= read -r _line || [ -n "$_line" ]; do
        # Escape special JSON characters in the line
        _escaped_line="$(printf '%s' "$_line" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/\\t/g')"

        if $_first; then
            _first=false
        else
            printf ',\n'
        fi

        # Check if line contains '='
        case "$_line" in
            *=*)
                # Split on first '=' only
                _key="${_line%%=*}"
                _value="${_line#*=}"
                _escaped_key="$(printf '%s' "$_key" | sed 's/\\/\\\\/g; s/"/\\"/g')"
                _escaped_value="$(printf '%s' "$_value" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/\\t/g')"
                printf '    {"type": "kv", "key": "%s", "value": "%s", "raw": "%s"}' "$_escaped_key" "$_escaped_value" "$_escaped_line"
                ;;
            *)
                printf '    {"type": "unparsed_line", "raw": "%s"}' "$_escaped_line"
                ;;
        esac
    done < "$_raw_file"

    printf '\n  ]\n'
    printf '}\n'
}

# --- Create run directory ---
mkdir -p "$RUN_DIR"
mkdir -p "$VERIFY_DIR"
echo "run_directory: $RUN_DIR"

# --- Step 1: Invoke V2-2 verification (MANDATORY, BLACK BOX) ---
echo "verification: invoking $VERIFY_SCRIPT"

set +e
"$VERIFY_SCRIPT" >"$VERIFY_DIR/stdout.txt" 2>"$VERIFY_DIR/stderr.txt"
VERIFY_EXIT_CODE=$?
set -e

echo "$VERIFY_EXIT_CODE" > "$VERIFY_DIR/exit_code.txt"
echo "verification: exit_code=$VERIFY_EXIT_CODE"

if [ "$VERIFY_EXIT_CODE" -ne 0 ]; then
    # Verification failed: create SKIPPED sentinel, no execution files
    touch "$RUN_DIR/execution.SKIPPED"
    write_execution_meta "false" "false" "null" "null" "null" "null" "Verification failed (exit $VERIFY_EXIT_CODE). Execution not attempted."
    echo "execution: SKIPPED (verification failed)"
    exit "$VERIFY_EXIT_CODE"
fi

# --- Step 2: Extract bundle for execution ---
mkdir -p "$EXTRACT_DIR"

if ! tar -xzf "$TARBALL" -C "$EXTRACT_DIR" 2>/dev/null; then
    # Wrapper failure before PoC invocation: NOT_RUN sentinel
    touch "$RUN_DIR/execution.NOT_RUN"
    write_execution_meta "true" "false" "null" "null" "null" "null" "Wrapper failure: tarball extraction failed."
    echo "ERROR: Extraction failed" >&2
    exit 1
fi

# Determine bundle root
EXTRACTED_ITEMS="$(ls -A "$EXTRACT_DIR")"
ITEM_COUNT="$(echo "$EXTRACTED_ITEMS" | wc -l | tr -d ' ')"

if [ "$ITEM_COUNT" -eq 1 ] && [ -d "$EXTRACT_DIR/$EXTRACTED_ITEMS" ]; then
    BUNDLE_ROOT="$EXTRACT_DIR/$EXTRACTED_ITEMS"
else
    BUNDLE_ROOT="$EXTRACT_DIR"
fi

# --- Step 3: Run bundle's verify.sh to set up internal state ---
# Required by PoC v2 documentation: "Verification MUST pass before any execution"
# V2-2 is the authoritative gate. This step satisfies PoC v2's documented internal requirement.
# Evidence: evidence/phase_v2_3/POC_V2_RUN_ORDER_EVIDENCE.md
BUNDLE_VERIFY=""
for CANDIDATE in "verify.sh" "VERIFY.sh" "bin/verify" "scripts/verify.sh"; do
    FULL_PATH="$BUNDLE_ROOT/$CANDIDATE"
    if [ -f "$FULL_PATH" ] && [ -x "$FULL_PATH" ]; then
        BUNDLE_VERIFY="$FULL_PATH"
        break
    fi
done

if [ -n "$BUNDLE_VERIFY" ]; then
    echo "execution: running bundle verify to set internal state"
    set +e
    (cd "$BUNDLE_ROOT" && "$BUNDLE_VERIFY") >/dev/null 2>&1
    BUNDLE_VERIFY_EXIT=$?
    set -e
    if [ "$BUNDLE_VERIFY_EXIT" -ne 0 ]; then
        # Wrapper failure before PoC invocation: NOT_RUN sentinel
        rm -rf "$EXTRACT_DIR"
        touch "$RUN_DIR/execution.NOT_RUN"
        write_execution_meta "true" "false" "null" "null" "null" "null" "Wrapper failure: bundle internal verify failed (exit $BUNDLE_VERIFY_EXIT)."
        echo "ERROR: Bundle internal verify failed" >&2
        exit 1
    fi
fi

# --- Step 4: Discover execution entrypoint (strict allowlist) ---
RUN_CANDIDATES=""
RUN_COUNT=0
RUN_ENTRYPOINT=""
RUN_ENTRYPOINT_REL=""

for CANDIDATE in "run.sh" "RUN.sh" "bin/run" "scripts/run.sh"; do
    FULL_PATH="$BUNDLE_ROOT/$CANDIDATE"
    if [ -f "$FULL_PATH" ] && [ -x "$FULL_PATH" ]; then
        RUN_CANDIDATES="${RUN_CANDIDATES}${RUN_CANDIDATES:+ }$CANDIDATE"
        RUN_COUNT=$((RUN_COUNT + 1))
        RUN_ENTRYPOINT="$FULL_PATH"
        RUN_ENTRYPOINT_REL="$CANDIDATE"
    fi
done

if [ "$RUN_COUNT" -eq 0 ]; then
    # Wrapper failure before PoC invocation: NOT_RUN sentinel
    rm -rf "$EXTRACT_DIR"
    touch "$RUN_DIR/execution.NOT_RUN"
    write_execution_meta "true" "false" "null" "null" "null" "null" "Wrapper failure: no run entrypoint found."
    echo "ERROR: No run entrypoint found" >&2
    exit 1
fi

if [ "$RUN_COUNT" -gt 1 ]; then
    # Wrapper failure before PoC invocation: NOT_RUN sentinel
    rm -rf "$EXTRACT_DIR"
    touch "$RUN_DIR/execution.NOT_RUN"
    write_execution_meta "true" "false" "null" "null" "null" "null" "Wrapper failure: ambiguous run entrypoints ($RUN_CANDIDATES)."
    echo "ERROR: Ambiguous run entrypoints: $RUN_CANDIDATES" >&2
    exit 1
fi

echo "execution: run_entrypoint=$RUN_ENTRYPOINT_REL"

# --- Step 5: Invoke execution (single run) ---
echo "execution: invoking with input=$INPUT_FILE"

STDOUT_FILE="$RUN_DIR/stdout.raw.kv"
STDERR_FILE="$RUN_DIR/stderr.raw.txt"
EXIT_CODE_FILE="$RUN_DIR/exit_code.txt"

EXEC_CWD="$BUNDLE_ROOT"

set +e
(cd "$EXEC_CWD" && "$RUN_ENTRYPOINT" "$INPUT_FILE") >"$STDOUT_FILE" 2>"$STDERR_FILE"
EXEC_EXIT_CODE=$?
set -e

echo "$EXEC_EXIT_CODE" > "$EXIT_CODE_FILE"

# --- Step 6: Generate derived output (optional, non-authoritative) ---
DERIVED_FILE="$RUN_DIR/stdout.derived.json"
generate_derived_json "$STDOUT_FILE" "$DERIVED_FILE" > "$DERIVED_FILE"

# --- Step 7: Write execution.meta.json ---
write_execution_meta "true" "true" "$EXEC_EXIT_CODE" '"stdout.raw.kv"' '"stderr.raw.txt"' '"stdout.derived.json"' "Execution completed."

# --- Step 8: Clean up extraction directory (not part of run artifacts) ---
rm -rf "$EXTRACT_DIR"

# --- Step 9: Report result (minimal status only, no stdout/stderr mirroring) ---
echo "execution: exit_code=$EXEC_EXIT_CODE"

exit "$EXEC_EXIT_CODE"
