#!/usr/bin/env python3
"""
Phase L-7 Locator Contract Tests (Closure-Grade)

Tests the expanded discovery mechanism that uses SHA256 matching
when delta-only discovery fails.

Test Matrix (Required):
1. Delta-only success path (L-6 behavior preserved)
2. Expanded discovery success path (unique SHA256 match)
3. Expanded discovery NONE (no stdout.raw.kv files)
4. Expanded discovery AMBIGUOUS (multiple SHA256 matches)
5. Determinism (identical outputs for identical inputs)

L-7 Contract:
- Allowed inputs: manifest.json (written by ./brok), stdout.raw.kv files under artifacts/run/
- Forbidden: timestamps, mtimes, file ordering, heuristics
- Outcomes: unique (exactly 1 match), none (0 matches), ambiguous (>1 matches)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Resolve paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_BROK_RUN_PATH = os.path.join(_REPO_ROOT, "brok-run")
_RUN_ROOT = os.path.join(_REPO_ROOT, "artifacts", "run")


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_wrapper(args: list) -> tuple:
    """Run ./brok-run with given args. Returns (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [_BROK_RUN_PATH] + args,
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT
    )
    return result.stdout, result.stderr, result.returncode


def create_temp_run_root():
    """Create a temporary run root for isolated testing."""
    return tempfile.mkdtemp(prefix="l7_test_run_root_")


def cleanup_temp_dir(path: str):
    """Safely remove a temporary directory."""
    if path and os.path.isdir(path) and path.startswith(tempfile.gettempdir()):
        shutil.rmtree(path)


# =============================================================================
# L-7 Locator Function Tests (Unit Tests)
# =============================================================================

# Import locator functions from brok-run
sys.path.insert(0, _REPO_ROOT)

def get_locator_functions():
    """Import L-7 locator functions from brok-run by executing the file."""
    import types
    module = types.ModuleType("brok_run")
    module.__file__ = _BROK_RUN_PATH
    with open(_BROK_RUN_PATH, 'r') as f:
        code = f.read()
    exec(compile(code, _BROK_RUN_PATH, 'exec'), module.__dict__)
    return module


def test_l7_scan_determinism():
    """
    L-7: Scanning stdout.raw.kv files must be deterministic.

    The scan must use sorted() on directory names to ensure iteration
    order is alphabetical, not dependent on OS file ordering.
    """
    module = get_locator_functions()

    # Run scan twice on actual run root
    results1 = module._scan_all_stdout_raw_kv(_RUN_ROOT)
    results2 = module._scan_all_stdout_raw_kv(_RUN_ROOT)

    # Results must be identical (same order, same content)
    assert len(results1) == len(results2), "Scan results length differs"

    for i, (path1, hash1) in enumerate(results1):
        path2, hash2 = results2[i]
        assert path1 == path2, f"Path mismatch at index {i}: {path1} != {path2}"
        assert hash1 == hash2, f"Hash mismatch at index {i}: {hash1} != {hash2}"

    print("[PASS] L-7: Scan is deterministic (sorted directory iteration)")


def test_l7_sha256_matching():
    """
    L-7: SHA256 matching must be exact and deterministic.
    """
    module = get_locator_functions()

    # Create test candidates
    candidates = [
        ("/path/a/stdout.raw.kv", "abc123"),
        ("/path/b/stdout.raw.kv", "def456"),
        ("/path/c/stdout.raw.kv", "abc123"),  # Duplicate hash
    ]

    # Test exact match
    matches = module._find_by_sha256("def456", candidates)
    assert len(matches) == 1, f"Expected 1 match for unique hash, got {len(matches)}"
    assert matches[0] == "/path/b/stdout.raw.kv"

    # Test multiple matches
    matches = module._find_by_sha256("abc123", candidates)
    assert len(matches) == 2, f"Expected 2 matches for duplicate hash, got {len(matches)}"

    # Test no match
    matches = module._find_by_sha256("nonexistent", candidates)
    assert len(matches) == 0, f"Expected 0 matches for nonexistent hash, got {len(matches)}"

    print("[PASS] L-7: SHA256 matching is exact and deterministic")


def test_l7_expanded_discovery_no_sha256_in_manifest():
    """
    L-7: If manifest has no stdout.raw.kv SHA256, outcome is NONE.
    """
    module = get_locator_functions()

    # Manifest without stdout.raw.kv entry
    manifest = {
        "artifacts": [
            {"type": "artifact", "path": "some/path", "sha256": "abc"}
        ]
    }

    outcome, path, details = module._expanded_discovery(manifest, _RUN_ROOT)

    assert outcome == module.LOCATOR_NONE, f"Expected NONE, got {outcome}"
    assert path is None, "Path should be None for NONE outcome"
    assert details.get("reason") == "no_sha256_in_manifest"

    print("[PASS] L-7: No SHA256 in manifest → NONE outcome")


def test_l7_expanded_discovery_unique_match():
    """
    L-7 TARGET SUCCESS CASE: Expanded discovery finds unique match.

    This test demonstrates the L-7 success path:
    - Manifest contains stdout.raw.kv SHA256
    - Exactly ONE file under run_root matches that SHA256
    - Outcome is UNIQUE (authoritative_found)

    Uses isolated fixture directory to guarantee uniqueness.
    """
    module = get_locator_functions()

    # Create isolated test directory
    test_run_root = create_temp_run_root()
    try:
        # Create a single execution directory with stdout.raw.kv
        exec_dir = os.path.join(test_run_root, "l4_run_test_unique")
        os.makedirs(exec_dir)

        # Write unique content to stdout.raw.kv
        stdout_path = os.path.join(exec_dir, "stdout.raw.kv")
        unique_content = b"L7_TEST_UNIQUE_CONTENT_12345\n"
        with open(stdout_path, 'wb') as f:
            f.write(unique_content)

        # Compute the SHA256 of this unique content
        expected_sha256 = sha256_file(stdout_path)

        # Create manifest that references this SHA256
        manifest = {
            "artifacts": [
                {"type": "stdout.raw.kv", "sha256": expected_sha256}
            ]
        }

        # Run expanded discovery
        outcome, found_path, details = module._expanded_discovery(manifest, test_run_root)

        # Assertions for success case
        assert outcome == module.LOCATOR_UNIQUE, (
            f"Expected UNIQUE outcome, got {outcome}. Details: {details}"
        )
        assert found_path is not None, "Found path should not be None for UNIQUE"
        assert found_path == stdout_path, (
            f"Found path mismatch. Expected: {stdout_path}, Got: {found_path}"
        )
        assert details.get("reason") == "unique_sha256_match", (
            f"Expected reason 'unique_sha256_match', got: {details.get('reason')}"
        )
        assert details.get("candidates_scanned") == 1, (
            f"Expected 1 candidate scanned, got: {details.get('candidates_scanned')}"
        )

        # Verify the found file's hash matches
        actual_sha256 = sha256_file(found_path)
        assert actual_sha256 == expected_sha256, (
            f"SHA256 mismatch. Expected: {expected_sha256}, Actual: {actual_sha256}"
        )

        print("[PASS] L-7 TARGET SUCCESS: Expanded discovery → UNIQUE (authoritative_found)")

    finally:
        cleanup_temp_dir(test_run_root)


def test_l7_expanded_discovery_ambiguous():
    """
    L-7 AMBIGUOUS CASE: Multiple files match the same SHA256.

    This test demonstrates correct AMBIGUOUS handling:
    - Two files have identical content (same SHA256)
    - Outcome is AMBIGUOUS (wrapper refuses to select)
    """
    module = get_locator_functions()

    # Create isolated test directory
    test_run_root = create_temp_run_root()
    try:
        # Create two directories with identical stdout.raw.kv content
        for i in range(2):
            exec_dir = os.path.join(test_run_root, f"l4_run_duplicate_{i}")
            os.makedirs(exec_dir)
            stdout_path = os.path.join(exec_dir, "stdout.raw.kv")
            # Same content = same SHA256
            with open(stdout_path, 'wb') as f:
                f.write(b"IDENTICAL_CONTENT\n")

        # Get the SHA256 of the duplicate content
        first_stdout = os.path.join(test_run_root, "l4_run_duplicate_0", "stdout.raw.kv")
        duplicate_sha256 = sha256_file(first_stdout)

        # Create manifest referencing the duplicate SHA256
        manifest = {
            "artifacts": [
                {"type": "stdout.raw.kv", "sha256": duplicate_sha256}
            ]
        }

        # Run expanded discovery
        outcome, found_path, details = module._expanded_discovery(manifest, test_run_root)

        # Assertions for ambiguous case
        assert outcome == module.LOCATOR_AMBIGUOUS, (
            f"Expected AMBIGUOUS outcome, got {outcome}. Details: {details}"
        )
        assert found_path is None, "Found path should be None for AMBIGUOUS"
        assert details.get("reason") == "multiple_sha256_matches", (
            f"Expected reason 'multiple_sha256_matches', got: {details.get('reason')}"
        )
        assert details.get("match_count") == 2, (
            f"Expected 2 matches, got: {details.get('match_count')}"
        )

        print("[PASS] L-7 AMBIGUOUS: Multiple matches → wrapper refuses to select")

    finally:
        cleanup_temp_dir(test_run_root)


# =============================================================================
# L-7 Integration Tests (Using Actual Wrapper)
# =============================================================================

def test_l7_integration_reject():
    """
    L-7: REJECT invocation should have discovery_status='authoritative_not_found'.
    """
    stdout, stderr, exit_code = run_wrapper(["payment succeeded"])

    assert exit_code == 0, f"REJECT should exit 0, got {exit_code}"

    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    assert summary["decision"] == "REJECT"
    assert summary["discovery_status"] == "authoritative_not_found", (
        f"REJECT should have discovery_status='authoritative_not_found', got: {summary['discovery_status']}"
    )
    assert summary["authoritative_stdout_raw_kv"] is None

    print("[PASS] L-7 Integration: REJECT → authoritative_not_found")


def test_l7_integration_accept_expanded():
    """
    L-7: ACCEPT invocation with expanded discovery.

    When delta-only fails, wrapper uses SHA256 matching from manifest.
    Outcome depends on number of matching stdout.raw.kv files.
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    assert exit_code == 0, f"ACCEPT should exit 0, got {exit_code}"

    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    assert summary["decision"] == "ACCEPT"

    # discovery_status must be one of the valid values
    valid_statuses = ["authoritative_found", "authoritative_not_found", "authoritative_ambiguous"]
    assert summary["discovery_status"] in valid_statuses, (
        f"discovery_status must be one of {valid_statuses}, got: {summary['discovery_status']}"
    )

    # If found, path must exist and hash must match
    if summary["discovery_status"] == "authoritative_found":
        assert summary["authoritative_stdout_raw_kv"] is not None
        assert os.path.isfile(summary["authoritative_stdout_raw_kv"])
        actual_hash = sha256_file(summary["authoritative_stdout_raw_kv"])
        assert actual_hash == summary["authoritative_stdout_raw_kv_sha256"]
        print("[PASS] L-7 Integration: ACCEPT → authoritative_found (unique match)")
    elif summary["discovery_status"] == "authoritative_ambiguous":
        assert summary["authoritative_stdout_raw_kv"] is None
        assert lines[1] == "Authoritative output: AMBIGUOUS"
        print("[PASS] L-7 Integration: ACCEPT → authoritative_ambiguous (multiple matches)")
    else:
        assert summary["authoritative_stdout_raw_kv"] is None
        print("[PASS] L-7 Integration: ACCEPT → authoritative_not_found")


def test_l7_determinism():
    """
    L-7: Wrapper must produce identical outputs for identical inputs.

    This test runs the same invocation twice and verifies:
    - Same JSON fields (except run_dir which may differ)
    - Same discovery_status
    - Same authoritative_stdout_raw_kv (path or null)
    """
    # Run twice with same input
    stdout1, stderr1, exit1 = run_wrapper(["create payment"])
    stdout2, stderr2, exit2 = run_wrapper(["create payment"])

    # Parse outputs
    summary1 = json.loads(stdout1.strip().split('\n')[0])
    summary2 = json.loads(stdout2.strip().split('\n')[0])

    # Exit codes must match
    assert exit1 == exit2, f"Exit codes differ: {exit1} vs {exit2}"

    # Decision must match
    assert summary1["decision"] == summary2["decision"], (
        f"Decision differs: {summary1['decision']} vs {summary2['decision']}"
    )

    # discovery_status must match
    assert summary1["discovery_status"] == summary2["discovery_status"], (
        f"discovery_status differs: {summary1['discovery_status']} vs {summary2['discovery_status']}"
    )

    # authoritative_stdout_raw_kv must match (both null or both same path)
    assert summary1["authoritative_stdout_raw_kv"] == summary2["authoritative_stdout_raw_kv"], (
        f"authoritative_stdout_raw_kv differs: {summary1['authoritative_stdout_raw_kv']} vs {summary2['authoritative_stdout_raw_kv']}"
    )

    # SHA256 must match
    assert summary1["authoritative_stdout_raw_kv_sha256"] == summary2["authoritative_stdout_raw_kv_sha256"], (
        f"SHA256 differs: {summary1['authoritative_stdout_raw_kv_sha256']} vs {summary2['authoritative_stdout_raw_kv_sha256']}"
    )

    print("[PASS] L-7 Determinism: Identical inputs → identical outputs")


def test_l7_disclaimer_present():
    """
    L-7: Wrapper must print disclaimer about non-authoritative status.
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    assert "This wrapper is non-authoritative" in stderr, (
        "L-7 requires disclaimer about wrapper being non-authoritative"
    )
    assert "Discovery status does not imply execution truth" in stderr, (
        "L-7 requires disclaimer about discovery not implying execution"
    )

    print("[PASS] L-7: Disclaimer present on stderr")


def test_l7_no_timestamps_used():
    """
    L-7: Verify that no timestamps are used in discovery.

    This is a code inspection test - we verify the scan function
    does not call mtime, ctime, atime, or time-based sorting functions.
    Comments documenting what is NOT used are allowed.
    """
    module = get_locator_functions()

    import inspect
    scan_source = inspect.getsource(module._scan_all_stdout_raw_kv)

    # Remove comments (lines starting with #) for checking
    code_lines = [line for line in scan_source.split('\n')
                  if not line.strip().startswith('#') and not line.strip().startswith('"""')]
    code_only = '\n'.join(code_lines)

    # Check for forbidden function calls (not in comments)
    forbidden_calls = ["getmtime(", "getctime(", "getatime(",
                       "os.stat(", ".st_mtime", ".st_ctime", ".st_atime"]

    for pattern in forbidden_calls:
        assert pattern not in code_only, (
            f"L-7 violation: scan function contains forbidden call '{pattern}'"
        )

    # Verify sorted() is used for determinism
    assert "sorted(" in scan_source, (
        "L-7 requires sorted() for deterministic iteration"
    )

    print("[PASS] L-7: No timestamp functions called, sorted() present")


# =============================================================================
# L-7 Schema Lock Test
# =============================================================================

# L-7 Frozen Schema: exactly these 5 keys, no more, no less
L7_FROZEN_SCHEMA_KEYS = frozenset([
    "run_dir",
    "decision",
    "authoritative_stdout_raw_kv",
    "authoritative_stdout_raw_kv_sha256",
    "discovery_status",
])


def test_l7_schema_lock():
    """
    L-7 Schema Lock: Wrapper JSON must have exactly the frozen key set.

    This test will FAIL if any key is added or removed from the schema.
    The frozen schema is:
      - run_dir
      - decision
      - authoritative_stdout_raw_kv
      - authoritative_stdout_raw_kv_sha256
      - discovery_status
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    assert exit_code == 0, f"Wrapper should exit 0, got {exit_code}"

    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    actual_keys = frozenset(summary.keys())

    # Check for exact match
    assert actual_keys == L7_FROZEN_SCHEMA_KEYS, (
        f"L-7 schema violation!\n"
        f"  Expected keys: {sorted(L7_FROZEN_SCHEMA_KEYS)}\n"
        f"  Actual keys:   {sorted(actual_keys)}\n"
        f"  Missing: {sorted(L7_FROZEN_SCHEMA_KEYS - actual_keys)}\n"
        f"  Extra:   {sorted(actual_keys - L7_FROZEN_SCHEMA_KEYS)}"
    )

    print(f"[PASS] L-7 Schema Lock: Exactly {len(L7_FROZEN_SCHEMA_KEYS)} keys, frozen set verified")


def test_l7_manifest_origin_proof():
    """
    L-7 Manifest Origin Proof: manifest.json is written by ./brok, NOT by brok-run.

    This test proves:
    1. The manifest writer code (ManifestBuilder.write) is in m4/src/manifest.py
    2. This code is NOT in brok-run
    3. Therefore manifest.json is written by the ./brok pipeline

    Governance status: manifest.json is DERIVED observability output.
    It is NOT authoritative. The wrapper reads it for discovery hints only.
    """
    # Path to brok-run (wrapper)
    wrapper_path = _BROK_RUN_PATH

    # Path to manifest writer (in m4 pipeline)
    manifest_writer_path = os.path.join(_REPO_ROOT, "m4", "src", "manifest.py")

    # Verify manifest writer exists in pipeline code
    assert os.path.isfile(manifest_writer_path), (
        f"Manifest writer not found at expected location: {manifest_writer_path}"
    )

    # Read wrapper code
    with open(wrapper_path, 'r') as f:
        wrapper_code = f.read()

    # Read manifest writer code
    with open(manifest_writer_path, 'r') as f:
        manifest_code = f.read()

    # Proof 1: ManifestBuilder class exists in manifest.py
    assert "class ManifestBuilder" in manifest_code, (
        "ManifestBuilder class not found in m4/src/manifest.py"
    )

    # Proof 2: ManifestBuilder.write method exists
    assert "def write(self" in manifest_code, (
        "ManifestBuilder.write method not found in m4/src/manifest.py"
    )

    # Proof 3: Wrapper does NOT contain ManifestBuilder
    assert "class ManifestBuilder" not in wrapper_code, (
        "ManifestBuilder should NOT be in brok-run"
    )

    # Proof 4: Wrapper does NOT write manifest.json (only reads it)
    # Check that wrapper only has _read_manifest, not write operations
    assert "_read_manifest" in wrapper_code, (
        "Wrapper should have _read_manifest function"
    )
    assert "manifest.json\", \"w\"" not in wrapper_code, (
        "Wrapper should NOT write to manifest.json"
    )
    assert "ManifestBuilder" not in wrapper_code, (
        "Wrapper should NOT use ManifestBuilder"
    )

    # Proof 5: Manifest schema docstring states it's DERIVED
    assert "DERIVED" in manifest_code and "non-authoritative" in manifest_code, (
        "Manifest code should document DERIVED/non-authoritative status"
    )

    print("[PASS] L-7 Manifest Origin: Written by ./brok (m4/src/manifest.py), read-only by wrapper")


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all L-7 locator tests."""
    print("=" * 72)
    print("Phase L-7 Locator Contract Tests")
    print("=" * 72)
    print()

    tests = [
        # Unit tests
        ("1. Scan determinism", test_l7_scan_determinism),
        ("2. SHA256 matching", test_l7_sha256_matching),
        ("3. No SHA256 in manifest → NONE", test_l7_expanded_discovery_no_sha256_in_manifest),
        ("4. Expanded discovery → UNIQUE (target success)", test_l7_expanded_discovery_unique_match),
        ("5. Expanded discovery → AMBIGUOUS", test_l7_expanded_discovery_ambiguous),

        # Integration tests
        ("6. Integration: REJECT", test_l7_integration_reject),
        ("7. Integration: ACCEPT expanded", test_l7_integration_accept_expanded),
        ("8. Determinism", test_l7_determinism),
        ("9. Disclaimer present", test_l7_disclaimer_present),
        ("10. No timestamps used", test_l7_no_timestamps_used),

        # Schema lock test
        ("11. Schema lock", test_l7_schema_lock),

        # Manifest governance test
        ("12. Manifest origin proof", test_l7_manifest_origin_proof),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"--- {name} ---")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            failed += 1
        print()

    print("=" * 72)
    print(f"Tests: {passed}/{passed + failed} passed")
    if failed == 0:
        print("All L-7 locator tests PASSED")
    else:
        print(f"FAILED: {failed} test(s)")
    print("=" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
