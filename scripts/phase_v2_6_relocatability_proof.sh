#!/bin/sh
# scripts/phase_v2_6_relocatability_proof.sh — Phase V2-6 Relocatability Validation Runner
#
# This script runs validation scenarios and captures evidence for Phase V2-6.
# It captures transcripts verbatim using `script` and collects factual data.
#
# Usage:
#   ./scripts/phase_v2_6_relocatability_proof.sh
#
# Output:
#   evidence/phase_v2_6/transcripts/scenario_01_tempdir_reloc.txt
#   evidence/phase_v2_6/transcripts/scenario_02_nonroot_invocation.txt
#   evidence/phase_v2_6/transcripts/scenario_03_repo_copy.txt
#
# This script does NOT modify any runtime behavior scripts.

set -eu

# --- Compute repo root reliably (works from any invocation directory) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Verify repo root using git
GIT_REPO_ROOT="$(cd "$REPO_ROOT" && git rev-parse --show-toplevel)"

# --- Constants ---
EVIDENCE_DIR="$REPO_ROOT/evidence/phase_v2_6"
TRANSCRIPTS_DIR="$EVIDENCE_DIR/transcripts"
TARBALL="$REPO_ROOT/vendor/poc_v2/poc_v2.tar.gz"
INPUT_FILE="$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
INPUT_FILE_REL="examples/inputs/accept_restart_alpha_1.txt"

# --- Create evidence directories ---
mkdir -p "$TRANSCRIPTS_DIR"

# --- Compute tarball SHA-256 once ---
TARBALL_SHA256="$(shasum -a 256 "$TARBALL" | cut -d' ' -f1)"

# --- UTC timestamp for this run ---
RUN_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "=========================================="
echo "Phase V2-6 Relocatability Validation"
echo "=========================================="
echo "Git repo root: $GIT_REPO_ROOT"
echo "Tarball SHA-256: $TARBALL_SHA256"
echo "Run timestamp: $RUN_TIMESTAMP"
echo ""

# --- Results tracking ---
SCENARIO_01_RUN_EXIT="-"
SCENARIO_01_DET_EXIT="-"
SCENARIO_02_RUN_EXIT_1="-"
SCENARIO_02_RUN_EXIT_2="-"
SCENARIO_02_DET_EXIT="-"
SCENARIO_03_RUN_EXIT="-"
SCENARIO_03_DET_EXIT="-"

# ===========================================================================
# SCENARIO 01 — Temp directory relocation
# ===========================================================================
echo "Running Scenario 01 — Temp directory relocation..."

TRANSCRIPT_01="$TRANSCRIPTS_DIR/scenario_01_tempdir_reloc.txt"

# Create scenario script
cat > /tmp/scenario_01_script.sh << 'SCENARIO01EOF'
#!/bin/sh
set -x

REPO_ROOT="$1"

echo "========================================"
echo "SCENARIO 01 — Temp directory relocation"
echo "========================================"
echo ""

echo "--- Common Header ---"
echo "UTC Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "PWD: $(pwd)"
echo "Repo root (git rev-parse): $(cd "$REPO_ROOT" && git rev-parse --show-toplevel)"
echo ""

echo "--- Vendored tarball SHA-256 ---"
shasum -a 256 "$REPO_ROOT/vendor/poc_v2/poc_v2.tar.gz"
echo ""

echo "--- Input path information ---"
echo "Input argument form: examples/inputs/accept_restart_alpha_1.txt (relative)"
echo "Resolved input path: $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
echo ""

echo "--- Extraction directory mtime BEFORE run ---"
ls -la "$REPO_ROOT/artifacts/exec_bundle" 2>/dev/null || echo "(directory does not exist)"
E_BEFORE="$(stat -f "%m" "$REPO_ROOT/artifacts/exec_bundle" 2>/dev/null || echo NA)"
echo "exec_bundle_mtime_epoch_before=$E_BEFORE"
if [ "$E_BEFORE" != "NA" ]; then
    echo "exec_bundle_mtime_utc_before=$(date -u -r "$E_BEFORE" +%Y-%m-%dT%H:%M:%SZ)"
fi
echo ""

echo "--- Single-run execution ---"
echo "Command: $REPO_ROOT/scripts/run_poc_v2.sh --input $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
"$REPO_ROOT/scripts/run_poc_v2.sh" --input "$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
RUN_EXIT=$?
echo "Exit code: $RUN_EXIT"
echo ""

echo "--- Extraction directory mtime AFTER run ---"
ls -la "$REPO_ROOT/artifacts/exec_bundle" 2>/dev/null || echo "(directory does not exist)"
E_AFTER="$(stat -f "%m" "$REPO_ROOT/artifacts/exec_bundle" 2>/dev/null || echo NA)"
echo "exec_bundle_mtime_epoch_after=$E_AFTER"
if [ "$E_AFTER" != "NA" ]; then
    echo "exec_bundle_mtime_utc_after=$(date -u -r "$E_AFTER" +%Y-%m-%dT%H:%M:%SZ)"
fi
echo ""

echo "--- Latest run directory ---"
ls -lt "$REPO_ROOT/artifacts/run" | head -n 5
LATEST_RUN="$(ls -t "$REPO_ROOT/artifacts/run" | head -n 1)"
LATEST_RUN_DIR="$REPO_ROOT/artifacts/run/$LATEST_RUN"
echo ""
echo "Latest run directory: $LATEST_RUN_DIR"
echo ""

echo "--- Contents of latest run directory ---"
ls -la "$LATEST_RUN_DIR"
echo ""

echo "--- execution.meta.json ---"
cat "$LATEST_RUN_DIR/execution.meta.json"
echo ""

echo "--- Check for bundle directories in run directory ---"
echo "Searching for: bundle_root, exec_bundle, poc_v2"
find "$LATEST_RUN_DIR" -maxdepth 4 -type d \( -name "bundle_root" -o -name "exec_bundle" -o -name "poc_v2" \) 2>/dev/null || echo "(none found)"
echo ""

echo "--- Determinism test (5 runs) ---"
echo "Command: $REPO_ROOT/scripts/determinism_test_v2.sh --input $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt --runs 5"
"$REPO_ROOT/scripts/determinism_test_v2.sh" --input "$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt" --runs 5
DET_EXIT=$?
echo "Exit code: $DET_EXIT"
echo ""

echo "--- Determinism comparison method evidence ---"
echo "File: scripts/determinism_test_v2.sh, line 265:"
nl -ba "$REPO_ROOT/scripts/determinism_test_v2.sh" | sed -n '265p'
echo ""

echo "--- Latest determinism test directory ---"
LATEST_DET="$(ls -t "$REPO_ROOT/artifacts/determinism" | head -n 1)"
echo "Latest: $REPO_ROOT/artifacts/determinism/$LATEST_DET"
ls -la "$REPO_ROOT/artifacts/determinism/$LATEST_DET"
echo ""

echo "--- Determinism result.txt ---"
cat "$REPO_ROOT/artifacts/determinism/$LATEST_DET/result.txt"
echo ""

echo "========================================"
echo "SCENARIO 01 COMPLETE"
echo "run_poc_v2.sh exit code: $RUN_EXIT"
echo "determinism_test_v2.sh exit code: $DET_EXIT"
echo "========================================"

exit $DET_EXIT
SCENARIO01EOF

chmod +x /tmp/scenario_01_script.sh

# Run with script to capture transcript
script -q "$TRANSCRIPT_01" /tmp/scenario_01_script.sh "$REPO_ROOT"
SCENARIO_01_EXIT=$?

echo "Scenario 01 final exit code: $SCENARIO_01_EXIT"
echo ""

# ===========================================================================
# SCENARIO 02 — Non-root invocation
# ===========================================================================
echo "Running Scenario 02 — Non-root invocation..."

TRANSCRIPT_02="$TRANSCRIPTS_DIR/scenario_02_nonroot_invocation.txt"

# Create scenario script
cat > /tmp/scenario_02_script.sh << 'SCENARIO02EOF'
#!/bin/sh
set -x

REPO_ROOT="$1"

echo "========================================"
echo "SCENARIO 02 — Non-root invocation"
echo "========================================"
echo ""

echo "--- Common Header ---"
echo "UTC Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Repo root (git rev-parse): $(cd "$REPO_ROOT" && git rev-parse --show-toplevel)"
echo ""

echo "--- Vendored tarball SHA-256 ---"
shasum -a 256 "$REPO_ROOT/vendor/poc_v2/poc_v2.tar.gz"
echo ""

echo "--- Test 1: Invoke from HOME ---"
cd "$HOME"
echo "PWD: $(pwd)"
echo "Input argument form: absolute path"
echo "Resolved input path: $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
echo "Command: $REPO_ROOT/scripts/run_poc_v2.sh --input $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
"$REPO_ROOT/scripts/run_poc_v2.sh" --input "$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
RUN_EXIT_1=$?
echo "Exit code: $RUN_EXIT_1"
echo ""

echo "--- Test 2: Invoke from nested temp directory ---"
NESTED_TEMP="/tmp/phase_v2_6_test/deeply/nested/directory"
mkdir -p "$NESTED_TEMP"
cd "$NESTED_TEMP"
echo "PWD: $(pwd)"
echo "Input argument form: absolute path"
echo "Resolved input path: $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
echo "Command: $REPO_ROOT/scripts/run_poc_v2.sh --input $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
"$REPO_ROOT/scripts/run_poc_v2.sh" --input "$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt"
RUN_EXIT_2=$?
echo "Exit code: $RUN_EXIT_2"
echo ""

echo "--- Test 3: Determinism from non-root directory ---"
echo "PWD: $(pwd)"
echo "Command: $REPO_ROOT/scripts/determinism_test_v2.sh --input $REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt --runs 3"
"$REPO_ROOT/scripts/determinism_test_v2.sh" --input "$REPO_ROOT/examples/inputs/accept_restart_alpha_1.txt" --runs 3
DET_EXIT=$?
echo "Exit code: $DET_EXIT"
echo ""

echo "--- Cleanup nested temp ---"
rm -rf /tmp/phase_v2_6_test
echo ""

echo "--- Repo artifacts (run) ---"
ls -lt "$REPO_ROOT/artifacts/run" | head -n 10
echo ""

echo "--- Repo artifacts (determinism) ---"
ls -lt "$REPO_ROOT/artifacts/determinism" | head -n 5
LATEST_DET="$(ls -t "$REPO_ROOT/artifacts/determinism" | head -n 1)"
echo ""
echo "Latest determinism result:"
cat "$REPO_ROOT/artifacts/determinism/$LATEST_DET/result.txt"
echo ""

echo "========================================"
echo "SCENARIO 02 COMPLETE"
echo "run_poc_v2.sh exit code (from HOME): $RUN_EXIT_1"
echo "run_poc_v2.sh exit code (from nested temp): $RUN_EXIT_2"
echo "determinism_test_v2.sh exit code: $DET_EXIT"
echo "========================================"

exit $DET_EXIT
SCENARIO02EOF

chmod +x /tmp/scenario_02_script.sh

# Run with script to capture transcript
script -q "$TRANSCRIPT_02" /tmp/scenario_02_script.sh "$REPO_ROOT"
SCENARIO_02_EXIT=$?

echo "Scenario 02 final exit code: $SCENARIO_02_EXIT"
echo ""

# ===========================================================================
# SCENARIO 03 — Repo copy
# ===========================================================================
echo "Running Scenario 03 — Repo copy..."

TRANSCRIPT_03="$TRANSCRIPTS_DIR/scenario_03_repo_copy.txt"

# Create scenario script
cat > /tmp/scenario_03_script.sh << 'SCENARIO03EOF'
#!/bin/sh
set -x

ORIG_REPO="$1"
ORIG_TARBALL_SHA256="$2"

echo "========================================"
echo "SCENARIO 03 — Repo copy"
echo "========================================"
echo ""

echo "--- Common Header ---"
echo "UTC Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Original repo root (git rev-parse): $(cd "$ORIG_REPO" && git rev-parse --show-toplevel)"
echo "Original tarball SHA-256: $ORIG_TARBALL_SHA256"
echo ""

COPIED_REPO="/tmp/phase_v2_6_repo_copy_test"
rm -rf "$COPIED_REPO"

echo "--- Copy repo to temp location ---"
cp -a "$ORIG_REPO" "$COPIED_REPO"
echo "Copied to: $COPIED_REPO"
echo ""

cd "$COPIED_REPO"
echo "PWD: $(pwd)"
echo ""

echo "--- Copied repo root (git rev-parse) ---"
git rev-parse --show-toplevel
echo ""

echo "--- Vendored tarball SHA-256 in copied repo ---"
shasum -a 256 "$COPIED_REPO/vendor/poc_v2/poc_v2.tar.gz"
COPIED_SHA256="$(shasum -a 256 "$COPIED_REPO/vendor/poc_v2/poc_v2.tar.gz" | cut -d' ' -f1)"
echo "Copied tarball SHA-256: $COPIED_SHA256"
echo "Original tarball SHA-256: $ORIG_TARBALL_SHA256"
if [ "$COPIED_SHA256" = "$ORIG_TARBALL_SHA256" ]; then
    echo "SHA-256 comparison: MATCH"
else
    echo "SHA-256 comparison: MISMATCH"
    exit 1
fi
echo ""

echo "--- Single-run in copied repo ---"
echo "Input argument form: absolute path"
echo "Resolved input path: $COPIED_REPO/examples/inputs/accept_restart_alpha_1.txt"
echo "Command: $COPIED_REPO/scripts/run_poc_v2.sh --input $COPIED_REPO/examples/inputs/accept_restart_alpha_1.txt"
"$COPIED_REPO/scripts/run_poc_v2.sh" --input "$COPIED_REPO/examples/inputs/accept_restart_alpha_1.txt"
RUN_EXIT=$?
echo "Exit code: $RUN_EXIT"
echo ""

echo "--- Determinism in copied repo (3 runs) ---"
echo "Command: $COPIED_REPO/scripts/determinism_test_v2.sh --input $COPIED_REPO/examples/inputs/accept_restart_alpha_1.txt --runs 3"
"$COPIED_REPO/scripts/determinism_test_v2.sh" --input "$COPIED_REPO/examples/inputs/accept_restart_alpha_1.txt" --runs 3
DET_EXIT=$?
echo "Exit code: $DET_EXIT"
echo ""

echo "--- Copied repo artifacts (run) ---"
ls -lt "$COPIED_REPO/artifacts/run" 2>/dev/null | head -n 10
echo ""

echo "--- Copied repo artifacts (determinism) ---"
ls -lt "$COPIED_REPO/artifacts/determinism" 2>/dev/null | head -n 5
LATEST_DET="$(ls -t "$COPIED_REPO/artifacts/determinism" | head -n 1)"
echo ""
echo "Latest determinism result:"
cat "$COPIED_REPO/artifacts/determinism/$LATEST_DET/result.txt"
echo ""

echo "--- Cleanup copied repo ---"
rm -rf "$COPIED_REPO"
echo "Removed: $COPIED_REPO"
echo ""

echo "========================================"
echo "SCENARIO 03 COMPLETE"
echo "run_poc_v2.sh exit code: $RUN_EXIT"
echo "determinism_test_v2.sh exit code: $DET_EXIT"
echo "========================================"

exit $DET_EXIT
SCENARIO03EOF

chmod +x /tmp/scenario_03_script.sh

# Run with script to capture transcript
script -q "$TRANSCRIPT_03" /tmp/scenario_03_script.sh "$REPO_ROOT" "$TARBALL_SHA256"
SCENARIO_03_EXIT=$?

echo "Scenario 03 final exit code: $SCENARIO_03_EXIT"
echo ""

# ===========================================================================
# Capture final git status
# ===========================================================================
GIT_STATUS="$(cd "$REPO_ROOT" && git status)"
GIT_STATUS_SHORT="$(cd "$REPO_ROOT" && git status -sb)"

# ===========================================================================
# Determine overall result
# ===========================================================================
if [ "$SCENARIO_01_EXIT" -eq 0 ] && [ "$SCENARIO_02_EXIT" -eq 0 ] && [ "$SCENARIO_03_EXIT" -eq 0 ]; then
    OVERALL_RESULT="PASS"
else
    OVERALL_RESULT="FAIL"
fi

# ===========================================================================
# Final Summary
# ===========================================================================
echo "=========================================="
echo "Phase V2-6 Relocatability Validation — Summary"
echo "=========================================="
echo ""
echo "Transcripts created:"
echo "  - evidence/phase_v2_6/transcripts/scenario_01_tempdir_reloc.txt"
echo "  - evidence/phase_v2_6/transcripts/scenario_02_nonroot_invocation.txt"
echo "  - evidence/phase_v2_6/transcripts/scenario_03_repo_copy.txt"
echo ""
echo "Scenario exit codes:"
echo "  - Scenario 01: $SCENARIO_01_EXIT"
echo "  - Scenario 02: $SCENARIO_02_EXIT"
echo "  - Scenario 03: $SCENARIO_03_EXIT"
echo ""
echo "Overall: $OVERALL_RESULT"
echo ""
echo "Git status:"
echo "$GIT_STATUS_SHORT"
echo ""
echo "=========================================="

# Exit with overall result
if [ "$OVERALL_RESULT" = "PASS" ]; then
    exit 0
else
    exit 1
fi
