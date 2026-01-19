#!/usr/bin/env python3
"""
Phase L-8: ACCEPT Regression Lock Tests & REJECT Gate Tests (Corrected)

This file contains two categories of tests:

1. ACCEPT REGRESSION LOCKS
   These tests prove that known ACCEPT envelopes remain stable and produce
   identical artifacts. Baselines are sourced from fixture files.

2. REJECT EXECUTION GATE TESTS
   These tests prove that REJECT artifacts do not trigger execution and
   no stdout.raw.kv is produced. This is the critical safety property:
   "no execution without ACCEPT."

Test Approach:
- Load canonical envelope bytes from fixture files
- Inject into artifact layer via the same path production uses
- For ACCEPT: verify decision, payload stability, and byte-identical artifacts
- For REJECT: verify gateway does not execute and no stdout.raw.kv exists

No runtime code changes. Tests only.
"""

import sys
import os
import unittest
import json
import tempfile
import shutil
import hashlib

# Add paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_ARTIFACT_SRC = os.path.join(_REPO_ROOT, 'artifact', 'src')
_M3_SRC = os.path.join(_REPO_ROOT, 'm3', 'src')
sys.path.insert(0, _ARTIFACT_SRC)
sys.path.insert(0, _M3_SRC)

from builder import build_artifact, artifact_to_json
from gateway import ExecutionGateway

# Fixture paths
_FIXTURES_DIR = os.path.join(_REPO_ROOT, 'tests', 'fixtures', 'l8')


def load_fixture_bytes(filename: str) -> bytes:
    """Load fixture file as bytes."""
    path = os.path.join(_FIXTURES_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()


def load_fixture_json(filename: str) -> dict:
    """Load fixture file as parsed JSON."""
    path = os.path.join(_FIXTURES_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class RegressionLockBase(unittest.TestCase):
    """Base class for regression lock tests."""

    def setUp(self):
        """Create temporary directory with required structure."""
        self.temp_dir = tempfile.mkdtemp(prefix='l8_regression_')
        self.run_dir = os.path.join(self.temp_dir, 'artifacts', 'run')
        os.makedirs(self.run_dir, exist_ok=True)

        # Create mock PoC script (for ROUTE execution tests)
        scripts_dir = os.path.join(self.temp_dir, 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        poc_script = os.path.join(scripts_dir, 'run_poc_v2.sh')
        with open(poc_script, 'w') as f:
            f.write('#!/bin/bash\necho "Mock PoC execution"\n')
        os.chmod(poc_script, 0o755)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _inject_and_build(self, proposal_set):
        """Inject ProposalSet and build artifact."""
        return build_artifact(
            proposal_set=proposal_set,
            run_id="regression_test",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

    def _artifact_json(self, artifact):
        """Get deterministic JSON string of artifact."""
        return artifact_to_json(artifact)

    def _artifact_hash(self, artifact):
        """Compute deterministic hash of artifact JSON."""
        json_str = self._artifact_json(artifact)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


# =============================================================================
# SECTION 1: ACCEPT REGRESSION LOCKS (from fixture files)
# =============================================================================

class TestL3EnvelopeAcceptLock(RegressionLockBase):
    """Test L-3 envelope ACCEPT regression lock using fixture."""

    def test_l3_envelope_produces_accept(self):
        """L-3 fixture envelope MUST produce ACCEPT."""
        envelope = load_fixture_json('l3_accept_envelope.json')
        artifact = self._inject_and_build(envelope)
        self.assertEqual(artifact["decision"], "ACCEPT")
        print(f"[FIXTURE TEST] l3_accept_envelope.json -> ACCEPT")

    def test_l3_envelope_accept_payload_structure(self):
        """L-3 ACCEPT payload MUST have correct ROUTE structure."""
        envelope = load_fixture_json('l3_accept_envelope.json')
        artifact = self._inject_and_build(envelope)

        self.assertIn("accept_payload", artifact)
        self.assertEqual(artifact["accept_payload"]["kind"], "ROUTE")
        self.assertEqual(artifact["accept_payload"]["route"]["intent"], "STATUS_QUERY")
        self.assertEqual(artifact["accept_payload"]["route"]["target"], "alpha")
        self.assertNotIn("mode", artifact["accept_payload"]["route"])

    def test_l3_envelope_byte_stable(self):
        """L-3 fixture envelope MUST produce byte-identical artifacts."""
        envelope = load_fixture_json('l3_accept_envelope.json')

        artifact1 = self._inject_and_build(envelope)
        artifact2 = self._inject_and_build(envelope)

        json1 = self._artifact_json(artifact1)
        json2 = self._artifact_json(artifact2)

        self.assertEqual(json1, json2, "Artifact JSON differs between runs - not byte-stable")
        print(f"[STABILITY TEST] L-3 artifact byte-stable: hash={self._artifact_hash(artifact1)[:16]}...")

    def test_l3_envelope_unaffected_by_input_raw_variations(self):
        """L-3 ACCEPT is determined by proposal, not input.raw."""
        # Same proposal structure, different input.raw
        envelope_variant = load_fixture_json('l3_accept_envelope.json')
        envelope_variant["input"]["raw"] = "different input text"

        artifact = self._inject_and_build(envelope_variant)
        self.assertEqual(artifact["decision"], "ACCEPT")


class TestL4TransitionAcceptLock(RegressionLockBase):
    """Test L-4 STATE_TRANSITION ACCEPT regression lock using fixtures."""

    def test_l4_create_payment_produces_accept(self):
        """L-4 create_payment fixture MUST produce ACCEPT."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)
        self.assertEqual(artifact["decision"], "ACCEPT")
        print(f"[FIXTURE TEST] l4_create_payment_envelope.json -> ACCEPT")

    def test_l4_create_payment_accept_payload_structure(self):
        """L-4 ACCEPT payload MUST have correct STATE_TRANSITION structure."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)

        self.assertIn("accept_payload", artifact)
        self.assertEqual(artifact["accept_payload"]["kind"], "STATE_TRANSITION")
        self.assertIn("transition", artifact["accept_payload"])

        transition = artifact["accept_payload"]["transition"]
        self.assertEqual(transition["order_id"], "demo-order-1")
        self.assertEqual(transition["previous_state"], "CREATED")
        self.assertEqual(transition["event"], "create_payment")
        self.assertEqual(transition["current_state"], "PAYMENT_PENDING")
        self.assertEqual(transition["terminal"], False)

    def test_l4_cancel_order_produces_accept(self):
        """L-4 cancel_order fixture MUST produce ACCEPT."""
        envelope = load_fixture_json('l4_cancel_order_envelope.json')
        artifact = self._inject_and_build(envelope)
        self.assertEqual(artifact["decision"], "ACCEPT")
        print(f"[FIXTURE TEST] l4_cancel_order_envelope.json -> ACCEPT")

    def test_l4_cancel_order_transition_terminal(self):
        """L-4 cancel_order transition MUST show terminal state."""
        envelope = load_fixture_json('l4_cancel_order_envelope.json')
        artifact = self._inject_and_build(envelope)

        transition = artifact["accept_payload"]["transition"]
        self.assertEqual(transition["previous_state"], "CREATED")
        self.assertEqual(transition["event"], "cancel_order")
        self.assertEqual(transition["current_state"], "CANCELLED")
        self.assertEqual(transition["terminal"], True)

    def test_l4_envelope_byte_stable(self):
        """L-4 fixture envelope MUST produce byte-identical artifacts."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')

        artifact1 = self._inject_and_build(envelope)
        artifact2 = self._inject_and_build(envelope)

        json1 = self._artifact_json(artifact1)
        json2 = self._artifact_json(artifact2)

        self.assertEqual(json1, json2, "L-4 artifact JSON differs - not byte-stable")


# =============================================================================
# SECTION 2: REJECT EXECUTION GATE TESTS
# =============================================================================

class TestRejectExecutionGate(RegressionLockBase):
    """
    Test that REJECT artifacts do not trigger execution.

    This is the critical safety property: the gateway must not execute
    when the artifact decision is REJECT, and no stdout.raw.kv must exist.
    """

    def test_reject_artifact_does_not_execute(self):
        """REJECT artifact passed to gateway MUST NOT execute."""
        # Create a REJECT artifact
        invalid_envelope = {"garbage": True}
        artifact = self._inject_and_build(invalid_envelope)

        self.assertEqual(artifact["decision"], "REJECT")

        # Pass to gateway - this should NOT execute
        gateway = ExecutionGateway(self.temp_dir)
        result = gateway.execute_if_accepted(artifact, "/tmp/dummy_input.txt")

        # Assert no execution occurred
        self.assertFalse(result.executed, "Gateway executed despite REJECT artifact")
        self.assertEqual(result.decision, "REJECT")
        print("[GATE TEST] REJECT artifact -> gateway did not execute")

    def test_reject_artifact_no_stdout_raw_kv(self):
        """REJECT artifact MUST NOT produce stdout.raw.kv anywhere."""
        # Create a REJECT artifact
        invalid_envelope = {
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": []  # Zero proposals -> REJECT
        }
        artifact = self._inject_and_build(invalid_envelope)

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "NO_PROPOSALS")

        # Pass to gateway
        gateway = ExecutionGateway(self.temp_dir)
        result = gateway.execute_if_accepted(artifact, "/tmp/dummy_input.txt")

        # Assert no execution
        self.assertFalse(result.executed)

        # Assert no stdout.raw.kv anywhere in run directory
        for root, dirs, files in os.walk(self.run_dir):
            self.assertNotIn("stdout.raw.kv", files,
                f"stdout.raw.kv found at {root} despite REJECT")
        print("[GATE TEST] REJECT artifact -> no stdout.raw.kv exists")

    def test_multiple_reject_reasons_no_execution(self):
        """Various REJECT reasons all result in no execution."""
        reject_cases = [
            ({}, "empty dict"),
            ({"schema_version": "wrong"}, "wrong schema"),
            ({"schema_version": "m1.0", "input": {"raw": "x"}, "proposals": []}, "zero proposals"),
            ({"schema_version": "m1.0", "input": {"raw": "x"}, "proposals": [
                {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}},
                {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}}
            ]}, "ambiguous proposals"),
        ]

        gateway = ExecutionGateway(self.temp_dir)

        for envelope, description in reject_cases:
            with self.subTest(description=description):
                artifact = self._inject_and_build(envelope)
                self.assertEqual(artifact["decision"], "REJECT")

                result = gateway.execute_if_accepted(artifact, "/tmp/dummy.txt")
                self.assertFalse(result.executed,
                    f"Gateway executed for {description}")

        print(f"[GATE TEST] {len(reject_cases)} REJECT cases -> none executed")


# =============================================================================
# SECTION 3: ACCEPT EXECUTION VERIFICATION
# =============================================================================

class TestAcceptExecutionOccurs(RegressionLockBase):
    """Test that ACCEPT artifacts trigger execution and produce stdout.raw.kv."""

    def test_l4_accept_triggers_execution(self):
        """L-4 ACCEPT artifact MUST trigger execution via gateway."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)

        self.assertEqual(artifact["decision"], "ACCEPT")

        # Execute via gateway
        gateway = ExecutionGateway(self.temp_dir)
        result = gateway.execute_if_accepted(artifact, "/tmp/dummy_input.txt")

        self.assertTrue(result.executed, f"Execution failed: {result.error}")
        self.assertEqual(result.exit_code, 0)
        print("[GATE TEST] L-4 ACCEPT artifact -> execution occurred")

    def test_l4_execution_creates_stdout_raw_kv(self):
        """L-4 execution MUST create stdout.raw.kv."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)

        gateway = ExecutionGateway(self.temp_dir)
        result = gateway.execute_if_accepted(artifact, "/tmp/dummy_input.txt")

        self.assertTrue(result.executed)

        # Check stdout.raw.kv exists
        stdout_path = os.path.join(result.run_directory, "stdout.raw.kv")
        self.assertTrue(os.path.exists(stdout_path),
            f"stdout.raw.kv not found at {stdout_path}")
        print(f"[GATE TEST] L-4 ACCEPT -> stdout.raw.kv created at {result.run_directory}")

    def test_l4_stdout_raw_kv_content_correct(self):
        """L-4 stdout.raw.kv MUST have correct content."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)

        gateway = ExecutionGateway(self.temp_dir)
        result = gateway.execute_if_accepted(artifact, "/tmp/dummy_input.txt")

        stdout_path = os.path.join(result.run_directory, "stdout.raw.kv")
        with open(stdout_path, 'r') as f:
            content = f.read()

        # Verify expected key=value pairs
        self.assertIn("order_id=demo-order-1", content)
        self.assertIn("previous_state=CREATED", content)
        self.assertIn("event=create_payment", content)
        self.assertIn("current_state=PAYMENT_PENDING", content)
        self.assertIn("terminal=false", content)

    def test_l4_stdout_raw_kv_byte_stable(self):
        """L-4 stdout.raw.kv MUST be byte-stable across runs."""
        envelope = load_fixture_json('l4_cancel_order_envelope.json')

        artifact = self._inject_and_build(envelope)
        gateway = ExecutionGateway(self.temp_dir)

        result1 = gateway.execute_if_accepted(artifact, "/tmp/dummy.txt")
        stdout_path1 = os.path.join(result1.run_directory, "stdout.raw.kv")
        with open(stdout_path1, 'rb') as f:
            content1 = f.read()

        # Second run overwrites same directory
        result2 = gateway.execute_if_accepted(artifact, "/tmp/dummy.txt")
        stdout_path2 = os.path.join(result2.run_directory, "stdout.raw.kv")
        with open(stdout_path2, 'rb') as f:
            content2 = f.read()

        self.assertEqual(content1, content2, "stdout.raw.kv differs between runs")
        print("[STABILITY TEST] stdout.raw.kv byte-stable across runs")


# =============================================================================
# SECTION 4: GARBAGE ISOLATION TESTS
# =============================================================================

class TestGarbageIsolation(RegressionLockBase):
    """
    Test that prior rejected attempts do not affect subsequent acceptance.

    This proves: invalid proposal bytes cannot poison subsequent runs.
    """

    def test_prior_reject_does_not_affect_subsequent_accept(self):
        """Prior REJECT attempt does not affect subsequent ACCEPT decision."""
        valid_envelope = load_fixture_json('l3_accept_envelope.json')

        # First: inject garbage (will REJECT)
        garbage_artifact = self._inject_and_build({"garbage": True})
        self.assertEqual(garbage_artifact["decision"], "REJECT")

        # Then: inject valid envelope
        valid_artifact = self._inject_and_build(valid_envelope)
        self.assertEqual(valid_artifact["decision"], "ACCEPT")

        # Compare with baseline (no prior garbage)
        baseline_artifact = self._inject_and_build(valid_envelope)

        # Accept payloads MUST be identical
        self.assertEqual(
            valid_artifact["accept_payload"],
            baseline_artifact["accept_payload"]
        )
        print("[ISOLATION TEST] Prior REJECT does not affect subsequent ACCEPT")

    def test_artifact_hash_unchanged_after_garbage(self):
        """ACCEPT artifact hash MUST be unchanged regardless of prior REJECT runs."""
        valid_envelope = load_fixture_json('l3_accept_envelope.json')

        # Run garbage first
        self._inject_and_build(b'\x00\x01\x02')  # Will fail and REJECT
        self._inject_and_build({"invalid": "schema"})
        self._inject_and_build([])

        # Now run valid envelope
        artifact_after_garbage = self._inject_and_build(valid_envelope)
        hash_after_garbage = self._artifact_hash(artifact_after_garbage)

        # Run valid envelope in fresh state
        baseline = self._inject_and_build(valid_envelope)
        baseline_hash = self._artifact_hash(baseline)

        self.assertEqual(hash_after_garbage, baseline_hash,
            "ACCEPT artifact hash changed after garbage - isolation violated")
        print(f"[ISOLATION TEST] Artifact hash stable: {baseline_hash[:16]}...")


# =============================================================================
# SECTION 5: FIXTURE HASH DOCUMENTATION
# =============================================================================

class TestFixtureHashDocumentation(RegressionLockBase):
    """Document stable hashes for fixture-based ACCEPT artifacts."""

    def test_l3_fixture_artifact_hash_documented(self):
        """Document L-3 fixture artifact hash for regression detection."""
        envelope = load_fixture_json('l3_accept_envelope.json')
        artifact = self._inject_and_build(envelope)
        artifact_hash = self._artifact_hash(artifact)

        print(f"\n[L-3 FIXTURE ARTIFACT HASH]: {artifact_hash}")

        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertEqual(artifact["accept_payload"]["kind"], "ROUTE")

    def test_l4_create_payment_artifact_hash_documented(self):
        """Document L-4 create_payment fixture artifact hash."""
        envelope = load_fixture_json('l4_create_payment_envelope.json')
        artifact = self._inject_and_build(envelope)
        artifact_hash = self._artifact_hash(artifact)

        print(f"\n[L-4 CREATE_PAYMENT FIXTURE ARTIFACT HASH]: {artifact_hash}")

        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertEqual(artifact["accept_payload"]["kind"], "STATE_TRANSITION")

    def test_l4_cancel_order_artifact_hash_documented(self):
        """Document L-4 cancel_order fixture artifact hash."""
        envelope = load_fixture_json('l4_cancel_order_envelope.json')
        artifact = self._inject_and_build(envelope)
        artifact_hash = self._artifact_hash(artifact)

        print(f"\n[L-4 CANCEL_ORDER FIXTURE ARTIFACT HASH]: {artifact_hash}")

        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertEqual(artifact["accept_payload"]["transition"]["terminal"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
