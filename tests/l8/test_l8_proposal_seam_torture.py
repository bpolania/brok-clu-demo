#!/usr/bin/env python3
"""
Phase L-8: Proposal Seam Torture Tests (Corrected)

TEST SCOPE:
These tests inject data at the artifact layer's build_artifact() function,
which receives parsed ProposalSet data. This tests the artifact layer's
ability to handle invalid/malformed ProposalSet data.

The tests cover two injection patterns:
1. BYTES INJECTION: Raw bytes that simulate what the seam would produce,
   then parsed through json.loads() before build_artifact() - same as
   production does.
2. DICT INJECTION: Direct dict injection to build_artifact() for schema
   violation tests where the data is already "parsed".

For raw bytes that cannot be parsed as JSON, the production path would
fail at json.loads() and collapse to REJECT. We test this by:
- Attempting json.loads() on the bytes
- If parsing fails, that confirms REJECT would occur
- If parsing succeeds, we pass the result to build_artifact()

Test Categories:
1. Empty/garbage bytes (cannot parse as JSON -> REJECT)
2. Invalid JSON bytes (truncated, malformed -> REJECT)
3. Valid JSON, invalid schema (missing fields, wrong types -> REJECT)
4. Unexpected fields (additionalProperties: false -> REJECT)
5. Multiple proposals (AMBIGUOUS_PROPOSALS -> REJECT)
6. Schema limit violations (max items, max length -> REJECT)
7. Control cases (valid L-3/L-4 envelopes -> ACCEPT)
8. Determinism verification

Assertions use only pre-existing stable reject reason codes:
- INVALID_PROPOSALS (M-2)
- NO_PROPOSALS (M-2)
- AMBIGUOUS_PROPOSALS (M-2)
- INVALID_EVENT_TOKEN (L-4)
- ILLEGAL_TRANSITION (L-4)

No runtime code changes. Tests only.
"""

import sys
import os
import unittest
import json
import tempfile
import shutil

# Add artifact/src to path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_ARTIFACT_SRC = os.path.join(_REPO_ROOT, 'artifact', 'src')
sys.path.insert(0, _ARTIFACT_SRC)

from builder import build_artifact, artifact_to_json

# Import gateway for execution gate tests
_M3_SRC = os.path.join(_REPO_ROOT, 'm3', 'src')
sys.path.insert(0, _M3_SRC)
from gateway import ExecutionGateway


class TortureTestBase(unittest.TestCase):
    """Base class for torture tests with common helpers."""

    def setUp(self):
        """Create temporary directory for test artifacts."""
        self.temp_dir = tempfile.mkdtemp(prefix='l8_torture_')
        self.run_dir = os.path.join(self.temp_dir, 'artifacts', 'run')
        os.makedirs(self.run_dir, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _inject_bytes(self, proposal_bytes: bytes):
        """
        Inject raw bytes simulating proposal engine output.

        This follows the production path:
        1. Proposal engine returns bytes
        2. Bytes are parsed as JSON
        3. Parsed dict is passed to build_artifact()

        If JSON parsing fails, returns a REJECT artifact (simulating what
        production would do via load_proposal_set error handling).

        Args:
            proposal_bytes: Raw bytes to inject

        Returns:
            Artifact dict
        """
        try:
            # Attempt to parse bytes as JSON (production path)
            proposal_set = json.loads(proposal_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # JSON parsing failed - production would REJECT
            # We simulate this by passing None which build_artifact handles
            proposal_set = None

        return build_artifact(
            proposal_set=proposal_set,
            run_id="torture_bytes_test",
            input_ref="test/torture_input.txt",
            proposal_set_ref="artifacts/proposals/torture/proposal_set.json"
        )

    def _inject_dict(self, proposal_set_dict):
        """
        Inject dict directly to build_artifact.

        Used for schema violation tests where we want to test the validator's
        handling of structurally invalid but JSON-parseable data.

        Args:
            proposal_set_dict: Dict to inject (or None, list, etc.)

        Returns:
            Artifact dict
        """
        return build_artifact(
            proposal_set=proposal_set_dict,
            run_id="torture_dict_test",
            input_ref="test/torture_input.txt",
            proposal_set_ref="artifacts/proposals/torture/proposal_set.json"
        )

    def _assert_reject(self, artifact, expected_reason=None):
        """Assert artifact is REJECT with optional reason check."""
        self.assertEqual(artifact["decision"], "REJECT",
            f"Expected REJECT, got {artifact['decision']}")
        if expected_reason:
            self.assertEqual(
                artifact["reject_payload"]["reason_code"],
                expected_reason,
                f"Expected reason {expected_reason}, got {artifact['reject_payload']['reason_code']}"
            )


class TestEmptyAndGarbageBytes(TortureTestBase):
    """Test 1: Empty and garbage bytes injection."""

    # Fixed byte fixtures for reproducibility
    GARBAGE_FIXTURES = [
        (b'', "empty bytes"),
        (b'\x00\x01\x02\x03\x04\x05', "binary garbage"),
        (b'\xff\xfe\xfd\xfc\xfb\xfa', "high-value bytes"),
        (b'\x89PNG\r\n\x1a\n', "PNG header"),
        (b'GIF89a', "GIF header"),
        (b'\x7fELF', "ELF header"),
    ]

    def test_empty_bytes_rejects(self):
        """Empty bytes cannot parse as JSON -> REJECT."""
        artifact = self._inject_bytes(b'')
        self._assert_reject(artifact, "INVALID_PROPOSALS")
        print(f"[BYTES TEST] Empty bytes -> REJECT (INVALID_PROPOSALS)")

    def test_garbage_bytes_reject(self):
        """Non-JSON binary bytes -> REJECT."""
        for fixture, description in self.GARBAGE_FIXTURES[1:]:  # Skip empty
            with self.subTest(description=description):
                artifact = self._inject_bytes(fixture)
                self._assert_reject(artifact, "INVALID_PROPOSALS")
        print(f"[BYTES TEST] {len(self.GARBAGE_FIXTURES)-1} garbage fixtures -> REJECT")

    def test_garbage_bytes_deterministic(self):
        """Same garbage bytes produce identical REJECT."""
        fixture = b'\x00\x01\x02\x03\x04\x05'
        artifact1 = self._inject_bytes(fixture)
        artifact2 = self._inject_bytes(fixture)

        self.assertEqual(artifact1["decision"], artifact2["decision"])
        self.assertEqual(
            artifact1["reject_payload"]["reason_code"],
            artifact2["reject_payload"]["reason_code"]
        )
        print("[BYTES TEST] Garbage bytes deterministic: same input -> same REJECT")


class TestInvalidJSONBytes(TortureTestBase):
    """Test 2: Invalid JSON bytes (actual malformed JSON, not Python objects)."""

    INVALID_JSON_FIXTURES = [
        (b'not json at all', "plain text"),
        (b'{"schema_version": "m1.0"', "truncated JSON object"),
        (b'{"unclosed": [1, 2, 3', "truncated JSON array"),
        (b"{'single': 'quotes'}", "single quotes (invalid JSON)"),
        (b'{"trailing": "comma",}', "trailing comma"),
        (b'undefined', "JavaScript undefined"),
        (b'NaN', "JavaScript NaN"),
    ]

    def test_invalid_json_bytes_reject(self):
        """Malformed JSON bytes -> REJECT."""
        for fixture, description in self.INVALID_JSON_FIXTURES:
            with self.subTest(description=description):
                artifact = self._inject_bytes(fixture)
                self._assert_reject(artifact, "INVALID_PROPOSALS")
        print(f"[BYTES TEST] {len(self.INVALID_JSON_FIXTURES)} invalid JSON fixtures -> REJECT")

    def test_invalid_utf8_bytes_reject(self):
        """Invalid UTF-8 sequences -> REJECT."""
        # These are invalid UTF-8 byte sequences
        invalid_utf8 = b'\xff\xfe' + b'{"valid": "json"}'
        artifact = self._inject_bytes(invalid_utf8)
        self._assert_reject(artifact, "INVALID_PROPOSALS")
        print("[BYTES TEST] Invalid UTF-8 prefix -> REJECT")


class TestValidJSONInvalidSchema(TortureTestBase):
    """Test 3: Valid JSON but invalid schema (dict injection)."""

    def test_wrong_schema_version(self):
        """Wrong schema_version -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "wrong_version",
            "input": {"raw": "test"},
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_missing_schema_version(self):
        """Missing schema_version -> REJECT."""
        artifact = self._inject_dict({
            "input": {"raw": "test"},
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_missing_input(self):
        """Missing input field -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_missing_proposals(self):
        """Missing proposals field -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"}
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_wrong_input_type(self):
        """Wrong input type (string instead of object) -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": "should be object",
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_wrong_proposals_type(self):
        """Wrong proposals type (string instead of array) -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": "should be array"
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_invalid_proposal_kind(self):
        """Invalid proposal kind -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "INVALID_KIND",
                "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}
            }]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_invalid_intent(self):
        """Invalid intent value -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {"intent": "HACK_SYSTEM", "slots": {"target": "alpha"}}
            }]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_non_dict_input_to_build_artifact(self):
        """Non-dict passed to build_artifact -> REJECT."""
        # This simulates what happens when JSON parsing returns non-dict
        artifact = self._inject_dict(None)
        self._assert_reject(artifact, "INVALID_PROPOSALS")

        artifact = self._inject_dict([])
        self._assert_reject(artifact, "INVALID_PROPOSALS")

        artifact = self._inject_dict("string")
        self._assert_reject(artifact, "INVALID_PROPOSALS")


class TestUnexpectedFields(TortureTestBase):
    """Test 4: Unexpected fields (additionalProperties: false)."""

    def test_unexpected_root_field(self):
        """Unexpected field at root level -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [],
            "unexpected_field": "should_fail"
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_unexpected_input_field(self):
        """Unexpected field in input object -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test", "extra": "bad"},
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_unexpected_proposal_field(self):
        """Unexpected field in proposal -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}},
                "confidence": 0.99  # Not allowed
            }]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_unexpected_payload_field(self):
        """Unexpected field in payload -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"},
                    "score": 100  # Not allowed
                }
            }]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_unexpected_slots_field(self):
        """Unexpected field in slots -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha", "priority": "high"}
                }
            }]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")


class TestMultipleProposals(TortureTestBase):
    """Test 5: Multiple proposals (pre-existing AMBIGUOUS_PROPOSALS code)."""

    def test_two_proposals_reject(self):
        """Two proposals -> REJECT with AMBIGUOUS_PROPOSALS."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [
                {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}},
                {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}}
            ]
        })
        self._assert_reject(artifact, "AMBIGUOUS_PROPOSALS")

    def test_max_proposals_reject(self):
        """Maximum (8) proposals -> REJECT with AMBIGUOUS_PROPOSALS."""
        proposals = [
            {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}}
            for _ in range(8)
        ]
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        })
        self._assert_reject(artifact, "AMBIGUOUS_PROPOSALS")

    def test_over_max_proposals_reject(self):
        """Over maximum (9) proposals -> REJECT with INVALID_PROPOSALS (schema violation)."""
        proposals = [
            {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}}
            for _ in range(9)
        ]
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")


class TestSchemaLimitViolations(TortureTestBase):
    """Test 6: Schema limit violations (field-level constraints)."""

    def test_input_raw_over_4096_chars(self):
        """input.raw over 4096 characters -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "x" * 4097},
            "proposals": []
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_input_raw_exactly_4096_chars_zero_proposals(self):
        """input.raw at exactly 4096 chars with zero proposals -> REJECT (NO_PROPOSALS)."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "x" * 4096},
            "proposals": []
        })
        # Valid structure, but zero proposals
        self._assert_reject(artifact, "NO_PROPOSALS")

    def test_error_entry_over_256_chars(self):
        """Error entry over 256 chars -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [],
            "errors": ["E" * 257]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_over_16_error_entries(self):
        """Over 16 error entries -> REJECT."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [],
            "errors": [f"ERROR_{i}" for i in range(17)]
        })
        self._assert_reject(artifact, "INVALID_PROPOSALS")

    def test_large_but_valid_proposalset_bytes(self):
        """Large ProposalSet bytes (CI-safe size) that is invalid -> REJECT, no crash."""
        # Create a large but JSON-parseable payload (invalid schema)
        large_payload = json.dumps({
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": [],
            "garbage": "x" * 50000  # Extra field, invalid
        }).encode('utf-8')

        artifact = self._inject_bytes(large_payload)
        self._assert_reject(artifact, "INVALID_PROPOSALS")
        print(f"[BYTES TEST] Large payload ({len(large_payload)} bytes) -> REJECT, no crash")


class TestControlCasesAccept(TortureTestBase):
    """Test 7: Control cases - valid envelopes produce ACCEPT."""

    def test_l3_envelope_accepts(self):
        """Exact L-3 envelope -> ACCEPT."""
        l3_bytes = json.dumps({
            "schema_version": "m1.0",
            "input": {"raw": "status of alpha"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"}
                }
            }]
        }).encode('utf-8')

        artifact = self._inject_bytes(l3_bytes)
        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertEqual(artifact["accept_payload"]["kind"], "ROUTE")
        print("[BYTES TEST] L-3 envelope bytes -> ACCEPT")

    def test_l4_create_payment_accepts(self):
        """Valid L-4 create_payment -> ACCEPT."""
        l4_bytes = json.dumps({
            "schema_version": "m1.0",
            "input": {"raw": "create payment"},
            "proposals": [{
                "kind": "STATE_TRANSITION_REQUEST",
                "payload": {"event_token": "create_payment"}
            }]
        }).encode('utf-8')

        artifact = self._inject_bytes(l4_bytes)
        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertEqual(artifact["accept_payload"]["kind"], "STATE_TRANSITION")
        print("[BYTES TEST] L-4 create_payment bytes -> ACCEPT")

    def test_l3_envelope_with_mode_rejects(self):
        """L-3 envelope with mode field -> REJECT (envelope mismatch)."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "status of alpha"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha", "mode": "graceful"}
                }
            }]
        })
        self._assert_reject(artifact)
        notes = artifact["reject_payload"].get("notes", [])
        self.assertIn("L3_ENVELOPE_MISMATCH", notes)


class TestL4StateTransition(TortureTestBase):
    """Test L-4 STATE_TRANSITION_REQUEST handling."""

    def test_invalid_event_token_rejects(self):
        """Invalid event_token -> REJECT with INVALID_EVENT_TOKEN."""
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "hack system"},
            "proposals": [{
                "kind": "STATE_TRANSITION_REQUEST",
                "payload": {"event_token": "hack_system"}
            }]
        })
        self._assert_reject(artifact, "INVALID_EVENT_TOKEN")

    def test_illegal_transition_rejects(self):
        """Illegal transition from CREATED state -> REJECT with ILLEGAL_TRANSITION."""
        # payment_succeeded requires PAYMENT_PENDING state, not CREATED
        artifact = self._inject_dict({
            "schema_version": "m1.0",
            "input": {"raw": "payment succeeded"},
            "proposals": [{
                "kind": "STATE_TRANSITION_REQUEST",
                "payload": {"event_token": "payment_succeeded"}
            }]
        })
        self._assert_reject(artifact, "ILLEGAL_TRANSITION")


class TestDeterminism(TortureTestBase):
    """Test 8: Determinism - same input produces same decision."""

    def test_reject_decision_deterministic(self):
        """Same invalid input produces identical REJECT decision."""
        test_cases = [
            ({}, "empty dict"),
            ({"garbage": True}, "garbage dict"),
            ({"schema_version": "m1.0", "input": {"raw": ""}, "proposals": []}, "zero proposals"),
        ]

        for fixture, description in test_cases:
            with self.subTest(description=description):
                artifact1 = self._inject_dict(fixture)
                artifact2 = self._inject_dict(fixture)

                # Decision must be identical
                self.assertEqual(artifact1["decision"], artifact2["decision"])

                # Reject reason must be identical
                self.assertEqual(
                    artifact1.get("reject_payload", {}).get("reason_code"),
                    artifact2.get("reject_payload", {}).get("reason_code")
                )
        print("[DETERMINISM TEST] Same input -> same REJECT decision")

    def test_accept_decision_deterministic(self):
        """Same valid input produces identical ACCEPT decision and payload."""
        l3_dict = {
            "schema_version": "m1.0",
            "input": {"raw": "status of alpha"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "STATUS_QUERY",
                    "slots": {"target": "alpha"}
                }
            }]
        }

        artifact1 = self._inject_dict(l3_dict)
        artifact2 = self._inject_dict(l3_dict)

        # Decision must be identical
        self.assertEqual(artifact1["decision"], artifact2["decision"])
        self.assertEqual(artifact1["decision"], "ACCEPT")

        # Accept payload must be identical
        self.assertEqual(artifact1["accept_payload"], artifact2["accept_payload"])
        print("[DETERMINISM TEST] Same input -> same ACCEPT decision and payload")

    def test_bytes_determinism(self):
        """Same bytes produce identical artifacts."""
        l3_bytes = json.dumps({
            "schema_version": "m1.0",
            "input": {"raw": "status of alpha"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {"intent": "STATUS_QUERY", "slots": {"target": "alpha"}}
            }]
        }, sort_keys=True).encode('utf-8')

        artifact1 = self._inject_bytes(l3_bytes)
        artifact2 = self._inject_bytes(l3_bytes)

        # Serialize both artifacts with same settings
        json1 = artifact_to_json(artifact1)
        json2 = artifact_to_json(artifact2)

        self.assertEqual(json1, json2)
        print("[DETERMINISM TEST] Same bytes -> byte-identical artifacts")


if __name__ == "__main__":
    unittest.main(verbosity=2)
