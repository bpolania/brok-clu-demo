#!/bin/sh
# scripts/verify_poc_v2.sh — PoC v2 Verification Wrapper
#
# Phase V2-2: Verification Wiring
#
# This script:
#   1. Verifies the vendored tarball SHA-256 against SHA256SUMS.vendor
#   2. Extracts the bundle to a timestamped artifacts directory
#   3. Discovers the canonical verification entrypoint
#   4. Invokes verification and captures results
#
# Usage: scripts/verify_poc_v2.sh
#        (can be run from any directory)
#
# Exit codes:
#   0   - Verification passed
#   1   - Wrapper-internal failure (hash mismatch, missing files, ambiguous entrypoint)
#   N   - PoC v2 verify entrypoint exited with code N (propagated verbatim)
#
# Testing (without modifying vendored tarball):
#
#   1. Success path:
#      ./scripts/verify_poc_v2.sh && echo "PASS"
#
#   2. Nonzero exit propagation:
#      The wrapper propagates the exact exit code from PoC v2's verify entrypoint.
#      To test: if PoC v2 verify exits 10, wrapper exits 10 (not 1).
#      Verify by checking: cat artifacts/verify/run_*/exit_code.txt
#
#   3. Ambiguous entrypoint detection (logic test):
#      The script searches for: verify.sh, VERIFY.sh, bin/verify, scripts/verify.sh
#      If >1 exist and are executable, it fails with "Ambiguous verification entrypoints".
#      This is tested by the discovery loop at lines 93-112.
#
#   4. Capture under failure:
#      Even if verify fails, stdout.txt, stderr.txt, exit_code.txt, and meta.json
#      are written before the wrapper exits. Verify by inducing a verify failure
#      and checking the capture directory exists with all files.
#
#   5. Wrapper-internal failure (negative test):
#      BROK_CLU_V2_TEST_EXTRACT_READONLY=1 ./scripts/verify_poc_v2.sh
#      Makes extraction directory read-only before tar runs, forcing extraction
#      failure (exit 1) with full capture files written to VERIFY_DIR.
#      TEST ONLY - never touches vendor/, operates only on artifacts/.
#      Permissions are restored via trap on exit.
#
# Capture file semantics:
#   The files stdout.txt, stderr.txt, exit_code.txt, meta.json in artifacts/verify/
#   are DEMO-OWNED capture evidence for audit/debug only. They are NOT PoC v2
#   verification artifacts and are never used to infer verification success.

set -eu

# --- Compute repo root reliably ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Constants ---
VENDOR_DIR="$REPO_ROOT/vendor/poc_v2"
TARBALL="$VENDOR_DIR/poc_v2.tar.gz"
SHASUMS="$VENDOR_DIR/SHA256SUMS.vendor"
ARTIFACTS_BASE="$REPO_ROOT/artifacts"

# --- Generate UTC timestamp (filesystem-safe) ---
UTC_TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# --- Directories for this run ---
EXTRACT_DIR="$ARTIFACTS_BASE/poc_v2_extracted/run_$UTC_TIMESTAMP/bundle_root"
VERIFY_DIR="$ARTIFACTS_BASE/verify/run_$UTC_TIMESTAMP"

# --- TEST ONLY: Permissions-based failure hook (V2-2 audit evidence) ---
# If BROK_CLU_V2_TEST_EXTRACT_READONLY=1, makes extraction parent dir read-only
# before tar runs, forcing extraction failure. VERIFY_DIR remains writable so
# fail() can write capture artifacts.
# - Never touches vendor/
# - Only operates on artifacts/ paths
# - Disabled by default; inert unless explicitly enabled
# - Permissions restored via trap
_TEST_READONLY_DIR=""
_TEST_ORIGINAL_PERMS=""

_test_cleanup() {
    if [ -n "$_TEST_READONLY_DIR" ] && [ -n "$_TEST_ORIGINAL_PERMS" ]; then
        chmod "$_TEST_ORIGINAL_PERMS" "$_TEST_READONLY_DIR" 2>/dev/null || true
    fi
}
trap _test_cleanup EXIT

# --- Helper: fail with message and capture artifacts ---
fail() {
    _FAIL_MSG="$1"
    echo "VERIFICATION FAILED: $_FAIL_MSG" >&2
    # Write capture artifacts for wrapper-internal failures
    if [ -n "${VERIFY_DIR:-}" ]; then
        mkdir -p "$VERIFY_DIR"
        echo "" > "$VERIFY_DIR/stdout.txt"
        echo "$_FAIL_MSG" > "$VERIFY_DIR/stderr.txt"
        echo "1" > "$VERIFY_DIR/exit_code.txt"
        cat > "$VERIFY_DIR/meta.json" << FAILMETA
{
  "tarball_sha256": "${ACTUAL_HASH:-unknown}",
  "extraction_path": "${EXTRACT_DIR:-unknown}",
  "bundle_root": "${BUNDLE_ROOT:-unknown}",
  "entrypoint_path": null,
  "utc_timestamp": "$UTC_TIMESTAMP",
  "invocation_cwd": "$(pwd)",
  "exit_code": 1,
  "bundle_artifact_paths": [],
  "wrapper_failure": "$_FAIL_MSG"
}
FAILMETA
        echo "Capture directory: $VERIFY_DIR" >&2
    fi
    exit 1
}

# --- Step 1: Verify tarball exists ---
if [ ! -f "$TARBALL" ]; then
    fail "Vendored tarball not found: $TARBALL"
fi

if [ ! -f "$SHASUMS" ]; then
    fail "SHA256SUMS.vendor not found: $SHASUMS"
fi

# --- Step 2: Create output directories ---
mkdir -p "$EXTRACT_DIR"
mkdir -p "$VERIFY_DIR"

# --- TEST ONLY: Activate permissions-based failure if requested ---
if [ "${BROK_CLU_V2_TEST_EXTRACT_READONLY:-}" = "1" ]; then
    echo "TEST MODE: Making extraction directory read-only to force tar failure" >&2
    _TEST_READONLY_DIR="$EXTRACT_DIR"
    # Store original permissions (macOS/POSIX compatible)
    _TEST_ORIGINAL_PERMS="$(stat -f '%Lp' "$EXTRACT_DIR" 2>/dev/null || stat -c '%a' "$EXTRACT_DIR" 2>/dev/null || echo '755')"
    chmod 555 "$EXTRACT_DIR"
fi

# --- Step 3: Verify tarball SHA-256 ---
EXPECTED_HASH="$(grep 'poc_v2.tar.gz' "$SHASUMS" | awk '{print $1}')"
if [ -z "$EXPECTED_HASH" ]; then
    fail "Could not find poc_v2.tar.gz hash in SHA256SUMS.vendor"
fi

ACTUAL_HASH="$(shasum -a 256 "$TARBALL" | awk '{print $1}')"

if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
    echo "Expected: $EXPECTED_HASH" >&2
    echo "Actual:   $ACTUAL_HASH" >&2
    fail "Tarball SHA-256 mismatch"
fi

echo "Tarball SHA-256 verified: $ACTUAL_HASH"

# --- Step 4: Extract tarball ---
echo "Extracting to: $EXTRACT_DIR"

# Use portable tar flags (no GNU-specific options)
# Extract into bundle_root, stripping any single top-level directory if present
if ! tar -xzf "$TARBALL" -C "$EXTRACT_DIR" 2>/dev/null; then
    fail "Extraction failed (tar could not write to $EXTRACT_DIR)"
fi

# Check if extraction created a single top-level directory
EXTRACTED_ITEMS="$(ls -A "$EXTRACT_DIR")"
ITEM_COUNT="$(echo "$EXTRACTED_ITEMS" | wc -l | tr -d ' ')"

if [ "$ITEM_COUNT" -eq 1 ] && [ -d "$EXTRACT_DIR/$EXTRACTED_ITEMS" ]; then
    # Single directory extracted - this is the bundle root content
    BUNDLE_ROOT="$EXTRACT_DIR/$EXTRACTED_ITEMS"
else
    # Multiple items or files directly - bundle_root is the extraction dir itself
    BUNDLE_ROOT="$EXTRACT_DIR"
fi

echo "Bundle root: $BUNDLE_ROOT"

# --- Step 5: Discover verification entrypoint ---
VERIFY_CANDIDATES=""
VERIFY_COUNT=0

for CANDIDATE in "verify.sh" "VERIFY.sh" "bin/verify" "scripts/verify.sh"; do
    FULL_PATH="$BUNDLE_ROOT/$CANDIDATE"
    if [ -f "$FULL_PATH" ] && [ -x "$FULL_PATH" ]; then
        VERIFY_CANDIDATES="${VERIFY_CANDIDATES}${VERIFY_CANDIDATES:+ }$CANDIDATE"
        VERIFY_COUNT=$((VERIFY_COUNT + 1))
        VERIFY_ENTRYPOINT="$FULL_PATH"
    fi
done

if [ "$VERIFY_COUNT" -eq 0 ]; then
    fail "No verification entrypoint found. Searched for: verify.sh, VERIFY.sh, bin/verify, scripts/verify.sh"
fi

if [ "$VERIFY_COUNT" -gt 1 ]; then
    fail "Ambiguous verification entrypoints found: $VERIFY_CANDIDATES"
fi

echo "Verification entrypoint: $VERIFY_ENTRYPOINT"

# --- Step 6: Invoke verification ---
echo "Invoking PoC v2 verification..."

STDOUT_FILE="$VERIFY_DIR/stdout.txt"
STDERR_FILE="$VERIFY_DIR/stderr.txt"
EXIT_CODE_FILE="$VERIFY_DIR/exit_code.txt"
META_FILE="$VERIFY_DIR/meta.json"

INVOCATION_CWD="$(pwd)"

# Run verification from within the bundle root
set +e
(cd "$BUNDLE_ROOT" && "$VERIFY_ENTRYPOINT") >"$STDOUT_FILE" 2>"$STDERR_FILE"
VERIFY_EXIT_CODE=$?
set -e

echo "$VERIFY_EXIT_CODE" > "$EXIT_CODE_FILE"

# --- Step 7: Copy any bundle-produced artifacts (before writing meta.json) ---
# Check for common artifact locations in the bundle
# This is conditional: only copy if directories exist, do not fail if absent
BUNDLE_ARTIFACTS_DIR="$VERIFY_DIR/bundle_artifacts"
DISCOVERED_ARTIFACT_PATHS=""

for ARTIFACT_PATH in "$BUNDLE_ROOT/artifacts" "$BUNDLE_ROOT/output" "$BUNDLE_ROOT/verify_output" "$BUNDLE_ROOT/bundles/verified"; do
    if [ -d "$ARTIFACT_PATH" ]; then
        mkdir -p "$BUNDLE_ARTIFACTS_DIR"
        cp -R "$ARTIFACT_PATH" "$BUNDLE_ARTIFACTS_DIR/" 2>/dev/null || true
        # Record discovered path (relative to bundle root)
        REL_PATH="${ARTIFACT_PATH#$BUNDLE_ROOT/}"
        DISCOVERED_ARTIFACT_PATHS="${DISCOVERED_ARTIFACT_PATHS}${DISCOVERED_ARTIFACT_PATHS:+, }\"$REL_PATH\""
    fi
done

# Default to empty array if no artifacts found
if [ -z "$DISCOVERED_ARTIFACT_PATHS" ]; then
    DISCOVERED_ARTIFACT_PATHS_JSON="[]"
else
    DISCOVERED_ARTIFACT_PATHS_JSON="[$DISCOVERED_ARTIFACT_PATHS]"
fi

# --- Step 8: Write meta.json ---
cat > "$META_FILE" << METAEOF
{
  "tarball_sha256": "$ACTUAL_HASH",
  "extraction_path": "$EXTRACT_DIR",
  "bundle_root": "$BUNDLE_ROOT",
  "entrypoint_path": "$VERIFY_ENTRYPOINT",
  "utc_timestamp": "$UTC_TIMESTAMP",
  "invocation_cwd": "$INVOCATION_CWD",
  "exit_code": $VERIFY_EXIT_CODE,
  "bundle_artifact_paths": $DISCOVERED_ARTIFACT_PATHS_JSON
}
METAEOF

# --- Step 9: Report result ---
echo ""
echo "Capture directory: $VERIFY_DIR"
echo ""

if [ "$VERIFY_EXIT_CODE" -eq 0 ]; then
    echo "VERIFICATION PASSED"
    echo ""
    cat "$STDOUT_FILE"
    exit 0
else
    echo "VERIFICATION FAILED (exit code: $VERIFY_EXIT_CODE)"
    echo ""
    echo "=== stdout ==="
    cat "$STDOUT_FILE"
    echo ""
    echo "=== stderr ==="
    cat "$STDERR_FILE"
    # Propagate the actual verify exit code, not a hardcoded 1
    exit "$VERIFY_EXIT_CODE"
fi
