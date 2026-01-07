#!/bin/sh
set -eu

BUNDLE_DIR="bundles/poc_v1"
MANIFEST="$BUNDLE_DIR/MANIFEST.txt"
CHECKSUMS="$BUNDLE_DIR/SHA256SUMS"
BINARY="$BUNDLE_DIR/bin/macos-arm64/cmd_interpreter"

ARTIFACTS_DIR="artifacts/last_run"
RAW_OUTPUT="$ARTIFACTS_DIR/output.raw.kv"
DERIVED_OUTPUT="$ARTIFACTS_DIR/output.derived.json"

DETERMINISM_DIR="artifacts/determinism"

STDOUT_TMP=""
STDERR_TMP=""
MANIFEST_TMP=""
FILES_TMP=""

cleanup() {
    [ -n "$STDOUT_TMP" ] && rm -f "$STDOUT_TMP" 2>/dev/null || true
    [ -n "$STDERR_TMP" ] && rm -f "$STDERR_TMP" 2>/dev/null || true
    [ -n "$MANIFEST_TMP" ] && rm -f "$MANIFEST_TMP" 2>/dev/null || true
    [ -n "$FILES_TMP" ] && rm -f "$FILES_TMP" 2>/dev/null || true
}
trap cleanup EXIT

fail_verification() {
    echo "VERIFICATION FAILED: $1" >&2
    # Write sentinel output to indicate verification was required
    mkdir -p "$ARTIFACTS_DIR"
    cat > "$RAW_OUTPUT" << 'SENTINEL'
status=VERIFY_REQUIRED
intent_id=-1
n_slots=0
SENTINEL
    exit 10
}

fail_usage() {
    echo "Usage: $0 <input-file>" >&2
    echo "       $0 --determinism-test --input <file> --runs <N>" >&2
    exit 2
}

# Parse arguments
DETERMINISM_MODE=0
INPUT_FILE=""
NUM_RUNS=0

if [ $# -eq 0 ]; then
    fail_usage
fi

# Check for determinism mode or legacy positional argument
if [ "$1" = "--determinism-test" ]; then
    DETERMINISM_MODE=1
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --input)
                [ $# -ge 2 ] || fail_usage
                INPUT_FILE="$2"
                shift 2
                ;;
            --runs)
                [ $# -ge 2 ] || fail_usage
                NUM_RUNS="$2"
                shift 2
                ;;
            *)
                fail_usage
                ;;
        esac
    done
    # Validate determinism mode arguments
    [ -n "$INPUT_FILE" ] || { echo "ERROR: --input required for determinism test" >&2; exit 2; }
    [ "$NUM_RUNS" -gt 0 ] 2>/dev/null || { echo "ERROR: --runs must be a positive integer" >&2; exit 2; }
else
    # Legacy single-argument mode
    [ $# -eq 1 ] || fail_usage
    INPUT_FILE="$1"
fi

# Verify input file exists and is readable
[ -f "$INPUT_FILE" ] || { echo "ERROR: Input file not found: $INPUT_FILE" >&2; exit 2; }
[ -r "$INPUT_FILE" ] || { echo "ERROR: Input file not readable: $INPUT_FILE" >&2; exit 2; }

# A) Verification enforcement (runs once, before any execution)

# 1. Existence checks
[ -f "$MANIFEST" ] && [ -r "$MANIFEST" ] || fail_verification "MANIFEST.txt missing or unreadable"
[ -f "$CHECKSUMS" ] && [ -r "$CHECKSUMS" ] || fail_verification "SHA256SUMS missing or unreadable"
[ -f "$BINARY" ] && [ -r "$BINARY" ] || fail_verification "cmd_interpreter missing or unreadable"
[ -x "$BINARY" ] || fail_verification "cmd_interpreter not executable"

# Create temp files
STDOUT_TMP=$(mktemp)
STDERR_TMP=$(mktemp)
MANIFEST_TMP=$(mktemp)
FILES_TMP=$(mktemp)

# 2. Manifest completeness - verify all listed files exist
while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    filepath="$BUNDLE_DIR/$line"
    [ -f "$filepath" ] || fail_verification "File listed in manifest does not exist: $line"
done < "$MANIFEST"

# 3. No extra files check
grep -v '^$' "$MANIFEST" | sort > "$MANIFEST_TMP"
(cd "$BUNDLE_DIR" && find . -type f ! -name 'MANIFEST.txt' ! -name 'SHA256SUMS' | sed 's|^\./||' | sort) > "$FILES_TMP"

if ! diff -q "$MANIFEST_TMP" "$FILES_TMP" >/dev/null 2>&1; then
    EXTRA=$(comm -13 "$MANIFEST_TMP" "$FILES_TMP" | head -1)
    if [ -n "$EXTRA" ]; then
        fail_verification "Extra file not in manifest: $EXTRA"
    fi
    MISSING=$(comm -23 "$MANIFEST_TMP" "$FILES_TMP" | head -1)
    if [ -n "$MISSING" ]; then
        fail_verification "File in manifest does not exist: $MISSING"
    fi
fi

# 4. SHA-256 verification
(cd "$BUNDLE_DIR" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || fail_verification "Checksum mismatch"

# B) Execution function (reusable for determinism mode)
run_single_execution() {
    # Prepare artifacts directory
    mkdir -p "$ARTIFACTS_DIR"
    rm -f "$RAW_OUTPUT" "$DERIVED_OUTPUT" 2>/dev/null || true

    # Invoke cmd_interpreter with --input argument
    set +e
    "$BINARY" --input "$INPUT_FILE" >"$STDOUT_TMP" 2>"$STDERR_TMP"
    EXIT_CODE=$?
    set -e

    # Always capture raw output if stdout was emitted
    if [ -s "$STDOUT_TMP" ]; then
        cp "$STDOUT_TMP" "$RAW_OUTPUT"
    fi

    if [ $EXIT_CODE -eq 0 ]; then
        # Success: emit stdout to console, generate derived JSON
        cat "$STDOUT_TMP"

        # Generate derived JSON from raw output (only on success)
        awk '
        BEGIN {
            print "{"
            print "  \"derived\": true,"
            print "  \"source_format\": \"key=value\","
            print "  \"kv\": {"
            first = 1
        }
        /=/ {
            sub(/\r$/, "")
            idx = index($0, "=")
            if (idx > 0) {
                key = substr($0, 1, idx - 1)
                val = substr($0, idx + 1)
                gsub(/\\/, "\\\\", key)
                gsub(/"/, "\\\"", key)
                gsub(/\\/, "\\\\", val)
                gsub(/"/, "\\\"", val)
                keys[key] = val
                if (!(key in order)) {
                    order[key] = ++count
                }
            }
        }
        END {
            for (i = 1; i <= count; i++) {
                for (k in order) {
                    if (order[k] == i) {
                        if (!first) print ","
                        first = 0
                        printf "    \"%s\": \"%s\"", k, keys[k]
                    }
                }
            }
            if (count > 0) print ""
            print "  }"
            print "}"
        }
        ' "$RAW_OUTPUT" > "$DERIVED_OUTPUT"
        return 0
    else
        # Failure: surface stderr, do not emit stdout, no derived output
        cat "$STDERR_TMP" >&2
        return $EXIT_CODE
    fi
}

# C) Mode dispatch

if [ "$DETERMINISM_MODE" -eq 0 ]; then
    # Single-run mode (Phase 3/4 behavior)
    run_single_execution
    exit $?
fi

# D) Determinism test mode

# Prepare determinism artifacts directory
rm -rf "$DETERMINISM_DIR"
mkdir -p "$DETERMINISM_DIR"

SUMMARY_FILE="$DETERMINISM_DIR/summary.txt"
FIRST_OUTPUT=""
DETERMINISM_PASS=1
FIRST_MISMATCH_A=0
FIRST_MISMATCH_B=0
FAILED_RUNS=""

echo "Determinism test: $NUM_RUNS runs"

for i in $(seq 1 "$NUM_RUNS"); do
    RUN_NUM=$(printf "%03d" "$i")
    RUN_DIR="$DETERMINISM_DIR/run_$RUN_NUM"
    mkdir -p "$RUN_DIR"

    # Run execution (suppress stdout for determinism mode, capture only)
    RUN_EXIT=0
    run_single_execution >/dev/null 2>&1 || RUN_EXIT=$?

    # Copy raw output to per-run directory
    if [ -f "$RAW_OUTPUT" ]; then
        cp "$RAW_OUTPUT" "$RUN_DIR/output.raw.kv"
    else
        # No output produced - record as failed run
        FAILED_RUNS="$FAILED_RUNS $i"
        DETERMINISM_PASS=0
        echo "  Run $i: FAILED (no output)"
        continue
    fi

    # Check for execution failure (non-zero exit while others succeed)
    if [ $RUN_EXIT -ne 0 ] && [ -z "$FAILED_RUNS" ]; then
        # First run to fail - will compare against this behavior
        :
    fi

    # Compare against first run
    if [ -z "$FIRST_OUTPUT" ]; then
        FIRST_OUTPUT="$RUN_DIR/output.raw.kv"
        echo "  Run $i: baseline captured"
    else
        if diff -q "$FIRST_OUTPUT" "$RUN_DIR/output.raw.kv" >/dev/null 2>&1; then
            echo "  Run $i: MATCH"
        else
            echo "  Run $i: MISMATCH"
            if [ "$DETERMINISM_PASS" -eq 1 ]; then
                FIRST_MISMATCH_A=1
                FIRST_MISMATCH_B=$i
            fi
            DETERMINISM_PASS=0
        fi
    fi
done

# Generate summary
{
    echo "Determinism Test Summary"
    echo "========================"
    echo "Input file: $INPUT_FILE"
    echo "Number of runs: $NUM_RUNS"
    echo ""
    if [ "$DETERMINISM_PASS" -eq 1 ]; then
        echo "Result: PASS"
        echo "All runs produced identical output."
    else
        echo "Result: FAIL"
        if [ -n "$FAILED_RUNS" ]; then
            echo "Failed runs (no output):$FAILED_RUNS"
        fi
        if [ "$FIRST_MISMATCH_A" -ne 0 ]; then
            echo "First mismatch: run $FIRST_MISMATCH_A vs run $FIRST_MISMATCH_B"
        fi
    fi
} > "$SUMMARY_FILE"

# Final output
echo ""
cat "$SUMMARY_FILE"

if [ "$DETERMINISM_PASS" -eq 1 ]; then
    echo ""
    echo "DETERMINISM TEST PASSED"
    exit 0
else
    echo ""
    echo "DETERMINISM TEST FAILED"
    exit 1
fi
