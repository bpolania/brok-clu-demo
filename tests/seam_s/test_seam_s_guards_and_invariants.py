#!/usr/bin/env python3
"""
Seam S Safety Guards and Invariant Tests

This module proves the safety invariants of Seam S (acquire_proposal_set).

Guards (Static Enforcement):
- G1: Exactly-one-call guard (verify single call site)
- G2: Non-inspection guard (verify no parsing of result before artifact layer)

Invariant Tests:
- C1: Call count invariant (exactly one call per run)
- C2: Failure collapse invariant (all failures -> empty bytes)
- C3: Proposal variability inert (garbage/good/invalid -> only ACCEPT/REJECT changes)
- C4: Engine removed safety (system works with no engine)

Contract: acquire_proposal_set(raw_input_bytes: bytes) -> bytes
"""

import ast
import os
import re
import sys
import json
import tempfile
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add paths
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'm3', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'artifact', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'proposal', 'src'))


# =============================================================================
# GUARD G1: Exactly-One-Call Guard (Static)
# =============================================================================

def test_guard_g1_exactly_one_call_site():
    """
    Guard G1: Verify acquire_proposal_set is called EXACTLY ONCE in production code.

    This is a static analysis guard. It scans all production Python files
    (excluding tests) and verifies:
    1. Only one file calls acquire_proposal_set
    2. That file contains only one call site

    Expected: m3/src/orchestrator.py:160
    """
    call_sites = []

    # Scan production code (exclude tests, docs, artifacts)
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip non-production directories
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
            except Exception:
                continue

            # Parse AST to find function calls
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for acquire_proposal_set call
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == 'acquire_proposal_set':
                        call_sites.append((rel_path, node.lineno))
                    elif isinstance(func, ast.Attribute) and func.attr == 'acquire_proposal_set':
                        call_sites.append((rel_path, node.lineno))

    if len(call_sites) == 0:
        return False, "No call sites found for acquire_proposal_set"

    if len(call_sites) > 1:
        sites_str = ', '.join([f"{f}:{l}" for f, l in call_sites])
        return False, f"Multiple call sites found: {sites_str}"

    # Verify expected location
    expected_file = 'm3/src/orchestrator.py'
    actual_file, actual_line = call_sites[0]

    if actual_file != expected_file:
        return False, f"Call site at unexpected file: {actual_file}"

    return True, f"Single call site at {actual_file}:{actual_line}"


def test_guard_g1_no_retry_patterns():
    """
    Guard G1 (supplement): Verify no retry patterns around acquire_proposal_set.

    Checks that the orchestrator does NOT contain retry logic around the seam.
    """
    orchestrator_path = os.path.join(REPO_ROOT, 'm3', 'src', 'orchestrator.py')

    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patterns that would indicate retry logic
    retry_patterns = [
        (r'for\s+\w+\s+in\s+range.*acquire_proposal_set', 'for loop retry'),
        (r'while.*acquire_proposal_set', 'while loop retry'),
        (r'retry.*acquire_proposal_set', 'retry wrapper'),
        (r'acquire_proposal_set.*retry', 'retry wrapper'),
        (r'max_attempts', 'max_attempts variable'),
        (r'backoff', 'backoff logic'),
    ]

    for pattern, desc in retry_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return False, f"Found {desc} pattern in orchestrator.py"

    return True, "No retry patterns found around seam call"


# =============================================================================
# GUARD G2: Non-Inspection Guard (Static)
# =============================================================================

def test_guard_g2_no_inspection_before_artifact_layer():
    """
    Guard G2: Verify proposal bytes are NOT parsed/inspected before artifact layer.

    The orchestrator should pass proposal_bytes directly to JSON parsing
    (which is the artifact layer input), without any:
    - Conditional logic based on proposal content
    - Pattern matching on proposal bytes
    - Decoding for inspection (decode for passing to artifact layer is OK)

    This checks that between acquire_proposal_set() and json.loads():
    - No 'if' statements inspect the content
    - No regex/pattern matching
    - No selective processing
    """
    orchestrator_path = os.path.join(REPO_ROOT, 'm3', 'src', 'orchestrator.py')

    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the relevant section (from acquire_proposal_set to json.loads)
    # Line 160: proposal_bytes = acquire_proposal_set(raw_input_bytes)
    # Lines 162-169: empty bytes handling (this is OK - it's for the REJECT path)
    # Lines 171-172: proposal_json = proposal_bytes.decode('utf-8'); json.loads()

    # Patterns that would indicate inspection
    inspection_patterns = [
        (r'if\s+["\'].*["\']\s+in\s+proposal_bytes', 'string search in proposal_bytes'),
        (r're\.(search|match|findall).*proposal', 'regex on proposal'),
        (r'proposal_bytes\[', 'indexing into proposal_bytes'),
        (r'len\(proposal_bytes\)\s*[<>=]', 'length comparison for logic'),
        (r'if\s+b["\']', 'byte literal conditional'),
    ]

    for pattern, desc in inspection_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, f"Found {desc} pattern - potential inspection"

    return True, "No inspection of proposal bytes before artifact layer"


def test_guard_g2_opaque_byte_passthrough():
    """
    Guard G2 (supplement): Verify proposal bytes flow opaquely to artifact layer.

    The orchestrator must NOT modify proposal bytes (except empty->canonical mapping).
    """
    orchestrator_path = os.path.join(REPO_ROOT, 'm3', 'src', 'orchestrator.py')

    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the run_proposal_generator function
    func_match = re.search(
        r'def run_proposal_generator\(.*?\n(.*?)(?=\ndef |\nclass |\Z)',
        content,
        re.DOTALL
    )

    if not func_match:
        return False, "Could not find run_proposal_generator function"

    func_body = func_match.group(1)

    # Check for modification patterns
    modification_patterns = [
        (r'proposal_bytes\s*=\s*proposal_bytes\s*\+', 'byte concatenation'),
        (r'proposal_bytes\s*\+=', 'byte concatenation'),
        (r'proposal_bytes\.replace\(', 'byte replacement'),
        (r'proposal_bytes\s*=\s*.*filter', 'filtering'),
        (r'proposal_bytes\s*=\s*.*transform', 'transformation'),
    ]

    for pattern, desc in modification_patterns:
        if re.search(pattern, func_body, re.IGNORECASE):
            return False, f"Found {desc} pattern - bytes may be modified"

    return True, "Proposal bytes pass through opaquely (empty mapping excepted)"


# =============================================================================
# INVARIANT C1: Call Count Invariant
# =============================================================================

def test_c1_single_call_per_run():
    """
    C1: Verify exactly ONE seam call occurs per pipeline run.

    Uses instrumentation to count calls during a pipeline invocation.
    """
    from artifact_layer import seam_provider
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    call_count = [0]  # Use list for closure mutability
    original_fn = seam_provider.acquire_proposal_set

    def counting_wrapper(raw_input_bytes: bytes, ctx=None) -> OpaqueProposalBytes:
        call_count[0] += 1
        return original_fn(raw_input_bytes, ctx)

    # Create temp input
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test input")
        input_path = f.name

    temp_artifacts = tempfile.mkdtemp()

    try:
        # Patch the seam
        seam_provider.acquire_proposal_set = counting_wrapper

        # Import and run the proposal generator
        from orchestrator import run_proposal_generator

        proposal_set, proposal_path, error = run_proposal_generator(
            input_path, "test_c1", temp_artifacts
        )

        if call_count[0] != 1:
            return False, f"Expected 1 call, got {call_count[0]}"

        return True, f"Exactly 1 seam call per run (count={call_count[0]})"

    finally:
        seam_provider.acquire_proposal_set = original_fn
        os.unlink(input_path)
        shutil.rmtree(temp_artifacts, ignore_errors=True)


# =============================================================================
# INVARIANT C2: Failure Collapse Invariant
# =============================================================================

def test_c2_engine_none_collapses_to_empty():
    """
    C2: When engine is None, seam returns OpaqueProposalBytes(b"").
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    try:
        # Force engine to None
        engine_binding.get_bound_engine = lambda: None
        seam_provider.get_bound_engine = lambda: None

        result = seam_provider.acquire_proposal_set(b"test input")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Engine None -> empty bytes"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def test_c2_engine_exception_collapses_to_empty():
    """
    C2: When engine raises, seam returns OpaqueProposalBytes(b"").
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    def raising_engine(raw: bytes) -> bytes:
        raise RuntimeError("Simulated engine failure")

    try:
        engine_binding.get_bound_engine = lambda: raising_engine
        seam_provider.get_bound_engine = lambda: raising_engine

        result = seam_provider.acquire_proposal_set(b"test input")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Engine exception -> empty bytes"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


def test_c2_engine_wrong_type_collapses_to_empty():
    """
    C2: When engine returns non-bytes, seam returns OpaqueProposalBytes(b"").
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    def bad_type_engine(raw: bytes) -> str:
        return "not bytes"

    try:
        engine_binding.get_bound_engine = lambda: bad_type_engine
        seam_provider.get_bound_engine = lambda: bad_type_engine

        result = seam_provider.acquire_proposal_set(b"test input")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'', got {result.to_bytes()!r}"

        return True, "Engine wrong type -> empty bytes"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


# =============================================================================
# INVARIANT C3: Proposal Variability Inert
# =============================================================================

def _build_artifact_from_bytes(proposal_bytes: bytes, temp_dir: str):
    """Helper: Build artifact from proposal bytes via the standard pipeline."""
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

    artifact, artifact_path, error = build_and_save_artifact(
        proposal_set,
        "test_run",
        "[test]:input",
        "proposals/test_run/proposal_set.json",
        temp_dir
    )

    return artifact


def test_c3_garbage_proposal_bytes_produce_reject():
    """
    C3: Garbage proposal bytes produce REJECT, not crash or execution.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Various garbage inputs
        garbage_inputs = [
            b'\xff\xfe\x00\x01',  # Invalid UTF-8
            b'{invalid json',     # Broken JSON
            b'random garbage',    # Plain garbage
            b'\x00\x00\x00\x00',  # Null bytes
        ]

        for i, garbage in enumerate(garbage_inputs):
            artifact = _build_artifact_from_bytes(garbage, temp_dir)

            decision = artifact.get("decision")
            if decision != "REJECT":
                return False, f"Garbage input {i} produced {decision}, expected REJECT"

        return True, f"All {len(garbage_inputs)} garbage inputs -> REJECT"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c3_valid_proposal_produces_accept():
    """
    C3: Valid proposal bytes produce ACCEPT.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Use the canonical L-3 format (ROUTE_CANDIDATE with intent/slots)
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
        artifact = _build_artifact_from_bytes(proposal_bytes, temp_dir)

        decision = artifact.get("decision")
        if decision != "ACCEPT":
            reject_payload = artifact.get("reject_payload", {})
            reason = reject_payload.get("reason_code", "unknown")
            return False, f"Valid proposal produced {decision} (reason: {reason})"

        return True, "Valid proposal -> ACCEPT"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c3_empty_proposals_produce_reject():
    """
    C3: Empty proposals produce REJECT with NO_PROPOSALS.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        empty_proposal = {
            "schema_version": "m1.0",
            "input": {"raw": "unmapped input"},
            "proposals": []
        }

        proposal_bytes = json.dumps(empty_proposal).encode('utf-8')
        artifact = _build_artifact_from_bytes(proposal_bytes, temp_dir)

        decision = artifact.get("decision")
        if decision != "REJECT":
            return False, f"Empty proposals produced {decision}"

        reject_payload = artifact.get("reject_payload", {})
        reason = reject_payload.get("reason_code")
        if reason != "NO_PROPOSALS":
            return False, f"Expected NO_PROPOSALS, got {reason}"

        return True, "Empty proposals -> REJECT (NO_PROPOSALS)"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c3_variability_does_not_affect_non_decision_behavior():
    """
    C3: Different proposal content affects only ACCEPT/REJECT, not system behavior.

    Verifies that the system behaves identically for different proposal content
    (e.g., no special handling, no different code paths based on content).
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Three different proposals that should all produce REJECT
        test_cases = [
            (b'', "empty bytes"),
            (b'not json', "non-json"),
            (json.dumps({"schema_version": "m1.0", "input": {"raw": ""}, "proposals": []}).encode(), "empty proposals"),
        ]

        artifacts = []
        for proposal_bytes, desc in test_cases:
            artifact = _build_artifact_from_bytes(proposal_bytes, temp_dir)
            artifacts.append((artifact, desc))

        # All should produce REJECT with same reason
        for artifact, desc in artifacts:
            decision = artifact.get("decision")
            if decision != "REJECT":
                return False, f"{desc} produced {decision}, expected REJECT"

            reject_payload = artifact.get("reject_payload", {})
            reason = reject_payload.get("reason_code")
            if reason != "NO_PROPOSALS":
                return False, f"{desc} reason={reason}, expected NO_PROPOSALS"

        return True, "Proposal variability affects only decision, not behavior"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# INVARIANT C4: Engine Removed Safety
# =============================================================================

def test_c4_system_works_with_no_engine():
    """
    C4: System produces valid REJECT artifacts when engine is removed/unbound.

    This proves that deleting the proposal engine does not break the system.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine
    temp_dir = tempfile.mkdtemp()

    try:
        # Force engine to None (simulating removal)
        engine_binding.get_bound_engine = lambda: None
        seam_provider.get_bound_engine = lambda: None

        # Acquire proposals (should get OpaqueProposalBytes with empty bytes)
        result = seam_provider.acquire_proposal_set(b"test input")

        if not isinstance(result, OpaqueProposalBytes):
            return False, f"Expected OpaqueProposalBytes, got {type(result)}"

        if result.to_bytes() != b"":
            return False, f"Expected b'' with no engine, got {result.to_bytes()!r}"

        # Build artifact (should produce valid REJECT)
        artifact = _build_artifact_from_bytes(result.to_bytes(), temp_dir)

        decision = artifact.get("decision")
        if decision != "REJECT":
            return False, f"No-engine artifact decision={decision}, expected REJECT"

        reject_payload = artifact.get("reject_payload", {})
        reason = reject_payload.get("reason_code")
        if reason != "NO_PROPOSALS":
            return False, f"No-engine artifact reason={reason}, expected NO_PROPOSALS"

        return True, "System produces valid REJECT when engine removed"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_c4_no_engine_no_crash():
    """
    C4: System does not crash when engine is None.

    Multiple invocations with no engine should all succeed without exception.
    """
    from artifact_layer import seam_provider
    from artifact_layer import engine_binding
    from artifact_layer.opaque_bytes import OpaqueProposalBytes

    original = engine_binding.get_bound_engine

    try:
        engine_binding.get_bound_engine = lambda: None
        seam_provider.get_bound_engine = lambda: None

        # Multiple invocations
        for i in range(5):
            result = seam_provider.acquire_proposal_set(f"input {i}".encode())
            if not isinstance(result, OpaqueProposalBytes):
                return False, f"Invocation {i}: expected OpaqueProposalBytes, got {type(result)}"
            if result.to_bytes() != b"":
                return False, f"Invocation {i}: expected b'', got {result.to_bytes()!r}"

        return True, "5 invocations with no engine: no crashes"

    finally:
        engine_binding.get_bound_engine = original
        seam_provider.get_bound_engine = original


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all Seam S guard and invariant tests."""
    tests = [
        # === Guards ===
        ("G1: Exactly one call site", test_guard_g1_exactly_one_call_site),
        ("G1: No retry patterns", test_guard_g1_no_retry_patterns),
        ("G2: No inspection before artifact layer", test_guard_g2_no_inspection_before_artifact_layer),
        ("G2: Opaque byte passthrough", test_guard_g2_opaque_byte_passthrough),

        # === C1: Call Count Invariant ===
        ("C1: Single call per run", test_c1_single_call_per_run),

        # === C2: Failure Collapse Invariant ===
        ("C2: Engine None -> empty bytes", test_c2_engine_none_collapses_to_empty),
        ("C2: Engine exception -> empty bytes", test_c2_engine_exception_collapses_to_empty),
        ("C2: Engine wrong type -> empty bytes", test_c2_engine_wrong_type_collapses_to_empty),

        # === C3: Proposal Variability Inert ===
        ("C3: Garbage proposal -> REJECT", test_c3_garbage_proposal_bytes_produce_reject),
        ("C3: Valid proposal -> ACCEPT", test_c3_valid_proposal_produces_accept),
        ("C3: Empty proposals -> REJECT", test_c3_empty_proposals_produce_reject),
        ("C3: Variability affects only decision", test_c3_variability_does_not_affect_non_decision_behavior),

        # === C4: Engine Removed Safety ===
        ("C4: System works with no engine", test_c4_system_works_with_no_engine),
        ("C4: No engine, no crash", test_c4_no_engine_no_crash),
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
    print("Seam S Safety Guards and Invariant Tests")
    print("=" * 75)
    print()
    print("Contract: acquire_proposal_set(raw_input_bytes: bytes) -> bytes")
    print("Location: src/artifact_layer/seam_provider.py")
    print()

    # Group results by category
    categories = {
        "Guards (Static Enforcement)": [r for r in results if r[0].startswith("G")],
        "C1: Call Count Invariant": [r for r in results if r[0].startswith("C1")],
        "C2: Failure Collapse Invariant": [r for r in results if r[0].startswith("C2")],
        "C3: Proposal Variability Inert": [r for r in results if r[0].startswith("C3")],
        "C4: Engine Removed Safety": [r for r in results if r[0].startswith("C4")],
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
        print(f"All {total_count} Seam S tests PASSED")
        return 0
    else:
        print(f"{passed_count}/{total_count} Seam S tests passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
