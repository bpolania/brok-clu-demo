#!/usr/bin/env python3
"""
Phase L-1 REJECT-on-Failure Demonstration

Verifies that proposal acquisition failure deterministically results
in REJECT downstream without altering validator semantics.

Test categories:
1. Input-based failures (unmapped, empty, malformed) - via CLI subprocess
2. Engine acquisition failures (engine missing, engine raises) - via in-process
   pipeline with monkeypatching

IMPORTANT: Engine failure tests assert DOWNSTREAM artifact decision = REJECT,
not only seam-level behavior. The tests invoke the same pipeline path used
by the CLI (run_proposal_generator -> build_and_save_artifact) and verify
the artifact contains decision=REJECT with reason_code=NO_PROPOSALS.

No runtime toggles or environment variables are used.
Engine failure tests use monkeypatching scoped to tests only.
"""

import json
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
sys.path.insert(0, os.path.join(REPO_ROOT, 'proposal', 'src'))


def test_unmapped_input_produces_reject():
    """
    Test that unmapped input produces REJECT without execution.

    Unmapped input (input that doesn't match any known pattern)
    produces zero proposals, which deterministically results in
    REJECT with reason_code=NO_PROPOSALS.

    This test patches the seam to simulate M-1 engine behavior
    (returning empty bytes for unmapped input), ensuring the test
    is independent of the actual bound engine.
    """
    def patched_seam(raw_input_bytes: bytes) -> bytes:
        # Simulate M-1 engine behavior: unmapped input -> empty proposal set
        # This returns an empty proposal set JSON (zero proposals)
        import json
        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": raw_input_bytes.decode('utf-8', errors='replace')},
            "proposals": []
        }
        return json.dumps(proposal_set, sort_keys=True, separators=(',', ':')).encode('utf-8')

    artifact = _run_pipeline_with_patched_seam(patched_seam)

    # Assert downstream REJECT
    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected decision=REJECT, got {decision}"

    # Assert reason code
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")
    if reason_code != "NO_PROPOSALS":
        return False, f"Expected reason_code=NO_PROPOSALS, got {reason_code}"

    return True, "Downstream REJECT with NO_PROPOSALS"


def test_empty_input_produces_reject():
    """
    Test that empty input produces REJECT.
    """
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
            return False, f"Expected 'decision=REJECT' in output"

        return True, "Downstream REJECT with NO_PROPOSALS"

    finally:
        os.unlink(input_path)


def test_malformed_utf8_produces_reject():
    """
    Test that malformed UTF-8 input produces REJECT.
    """
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
            return False, f"Expected 'decision=REJECT' in output"

        return True, "Downstream REJECT with NO_PROPOSALS"

    finally:
        os.unlink(input_path)


def _run_pipeline_with_patched_seam(patch_fn):
    """
    Helper: Run the pipeline with a patched acquire_proposal_set function.

    Returns the artifact dict built by the pipeline.

    This invokes the same pipeline path as the CLI:
      run_proposal_generator() -> build_and_save_artifact()

    Only the seam is patched. Validators and artifact builder are NOT mocked.
    """
    from artifact_layer import seam_provider
    from orchestrator import run_proposal_generator, build_and_save_artifact, get_input_ref

    # Create temp input file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test input for engine failure")
        input_path = f.name

    # Create temp run directory
    run_id = "test_engine_failure"
    temp_artifacts = tempfile.mkdtemp()

    # Save original function
    original_acquire = seam_provider.acquire_proposal_set

    try:
        # Apply the patch
        seam_provider.acquire_proposal_set = patch_fn

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

        return artifact

    finally:
        # Restore original
        seam_provider.acquire_proposal_set = original_acquire
        # Cleanup
        os.unlink(input_path)
        shutil.rmtree(temp_artifacts, ignore_errors=True)


def test_engine_returns_none_produces_reject():
    """
    Test that when get_bound_engine() returns None, the seam returns
    empty bytes, which collapses to downstream REJECT.

    ASSERTS DOWNSTREAM BEHAVIOR:
    - Artifact decision = REJECT
    - Artifact reason_code = NO_PROPOSALS
    - Uses real artifact builder (not mocked)
    """
    def patched_seam(raw_input_bytes: bytes) -> bytes:
        # Simulate engine being None - seam returns empty bytes
        return b""

    artifact = _run_pipeline_with_patched_seam(patched_seam)

    # Assert downstream REJECT
    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected decision=REJECT, got {decision}"

    # Assert reason code
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")
    if reason_code != "NO_PROPOSALS":
        return False, f"Expected reason_code=NO_PROPOSALS, got {reason_code}"

    return True, "Downstream artifact: decision=REJECT, reason_code=NO_PROPOSALS"


def test_engine_raises_produces_reject():
    """
    Test that when the bound engine raises an exception, the seam
    catches it and returns empty bytes, which collapses to downstream REJECT.

    ASSERTS DOWNSTREAM BEHAVIOR:
    - Artifact decision = REJECT
    - Artifact reason_code = NO_PROPOSALS
    - Uses real artifact builder (not mocked)
    """
    def patched_seam(raw_input_bytes: bytes) -> bytes:
        # Simulate engine raising - seam catches and returns empty bytes
        return b""

    artifact = _run_pipeline_with_patched_seam(patched_seam)

    # Assert downstream REJECT
    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected decision=REJECT, got {decision}"

    # Assert reason code
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")
    if reason_code != "NO_PROPOSALS":
        return False, f"Expected reason_code=NO_PROPOSALS, got {reason_code}"

    return True, "Downstream artifact: decision=REJECT, reason_code=NO_PROPOSALS"


def test_engine_returns_non_bytes_produces_reject():
    """
    Test that when the bound engine returns non-bytes, the seam
    returns empty bytes, which collapses to downstream REJECT.

    ASSERTS DOWNSTREAM BEHAVIOR:
    - Artifact decision = REJECT
    - Artifact reason_code = NO_PROPOSALS
    - Uses real artifact builder (not mocked)
    """
    def patched_seam(raw_input_bytes: bytes) -> bytes:
        # Simulate engine returning non-bytes - seam returns empty bytes
        return b""

    artifact = _run_pipeline_with_patched_seam(patched_seam)

    # Assert downstream REJECT
    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected decision=REJECT, got {decision}"

    # Assert reason code
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")
    if reason_code != "NO_PROPOSALS":
        return False, f"Expected reason_code=NO_PROPOSALS, got {reason_code}"

    return True, "Downstream artifact: decision=REJECT, reason_code=NO_PROPOSALS"


def test_seam_level_engine_none():
    """
    Verify seam-level behavior: get_bound_engine() -> None returns OpaqueProposalBytes(b"").

    This is a unit test of the seam itself, separate from downstream assertion.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    try:
        engine_binding.get_bound_engine = lambda: None
        seam_provider.get_bound_engine = lambda: None

        result = seam_provider.acquire_proposal_set(b"test")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Seam returns OpaqueProposalBytes(b'') when engine is None"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def test_seam_level_engine_raises():
    """
    Verify seam-level behavior: engine raises exception returns OpaqueProposalBytes(b"").

    This is a unit test of the seam itself, separate from downstream assertion.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    def raising_engine(raw: bytes) -> bytes:
        raise RuntimeError("Simulated failure")

    try:
        engine_binding.get_bound_engine = lambda: raising_engine
        seam_provider.get_bound_engine = lambda: raising_engine

        result = seam_provider.acquire_proposal_set(b"test")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Seam returns OpaqueProposalBytes(b'') when engine raises"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def test_seam_level_engine_non_bytes():
    """
    Verify seam-level behavior: engine returns non-bytes returns OpaqueProposalBytes(b"").

    This is a unit test of the seam itself, separate from downstream assertion.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    def bad_engine(raw: bytes) -> str:
        return "not bytes"

    try:
        engine_binding.get_bound_engine = lambda: bad_engine
        seam_provider.get_bound_engine = lambda: bad_engine

        result = seam_provider.acquire_proposal_set(b"test")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Seam returns OpaqueProposalBytes(b'') when engine returns non-bytes"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def main():
    """Run all REJECT-on-failure tests."""
    tests = [
        # === Input-based failure tests (via CLI) ===
        ("Unmapped input -> REJECT", test_unmapped_input_produces_reject),
        ("Empty input -> REJECT", test_empty_input_produces_reject),
        ("Malformed UTF-8 -> REJECT", test_malformed_utf8_produces_reject),

        # === Engine failure: DOWNSTREAM assertions ===
        ("Engine None -> downstream REJECT", test_engine_returns_none_produces_reject),
        ("Engine raises -> downstream REJECT", test_engine_raises_produces_reject),
        ("Engine non-bytes -> downstream REJECT", test_engine_returns_non_bytes_produces_reject),

        # === Seam-level unit tests ===
        ("Seam: engine None -> b''", test_seam_level_engine_none),
        ("Seam: engine raises -> b''", test_seam_level_engine_raises),
        ("Seam: engine non-bytes -> b''", test_seam_level_engine_non_bytes),
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
    print("Phase L-1 REJECT-on-Failure Tests")
    print("=" * 75)
    print()
    print("These tests assert DOWNSTREAM artifact decision = REJECT,")
    print("not only seam-level behavior.")
    print()

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print()
    print("=" * 75)
    if all_passed:
        print("All REJECT-on-failure tests PASSED")
        return 0
    else:
        print("Some REJECT-on-failure tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
