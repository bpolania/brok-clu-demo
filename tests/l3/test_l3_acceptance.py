#!/usr/bin/env python3
"""
Phase L-3 Single-Envelope Acceptance Tests

Tests the AUTHORITATIVE L-3 envelope gate which enforces exactly ONE
explicitly enumerated ACCEPT envelope. All schema-valid alternatives
outside this envelope are REJECTED.

L-3 SINGLE ACCEPT ENVELOPE:
  - ProposalSet contains exactly 1 proposal
  - kind == "ROUTE_CANDIDATE"
  - payload.intent == "STATUS_QUERY"
  - payload.slots == {"target": "alpha"} (no mode, no extra keys)
  - No extra keys anywhere

AUTHORITATIVE GATE LOCATION: artifact/src/builder.py
  - L3_ENVELOPE_ENABLED = True
  - _check_l3_envelope() function
  - Applied before ACCEPT in build_artifact()

This is NOT dependent on LLM engine behavior. Even if the engine emitted
a schema-valid alternative, the authoritative gate would REJECT it.

Test categories:
1. Exact envelope ACCEPT
2. Schema-valid alternatives REJECT (brittle envelope proof)
3. Structural REJECT cases (0, 2+ proposals, extra fields)
4. CLI integration
5. Determinism
"""

import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BROK_CLI = os.path.join(REPO_ROOT, 'brok')
DEMO_INPUT = os.path.join(REPO_ROOT, 'inputs', 'l3_accept_demo.txt')

# Add paths for direct module access
sys.path.insert(0, os.path.join(REPO_ROOT, 'artifact', 'src'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'proposal', 'src'))


# =============================================================================
# L-3 Single ACCEPT Envelope (must match artifact/src/builder.py)
# =============================================================================
L3_ENVELOPE = {
    "kind": "ROUTE_CANDIDATE",
    "payload": {
        "intent": "STATUS_QUERY",
        "slots": {"target": "alpha"}
    }
}


def _make_proposal_set(proposals, input_raw="status of alpha subsystem\n"):
    """Create a ProposalSet dict."""
    return {
        "schema_version": "m1.0",
        "input": {"raw": input_raw},
        "proposals": proposals
    }


def _run_artifact_builder(proposal_set):
    """
    Run the artifact builder directly with a ProposalSet.
    This tests the AUTHORITATIVE L-3 envelope gate.
    """
    from builder import build_artifact
    return build_artifact(
        proposal_set=proposal_set,
        run_id="test_l3",
        input_ref="test_input.txt",
        proposal_set_ref="proposal_set.json"
    )


def _run_cli(input_path):
    """Run the CLI and return result."""
    result = subprocess.run(
        [sys.executable, BROK_CLI, '--input', input_path],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )
    return result


# =============================================================================
# Test Category 1: Exact Envelope ACCEPT
# =============================================================================
def test_exact_envelope_accepts():
    """
    AUTHORITATIVE TEST: The exact L-3 envelope produces ACCEPT.
    """
    proposal_set = _make_proposal_set([L3_ENVELOPE])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "ACCEPT":
        return False, f"Expected ACCEPT for exact envelope, got {decision}"

    route = artifact.get("accept_payload", {}).get("route", {})
    if route.get("intent") != "STATUS_QUERY":
        return False, f"Wrong intent in route: {route.get('intent')}"
    if route.get("target") != "alpha":
        return False, f"Wrong target in route: {route.get('target')}"

    return True, "Exact L-3 envelope → ACCEPT"


# =============================================================================
# Test Category 2: Schema-Valid Alternatives REJECT (Brittle Envelope Proof)
# =============================================================================
def test_status_query_beta_rejects():
    """
    AUTHORITATIVE TEST: STATUS_QUERY on beta is schema-valid but MUST REJECT.
    This proves the envelope is brittle, not "any valid proposal."
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STATUS_QUERY",
            "slots": {"target": "beta"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for STATUS_QUERY beta, got {decision}"

    notes = artifact.get("reject_payload", {}).get("notes", [])
    if "L3_ENVELOPE_MISMATCH" not in notes:
        return False, f"Expected L3_ENVELOPE_MISMATCH note, got {notes}"

    return True, "STATUS_QUERY target=beta → REJECT (L3_ENVELOPE_MISMATCH)"


def test_status_query_gamma_rejects():
    """
    AUTHORITATIVE TEST: STATUS_QUERY on gamma is schema-valid but MUST REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STATUS_QUERY",
            "slots": {"target": "gamma"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for STATUS_QUERY gamma, got {decision}"

    return True, "STATUS_QUERY target=gamma → REJECT (L3_ENVELOPE_MISMATCH)"


def test_stop_subsystem_alpha_rejects():
    """
    AUTHORITATIVE TEST: STOP_SUBSYSTEM on alpha is schema-valid but MUST REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STOP_SUBSYSTEM",
            "slots": {"target": "alpha"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for STOP_SUBSYSTEM alpha, got {decision}"

    return True, "STOP_SUBSYSTEM target=alpha → REJECT (L3_ENVELOPE_MISMATCH)"


def test_restart_subsystem_alpha_rejects():
    """
    AUTHORITATIVE TEST: RESTART_SUBSYSTEM on alpha is schema-valid but MUST REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "RESTART_SUBSYSTEM",
            "slots": {"target": "alpha"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for RESTART_SUBSYSTEM alpha, got {decision}"

    return True, "RESTART_SUBSYSTEM target=alpha → REJECT (L3_ENVELOPE_MISMATCH)"


def test_restart_subsystem_beta_graceful_rejects():
    """
    AUTHORITATIVE TEST: RESTART_SUBSYSTEM on beta with mode is schema-valid but MUST REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "RESTART_SUBSYSTEM",
            "slots": {"target": "beta", "mode": "graceful"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for RESTART_SUBSYSTEM beta graceful, got {decision}"

    return True, "RESTART_SUBSYSTEM target=beta mode=graceful → REJECT"


# =============================================================================
# Test Category 3: Structural REJECT Cases
# =============================================================================
def test_extra_mode_slot_rejects():
    """
    AUTHORITATIVE TEST: Adding mode slot to STATUS_QUERY alpha MUST REJECT.
    The envelope requires slots == {"target": "alpha"} exactly.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STATUS_QUERY",
            "slots": {"target": "alpha", "mode": "graceful"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for extra mode slot, got {decision}"

    return True, "STATUS_QUERY alpha + mode slot → REJECT (L3_ENVELOPE_MISMATCH)"


def test_zero_proposals_rejects():
    """
    AUTHORITATIVE TEST: Zero proposals produces REJECT.
    """
    proposal_set = _make_proposal_set([])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for 0 proposals, got {decision}"

    reason = artifact.get("reject_payload", {}).get("reason_code")
    if reason != "NO_PROPOSALS":
        return False, f"Expected NO_PROPOSALS, got {reason}"

    return True, "Zero proposals → REJECT (NO_PROPOSALS)"


def test_two_proposals_rejects():
    """
    AUTHORITATIVE TEST: Two proposals produces REJECT.
    """
    proposal_set = _make_proposal_set([L3_ENVELOPE, L3_ENVELOPE])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for 2 proposals, got {decision}"

    reason = artifact.get("reject_payload", {}).get("reason_code")
    if reason != "AMBIGUOUS_PROPOSALS":
        return False, f"Expected AMBIGUOUS_PROPOSALS, got {reason}"

    return True, "Two proposals → REJECT (AMBIGUOUS_PROPOSALS)"


def test_invalid_intent_rejects():
    """
    AUTHORITATIVE TEST: Invalid intent produces REJECT (schema validation).
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "INVALID_INTENT",
            "slots": {"target": "alpha"}
        }
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for invalid intent, got {decision}"

    return True, "Invalid intent → REJECT (INVALID_PROPOSALS)"


def test_extra_field_in_proposal_rejects():
    """
    AUTHORITATIVE TEST: Extra field in proposal MUST REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STATUS_QUERY",
            "slots": {"target": "alpha"}
        },
        "extra_field": "should_not_exist"
    }
    proposal_set = _make_proposal_set([proposal])
    artifact = _run_artifact_builder(proposal_set)

    decision = artifact.get("decision")
    if decision != "REJECT":
        return False, f"Expected REJECT for extra field in proposal, got {decision}"

    return True, "Extra field in proposal → REJECT"


# =============================================================================
# Test Category 4: CLI Integration
# =============================================================================
EXAMPLES_DIR = os.path.join(REPO_ROOT, 'examples', 'inputs')
ACCEPT_STATUS_ALPHA = os.path.join(EXAMPLES_DIR, 'accept_status_alpha.txt')
ACCEPT_STATUS_BETA = os.path.join(EXAMPLES_DIR, 'accept_status_beta.txt')


def test_demo_input_via_cli_accepts():
    """
    CLI TEST: The demo input file produces ACCEPT via CLI.
    The engine emits the L-3 envelope for this input, and the authoritative
    gate accepts it.
    """
    if not os.path.exists(DEMO_INPUT):
        return False, f"Demo input file not found: {DEMO_INPUT}"

    result = _run_cli(DEMO_INPUT)

    if result.returncode != 0:
        return False, f"Expected exit code 0, got {result.returncode}"

    if 'decision=ACCEPT' not in result.stdout:
        return False, f"Expected ACCEPT, got: {result.stdout[-200:]}"

    if 'executed=true' not in result.stdout:
        return False, f"Expected executed=true in output"

    return True, "Demo input via CLI → ACCEPT"


def test_example_accept_status_alpha_accepts():
    """
    CLI TEST: The examples/inputs/accept_status_alpha.txt produces ACCEPT.
    This is the canonical demo trigger file for users.
    """
    if not os.path.exists(ACCEPT_STATUS_ALPHA):
        return False, f"Example file not found: {ACCEPT_STATUS_ALPHA}"

    result = _run_cli(ACCEPT_STATUS_ALPHA)

    if result.returncode != 0:
        return False, f"Expected exit code 0, got {result.returncode}"

    if 'decision=ACCEPT' not in result.stdout:
        return False, f"Expected ACCEPT, got: {result.stdout[-200:]}"

    if 'executed=true' not in result.stdout:
        return False, f"Expected executed=true in output"

    return True, "examples/inputs/accept_status_alpha.txt → ACCEPT"


def test_example_accept_status_beta_rejects():
    """
    CLI TEST: The examples/inputs/accept_status_beta.txt produces REJECT under L-3.
    This file contains "status of beta" which is NOT the demo trigger.
    """
    if not os.path.exists(ACCEPT_STATUS_BETA):
        return False, f"Example file not found: {ACCEPT_STATUS_BETA}"

    result = _run_cli(ACCEPT_STATUS_BETA)

    if 'decision=REJECT' not in result.stdout:
        return False, f"Expected REJECT for status beta, got: {result.stdout[-200:]}"

    return True, "examples/inputs/accept_status_beta.txt → REJECT"


def test_non_demo_input_via_cli_rejects():
    """
    CLI TEST: Non-demo inputs produce REJECT via CLI.
    The engine produces unmapped proposals for non-demo inputs.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("status beta\n")
        input_path = f.name

    try:
        result = _run_cli(input_path)

        if 'decision=REJECT' not in result.stdout:
            return False, f"Expected REJECT for non-demo input, got: {result.stdout[-200:]}"

        return True, "Non-demo input via CLI → REJECT"
    finally:
        os.unlink(input_path)


# =============================================================================
# Test Category 5: Determinism
# =============================================================================
def test_determinism_of_envelope_gate():
    """
    Repeated calls with identical ProposalSet yield identical decision.
    """
    proposal_set = _make_proposal_set([L3_ENVELOPE])

    results = []
    for _ in range(5):
        artifact = _run_artifact_builder(proposal_set)
        results.append(json.dumps(artifact, sort_keys=True))

    if len(set(results)) != 1:
        return False, f"Non-deterministic: {len(set(results))} unique results"

    return True, "Authoritative gate deterministic (5 runs)"


def test_determinism_of_reject_gate():
    """
    Repeated calls with schema-valid alternative yield identical REJECT.
    """
    proposal = {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": "STATUS_QUERY",
            "slots": {"target": "beta"}
        }
    }
    proposal_set = _make_proposal_set([proposal])

    results = []
    for _ in range(5):
        artifact = _run_artifact_builder(proposal_set)
        results.append(artifact.get("decision"))

    if not all(d == "REJECT" for d in results):
        return False, f"Non-deterministic REJECT: {results}"

    return True, "Schema-valid alternative REJECT deterministic (5 runs)"


# =============================================================================
# Test Category 6: CLI Invariants
# =============================================================================
def test_cli_rejects_unknown_flags():
    """
    CLI rejects unknown flags.
    """
    result = subprocess.run(
        [sys.executable, BROK_CLI, '--unknown-flag', '--input', DEMO_INPUT],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )

    if result.returncode == 0:
        return False, "CLI should reject unknown flags"

    if 'unrecognized arguments' not in result.stderr:
        return False, f"Expected 'unrecognized arguments' error"

    return True, "CLI rejects unknown flags"


def test_cli_requires_input_flag():
    """
    CLI requires --input flag.
    """
    result = subprocess.run(
        [sys.executable, BROK_CLI],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT
    )

    if result.returncode == 0:
        return False, "CLI should fail without --input"

    return True, "CLI requires --input flag"


# =============================================================================
# Main
# =============================================================================
def main():
    """Run all L-3 single-envelope acceptance tests."""
    tests = [
        # Exact envelope ACCEPT
        ("Exact L-3 envelope → ACCEPT", test_exact_envelope_accepts),

        # Schema-valid alternatives REJECT (brittle proof)
        ("STATUS_QUERY beta → REJECT", test_status_query_beta_rejects),
        ("STATUS_QUERY gamma → REJECT", test_status_query_gamma_rejects),
        ("STOP_SUBSYSTEM alpha → REJECT", test_stop_subsystem_alpha_rejects),
        ("RESTART_SUBSYSTEM alpha → REJECT", test_restart_subsystem_alpha_rejects),
        ("RESTART_SUBSYSTEM beta graceful → REJECT", test_restart_subsystem_beta_graceful_rejects),

        # Structural REJECT cases
        ("Extra mode slot → REJECT", test_extra_mode_slot_rejects),
        ("Zero proposals → REJECT", test_zero_proposals_rejects),
        ("Two proposals → REJECT", test_two_proposals_rejects),
        ("Invalid intent → REJECT", test_invalid_intent_rejects),
        ("Extra field in proposal → REJECT", test_extra_field_in_proposal_rejects),

        # CLI integration
        ("Demo input via CLI → ACCEPT", test_demo_input_via_cli_accepts),
        ("Example accept_status_alpha.txt → ACCEPT", test_example_accept_status_alpha_accepts),
        ("Example accept_status_beta.txt → REJECT", test_example_accept_status_beta_rejects),
        ("Non-demo input via CLI → REJECT", test_non_demo_input_via_cli_rejects),

        # Determinism
        ("Determinism of ACCEPT gate", test_determinism_of_envelope_gate),
        ("Determinism of REJECT gate", test_determinism_of_reject_gate),

        # CLI invariants
        ("CLI rejects unknown flags", test_cli_rejects_unknown_flags),
        ("CLI requires --input", test_cli_requires_input_flag),
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
    print("Phase L-3 Single-Envelope Acceptance Tests")
    print("=" * 75)
    print()
    print("L-3 SINGLE ACCEPT ENVELOPE (AUTHORITATIVE):")
    print("  - kind == 'ROUTE_CANDIDATE'")
    print("  - payload.intent == 'STATUS_QUERY'")
    print("  - payload.slots == {'target': 'alpha'} (no mode, no extras)")
    print()
    print("Schema-valid alternatives are REJECTED by the authoritative gate.")
    print("Gate location: artifact/src/builder.py")
    print()

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print()
    print("=" * 75)
    if all_passed:
        print("All L-3 single-envelope tests PASSED")
        return 0
    else:
        print("Some L-3 single-envelope tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
