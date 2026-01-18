#!/usr/bin/env python3
"""
Phase L-6 Path A Run Discovery Tests (Closure-Grade)

Verifies L-6 Path A contract: Delta-only authoritative selection

L-6 Path A Contract:
  - Multiple directories per invocation allowed
  - Authority selection based SOLELY on stdout.raw.kv presence IN DELTA
  - NO manifest-based derivation of execution directories
  - NO selection outside delta set
  - Three outcomes:
    1. Exactly 1 delta directory with stdout.raw.kv → use it
    2. 0 delta directories with stdout.raw.kv → no execution (authoritative=null)
    3. >1 delta directories with stdout.raw.kv → fail closed

These tests verify delta-only selection without relying on ./brok behavior.
"""

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

# Exit codes (must match brok-run)
EXIT_WRAPPER_FAILURE = 3


# =============================================================================
# L-6 Path A Discovery Functions (reference implementation for testing)
# These must match the logic in brok-run exactly - DELTA ONLY
# =============================================================================

def _snapshot_run_dirs(run_root: str) -> set:
    """Snapshot immediate child directories of run root."""
    if not os.path.isdir(run_root):
        return set()
    return set(os.listdir(run_root))


def _compute_delta(before: set, after: set) -> set:
    """Compute newly created directories."""
    return after - before


def _find_authoritative_dirs(new_dirs: set, run_root: str) -> list:
    """
    Find directories containing stdout.raw.kv in DELTA ONLY.

    L-6 Path A contract: authority is determined solely by presence of
    stdout.raw.kv in newly created directories (delta set).

    Does NOT search outside delta.
    Does NOT derive from manifests.
    Does NOT use directory name patterns.

    Returns list of absolute paths to directories containing stdout.raw.kv.
    """
    authoritative = []
    for dir_name in new_dirs:
        dir_path = os.path.join(run_root, dir_name)
        stdout_path = os.path.join(dir_path, "stdout.raw.kv")
        if os.path.isfile(stdout_path):
            authoritative.append(dir_path)
    return authoritative


def _find_observability_dir(new_dirs: set, run_root: str) -> str | None:
    """
    Find an observability directory (one with manifest.json but no stdout.raw.kv).

    Used to determine run_dir when no execution occurred.
    """
    for dir_name in new_dirs:
        dir_path = os.path.join(run_root, dir_name)
        manifest_path = os.path.join(dir_path, "manifest.json")
        stdout_path = os.path.join(dir_path, "stdout.raw.kv")
        if os.path.isfile(manifest_path) and not os.path.isfile(stdout_path):
            return dir_path
    return None


# =============================================================================
# Test Utilities
# =============================================================================

def create_temp_run_root():
    """Create a temporary run root for isolated testing."""
    return tempfile.mkdtemp(prefix="l6_test_run_root_")


def create_mock_directory(run_root: str, name: str, has_stdout_raw_kv: bool = False,
                          has_manifest: bool = True, decision: str = "ACCEPT"):
    """
    Create a mock run directory with specified properties.

    Args:
        run_root: Parent directory for run directories
        name: Directory name
        has_stdout_raw_kv: Whether to create stdout.raw.kv file
        has_manifest: Whether to create manifest.json
        decision: Decision value for artifact.json
    """
    dir_path = os.path.join(run_root, name)
    os.makedirs(dir_path, exist_ok=True)

    if has_stdout_raw_kv:
        stdout_path = os.path.join(dir_path, "stdout.raw.kv")
        with open(stdout_path, 'w') as f:
            f.write("mock stdout output\n")

    if has_manifest:
        # Create minimal manifest pointing to artifact
        artifact_rel_path = f"artifacts/run/{name}/artifact.json"
        manifest = {
            "artifacts": [
                {"type": "artifact", "path": artifact_rel_path}
            ]
        }
        manifest_path = os.path.join(dir_path, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        # Create artifact.json with decision
        artifact_path = os.path.join(dir_path, "artifact.json")
        artifact = {"decision": decision}
        with open(artifact_path, 'w') as f:
            json.dump(artifact, f)

    return dir_path


def cleanup_temp_dir(path: str):
    """Safely remove a temporary directory."""
    if path and os.path.isdir(path) and path.startswith(tempfile.gettempdir()):
        shutil.rmtree(path)


# =============================================================================
# L-6 Path A Scenario 1: Multi-directory delta, single authoritative
# =============================================================================

def test_l6_scenario1_multi_dir_single_authoritative():
    """
    Scenario 1: Multiple directories in delta, exactly one has stdout.raw.kv.

    Path A contract: Wrapper selects the single authoritative directory.
    """
    run_root = create_temp_run_root()
    try:
        # Create 3 directories in delta: 2 observability-only, 1 authoritative
        create_mock_directory(run_root, "dir_obs_1", has_stdout_raw_kv=False)
        create_mock_directory(run_root, "dir_obs_2", has_stdout_raw_kv=False)
        create_mock_directory(run_root, "dir_auth", has_stdout_raw_kv=True)

        new_dirs = {"dir_obs_1", "dir_obs_2", "dir_auth"}

        # Test authority selection
        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        # Exactly 1 authoritative directory
        assert len(authoritative) == 1, (
            f"Scenario 1: Expected 1 authoritative dir, got {len(authoritative)}"
        )

        # Correct directory selected (by stdout.raw.kv presence)
        assert authoritative[0].endswith("dir_auth"), (
            f"Scenario 1: Wrong directory selected. Got: {authoritative[0]}"
        )

        print("[PASS] Scenario 1: Multi-dir delta, single authoritative selected")

    finally:
        cleanup_temp_dir(run_root)


def test_l6_scenario1_selection_by_file_not_name():
    """
    Scenario 1 variant: Selection is by stdout.raw.kv presence, not dir name.

    Path A contract: Directory names (m4_*, l4_*, etc.) must NOT influence selection.
    """
    run_root = create_temp_run_root()
    try:
        # Misleading names: put stdout.raw.kv in dir named "observability"
        create_mock_directory(run_root, "l4_run_fake", has_stdout_raw_kv=False)
        create_mock_directory(run_root, "observability_has_exec", has_stdout_raw_kv=True)
        create_mock_directory(run_root, "random_dir", has_stdout_raw_kv=False)

        new_dirs = {"l4_run_fake", "observability_has_exec", "random_dir"}

        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        # Must select by stdout.raw.kv, not by name pattern
        assert len(authoritative) == 1, "Expected 1 authoritative dir"
        assert authoritative[0].endswith("observability_has_exec"), (
            f"Selection must be by file presence, not name. Got: {authoritative[0]}"
        )

        print("[PASS] Scenario 1: Selection by stdout.raw.kv presence, not name")

    finally:
        cleanup_temp_dir(run_root)


# =============================================================================
# L-6 Path A Scenario 2: Observability-only (no authoritative in delta)
# =============================================================================

def test_l6_scenario2_no_authoritative_in_delta():
    """
    Scenario 2: Multiple directories in delta, none have stdout.raw.kv.

    Path A contract: Wrapper reports authoritative=null, does NOT fail,
    does NOT attempt to derive execution directory from manifest.
    """
    run_root = create_temp_run_root()
    try:
        # Create directories without stdout.raw.kv
        create_mock_directory(run_root, "dir_1", has_stdout_raw_kv=False, decision="REJECT")
        create_mock_directory(run_root, "dir_2", has_stdout_raw_kv=False, decision="REJECT")

        new_dirs = {"dir_1", "dir_2"}

        # Test authority selection
        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        # Zero authoritative directories - valid state under Path A
        assert len(authoritative) == 0, (
            f"Scenario 2: Expected 0 authoritative dirs, got {len(authoritative)}"
        )

        # Observability directory should still be findable for run_dir
        obs_dir = _find_observability_dir(new_dirs, run_root)
        assert obs_dir is not None, "Scenario 2: Should find observability dir for run_dir"

        print("[PASS] Scenario 2: No authoritative in delta, valid state")

    finally:
        cleanup_temp_dir(run_root)


def test_l6_scenario2_single_dir_no_stdout():
    """
    Scenario 2 variant: Single directory in delta, no stdout.raw.kv.

    Path A contract: Wrapper must NOT fail due to "expected 1 dir".
    Multiple dirs allowed; 0 authoritative is valid.
    """
    run_root = create_temp_run_root()
    try:
        # Create single observability directory
        create_mock_directory(run_root, "single_dir", has_stdout_raw_kv=False, decision="REJECT")

        new_dirs = {"single_dir"}

        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        # Zero authoritative is valid
        assert len(authoritative) == 0, "Expected 0 authoritative dirs"

        # Observability dir findable
        obs_dir = _find_observability_dir(new_dirs, run_root)
        assert obs_dir is not None, "Should find observability dir"

        print("[PASS] Scenario 2: Single dir, no stdout.raw.kv, valid state")

    finally:
        cleanup_temp_dir(run_root)


# =============================================================================
# L-6 Path A Scenario 3: Contract violation (multiple authoritative)
# =============================================================================

def test_l6_scenario3_multiple_authoritative():
    """
    Scenario 3: Multiple directories in delta have stdout.raw.kv.

    Path A contract: This is a contract violation. Wrapper must fail closed.
    """
    run_root = create_temp_run_root()
    try:
        # Create multiple directories with stdout.raw.kv (violation)
        create_mock_directory(run_root, "auth_1", has_stdout_raw_kv=True)
        create_mock_directory(run_root, "auth_2", has_stdout_raw_kv=True)
        create_mock_directory(run_root, "obs_1", has_stdout_raw_kv=False)

        new_dirs = {"auth_1", "auth_2", "obs_1"}

        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        # Multiple authoritative directories = contract violation
        assert len(authoritative) > 1, (
            f"Scenario 3 setup: Expected >1 authoritative, got {len(authoritative)}"
        )

        print("[PASS] Scenario 3: Multiple authoritative detected (violation)")

    finally:
        cleanup_temp_dir(run_root)


def test_l6_scenario3_exact_count():
    """
    Scenario 3 variant: Verify exact count of authoritative directories.
    """
    run_root = create_temp_run_root()
    try:
        # Create exactly 3 authoritative directories
        for i in range(3):
            create_mock_directory(run_root, f"auth_{i}", has_stdout_raw_kv=True)

        new_dirs = {f"auth_{i}" for i in range(3)}

        authoritative = _find_authoritative_dirs(new_dirs, run_root)

        assert len(authoritative) == 3, f"Expected 3 authoritative, got {len(authoritative)}"

        print("[PASS] Scenario 3: Exact count verified (3 authoritative)")

    finally:
        cleanup_temp_dir(run_root)


# =============================================================================
# L-6 Path A Edge Cases
# =============================================================================

def test_l6_empty_delta():
    """
    Edge case: No new directories created (empty delta).
    """
    run_root = create_temp_run_root()
    try:
        new_dirs = set()  # Empty delta

        authoritative = _find_authoritative_dirs(new_dirs, run_root)
        assert len(authoritative) == 0, "Empty delta: 0 authoritative"

        obs_dir = _find_observability_dir(new_dirs, run_root)
        assert obs_dir is None, "Empty delta: no observability dir"

        print("[PASS] Edge: Empty delta handled correctly")

    finally:
        cleanup_temp_dir(run_root)


def test_l6_delta_computation():
    """
    Verify filesystem delta computation is correct.
    """
    run_root = create_temp_run_root()
    try:
        # Create initial state
        os.makedirs(os.path.join(run_root, "existing_dir"))

        before = _snapshot_run_dirs(run_root)
        assert "existing_dir" in before, "Before should include existing_dir"

        # Simulate new directories
        os.makedirs(os.path.join(run_root, "new_dir_1"))
        os.makedirs(os.path.join(run_root, "new_dir_2"))

        after = _snapshot_run_dirs(run_root)
        delta = _compute_delta(before, after)

        assert "new_dir_1" in delta, "Delta should include new_dir_1"
        assert "new_dir_2" in delta, "Delta should include new_dir_2"
        assert "existing_dir" not in delta, "Delta must NOT include existing_dir"
        assert len(delta) == 2, f"Delta should have 2 dirs, got {len(delta)}"

        print("[PASS] Edge: Delta computation correct")

    finally:
        cleanup_temp_dir(run_root)


# =============================================================================
# L-6 Path A Integration Tests
# =============================================================================

def test_l6_integration_reject():
    """
    Integration: REJECT invocation via actual wrapper.

    Path A: REJECT creates observability dir only, no stdout.raw.kv in delta.
    Wrapper should report authoritative=null.
    """
    result = subprocess.run(
        [_BROK_RUN_PATH, "payment succeeded"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT
    )

    # Should succeed (REJECT is valid)
    assert result.returncode == 0, (
        f"REJECT should exit 0, got {result.returncode}. stderr: {result.stderr}"
    )

    # Parse output
    lines = result.stdout.strip().split('\n')
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"

    summary = json.loads(lines[0])

    # Path A: REJECT has no stdout.raw.kv in delta
    assert summary["decision"] == "REJECT", f"Expected REJECT, got {summary['decision']}"
    assert summary["authoritative_stdout_raw_kv"] is None, "REJECT: authoritative must be null"
    assert summary["authoritative_stdout_raw_kv_sha256"] is None, "REJECT: sha256 must be null"
    assert lines[1] == "Authoritative output: NONE", f"Expected NONE, got: {lines[1]}"

    print("[PASS] Integration: REJECT (authoritative=null)")


def test_l6_integration_accept_delta_behavior():
    """
    Integration: ACCEPT invocation via actual wrapper.

    Path A contract: Wrapper reports authoritative output ONLY if stdout.raw.kv
    is found in newly created run directories (delta set).

    This test documents Path A behavior: we do NOT derive from manifests.

    L-6B CONTRACT BOUNDARY NOTE:
    - Observed condition: brok-run may report decision=ACCEPT while authoritative_stdout_raw_kv is null.
    - Path A explanation: delta-only discovery did not find stdout.raw.kv in newly created run directories.
    - Contract boundary: brok-run does not search outside the delta set under Path A.
    - A follow-on phase is required to address this gap.
    """
    result = subprocess.run(
        [_BROK_RUN_PATH, "create payment"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT
    )

    # Should succeed
    assert result.returncode == 0, (
        f"ACCEPT should exit 0, got {result.returncode}. stderr: {result.stderr}"
    )

    # Parse output
    lines = result.stdout.strip().split('\n')
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"

    summary = json.loads(lines[0])

    # Verify decision is ACCEPT
    assert summary["decision"] == "ACCEPT", f"Expected ACCEPT, got {summary['decision']}"

    # Path A: authoritative output depends on whether stdout.raw.kv was in delta
    # This is Path A contract behavior

    # Verify frozen schema has all 4 fields
    assert "run_dir" in summary, "Frozen schema requires run_dir"
    assert "decision" in summary, "Frozen schema requires decision"
    assert "authoritative_stdout_raw_kv" in summary, "Frozen schema requires authoritative_stdout_raw_kv"
    assert "authoritative_stdout_raw_kv_sha256" in summary, "Frozen schema requires sha256"

    # If authoritative is not null, verify it points to real file
    if summary["authoritative_stdout_raw_kv"] is not None:
        assert os.path.isfile(summary["authoritative_stdout_raw_kv"]), (
            "authoritative path must exist if not null"
        )
        # No warning expected when authoritative is found
        assert "Warning:" not in result.stderr, (
            "No warning expected when authoritative is in delta"
        )
        print("[PASS] Integration: ACCEPT (authoritative in delta)")
    else:
        # L-6B: stdout.raw.kv not found in delta set
        # Contract boundary: brok-run does not search outside delta under Path A
        # The wrapper MUST print exact warning messages to stderr (L-6B requirement)
        assert "Warning: ACCEPT reported, but no stdout.raw.kv was found in newly created run directories (delta-only discovery)." in result.stderr, (
            "L-6B: ACCEPT with null authoritative MUST print exact warning line 1 to stderr"
        )
        assert "Note: Under Path A, brok-run does not search outside the delta set for authoritative output." in result.stderr, (
            "L-6B: ACCEPT with null authoritative MUST print exact warning line 2 to stderr"
        )
        print("[PASS] Integration: ACCEPT (stdout.raw.kv not in delta, authoritative=null)")


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all L-6 Path A tests."""
    print("=" * 72)
    print("Phase L-6 Path A Run Discovery Tests (Delta-Only Selection)")
    print("=" * 72)
    print()

    tests = [
        # Scenario 1: Multi-directory, single authoritative
        ("Scenario 1a: Multi-dir, single auth", test_l6_scenario1_multi_dir_single_authoritative),
        ("Scenario 1b: Selection by file not name", test_l6_scenario1_selection_by_file_not_name),

        # Scenario 2: Observability-only
        ("Scenario 2a: No auth in delta", test_l6_scenario2_no_authoritative_in_delta),
        ("Scenario 2b: Single dir no stdout", test_l6_scenario2_single_dir_no_stdout),

        # Scenario 3: Contract violation
        ("Scenario 3a: Multiple authoritative", test_l6_scenario3_multiple_authoritative),
        ("Scenario 3b: Exact count", test_l6_scenario3_exact_count),

        # Edge cases
        ("Edge: Empty delta", test_l6_empty_delta),
        ("Edge: Delta computation", test_l6_delta_computation),

        # Integration tests
        ("Integration: REJECT", test_l6_integration_reject),
        ("Integration: ACCEPT delta", test_l6_integration_accept_delta_behavior),
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
        print("All L-6 Path A tests PASSED")
    else:
        print(f"FAILED: {failed} test(s)")
    print("=" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
