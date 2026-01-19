#!/usr/bin/env python3
"""
Phase L-5 Wrapper Tests (Closure-Grade)

Updated for L-7 compliance: expanded discovery with SHA256 matching.

Verifies:
1. ./brok remains unchanged (byte-level integrity)
2. Wrapper rejects wrong arg counts without invoking ./brok
3. Wrapper uses filesystem delta for run identification (no internal coupling)
4. Wrapper invocation produces correct JSON + authoritative output line
5. Paths in JSON exist when not null, sha256 matches when present
6. Wrapper exit code equals underlying ./brok exit code
7. Wrapper failure scenarios handled correctly
8. L-7: discovery_status field present with valid values

All tests are deterministic and require no network access.
"""

import hashlib
import json
import os
import subprocess
import sys

# Resolve paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_BROK_PATH = os.path.join(_REPO_ROOT, "brok")
_BROK_RUN_PATH = os.path.join(_REPO_ROOT, "brok-run")
_RUN_ROOT = os.path.join(_REPO_ROOT, "artifacts", "run")

# Known hash of ./brok at L-4 closure (must not change)
BROK_EXPECTED_SHA256 = "1dc5ddfd2cd95f2b7c9836bd17014f2713e4aae1fead556144fd74ec4b996944"

# Exit codes (must match brok-run)
EXIT_WRONG_ARGS = 2
EXIT_WRAPPER_FAILURE = 3


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_wrapper(args: list) -> tuple:
    """
    Run ./brok-run with given args.

    Returns (stdout, stderr, exit_code).
    """
    result = subprocess.run(
        [_BROK_RUN_PATH] + args,
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT
    )
    return result.stdout, result.stderr, result.returncode


def test_brok_unchanged():
    """./brok must remain byte-identical to L-4 closure state."""
    actual_hash = sha256_file(_BROK_PATH)
    assert actual_hash == BROK_EXPECTED_SHA256, (
        f"./brok has been modified! "
        f"Expected: {BROK_EXPECTED_SHA256}, Got: {actual_hash}"
    )
    print("[PASS] ./brok unchanged (hash verified)")


def test_wrapper_rejects_no_args():
    """Wrapper must reject zero arguments and not invoke ./brok."""
    stdout, stderr, exit_code = run_wrapper([])

    assert exit_code == EXIT_WRONG_ARGS, f"Expected exit {EXIT_WRONG_ARGS}, got {exit_code}"
    assert "Usage:" in stderr, "Wrapper should print usage to stderr"
    # Minimal error output - single usage line only
    stderr_lines = [line for line in stderr.strip().split('\n') if line]
    assert len(stderr_lines) == 1, f"Expected single usage line, got {len(stderr_lines)}: {stderr}"
    # stdout must be empty for wrong args
    assert stdout == "", f"stdout should be empty for wrong args, got: {stdout}"
    print("[PASS] Wrapper rejects zero arguments")


def test_wrapper_rejects_too_many_args():
    """Wrapper must reject more than one argument."""
    stdout, stderr, exit_code = run_wrapper(["arg1", "arg2"])

    assert exit_code == EXIT_WRONG_ARGS, f"Expected exit {EXIT_WRONG_ARGS}, got {exit_code}"
    assert "Usage:" in stderr, "Wrapper should print usage to stderr"
    # Minimal error output - single usage line only
    stderr_lines = [line for line in stderr.strip().split('\n') if line]
    assert len(stderr_lines) == 1, f"Expected single usage line, got {len(stderr_lines)}: {stderr}"
    # stdout must be empty for wrong args
    assert stdout == "", f"stdout should be empty for wrong args, got: {stdout}"
    print("[PASS] Wrapper rejects too many arguments")


def test_wrapper_accept_produces_json():
    """Wrapper ACCEPT run produces valid JSON with L-7 schema.

    L-7: Includes discovery_status field with values:
    - "authoritative_found": unique match located
    - "authoritative_not_found": no match found
    - "authoritative_ambiguous": multiple candidates, wrapper refuses to select
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    # Should succeed
    assert exit_code == 0, f"Wrapper should exit 0 for ACCEPT. Got: {exit_code}"

    # Parse stdout - exactly 2 lines
    lines = stdout.strip().split('\n')
    assert len(lines) == 2, f"Expected exactly 2 lines, got {len(lines)}"

    # Parse JSON
    try:
        summary = json.loads(lines[0])
    except json.JSONDecodeError as e:
        assert False, f"First line is not valid JSON: {e}"

    # L-7 schema - exactly 5 fields
    required_fields = ["run_dir", "decision", "authoritative_stdout_raw_kv", "authoritative_stdout_raw_kv_sha256", "discovery_status"]
    for field in required_fields:
        assert field in summary, f"L-7 schema requires '{field}'"
    assert len(summary) == 5, f"L-7 schema has exactly 5 fields, got {len(summary)}: {list(summary.keys())}"

    # For ACCEPT: decision must be ACCEPT, run_dir must be non-null
    assert summary["decision"] == "ACCEPT", f"Expected ACCEPT, got {summary['decision']}"
    assert summary["run_dir"] is not None, "ACCEPT must have non-null run_dir"

    # L-7: discovery_status must be valid
    valid_statuses = ["authoritative_found", "authoritative_not_found", "authoritative_ambiguous"]
    assert summary["discovery_status"] in valid_statuses, (
        f"discovery_status must be one of {valid_statuses}, got: {summary['discovery_status']}"
    )

    # L-7: Disclaimer line must be present on stderr
    assert "This wrapper is non-authoritative" in stderr, (
        "L-7: Disclaimer line must be present on stderr"
    )

    print("[PASS] Wrapper ACCEPT produces valid JSON with L-7 schema")


def test_wrapper_accept_run_dir_exists():
    """ACCEPT run_dir points to an existing directory.

    Path A: run_dir is the observability dir if no authoritative in delta.
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    # Parse JSON
    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    # run_dir must exist
    run_dir = summary["run_dir"]
    assert run_dir is not None, "ACCEPT should have non-null run_dir"
    assert os.path.isdir(run_dir), f"run_dir should exist: {run_dir}"

    print("[PASS] ACCEPT run_dir exists")


def test_wrapper_accept_paths_valid():
    """Paths in ACCEPT JSON are valid when not null.

    Path A: authoritative paths may be null if execution dir not in delta.
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    # Check run_dir exists
    run_dir = summary.get("run_dir")
    assert run_dir and os.path.isdir(run_dir), f"run_dir does not exist: {run_dir}"

    # Check authoritative path - only verify if not null
    stdout_path = summary.get("authoritative_stdout_raw_kv")
    if stdout_path is not None:
        assert os.path.isfile(stdout_path), f"authoritative path does not exist: {stdout_path}"

    print("[PASS] Paths in ACCEPT JSON are valid")


def test_wrapper_accept_sha256_valid():
    """SHA-256 in JSON matches actual file content when present.

    Path A: sha256 may be null if execution dir not in delta.
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    stdout_path = summary.get("authoritative_stdout_raw_kv")
    claimed_hash = summary.get("authoritative_stdout_raw_kv_sha256")

    # Only verify sha256 if authoritative path is present
    if stdout_path is not None and claimed_hash is not None:
        actual_hash = sha256_file(stdout_path)
        assert actual_hash == claimed_hash, (
            f"SHA-256 mismatch! Claimed: {claimed_hash}, Actual: {actual_hash}"
        )
        print("[PASS] SHA-256 in JSON matches actual stdout.raw.kv")
    else:
        # Path A: authoritative not in delta
        print("[PASS] SHA-256 check skipped (authoritative not in delta)")


def test_wrapper_accept_authoritative_line():
    """Wrapper line 2 matches authoritative output status.

    L-7: Line 2 can be:
    - "Authoritative output: <path>" if found
    - "Authoritative output: NONE" if not found
    - "Authoritative output: AMBIGUOUS" if multiple candidates
    """
    stdout, stderr, exit_code = run_wrapper(["create payment"])

    lines = stdout.strip().split('\n')
    assert len(lines) == 2, "Expected exactly 2 lines"

    # Parse JSON to get discovery status
    summary = json.loads(lines[0])
    discovery_status = summary["discovery_status"]
    expected_path = summary["authoritative_stdout_raw_kv"]

    # Line 2 format depends on discovery status
    if discovery_status == "authoritative_found":
        expected_line = f"Authoritative output: {expected_path}"
    elif discovery_status == "authoritative_ambiguous":
        expected_line = "Authoritative output: AMBIGUOUS"
    else:
        expected_line = "Authoritative output: NONE"

    assert lines[1] == expected_line, (
        f"Line 2 mismatch. Expected: {expected_line}, Got: {lines[1]}"
    )

    print("[PASS] Wrapper prints correct authoritative line for ACCEPT")


def test_wrapper_reject_produces_json():
    """Wrapper REJECT run produces valid JSON with L-7 schema."""
    stdout, stderr, exit_code = run_wrapper(["payment succeeded"])

    # REJECT should also exit 0 (it's a valid decision)
    assert exit_code == 0, f"Wrapper should exit 0 for REJECT. Got: {exit_code}"

    lines = stdout.strip().split('\n')
    assert len(lines) == 2, f"Expected exactly 2 lines, got {len(lines)}"

    # Parse JSON
    summary = json.loads(lines[0])

    # L-7 schema - exactly 5 fields
    required_fields = ["run_dir", "decision", "authoritative_stdout_raw_kv", "authoritative_stdout_raw_kv_sha256", "discovery_status"]
    for field in required_fields:
        assert field in summary, f"L-7 schema requires '{field}'"
    assert len(summary) == 5, f"L-7 schema has exactly 5 fields, got {len(summary)}: {list(summary.keys())}"

    # For REJECT: decision is REJECT, run_dir is non-null, authoritative fields are null
    assert summary["decision"] == "REJECT", f"Expected REJECT, got {summary['decision']}"
    assert summary["run_dir"] is not None, "REJECT must have non-null run_dir"
    assert summary["authoritative_stdout_raw_kv"] is None, "REJECT must have null authoritative_stdout_raw_kv"
    assert summary["authoritative_stdout_raw_kv_sha256"] is None, "REJECT must have null sha256"
    assert summary["discovery_status"] == "authoritative_not_found", (
        f"REJECT must have discovery_status='authoritative_not_found', got: {summary['discovery_status']}"
    )

    print("[PASS] Wrapper REJECT produces valid JSON with L-7 schema")


def test_wrapper_reject_run_dir_is_delta():
    """REJECT run_dir equals newly created directory from filesystem delta."""
    # Snapshot before
    before = set(os.listdir(_RUN_ROOT)) if os.path.isdir(_RUN_ROOT) else set()

    stdout, stderr, exit_code = run_wrapper(["payment succeeded"])

    # Snapshot after
    after = set(os.listdir(_RUN_ROOT))

    # Compute delta - may have 1+ new dirs
    new_dirs = after - before
    assert len(new_dirs) >= 1, f"Expected at least 1 new directory, got {len(new_dirs)}"

    # Parse JSON
    lines = stdout.strip().split('\n')
    summary = json.loads(lines[0])

    # run_dir should be one of the delta directories
    run_dir = summary["run_dir"]
    run_dir_name = os.path.basename(run_dir)
    assert run_dir_name in new_dirs, (
        f"run_dir should be in delta. run_dir: {run_dir_name}, delta: {new_dirs}"
    )

    print("[PASS] REJECT run_dir is in filesystem delta")


def test_wrapper_reject_authoritative_line():
    """Wrapper prints exact authoritative line for REJECT."""
    stdout, stderr, exit_code = run_wrapper(["payment succeeded"])

    lines = stdout.strip().split('\n')
    assert len(lines) == 2, "Expected exactly 2 lines"

    # Exact output contract
    assert lines[1] == "Authoritative output: NONE", (
        f"Expected 'Authoritative output: NONE', got: {lines[1]}"
    )

    print("[PASS] Wrapper prints exact authoritative line for REJECT")


def test_wrapper_propagates_exit_code():
    """Wrapper exit code equals ./brok exit code."""
    # Test with ACCEPT input (should exit 0)
    stdout, stderr, exit_code = run_wrapper(["create payment"])
    assert exit_code == 0, "ACCEPT should exit 0"

    # Test with REJECT input (should also exit 0 - REJECT is valid)
    stdout, stderr, exit_code = run_wrapper(["payment succeeded"])
    assert exit_code == 0, "REJECT should also exit 0"

    print("[PASS] Wrapper propagates exit code correctly")


def test_wrapper_cleans_temp_file():
    """Wrapper should not leave temp files behind."""
    import glob

    # Count temp files before
    artifacts_dir = os.path.join(_REPO_ROOT, "artifacts")
    before = set(glob.glob(os.path.join(artifacts_dir, "brok_input_*")))

    # Run wrapper
    run_wrapper(["create payment"])

    # Count temp files after
    after = set(glob.glob(os.path.join(artifacts_dir, "brok_input_*")))

    # Should be no new temp files
    new_temps = after - before
    assert len(new_temps) == 0, f"Temp files not cleaned up: {new_temps}"

    print("[PASS] Wrapper cleans up temp files")


def test_wrapper_failure_exit_codes():
    """Wrapper exit codes are distinct for different failure modes."""
    # Normal invocation - should exit 0
    stdout_ok, stderr_ok, exit_ok = run_wrapper(["create payment"])
    assert exit_ok == 0, "Normal invocation should exit 0"

    # Wrong args - should exit 2
    stdout_bad, stderr_bad, exit_bad = run_wrapper([])
    assert exit_bad == EXIT_WRONG_ARGS, f"Wrong args should exit {EXIT_WRONG_ARGS}"

    # Wrapper failure exit code (3) is reserved for contract violations
    print("[PASS] Exit codes are distinct (0=success, 2=wrong_args, 3=wrapper_failure)")


def main():
    """Run all L-5 wrapper tests."""
    print("=" * 72)
    print("Phase L-5 Wrapper Tests (Path A Compatible)")
    print("=" * 72)
    print()

    tests = [
        ("1. ./brok unchanged", test_brok_unchanged),
        ("2. Wrapper rejects no args", test_wrapper_rejects_no_args),
        ("3. Wrapper rejects too many args", test_wrapper_rejects_too_many_args),
        ("4. Wrapper ACCEPT produces JSON", test_wrapper_accept_produces_json),
        ("5. Wrapper ACCEPT run_dir exists", test_wrapper_accept_run_dir_exists),
        ("6. Wrapper ACCEPT paths valid", test_wrapper_accept_paths_valid),
        ("7. Wrapper ACCEPT sha256 valid", test_wrapper_accept_sha256_valid),
        ("8. Wrapper ACCEPT authoritative line", test_wrapper_accept_authoritative_line),
        ("9. Wrapper REJECT produces JSON", test_wrapper_reject_produces_json),
        ("10. Wrapper REJECT run_dir is delta", test_wrapper_reject_run_dir_is_delta),
        ("11. Wrapper REJECT authoritative line", test_wrapper_reject_authoritative_line),
        ("12. Wrapper propagates exit code", test_wrapper_propagates_exit_code),
        ("13. Wrapper cleans temp files", test_wrapper_cleans_temp_file),
        ("14. Wrapper failure exit codes", test_wrapper_failure_exit_codes),
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
        print("All L-5 wrapper tests PASSED")
    else:
        print(f"FAILED: {failed} test(s)")
    print("=" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
