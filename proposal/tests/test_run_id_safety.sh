#!/usr/bin/env bash
#
# Phase M-1: Run-ID Safety Tests
#
# Tests that the proposal generator wrapper correctly rejects unsafe run-id values.
# All tests should exit with non-zero status for invalid run-ids.
#

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GENERATOR="$REPO_ROOT/scripts/generate_proposals.sh"

PASS=0
FAIL=0

# Test helper
test_run_id() {
    local description="$1"
    local run_id="$2"
    local expect_fail="$3"  # "fail" or "pass"

    # Run generator with the run-id, capture exit code
    echo "test" | "$GENERATOR" --input - --run-id "$run_id" > /dev/null 2>&1
    local exit_code=$?

    if [[ "$expect_fail" == "fail" ]]; then
        if [[ $exit_code -ne 0 ]]; then
            echo "PASS: $description (correctly rejected)"
            ((PASS++))
        else
            echo "FAIL: $description (should have been rejected)"
            ((FAIL++))
        fi
    else
        if [[ $exit_code -eq 0 ]]; then
            echo "PASS: $description (correctly accepted)"
            ((PASS++))
        else
            echo "FAIL: $description (should have been accepted)"
            ((FAIL++))
        fi
    fi
}

echo "=== Run-ID Safety Tests ==="
echo ""

# Valid run-ids (should pass)
test_run_id "Simple alphanumeric" "test123" "pass"
test_run_id "With underscore" "test_run" "pass"
test_run_id "With hyphen" "test-run" "pass"
test_run_id "With dot" "test.run" "pass"
test_run_id "Mixed valid chars" "Test_Run-1.0" "pass"
test_run_id "Max length (64 chars)" "$(printf 'a%.0s' {1..64})" "pass"

# Invalid run-ids (should fail)
test_run_id "Empty string" "" "fail"
test_run_id "Contains slash" "test/run" "fail"
test_run_id "Contains backslash" 'test\run' "fail"
test_run_id "Contains space" "test run" "fail"
test_run_id "Contains colon" "test:run" "fail"
test_run_id "Path traversal .." "../test" "fail"
test_run_id "Absolute path attempt" "/tmp/test" "fail"
test_run_id "Too long (65 chars)" "$(printf 'a%.0s' {1..65})" "fail"
test_run_id "Contains asterisk" "test*run" "fail"
test_run_id "Contains question mark" "test?run" "fail"
test_run_id "Contains angle bracket" "test<run" "fail"
test_run_id "Contains pipe" "test|run" "fail"
test_run_id "Contains quotes" 'test"run' "fail"

echo ""
echo "=== Results ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
