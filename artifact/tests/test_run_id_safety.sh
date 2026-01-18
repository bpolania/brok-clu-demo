#!/usr/bin/env bash
#
# Phase M-2: Run-ID Safety Tests
#
# Tests that build_artifact.sh and run_brok.sh correctly reject unsafe run-id values.
#

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_ARTIFACT="$REPO_ROOT/scripts/build_artifact.sh"
RUN_BROK="$REPO_ROOT/scripts/run_brok.sh"

# Create a minimal test fixture
TEST_DIR="$REPO_ROOT/artifacts/test_fixtures"
mkdir -p "$TEST_DIR"

# Create a minimal valid proposal_set.json for testing
cat > "$TEST_DIR/proposal_set.json" << 'EOF'
{
  "schema_version": "m1.0",
  "input": {"raw": "test"},
  "proposals": []
}
EOF

# Create a minimal input file for testing
echo "test input" > "$TEST_DIR/input.txt"

PASS=0
FAIL=0

# Test helper for build_artifact.sh
test_build_artifact_run_id() {
    local description="$1"
    local run_id="$2"
    local expect_fail="$3"

    "$BUILD_ARTIFACT" \
        --proposal-set "$TEST_DIR/proposal_set.json" \
        --run-id "$run_id" \
        --input-ref "test/input.txt" > /dev/null 2>&1
    local exit_code=$?

    if [[ "$expect_fail" == "fail" ]]; then
        if [[ $exit_code -ne 0 ]]; then
            echo "PASS: build_artifact.sh - $description (correctly rejected)"
            ((PASS++))
        else
            echo "FAIL: build_artifact.sh - $description (should have been rejected)"
            ((FAIL++))
        fi
    else
        if [[ $exit_code -eq 0 ]]; then
            echo "PASS: build_artifact.sh - $description (correctly accepted)"
            ((PASS++))
        else
            echo "FAIL: build_artifact.sh - $description (should have been accepted)"
            ((FAIL++))
        fi
    fi
}

# Test helper for run_brok.sh
test_run_brok_run_id() {
    local description="$1"
    local run_id="$2"
    local expect_fail="$3"

    "$RUN_BROK" \
        --input "$TEST_DIR/input.txt" \
        --run-id "$run_id" > /dev/null 2>&1
    local exit_code=$?

    if [[ "$expect_fail" == "fail" ]]; then
        if [[ $exit_code -ne 0 ]]; then
            echo "PASS: run_brok.sh - $description (correctly rejected)"
            ((PASS++))
        else
            echo "FAIL: run_brok.sh - $description (should have been rejected)"
            ((FAIL++))
        fi
    else
        # For valid run-ids, run_brok.sh may return 0 (REJECT decision is OK)
        # We just check it doesn't fail with exit code 1 (usage error)
        if [[ $exit_code -ne 1 ]]; then
            echo "PASS: run_brok.sh - $description (correctly accepted)"
            ((PASS++))
        else
            echo "FAIL: run_brok.sh - $description (should have been accepted)"
            ((FAIL++))
        fi
    fi
}

echo "=== Run-ID Safety Tests for build_artifact.sh ==="
echo ""

# Valid run-ids (should pass)
test_build_artifact_run_id "Simple alphanumeric" "test123" "pass"
test_build_artifact_run_id "With underscore" "test_run" "pass"
test_build_artifact_run_id "With hyphen" "test-run" "pass"
test_build_artifact_run_id "With dot" "test.run" "pass"
test_build_artifact_run_id "Mixed valid chars" "Test_Run-1.0" "pass"

# Invalid run-ids (should fail)
test_build_artifact_run_id "Empty string" "" "fail"
test_build_artifact_run_id "Contains slash" "test/run" "fail"
test_build_artifact_run_id "Contains space" "test run" "fail"
test_build_artifact_run_id "Path traversal .." "../test" "fail"
test_build_artifact_run_id "Absolute path attempt" "/tmp/test" "fail"
test_build_artifact_run_id "Too long (65 chars)" "$(printf 'a%.0s' {1..65})" "fail"

echo ""
echo "=== Run-ID Safety Tests for run_brok.sh ==="
echo ""

# Valid run-ids (should pass)
test_run_brok_run_id "Simple alphanumeric" "brok_test123" "pass"
test_run_brok_run_id "With underscore" "brok_test_run" "pass"
test_run_brok_run_id "With hyphen" "brok_test-run" "pass"

# Invalid run-ids (should fail)
test_run_brok_run_id "Empty string" "" "fail"
test_run_brok_run_id "Contains slash" "brok/test" "fail"
test_run_brok_run_id "Path traversal .." "../brok" "fail"

echo ""
echo "=== Results ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

# Cleanup test fixtures
rm -rf "$TEST_DIR"
rm -rf "$REPO_ROOT/artifacts/artifacts/test"*
rm -rf "$REPO_ROOT/artifacts/artifacts/brok"*
rm -rf "$REPO_ROOT/artifacts/proposals/brok"*

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
