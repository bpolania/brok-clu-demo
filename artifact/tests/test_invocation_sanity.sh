#!/usr/bin/env bash
#
# Sanity tests for PoC v2 invocation in run_brok.sh
#
# Verifies:
# 1. run_brok.sh invokes run_poc_v2.sh with --input <file> only
# 2. No "route parameters" or other flags are passed to PoC v2
# 3. build_artifact.sh rejects absolute paths in --input-ref
#
# These tests ensure critical constraints do not regress.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    echo "PASS: $1"
    ((PASS_COUNT++)) || true
}

fail() {
    echo "FAIL: $1"
    ((FAIL_COUNT++)) || true
}

echo "=== Invocation Sanity Tests ==="
echo ""

# Test 1: run_brok.sh must invoke run_poc_v2.sh with --input only
echo "--- Test: run_brok.sh PoC v2 invocation form ---"

# Extract the line that invokes run_poc_v2.sh
INVOCATION_LINE=$(grep -E 'run_poc_v2\.sh' "$REPO_ROOT/scripts/run_brok.sh" | grep -v '^#' || true)

if [[ -z "$INVOCATION_LINE" ]]; then
    fail "Could not find run_poc_v2.sh invocation in run_brok.sh"
else
    # Check it uses --input flag
    if echo "$INVOCATION_LINE" | grep -q '\-\-input'; then
        pass "run_brok.sh invokes run_poc_v2.sh with --input flag"
    else
        fail "run_brok.sh invocation missing --input flag"
    fi

    # Check NO route parameters (--intent, --target, --mode)
    if echo "$INVOCATION_LINE" | grep -qE '\-\-(intent|target|mode|route)'; then
        fail "run_brok.sh passes route parameters to run_poc_v2.sh (PROHIBITED)"
    else
        pass "run_brok.sh does not pass route parameters to run_poc_v2.sh"
    fi

    # Check no extra flags beyond --input
    # The invocation should be: run_poc_v2.sh --input <something>
    # Count flags (words starting with --)
    FLAG_COUNT=$(echo "$INVOCATION_LINE" | grep -oE '\-\-[a-z]+' | wc -l | tr -d ' ')
    if [[ "$FLAG_COUNT" -eq 1 ]]; then
        pass "run_brok.sh uses exactly one flag (--input) for run_poc_v2.sh"
    else
        fail "run_brok.sh uses $FLAG_COUNT flags for run_poc_v2.sh (expected 1)"
    fi
fi

echo ""
echo "--- Test: build_artifact.sh rejects absolute paths ---"

# Test that build_artifact.sh rejects absolute input-ref
OUTPUT=$(cd "$REPO_ROOT" && ./scripts/build_artifact.sh \
    --proposal-set "artifacts/proposals/test/proposal_set.json" \
    --run-id "sanity_test" \
    --input-ref "/tmp/absolute.txt" 2>&1 || true)

if echo "$OUTPUT" | grep -q "must be repo-relative"; then
    pass "build_artifact.sh rejects absolute --input-ref"
else
    fail "build_artifact.sh did not reject absolute --input-ref"
fi

echo ""
echo "--- Test: run_brok.sh handles external inputs ---"

# Check that run_brok.sh copies external inputs to artifacts/inputs/
if grep -q 'artifacts/inputs/' "$REPO_ROOT/scripts/run_brok.sh"; then
    pass "run_brok.sh handles external inputs via artifacts/inputs/"
else
    fail "run_brok.sh does not handle external inputs (missing artifacts/inputs/)"
fi

# Check the copy logic exists (cp command and ARTIFACT_INPUT_DIR variable)
if grep -qE 'cp.*\$ARTIFACT_INPUT_DIR' "$REPO_ROOT/scripts/run_brok.sh" && \
   grep -qE 'ARTIFACT_INPUT_DIR=.*artifacts/inputs' "$REPO_ROOT/scripts/run_brok.sh"; then
    pass "run_brok.sh copies external inputs to artifacts/inputs/"
else
    fail "run_brok.sh missing cp command for external inputs"
fi

echo ""
echo "=== Results ==="
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi
exit 0
