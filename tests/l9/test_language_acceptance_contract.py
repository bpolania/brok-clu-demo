#!/usr/bin/env python3
"""
Phase L-9: Language Acceptance Contract Tests

Tests for the L-9 language acceptance contract.

TEST CATEGORIES:
- Unit: Test normalize_and_map function directly
- Integration: Test engine integration and mutual exclusivity
- Sanity: Non-authoritative checks (not closure evidence)

INVARIANTS TESTED:
- L9-I1: Deterministic - same raw input always produces same output
- L9-I2: Identity preservation - unknown inputs returned verbatim
- L9-I3: No side effects - pure function
- L9-I4: Single-pass - no chaining

NOTE: Closure-grade evidence for stdout.raw.kv hash equivalence is in
      artifacts/evidence/l9/ - NOT in this test file. Proposal JSON
      comparisons are sanity checks only, not authoritative evidence.

SCOPE: L-9 minimal payment synonym set ONLY:
    - "submit payment" -> "create payment"
    - "new payment" -> "create payment"
    - "make a payment" -> "create payment"
"""

import json
import os
import sys

# Setup paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, 'proposal', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))


# =============================================================================
# Unit Tests: Contract Module
# =============================================================================

def test_normalize_and_map_exact_match():
    """
    Test that exact matches return canonical phrase.
    L-9 minimal set: payment synonyms only.
    """
    from language_acceptance_contract import normalize_and_map

    # Test payment synonyms (L-9 minimal set)
    test_cases = [
        ("submit payment", "create payment"),
        ("new payment", "create payment"),
        ("make a payment", "create payment"),
    ]

    for input_phrase, expected in test_cases:
        result = normalize_and_map(input_phrase)
        if result != expected:
            return False, f"Expected '{expected}' for '{input_phrase}', got '{result}'"

    return True, "L-9 minimal set: all payment synonyms map correctly"


def test_normalize_and_map_case_insensitive():
    """
    Test that matching is case-insensitive (ASCII only).
    """
    from language_acceptance_contract import normalize_and_map

    test_cases = [
        "SUBMIT PAYMENT",
        "Submit Payment",
        "SuBmIt PaYmEnT",
        "SUBMIT payment",
    ]

    for test_input in test_cases:
        result = normalize_and_map(test_input)
        if result != "create payment":
            return False, f"Expected 'create payment' for '{test_input}', got '{result}'"

    return True, "ASCII case-insensitive matching works"


def test_normalize_and_map_whitespace_tolerant():
    """
    Test that matching tolerates extra whitespace.
    """
    from language_acceptance_contract import normalize_and_map

    test_cases = [
        "  submit payment  ",      # Leading/trailing
        "submit   payment",        # Internal multiple spaces
        "submit\t  payment",       # Tab
        "submit \n payment",       # Newline
    ]

    for test_input in test_cases:
        result = normalize_and_map(test_input)
        if result != "create payment":
            return False, f"Expected 'create payment' for whitespace variant, got '{result}'"

    return True, "Whitespace tolerance works correctly"


def test_normalize_and_map_unknown_unchanged():
    """
    Test that unknown inputs are returned unchanged.
    """
    from language_acceptance_contract import normalize_and_map

    test_cases = [
        "do something completely unknown",
        "submit payment now",      # Extra word - no match
        "submitpayment",           # No space - no match
        "create invoice",          # Not in L-9 minimal set
        "status",                  # NOT in L-9 scope (removed)
        "check status",            # NOT in L-9 scope (removed)
    ]

    for test_input in test_cases:
        result = normalize_and_map(test_input)
        if result != test_input:
            return False, f"Expected unchanged input '{test_input}', got '{result}'"

    return True, "Unknown inputs returned unchanged"


def test_punctuation_not_stripped():
    """
    Test that punctuation variants do NOT match (no punctuation stripping).

    This is a critical constraint: only whitespace handling is allowed.
    """
    from language_acceptance_contract import normalize_and_map

    # These should NOT match because punctuation is preserved
    test_cases = [
        "submit-payment",       # Hyphen
        "submit_payment",       # Underscore
        "submit.payment",       # Period
        "submit/payment",       # Slash
        "'submit payment'",     # Quotes
    ]

    for test_input in test_cases:
        result = normalize_and_map(test_input)
        if result != test_input:
            return False, f"Punctuation variant '{test_input}' should be unchanged, got '{result}'"

    return True, "Punctuation is preserved (not stripped)"


def test_normalize_and_map_empty_input():
    """
    Test that empty input is returned unchanged.
    """
    from language_acceptance_contract import normalize_and_map

    result = normalize_and_map("")
    if result != "":
        return False, f"Expected empty string, got '{result}'"

    result = normalize_and_map("   ")
    if result != "   ":
        return False, f"Expected whitespace-only unchanged, got '{result}'"

    return True, "Empty/whitespace input returned unchanged"


def test_normalize_and_map_deterministic():
    """
    Test that same input always produces same output.
    """
    from language_acceptance_contract import normalize_and_map

    # Run multiple times with mapped input
    for _ in range(10):
        result = normalize_and_map("submit payment")
        if result != "create payment":
            return False, f"Non-deterministic result: got '{result}'"

    # Run with unknown input multiple times
    test_input = "some random input"
    for _ in range(10):
        result = normalize_and_map(test_input)
        if result != test_input:
            return False, f"Non-deterministic result for unknown: got '{result}'"

    return True, "Results are deterministic"


def test_no_chaining():
    """
    Test that canonical phrases are NOT re-mapped (no chaining).

    Canonical values must never appear as keys in the mapping table.
    """
    from language_acceptance_contract import normalize_and_map

    # "create payment" is a canonical form - should NOT be re-mapped
    result = normalize_and_map("create payment")
    if result != "create payment":
        return False, f"Expected 'create payment' unchanged, got '{result}'"

    return True, "Canonical phrases not re-mapped (no chaining)"


def test_mapping_table_scope():
    """
    Test that mapping table contains ONLY L-9 minimal set.

    L-9 scope is limited to payment synonyms only.
    Status synonyms and other mappings are NOT authorized.
    """
    from language_acceptance_contract import PHRASE_MAPPING_TABLE

    # Expected L-9 minimal set
    expected_keys = {"submit payment", "new payment", "make a payment"}
    expected_value = "create payment"

    actual_keys = set(PHRASE_MAPPING_TABLE.keys())

    if actual_keys != expected_keys:
        extra = actual_keys - expected_keys
        missing = expected_keys - actual_keys
        return False, f"Scope drift detected. Extra: {extra}, Missing: {missing}"

    for key in expected_keys:
        if PHRASE_MAPPING_TABLE[key] != expected_value:
            return False, f"Key '{key}' has wrong value: {PHRASE_MAPPING_TABLE[key]}"

    return True, f"Mapping table contains exactly L-9 minimal set ({len(expected_keys)} entries)"


def test_mapping_table_immutable():
    """
    Test that get_mapping_table_snapshot returns a copy.
    """
    from language_acceptance_contract import (
        get_mapping_table_snapshot,
        PHRASE_MAPPING_TABLE
    )

    snapshot = get_mapping_table_snapshot()

    # Modify the snapshot
    snapshot["test key"] = "test value"

    # Original should be unchanged
    if "test key" in PHRASE_MAPPING_TABLE:
        return False, "Modifying snapshot affected original table"

    return True, "Mapping table snapshot is a copy"


# =============================================================================
# Integration Tests
# =============================================================================

def test_generator_does_not_use_l9():
    """
    Verify: Deterministic generator does NOT apply L-9 contract.

    Under B1 outcome, L-9 is integrated ONLY in llm_engine.py.
    The deterministic generator path is unused under current build
    (BOUND_ENGINE_NAME = "llm"), so L-9 is not present there.

    This test confirms the generator does NOT map synonyms.
    """
    from generator import generate_proposal_set

    # If generator used L-9, "submit payment" would map to "create payment"
    # But with B1 outcome, generator does NOT use L-9
    synonym_result = generate_proposal_set("submit payment")
    canonical_result = generate_proposal_set("create payment")

    # Both produce 0 proposals (no pattern matches), but input.raw differs
    if synonym_result["input"]["raw"] != "submit payment":
        return False, "Expected input preserved as 'submit payment'"

    if canonical_result["input"]["raw"] != "create payment":
        return False, "Expected input preserved as 'create payment'"

    return True, "Generator does NOT apply L-9 (B1 outcome confirmed)"


def test_integration_single_entry_point():
    """
    Test B1 outcome: L-9 has single integration point (llm_engine only).

    Under current build (BOUND_ENGINE_NAME = "llm"):
    - llm_engine.py has L-9 integration (ACTIVE)
    - generator.py does NOT have L-9 integration (removed per B1)
    """
    from artifact_layer.engine_binding import BOUND_ENGINE_NAME, _ENGINES

    # Verify build-time binding is set to llm
    if BOUND_ENGINE_NAME != "llm":
        return False, f"Expected BOUND_ENGINE_NAME='llm', got '{BOUND_ENGINE_NAME}'"

    # Verify the bound engine exists
    from artifact_layer.engine_binding import get_bound_engine
    engine = get_bound_engine()
    if engine is None:
        return False, "get_bound_engine() returned None"

    # Verify llm_engine has L-9 import (structural check)
    from artifact_layer import llm_engine
    if not hasattr(llm_engine, 'normalize_and_map'):
        # Check module imports instead
        import inspect
        source = inspect.getsource(llm_engine)
        if 'normalize_and_map' not in source:
            return False, "llm_engine does not import normalize_and_map"

    return True, f"B1: Single integration point (llm_engine), BOUND_ENGINE_NAME='{BOUND_ENGINE_NAME}'"


def test_l9_applied_exactly_once_per_run():
    """
    Verify L-9 mapping cannot be applied twice in a single run.

    This test confirms that the engine binding mechanism ensures
    exactly one application of L-9 per run.
    """
    from artifact_layer.seam_provider import acquire_proposal_set
    from artifact_layer.run_context import RunContext, SeamSViolation

    ctx = RunContext()

    # First call succeeds
    result1 = acquire_proposal_set(b"submit payment", ctx)

    # Second call raises SeamSViolation
    try:
        result2 = acquire_proposal_set(b"submit payment", ctx)
        return False, "Expected SeamSViolation on second call"
    except SeamSViolation:
        pass

    return True, "Seam S exactly-one-call enforces single L-9 application"


# =============================================================================
# Safety Tests
# =============================================================================

def test_l9_does_not_affect_seam_contract():
    """
    Safety test: L-9 contract does not affect Seam S behavior.
    """
    from artifact_layer.seam_provider import acquire_proposal_set
    from artifact_layer.opaque_bytes import OpaqueProposalBytes
    from artifact_layer.run_context import RunContext

    ctx = RunContext()
    result = acquire_proposal_set(b"test input", ctx)

    if not isinstance(result, OpaqueProposalBytes):
        return False, f"Expected OpaqueProposalBytes, got {type(result)}"

    raw = result.to_bytes()
    if not isinstance(raw, bytes):
        return False, f"to_bytes() should return bytes, got {type(raw)}"

    return True, "Seam S contract unchanged by L-9"


def test_l9_preserves_existing_pattern_behavior():
    """
    Safety test: L-9 does not change behavior for existing patterns.
    """
    from generator import generate_proposal_set

    # This pattern is recognized by the existing generator
    test_input = "status of alpha"
    result = generate_proposal_set(test_input)

    proposals = result.get("proposals", [])
    if len(proposals) != 1:
        return False, f"Expected 1 proposal for '{test_input}', got {len(proposals)}"

    proposal = proposals[0]
    if proposal.get("payload", {}).get("intent") != "STATUS_QUERY":
        return False, f"Expected STATUS_QUERY intent"

    return True, "Existing pattern behavior preserved"


# =============================================================================
# Main
# =============================================================================

def main():
    """Run all L-9 tests."""
    tests = [
        # Unit tests - contract behavior
        ("Unit: L-9 minimal set mapping", test_normalize_and_map_exact_match),
        ("Unit: ASCII case insensitive", test_normalize_and_map_case_insensitive),
        ("Unit: whitespace tolerant", test_normalize_and_map_whitespace_tolerant),
        ("Unit: unknown unchanged", test_normalize_and_map_unknown_unchanged),
        ("Unit: punctuation preserved", test_punctuation_not_stripped),
        ("Unit: empty input unchanged", test_normalize_and_map_empty_input),
        ("Unit: deterministic", test_normalize_and_map_deterministic),
        ("Unit: no chaining", test_no_chaining),
        ("Unit: mapping table scope", test_mapping_table_scope),
        ("Unit: mapping table immutable", test_mapping_table_immutable),

        # Integration tests (B1 outcome: single entry point)
        ("Integration: generator does NOT use L-9 (B1)", test_generator_does_not_use_l9),
        ("Integration: single entry point (B1)", test_integration_single_entry_point),
        ("Integration: exactly-once per run", test_l9_applied_exactly_once_per_run),

        # Safety tests
        ("Safety: Seam S unchanged", test_l9_does_not_affect_seam_contract),
        ("Safety: patterns preserved", test_l9_preserves_existing_pattern_behavior),
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

    print("=" * 70)
    print("Phase L-9 Language Acceptance Contract Tests")
    print("=" * 70)
    print()
    print("SCOPE: L-9 minimal payment synonym set only")
    print("       Authoritative evidence is in artifacts/evidence/l9/")
    print()

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print()
    print("=" * 70)
    if all_passed:
        print(f"All {len(tests)} L-9 tests PASSED")
        return 0
    else:
        print("Some L-9 tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
