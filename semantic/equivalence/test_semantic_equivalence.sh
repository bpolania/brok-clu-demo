#!/bin/sh
# semantic/equivalence/test_semantic_equivalence.sh
# Phase S-5: Acceptance Tests for Semantic Equivalence CLI
#
# Tests the semantic_equivalence.sh CLI against synthetic stdout.raw.kv files.
# Does NOT touch real runtime artifacts.
#
# Exit 0 if all tests pass, non-zero if any test fails.
#
# Terminology: Uses "matching" not "identical/same/equal" per S-5 constraints.

set -eu

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/../scripts/semantic_equivalence.sh"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Temp directory for synthetic files
TEST_TMP=""

# -----------------------------------------------------------------------------
# Setup and Teardown
# -----------------------------------------------------------------------------

setup() {
    TEST_TMP=$(mktemp -d)
    if [ ! -d "$TEST_TMP" ]; then
        echo "FATAL: Cannot create temp directory" >&2
        exit 1
    fi
}

teardown() {
    if [ -n "$TEST_TMP" ] && [ -d "$TEST_TMP" ]; then
        rm -rf "$TEST_TMP"
    fi
}

trap teardown EXIT

# -----------------------------------------------------------------------------
# Test Helpers
# -----------------------------------------------------------------------------

create_kv_file() {
    dir="$1"
    name="$2"
    content="$3"

    mkdir -p "$dir/$name"
    echo "$content" > "$dir/$name/stdout.raw.kv"
}

run_test() {
    test_name="$1"
    expected_exit="$2"
    expected_pattern="$3"
    shift 3

    TESTS_RUN=$((TESTS_RUN + 1))

    # Capture output and exit code
    set +e
    output=$("$CLI_SCRIPT" "$@" 2>&1)
    actual_exit=$?
    set -e

    # Check exit code
    if [ "$actual_exit" -ne "$expected_exit" ]; then
        echo "FAIL: $test_name"
        echo "  Expected exit: $expected_exit, got: $actual_exit"
        echo "  Output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Check output pattern (if provided)
    if [ -n "$expected_pattern" ]; then
        if ! echo "$output" | grep -q "$expected_pattern"; then
            echo "FAIL: $test_name"
            echo "  Expected pattern: $expected_pattern"
            echo "  Output: $output"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    fi

    echo "PASS: $test_name"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
}

# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

test_equivalent_matching_runs() {
    # Two runs with matching (status, intent_id, n_slots) => EQUIVALENT
    create_kv_file "$TEST_TMP" "run_a" "status=OK
intent_id=14
n_slots=0
dispatch=unknown"

    create_kv_file "$TEST_TMP" "run_b" "status=OK
intent_id=14
n_slots=0
dispatch=different"

    run_test "matching signatures => EQUIVALENT" \
        0 \
        "EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_a" "$TEST_TMP/run_b"
}

test_equivalent_three_runs() {
    # Three runs with matching signatures
    create_kv_file "$TEST_TMP" "run_c" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_d" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_e" "status=OK
intent_id=14
n_slots=0"

    run_test "three matching signatures => EQUIVALENT" \
        0 \
        "EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_c" "$TEST_TMP/run_d" "$TEST_TMP/run_e"
}

test_not_equivalent_status_differs() {
    # Two runs with different status
    create_kv_file "$TEST_TMP" "run_f" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_g" "status=ERROR
intent_id=14
n_slots=0"

    run_test "different status => NOT_EQUIVALENT" \
        0 \
        "NOT_EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_f" "$TEST_TMP/run_g"
}

test_not_equivalent_intent_differs() {
    # Two runs with different intent_id
    create_kv_file "$TEST_TMP" "run_h" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_i" "status=OK
intent_id=99
n_slots=0"

    run_test "different intent_id => NOT_EQUIVALENT" \
        0 \
        "NOT_EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_h" "$TEST_TMP/run_i"
}

test_not_equivalent_nslots_differs() {
    # Two runs with different n_slots
    create_kv_file "$TEST_TMP" "run_j" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_k" "status=OK
intent_id=14
n_slots=5"

    run_test "different n_slots => NOT_EQUIVALENT" \
        0 \
        "NOT_EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_j" "$TEST_TMP/run_k"
}

test_undecidable_missing_status() {
    # One run missing status
    create_kv_file "$TEST_TMP" "run_l" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_m" "intent_id=14
n_slots=0"

    run_test "missing status => UNDECIDABLE" \
        0 \
        "UNDECIDABLE_UNDER_RULE_V1" \
        "$TEST_TMP/run_l" "$TEST_TMP/run_m"
}

test_undecidable_missing_intent_id() {
    # One run missing intent_id
    create_kv_file "$TEST_TMP" "run_n" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_o" "status=OK
n_slots=0"

    run_test "missing intent_id => UNDECIDABLE" \
        0 \
        "UNDECIDABLE_UNDER_RULE_V1" \
        "$TEST_TMP/run_n" "$TEST_TMP/run_o"
}

test_undecidable_missing_n_slots() {
    # One run missing n_slots
    create_kv_file "$TEST_TMP" "run_p" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_q" "status=OK
intent_id=14"

    run_test "missing n_slots => UNDECIDABLE" \
        0 \
        "UNDECIDABLE_UNDER_RULE_V1" \
        "$TEST_TMP/run_p" "$TEST_TMP/run_q"
}

test_invalid_path_nonexistent() {
    # Invalid path should fail
    run_test "nonexistent path => exit non-zero" \
        1 \
        "Cannot resolve" \
        "$TEST_TMP/nonexistent" "$TEST_TMP/also_nonexistent"
}

test_single_input_fails() {
    # Single input should fail
    create_kv_file "$TEST_TMP" "run_r" "status=OK
intent_id=14
n_slots=0"

    run_test "single input => exit non-zero" \
        1 \
        "At least 2" \
        "$TEST_TMP/run_r"
}

test_no_inputs_fails() {
    # No inputs should fail
    run_test "no inputs => exit non-zero" \
        1 \
        "At least 2"
}

test_direct_file_path() {
    # Direct path to stdout.raw.kv
    create_kv_file "$TEST_TMP" "run_s" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_t" "status=OK
intent_id=14
n_slots=0"

    run_test "direct file paths => EQUIVALENT" \
        0 \
        "EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_s/stdout.raw.kv" "$TEST_TMP/run_t/stdout.raw.kv"
}

test_dispatch_ignored() {
    # Dispatch key should be ignored
    create_kv_file "$TEST_TMP" "run_u" "status=OK
intent_id=14
n_slots=0
dispatch=action_a"

    create_kv_file "$TEST_TMP" "run_v" "status=OK
intent_id=14
n_slots=0
dispatch=action_b"

    run_test "different dispatch => still EQUIVALENT (ignored key)" \
        0 \
        "EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_u" "$TEST_TMP/run_v"
}

test_extra_keys_ignored() {
    # Extra keys should be ignored
    create_kv_file "$TEST_TMP" "run_w" "status=OK
intent_id=14
n_slots=0
extra_key=value1
another_key=value2"

    create_kv_file "$TEST_TMP" "run_x" "status=OK
intent_id=14
n_slots=0"

    run_test "extra keys ignored => EQUIVALENT" \
        0 \
        "EQUIVALENT_UNDER_RULE_V1" \
        "$TEST_TMP/run_w" "$TEST_TMP/run_x"
}

test_disclaimer_present() {
    # Disclaimer should always be present
    create_kv_file "$TEST_TMP" "run_y" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_z" "status=OK
intent_id=14
n_slots=0"

    run_test "disclaimer present in output" \
        0 \
        "Equivalence here is defined by rule, not by meaning" \
        "$TEST_TMP/run_y" "$TEST_TMP/run_z"
}

test_determinism_distinction_present() {
    # Determinism vs equivalence distinction should be present
    create_kv_file "$TEST_TMP" "run_det1" "status=OK
intent_id=14
n_slots=0"

    create_kv_file "$TEST_TMP" "run_det2" "status=OK
intent_id=14
n_slots=0"

    run_test "determinism vs equivalence distinction present" \
        0 \
        "Determinism means the same input produces the same bytes" \
        "$TEST_TMP/run_det1" "$TEST_TMP/run_det2"
}

test_duplicate_status_key_fails() {
    # Duplicate status key should cause operational failure
    create_kv_file "$TEST_TMP" "run_dup1" "status=OK
intent_id=14
n_slots=0"

    # Create file with duplicate status key
    mkdir -p "$TEST_TMP/run_dup2"
    cat > "$TEST_TMP/run_dup2/stdout.raw.kv" <<EOF
status=OK
intent_id=14
n_slots=0
status=ERROR
EOF

    run_test "duplicate status key => exit non-zero" \
        1 \
        "Duplicate 'status' key" \
        "$TEST_TMP/run_dup1" "$TEST_TMP/run_dup2"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

echo "========================================================================"
echo "Phase S-5: Semantic Equivalence CLI Acceptance Tests"
echo "========================================================================"
echo ""

# Verify CLI script exists
if [ ! -x "$CLI_SCRIPT" ]; then
    echo "FATAL: CLI script not found or not executable: $CLI_SCRIPT" >&2
    exit 1
fi

# Setup temp directory
setup

# Run all tests
test_equivalent_matching_runs
test_equivalent_three_runs
test_not_equivalent_status_differs
test_not_equivalent_intent_differs
test_not_equivalent_nslots_differs
test_undecidable_missing_status
test_undecidable_missing_intent_id
test_undecidable_missing_n_slots
test_invalid_path_nonexistent
test_single_input_fails
test_no_inputs_fails
test_direct_file_path
test_dispatch_ignored
test_extra_keys_ignored
test_disclaimer_present
test_determinism_distinction_present
test_duplicate_status_key_fails

# Summary
echo ""
echo "========================================================================"
echo "Test Summary"
echo "========================================================================"
echo "Tests run:    $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ "$TESTS_FAILED" -gt 0 ]; then
    echo "RESULT: FAILED"
    exit 1
fi

echo "RESULT: PASSED"
exit 0
