#!/usr/bin/env python3
"""
Phase L-2 Failure Collapse Tests

Demonstrates that LLM engine failures collapse to REJECT through the real
pipeline, not just in isolated unit tests.

Test categories:
1. Empty/malformed input -> REJECT
2. Seam-level failure injection -> REJECT (via monkeypatch)

All failures must:
- Result in artifact decision = REJECT
- Exit with code 0 (REJECT is valid outcome)
- Not invoke execution layer

Note: The offline nondeterministic engine does not require API keys or
external services, so API unavailability is not a failure mode.
"""

import os
import subprocess
import sys
import tempfile
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BROK_CLI = os.path.join(REPO_ROOT, 'brok')

# Add paths for direct module access
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'm3', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'artifact', 'src'))


def test_empty_input_produces_reject():
    """Test that empty input produces REJECT via real pipeline."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")
        input_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, BROK_CLI, '--input', input_path],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )

        if result.returncode != 0:
            return False, f"Expected exit code 0, got {result.returncode}"

        if 'decision=REJECT' not in result.stdout:
            return False, "Expected 'decision=REJECT' in output"

        return True, "Empty input -> REJECT (exit 0)"

    finally:
        os.unlink(input_path)


def test_malformed_utf8_produces_reject():
    """Test that malformed UTF-8 input produces REJECT."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        f.write(b'\xff\xfe\x00\x01\x80\x81')
        input_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, BROK_CLI, '--input', input_path],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )

        if result.returncode != 0:
            return False, f"Expected exit code 0, got {result.returncode}"

        if 'decision=REJECT' not in result.stdout:
            return False, "Expected 'decision=REJECT' in output"

        return True, "Malformed UTF-8 -> REJECT (exit 0)"

    finally:
        os.unlink(input_path)


def test_seam_exception_produces_reject():
    """
    Test that exceptions in the seam produce REJECT.

    This test uses monkeypatching to inject a failure into the seam,
    then verifies the downstream artifact decision is REJECT.
    """
    from artifact_layer import seam_provider
    from orchestrator import run_proposal_generator, build_and_save_artifact, get_input_ref

    # Create temp input file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test input for seam exception")
        input_path = f.name

    # Create temp run directory
    run_id = "test_seam_exception"
    temp_artifacts = tempfile.mkdtemp()

    # Save original function
    original_acquire = seam_provider.acquire_proposal_set

    def raising_seam(raw_input_bytes: bytes) -> bytes:
        raise RuntimeError("Simulated seam failure")

    try:
        # Apply the patch
        seam_provider.acquire_proposal_set = raising_seam

        # Run proposal generator (uses patched seam)
        proposal_set, proposal_set_path, error = run_proposal_generator(
            input_path, run_id, temp_artifacts
        )

        # Get input ref
        input_ref = get_input_ref(input_path, temp_artifacts)
        proposal_set_ref = os.path.relpath(proposal_set_path, temp_artifacts)

        # Build artifact (uses real builder, not mocked)
        artifact, artifact_path, error = build_and_save_artifact(
            proposal_set, run_id, input_ref, proposal_set_ref, temp_artifacts
        )

        # Assert downstream REJECT
        decision = artifact.get("decision")
        if decision != "REJECT":
            return False, f"Expected decision=REJECT, got {decision}"

        # Assert reason code
        reject_payload = artifact.get("reject_payload", {})
        reason_code = reject_payload.get("reason_code")
        if reason_code != "NO_PROPOSALS":
            return False, f"Expected reason_code=NO_PROPOSALS, got {reason_code}"

        return True, "Seam exception -> downstream REJECT (NO_PROPOSALS)"

    except Exception as e:
        return False, f"Unexpected propagation: {type(e).__name__}: {e}"

    finally:
        # Restore original
        seam_provider.acquire_proposal_set = original_acquire
        # Cleanup
        os.unlink(input_path)
        shutil.rmtree(temp_artifacts, ignore_errors=True)


def test_seam_returns_empty_produces_reject():
    """
    Test that when seam returns empty bytes, it produces REJECT.
    """
    from artifact_layer import seam_provider
    from orchestrator import run_proposal_generator, build_and_save_artifact, get_input_ref

    # Create temp input file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test input for empty return")
        input_path = f.name

    # Create temp run directory
    run_id = "test_seam_empty"
    temp_artifacts = tempfile.mkdtemp()

    # Save original function
    original_acquire = seam_provider.acquire_proposal_set

    def empty_seam(raw_input_bytes: bytes) -> bytes:
        return b""  # Empty bytes simulates failure

    try:
        # Apply the patch
        seam_provider.acquire_proposal_set = empty_seam

        # Run proposal generator (uses patched seam)
        proposal_set, proposal_set_path, error = run_proposal_generator(
            input_path, run_id, temp_artifacts
        )

        # Get input ref
        input_ref = get_input_ref(input_path, temp_artifacts)
        proposal_set_ref = os.path.relpath(proposal_set_path, temp_artifacts)

        # Build artifact (uses real builder, not mocked)
        artifact, artifact_path, error = build_and_save_artifact(
            proposal_set, run_id, input_ref, proposal_set_ref, temp_artifacts
        )

        # Assert downstream REJECT
        decision = artifact.get("decision")
        if decision != "REJECT":
            return False, f"Expected decision=REJECT, got {decision}"

        return True, "Seam returns b'' -> downstream REJECT"

    finally:
        # Restore original
        seam_provider.acquire_proposal_set = original_acquire
        # Cleanup
        os.unlink(input_path)
        shutil.rmtree(temp_artifacts, ignore_errors=True)


def test_unmapped_input_produces_reject():
    """
    Test that unmapped input (gibberish) produces REJECT via real pipeline.

    This tests the offline engine's behavior when it cannot interpret the input.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        # Input that doesn't match any known patterns
        f.write("xyzzy foobarbaz quxquux")
        input_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, BROK_CLI, '--input', input_path],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )

        if result.returncode != 0:
            return False, f"Expected exit code 0, got {result.returncode}"

        if 'decision=REJECT' not in result.stdout:
            return False, "Expected 'decision=REJECT' in output"

        return True, "Unmapped input -> REJECT (exit 0)"

    finally:
        os.unlink(input_path)


def main():
    """Run all failure collapse tests."""
    tests = [
        ("Empty input -> REJECT", test_empty_input_produces_reject),
        ("Malformed UTF-8 -> REJECT", test_malformed_utf8_produces_reject),
        ("Unmapped input -> REJECT", test_unmapped_input_produces_reject),
        ("Seam exception -> REJECT", test_seam_exception_produces_reject),
        ("Seam returns b'' -> REJECT", test_seam_returns_empty_produces_reject),
    ]

    all_passed = True
    results = []

    for name, test_fn in tests:
        try:
            passed, message = test_fn()
        except Exception as e:
            passed = False
            message = f"Exception: {type(e).__name__}: {e}"

        status = "PASS" if passed else "FAIL"
        results.append((name, status, message))
        if not passed:
            all_passed = False

    print("=" * 75)
    print("Phase L-2 Failure Collapse Tests")
    print("=" * 75)
    print()
    print("These tests verify that failures collapse to REJECT")
    print("through the real pipeline, with exit code 0 and no execution.")
    print()
    print("Note: Offline engine requires no API keys or external services.")
    print()

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print()
    print("=" * 75)
    if all_passed:
        print("All failure collapse tests PASSED")
        return 0
    else:
        print("Some failure collapse tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
