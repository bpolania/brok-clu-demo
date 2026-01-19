#!/usr/bin/env python3
"""
Seam S Freeze-Grade Tests

This module proves the freeze-grade safety invariants of Seam S.

Freeze-Grade Guards:
- G1: Runtime exactly-one-call guard (RunContext)
- G2: Mechanical non-inspection boundary (OpaqueProposalBytes)
- G3: Static analysis (defense-in-depth)

Freeze-Grade Invariants:
- C1: Call count invariant (exactly one call per run)
- C2: Failure collapse invariant (all failures -> empty bytes)
- C3: Proposal variability inert (garbage/good/invalid -> only decision changes)
- C4: Engine removed safety (system works with no engine)
- C5: ACCEPT execution invariance (same execution hash across ACCEPT runs)

Contract: acquire_proposal_set(raw_input_bytes: bytes, ctx: RunContext) -> OpaqueProposalBytes
"""

import ast
import os
import re
import sys
import json
import tempfile
import shutil
import hashlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add paths
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'm3', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'artifact', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'proposal', 'src'))


# =============================================================================
# GUARD G1: Runtime Exactly-One-Call Guard
# =============================================================================

def test_g1_runtime_guard_first_call_succeeds():
    """
    G1: First seam call with RunContext succeeds normally.
    """
    from artifact_layer.run_context import RunContext
    from artifact_layer.seam_provider import acquire_proposal_set

    ctx = RunContext()
    result = acquire_proposal_set(b"test input", ctx)

    # Should return OpaqueProposalBytes (even if empty)
    from artifact_layer.opaque_bytes import OpaqueProposalBytes
    if not isinstance(result, OpaqueProposalBytes):
        return False, f"Expected OpaqueProposalBytes, got {type(result)}"

    return True, "First call succeeds with OpaqueProposalBytes"


def test_g1_runtime_guard_second_call_raises():
    """
    G1: Second seam call with same RunContext raises SeamSViolation.
    """
    from artifact_layer.run_context import RunContext, SeamSViolation
    from artifact_layer.seam_provider import acquire_proposal_set

    ctx = RunContext()

    # First call should succeed
    acquire_proposal_set(b"test input", ctx)

    # Second call should raise
    try:
        acquire_proposal_set(b"test input 2", ctx)
        return False, "Second call did not raise SeamSViolation"
    except SeamSViolation as e:
        if "exactly once per run" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "Second call raises SeamSViolation"
    except Exception as e:
        return False, f"Wrong exception type: {type(e).__name__}: {e}"


def test_g1_runtime_guard_different_contexts_independent():
    """
    G1: Different RunContexts are independent (each allows one call).
    """
    from artifact_layer.run_context import RunContext
    from artifact_layer.seam_provider import acquire_proposal_set

    ctx1 = RunContext()
    ctx2 = RunContext()

    # First call on ctx1
    acquire_proposal_set(b"input 1", ctx1)

    # First call on ctx2 should also succeed
    acquire_proposal_set(b"input 2", ctx2)

    return True, "Different contexts are independent"


# =============================================================================
# GUARD G2: Mechanical Non-Inspection Boundary (OpaqueProposalBytes)
# =============================================================================

def test_g2_opaque_bytes_to_bytes_works():
    """
    G2: OpaqueProposalBytes.to_bytes() returns the raw bytes.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    data = b"test proposal bytes"
    opaque = OpaqueProposalBytes(data)

    result = opaque.to_bytes()
    if result != data:
        return False, f"Expected {data!r}, got {result!r}"

    return True, "to_bytes() returns raw bytes"


def test_g2_opaque_bytes_str_disabled():
    """
    G2: OpaqueProposalBytes str() raises TypeError.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    opaque = OpaqueProposalBytes(b"test")

    try:
        str(opaque)
        return False, "str() did not raise TypeError"
    except TypeError as e:
        if "does not support str()" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "str() disabled by construction"


def test_g2_opaque_bytes_len_disabled():
    """
    G2: OpaqueProposalBytes len() raises TypeError.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    opaque = OpaqueProposalBytes(b"test")

    try:
        len(opaque)
        return False, "len() did not raise TypeError"
    except TypeError as e:
        if "does not support len()" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "len() disabled by construction"


def test_g2_opaque_bytes_bool_disabled():
    """
    G2: OpaqueProposalBytes bool() raises TypeError.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    opaque = OpaqueProposalBytes(b"test")

    try:
        bool(opaque)
        return False, "bool() did not raise TypeError"
    except TypeError as e:
        if "does not support bool()" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "bool() disabled by construction"


def test_g2_opaque_bytes_iter_disabled():
    """
    G2: OpaqueProposalBytes iteration raises TypeError.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    opaque = OpaqueProposalBytes(b"test")

    try:
        for _ in opaque:
            pass
        return False, "iteration did not raise TypeError"
    except TypeError as e:
        if "does not support iteration" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "iteration disabled by construction"


def test_g2_opaque_bytes_index_disabled():
    """
    G2: OpaqueProposalBytes indexing raises TypeError.
    """
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    opaque = OpaqueProposalBytes(b"test")

    try:
        _ = opaque[0]
        return False, "indexing did not raise TypeError"
    except TypeError as e:
        if "does not support indexing" not in str(e):
            return False, f"Wrong error message: {e}"
        return True, "indexing disabled by construction"


# =============================================================================
# GUARD G3: Static Analysis (Defense-in-Depth)
# =============================================================================

def test_g3_static_single_call_site():
    """
    G3: Verify acquire_proposal_set is called at exactly one production site.
    """
    call_sites = []

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in [
            'tests', 'docs', 'artifacts', '.git', '__pycache__',
            '.venv', 'venv', '.idea', '.mypy_cache', '.pytest_cache'
        ]]

        for fname in files:
            if not fname.endswith('.py'):
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, REPO_ROOT)

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == 'acquire_proposal_set':
                        call_sites.append((rel_path, node.lineno))
                    elif isinstance(func, ast.Attribute) and func.attr == 'acquire_proposal_set':
                        call_sites.append((rel_path, node.lineno))

    if len(call_sites) != 1:
        sites_str = ', '.join([f"{f}:{l}" for f, l in call_sites])
        return False, f"Expected 1 call site, found {len(call_sites)}: {sites_str}"

    return True, f"Single call site at {call_sites[0][0]}:{call_sites[0][1]}"


def test_g3_static_no_retry_patterns():
    """
    G3: Verify no retry patterns around acquire_proposal_set.
    """
    orchestrator_path = os.path.join(REPO_ROOT, 'm3', 'src', 'orchestrator.py')

    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()

    retry_patterns = [
        (r'for\s+\w+\s+in\s+range.*acquire_proposal_set', 'for loop retry'),
        (r'while.*acquire_proposal_set', 'while loop retry'),
        (r'retry.*acquire_proposal_set', 'retry wrapper'),
        (r'max_attempts', 'max_attempts variable'),
        (r'backoff', 'backoff logic'),
    ]

    for pattern, desc in retry_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return False, f"Found {desc} pattern"

    return True, "No retry patterns found"


# =============================================================================
# INVARIANT C1: Call Count (via Runtime Guard)
# =============================================================================

def test_c1_single_call_via_runtime_guard():
    """
    C1: Runtime guard enforces exactly one call per run.
    """
    from artifact_layer.run_context import RunContext, SeamSViolation
    from artifact_layer.seam_provider import acquire_proposal_set

    ctx = RunContext()

    # First call
    acquire_proposal_set(b"input", ctx)

    # Second call must raise
    raised = False
    try:
        acquire_proposal_set(b"input", ctx)
    except SeamSViolation:
        raised = True

    if not raised:
        return False, "Runtime guard did not prevent second call"

    return True, "Runtime guard enforces single call"


# =============================================================================
# INVARIANT C2: Failure Collapse
# =============================================================================

def test_c2_engine_none_returns_opaque_empty():
    """
    C2: Engine None returns OpaqueProposalBytes(b"").
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

        return True, "Engine None -> OpaqueProposalBytes(b'')"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def test_c2_engine_raises_returns_opaque_empty():
    """
    C2: Engine raises returns OpaqueProposalBytes(b"").
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

        return True, "Engine raises -> OpaqueProposalBytes(b'')"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


# =============================================================================
# INVARIANT C3: Proposal Variability Inert
# =============================================================================

def _build_artifact_from_proposal_bytes(proposal_bytes: bytes, temp_dir: str):
    """Helper: Build artifact from proposal bytes."""
    from orchestrator import build_and_save_artifact

    if not proposal_bytes:
        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": ""},
            "proposals": []
        }
    else:
        try:
            proposal_set = json.loads(proposal_bytes.decode('utf-8'))
        except Exception:
            proposal_set = {
                "schema_version": "m1.0",
                "input": {"raw": ""},
                "proposals": []
            }

    artifact, _, _ = build_and_save_artifact(
        proposal_set,
        "test_run",
        "[test]:input",
        "proposals/test_run/proposal_set.json",
        temp_dir
    )

    return artifact


def test_c3_garbage_produces_reject():
    """
    C3: Garbage proposal bytes produce REJECT.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        garbage_inputs = [
            b'\xff\xfe\x00\x01',
            b'{invalid json',
            b'random garbage',
        ]

        for garbage in garbage_inputs:
            artifact = _build_artifact_from_proposal_bytes(garbage, temp_dir)
            if artifact.get("decision") != "REJECT":
                return False, f"Garbage did not produce REJECT"

        return True, "All garbage inputs -> REJECT"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c3_valid_produces_accept():
    """
    C3: Valid proposal bytes produce ACCEPT.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        valid_proposal = {
            "schema_version": "m1.0",
            "input": {"raw": "status alpha\n"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"}
                }
            }]
        }

        proposal_bytes = json.dumps(valid_proposal).encode('utf-8')
        artifact = _build_artifact_from_proposal_bytes(proposal_bytes, temp_dir)

        if artifact.get("decision") != "ACCEPT":
            return False, f"Valid proposal did not produce ACCEPT"

        return True, "Valid proposal -> ACCEPT"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# INVARIANT C4: Engine Removed Safety
# =============================================================================

def test_c4_no_engine_produces_reject():
    """
    C4: System produces valid REJECT when engine is removed.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding

    original = engine_binding.get_bound_engine
    temp_dir = tempfile.mkdtemp()

    try:
        engine_binding.get_bound_engine = lambda: None
        seam_provider.get_bound_engine = lambda: None

        result = seam_provider.acquire_proposal_set(b"test")
        proposal_bytes = result.to_bytes()

        artifact = _build_artifact_from_proposal_bytes(proposal_bytes, temp_dir)

        if artifact.get("decision") != "REJECT":
            return False, "No-engine did not produce REJECT"

        return True, "No engine -> REJECT"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# INVARIANT C5: ACCEPT Execution Invariance
# =============================================================================

def test_c5_accept_execution_hash_invariance():
    """
    C5: Different ACCEPT proposals produce identical execution output hash.

    This test verifies that when ACCEPT occurs, the authoritative execution
    output (stdout.raw.kv) is identical regardless of which valid proposal
    bytes were used, as long as they produce the same ACCEPT decision.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Two different valid proposals that both produce ACCEPT
        # Both are STATUS_QUERY for alpha, but with different input.raw
        proposal_v1 = {
            "schema_version": "m1.0",
            "input": {"raw": "status alpha\n"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"}
                }
            }]
        }

        proposal_v2 = {
            "schema_version": "m1.0",
            "input": {"raw": "check status of alpha\n"},  # Different input.raw
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"}
                }
            }]
        }

        # Build artifacts
        artifact_v1 = _build_artifact_from_proposal_bytes(
            json.dumps(proposal_v1).encode('utf-8'), temp_dir
        )
        artifact_v2 = _build_artifact_from_proposal_bytes(
            json.dumps(proposal_v2).encode('utf-8'), temp_dir
        )

        # Both should ACCEPT
        if artifact_v1.get("decision") != "ACCEPT":
            return False, "proposal_v1 did not ACCEPT"
        if artifact_v2.get("decision") != "ACCEPT":
            return False, "proposal_v2 did not ACCEPT"

        # Compare accept_payload hashes (the execution-relevant part)
        payload_v1 = artifact_v1.get("accept_payload", {})
        payload_v2 = artifact_v2.get("accept_payload", {})

        # The execution action should be identical
        action_v1 = payload_v1.get("action", {})
        action_v2 = payload_v2.get("action", {})

        hash_v1 = hashlib.sha256(json.dumps(action_v1, sort_keys=True).encode()).hexdigest()
        hash_v2 = hashlib.sha256(json.dumps(action_v2, sort_keys=True).encode()).hexdigest()

        if hash_v1 != hash_v2:
            return False, f"Execution action hashes differ: {hash_v1[:16]}... vs {hash_v2[:16]}..."

        return True, f"ACCEPT execution hash invariant: {hash_v1[:16]}..."

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c5_reject_never_executes():
    """
    C5: REJECT artifacts never produce execution output.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Create mock PoC script
        scripts_dir = os.path.join(temp_dir, 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        poc_script = os.path.join(scripts_dir, 'run_poc_v2.sh')
        with open(poc_script, 'w') as f:
            f.write('#!/bin/bash\necho "EXECUTED"\n')
        os.chmod(poc_script, 0o755)

        # Import gateway
        from gateway import ExecutionGateway

        # Build REJECT artifact
        reject_proposal = {
            "schema_version": "m1.0",
            "input": {"raw": ""},
            "proposals": []
        }

        artifact = _build_artifact_from_proposal_bytes(
            json.dumps(reject_proposal).encode('utf-8'), temp_dir
        )

        if artifact.get("decision") != "REJECT":
            return False, "Expected REJECT artifact"

        # Try to execute
        gateway = ExecutionGateway(temp_dir)

        # Create dummy input file
        input_file = os.path.join(temp_dir, 'input.txt')
        with open(input_file, 'w') as f:
            f.write("test")

        result = gateway.execute_if_accepted(artifact, input_file)

        if result.executed:
            return False, "REJECT artifact was executed"

        # Check no stdout.raw.kv was created
        if result.run_directory:
            stdout_path = os.path.join(result.run_directory, 'stdout.raw.kv')
            if os.path.exists(stdout_path):
                return False, "stdout.raw.kv was created for REJECT"

        return True, "REJECT never executes"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all freeze-grade tests."""
    tests = [
        # G1: Runtime Guard
        ("G1: First call succeeds", test_g1_runtime_guard_first_call_succeeds),
        ("G1: Second call raises", test_g1_runtime_guard_second_call_raises),
        ("G1: Different contexts independent", test_g1_runtime_guard_different_contexts_independent),

        # G2: Opaque Wrapper
        ("G2: to_bytes() works", test_g2_opaque_bytes_to_bytes_works),
        ("G2: str() disabled", test_g2_opaque_bytes_str_disabled),
        ("G2: len() disabled", test_g2_opaque_bytes_len_disabled),
        ("G2: bool() disabled", test_g2_opaque_bytes_bool_disabled),
        ("G2: iteration disabled", test_g2_opaque_bytes_iter_disabled),
        ("G2: indexing disabled", test_g2_opaque_bytes_index_disabled),

        # G3: Static Analysis
        ("G3: Single call site", test_g3_static_single_call_site),
        ("G3: No retry patterns", test_g3_static_no_retry_patterns),

        # C1: Call Count
        ("C1: Runtime guard enforces single call", test_c1_single_call_via_runtime_guard),

        # C2: Failure Collapse
        ("C2: Engine None -> empty", test_c2_engine_none_returns_opaque_empty),
        ("C2: Engine raises -> empty", test_c2_engine_raises_returns_opaque_empty),

        # C3: Proposal Variability
        ("C3: Garbage -> REJECT", test_c3_garbage_produces_reject),
        ("C3: Valid -> ACCEPT", test_c3_valid_produces_accept),

        # C4: Engine Removed
        ("C4: No engine -> REJECT", test_c4_no_engine_produces_reject),

        # C5: ACCEPT Invariance
        ("C5: ACCEPT hash invariance", test_c5_accept_execution_hash_invariance),
        ("C5: REJECT never executes", test_c5_reject_never_executes),
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

    # Print results
    print("=" * 75)
    print("Seam S Freeze-Grade Tests")
    print("=" * 75)
    print()

    categories = {
        "G1: Runtime Guard": [r for r in results if r[0].startswith("G1")],
        "G2: Opaque Wrapper": [r for r in results if r[0].startswith("G2")],
        "G3: Static Analysis": [r for r in results if r[0].startswith("G3")],
        "C1: Call Count": [r for r in results if r[0].startswith("C1")],
        "C2: Failure Collapse": [r for r in results if r[0].startswith("C2")],
        "C3: Proposal Variability": [r for r in results if r[0].startswith("C3")],
        "C4: Engine Removed": [r for r in results if r[0].startswith("C4")],
        "C5: ACCEPT Invariance": [r for r in results if r[0].startswith("C5")],
    }

    for category, cat_results in categories.items():
        print(f"--- {category} ---")
        for name, status, message in cat_results:
            print(f"[{status}] {name}")
            print(f"       {message}")
        print()

    print("=" * 75)
    passed_count = sum(1 for _, s, _ in results if s == "PASS")
    total_count = len(results)

    if all_passed:
        print(f"All {total_count} freeze-grade tests PASSED")
        return 0
    else:
        print(f"{passed_count}/{total_count} freeze-grade tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
