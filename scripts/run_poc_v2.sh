#!/bin/sh
# scripts/run_poc_v2.sh — PoC v2 Execution Wrapper
#
# Phase V2-3: Execution Wiring
#
# This script:
#   1. Invokes V2-2 verification (scripts/verify_poc_v2.sh) as authoritative black box
#   2. Only after verification success, extracts bundle and discovers run entrypoint
#   3. Invokes run entrypoint exactly once with user-provided input
#   4. Captures stdout/stderr/exit_code verbatim
#   5. Writes meta.txt (plain text, factual fields only)
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

# --- Directories for this run ---
RUN_DIR="$ARTIFACTS_BASE/run/run_$UTC_TIMESTAMP"
EXTRACT_DIR="$RUN_DIR/bundle_root"

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

# --- Create run directory ---
mkdir -p "$RUN_DIR"
echo "run_directory: $RUN_DIR"

# --- Step 1: Invoke V2-2 verification (MANDATORY, BLACK BOX) ---
echo "verification: invoking $VERIFY_SCRIPT"

VERIFY_STDOUT="$RUN_DIR/verify_stdout.txt"
VERIFY_STDERR="$RUN_DIR/verify_stderr.txt"

set +e
"$VERIFY_SCRIPT" >"$VERIFY_STDOUT" 2>"$VERIFY_STDERR"
VERIFY_EXIT_CODE=$?
set -e

echo "$VERIFY_EXIT_CODE" > "$RUN_DIR/verify_exit_code.txt"
echo "verification: exit_code=$VERIFY_EXIT_CODE"

if [ "$VERIFY_EXIT_CODE" -ne 0 ]; then
    # Write meta.txt for failed verification
    cat > "$RUN_DIR/meta.txt" << VERIFYFAILMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: $VERIFY_EXIT_CODE
input_file: $INPUT_FILE
working_directory: $(pwd)
VERIFYFAILMETA

    # Execution not attempted - no execution fields in meta.txt
    echo "" > "$RUN_DIR/stdout.txt"
    echo "" > "$RUN_DIR/stderr.txt"
    echo "$VERIFY_EXIT_CODE" > "$RUN_DIR/exit_code.txt"

    exit "$VERIFY_EXIT_CODE"
fi

# --- Step 2: Extract bundle for execution ---
mkdir -p "$EXTRACT_DIR"

if ! tar -xzf "$TARBALL" -C "$EXTRACT_DIR" 2>/dev/null; then
    cat > "$RUN_DIR/meta.txt" << EXTRACTFAILMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: 0
extraction_path: $EXTRACT_DIR
input_file: $INPUT_FILE
working_directory: $(pwd)
wrapper_failure: extraction failed
EXTRACTFAILMETA
    echo "" > "$RUN_DIR/stdout.txt"
    echo "Extraction failed" > "$RUN_DIR/stderr.txt"
    echo "1" > "$RUN_DIR/exit_code.txt"
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
        cat > "$RUN_DIR/meta.txt" << BUNDLEVERIFYFAILMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: 0
extraction_path: $EXTRACT_DIR
bundle_root: $BUNDLE_ROOT
input_file: $INPUT_FILE
working_directory: $(pwd)
wrapper_failure: bundle internal verify failed (exit $BUNDLE_VERIFY_EXIT)
BUNDLEVERIFYFAILMETA
        echo "" > "$RUN_DIR/stdout.txt"
        echo "Bundle internal verify failed" > "$RUN_DIR/stderr.txt"
        echo "1" > "$RUN_DIR/exit_code.txt"
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
    cat > "$RUN_DIR/meta.txt" << NORUNMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: 0
extraction_path: $EXTRACT_DIR
bundle_root: $BUNDLE_ROOT
input_file: $INPUT_FILE
working_directory: $(pwd)
wrapper_failure: no run entrypoint found
NORUNMETA
    echo "" > "$RUN_DIR/stdout.txt"
    echo "No run entrypoint found. Searched: run.sh, RUN.sh, bin/run, scripts/run.sh" > "$RUN_DIR/stderr.txt"
    echo "1" > "$RUN_DIR/exit_code.txt"
    echo "ERROR: No run entrypoint found" >&2
    exit 1
fi

if [ "$RUN_COUNT" -gt 1 ]; then
    cat > "$RUN_DIR/meta.txt" << AMBIGMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: 0
extraction_path: $EXTRACT_DIR
bundle_root: $BUNDLE_ROOT
run_entrypoint: ambiguous ($RUN_CANDIDATES)
input_file: $INPUT_FILE
working_directory: $(pwd)
wrapper_failure: ambiguous run entrypoints
AMBIGMETA
    echo "" > "$RUN_DIR/stdout.txt"
    echo "Ambiguous run entrypoints: $RUN_CANDIDATES" > "$RUN_DIR/stderr.txt"
    echo "1" > "$RUN_DIR/exit_code.txt"
    echo "ERROR: Ambiguous run entrypoints: $RUN_CANDIDATES" >&2
    exit 1
fi

echo "execution: run_entrypoint=$RUN_ENTRYPOINT_REL"

# --- Step 4: Invoke execution (single run) ---
echo "execution: invoking with input=$INPUT_FILE"

STDOUT_FILE="$RUN_DIR/stdout.txt"
STDERR_FILE="$RUN_DIR/stderr.txt"
EXIT_CODE_FILE="$RUN_DIR/exit_code.txt"

EXEC_CWD="$BUNDLE_ROOT"

set +e
(cd "$EXEC_CWD" && "$RUN_ENTRYPOINT" "$INPUT_FILE") >"$STDOUT_FILE" 2>"$STDERR_FILE"
EXEC_EXIT_CODE=$?
set -e

echo "$EXEC_EXIT_CODE" > "$EXIT_CODE_FILE"

# --- Step 5: Write meta.txt (factual fields only) ---
cat > "$RUN_DIR/meta.txt" << METAMETA
utc_timestamp: $UTC_TIMESTAMP
verify_invocation: $VERIFY_SCRIPT
verify_exit_code: 0
extraction_path: $EXTRACT_DIR
bundle_root: $BUNDLE_ROOT
run_entrypoint: $RUN_ENTRYPOINT_REL
input_file: $INPUT_FILE
working_directory: $EXEC_CWD
execution_exit_code: $EXEC_EXIT_CODE
METAMETA

# --- Step 6: Report result (minimal status only, no stdout/stderr mirroring) ---
echo "execution: exit_code=$EXEC_EXIT_CODE"

exit "$EXEC_EXIT_CODE"
