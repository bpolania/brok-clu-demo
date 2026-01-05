#!/bin/sh
set -eu

BUNDLE_DIR="bundles/poc_v1"
MANIFEST="$BUNDLE_DIR/MANIFEST.txt"
CHECKSUMS="$BUNDLE_DIR/SHA256SUMS"
BINARY="$BUNDLE_DIR/bin/macos-arm64/cmd_interpreter"

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
    exit 1
}

fail_usage() {
    echo "Usage: $0 <input-file>" >&2
    exit 2
}

# Require exactly one argument
[ $# -eq 1 ] || fail_usage
INPUT_FILE="$1"

# Verify input file exists and is readable
[ -f "$INPUT_FILE" ] || { echo "ERROR: Input file not found: $INPUT_FILE" >&2; exit 2; }
[ -r "$INPUT_FILE" ] || { echo "ERROR: Input file not readable: $INPUT_FILE" >&2; exit 2; }

# A) Verification enforcement

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
# Get sorted list of files from manifest (non-empty lines)
grep -v '^$' "$MANIFEST" | sort > "$MANIFEST_TMP"

# Get sorted list of actual files under bundle dir (excluding MANIFEST.txt and SHA256SUMS)
(cd "$BUNDLE_DIR" && find . -type f ! -name 'MANIFEST.txt' ! -name 'SHA256SUMS' | sed 's|^\./||' | sort) > "$FILES_TMP"

# Compare
if ! diff -q "$MANIFEST_TMP" "$FILES_TMP" >/dev/null 2>&1; then
    # Find extra files
    EXTRA=$(comm -13 "$MANIFEST_TMP" "$FILES_TMP" | head -1)
    if [ -n "$EXTRA" ]; then
        fail_verification "Extra file not in manifest: $EXTRA"
    fi
    # Find missing files (should have been caught above, but be thorough)
    MISSING=$(comm -23 "$MANIFEST_TMP" "$FILES_TMP" | head -1)
    if [ -n "$MISSING" ]; then
        fail_verification "File in manifest does not exist: $MISSING"
    fi
fi

# 4. SHA-256 verification
(cd "$BUNDLE_DIR" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || fail_verification "Checksum mismatch"

# B) Controlled execution (verification passed)

# Invoke cmd_interpreter with --input argument
set +e
"$BINARY" --input "$INPUT_FILE" >"$STDOUT_TMP" 2>"$STDERR_TMP"
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    # Success: emit stdout exactly
    cat "$STDOUT_TMP"
else
    # Failure: surface stderr, do not emit stdout
    cat "$STDERR_TMP" >&2
    exit $EXIT_CODE
fi
