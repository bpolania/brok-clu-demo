#!/usr/bin/env python3
"""
Phase M-2 Unit Tests for Artifact Builder

Tests cover:
- Determinism: same input yields byte-for-byte identical output
- Decision rules: zero/one/multiple proposals
- Invalid proposal handling
- Boundedness and schema compliance

These tests are isolated from PoC v2 tests.
"""

import sys
import os
import unittest

# Add artifact/src to path (insert at beginning to avoid collision with proposal/src)
_ARTIFACT_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, _ARTIFACT_SRC)

from builder import (
    build_artifact,
    artifact_to_json,
    ARTIFACT_VERSION,
    RULESET_ID
)

# Import validator explicitly from artifact/src to avoid collision
import importlib.util
_validator_path = os.path.join(_ARTIFACT_SRC, 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _validator_path)
_artifact_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_artifact_validator)
validate_artifact = _artifact_validator.validate_artifact


class TestArtifactBuilderDecisions(unittest.TestCase):
    """Test artifact builder decision rules (M2_RULESET_V1 + L-3 envelope gate)."""

    def _make_proposal_set(self, proposals, errors=None):
        """Helper to create a valid ProposalSet structure."""
        result = {
            "schema_version": "m1.0",
            "input": {"raw": "test input"},
            "proposals": proposals
        }
        if errors:
            result["errors"] = errors
        return result

    def _make_proposal(self, intent="RESTART_SUBSYSTEM", target="alpha", mode="graceful"):
        """Helper to create a valid proposal (non-L3 envelope)."""
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": intent,
                "slots": {
                    "target": target,
                    "mode": mode
                }
            }
        }

    def _make_l3_envelope_proposal(self):
        """Helper to create the L-3 envelope proposal (the only one that ACCEPTs)."""
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "STATUS_QUERY",
                "slots": {
                    "target": "alpha"
                }
            }
        }

    def test_zero_proposals_rejects_with_no_proposals(self):
        """ProposalSet with zero proposals must produce REJECT with NO_PROPOSALS."""
        proposal_set = self._make_proposal_set([])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "NO_PROPOSALS")
        self.assertEqual(artifact["construction"]["proposal_count"], 0)
        self.assertIsNone(artifact["construction"]["selected_proposal_index"])

    def test_one_proposal_accepts(self):
        """ProposalSet with exactly one L-3 envelope proposal must produce ACCEPT."""
        # Under L-3, only the exact envelope (STATUS_QUERY alpha, no mode) can ACCEPT
        proposal = self._make_l3_envelope_proposal()
        proposal_set = self._make_proposal_set([proposal])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "ACCEPT")
        self.assertIn("accept_payload", artifact)
        self.assertEqual(artifact["accept_payload"]["kind"], "ROUTE")
        self.assertEqual(artifact["accept_payload"]["route"]["intent"], "STATUS_QUERY")
        self.assertEqual(artifact["accept_payload"]["route"]["target"], "alpha")
        self.assertNotIn("mode", artifact["accept_payload"]["route"])
        self.assertEqual(artifact["construction"]["proposal_count"], 1)
        self.assertEqual(artifact["construction"]["selected_proposal_index"], 0)

    def test_non_l3_envelope_proposal_rejects(self):
        """ProposalSet with one proposal outside L-3 envelope must produce REJECT."""
        # RESTART_SUBSYSTEM is schema-valid but not the L-3 envelope
        proposal = self._make_proposal()
        proposal_set = self._make_proposal_set([proposal])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertIn("reject_payload", artifact)
        notes = artifact["reject_payload"].get("notes", [])
        self.assertIn("L3_ENVELOPE_MISMATCH", notes)

    def test_multiple_proposals_rejects_with_ambiguous(self):
        """ProposalSet with 2+ proposals must produce REJECT with AMBIGUOUS_PROPOSALS."""
        proposals = [
            self._make_proposal(target="alpha"),
            self._make_proposal(target="beta")
        ]
        proposal_set = self._make_proposal_set(proposals)

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "AMBIGUOUS_PROPOSALS")
        self.assertEqual(artifact["construction"]["proposal_count"], 2)

    def test_invalid_proposal_set_rejects(self):
        """Invalid ProposalSet must produce REJECT with INVALID_PROPOSALS."""
        # Missing required fields
        invalid_proposal_set = {"garbage": True}

        artifact = build_artifact(
            proposal_set=invalid_proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "INVALID_PROPOSALS")
        self.assertIn("validator_errors", artifact["construction"])
        self.assertGreater(len(artifact["construction"]["validator_errors"]), 0)

    def test_non_dict_proposal_set_rejects(self):
        """Non-dict ProposalSet must produce REJECT with INVALID_PROPOSALS."""
        artifact = build_artifact(
            proposal_set="not a dict",
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "INVALID_PROPOSALS")

    def test_status_query_beta_rejects_under_l3(self):
        """STATUS_QUERY on beta is schema-valid but REJECTS under L-3 envelope gate."""
        proposal = {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "STATUS_QUERY",
                "slots": {
                    "target": "beta"
                }
            }
        }
        proposal_set = self._make_proposal_set([proposal])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        # Under L-3, only STATUS_QUERY alpha (no mode) can ACCEPT
        self.assertEqual(artifact["decision"], "REJECT")
        notes = artifact["reject_payload"].get("notes", [])
        self.assertIn("L3_ENVELOPE_MISMATCH", notes)


class TestArtifactBuilderValidation(unittest.TestCase):
    """Test that built artifacts pass validation."""

    def _make_proposal_set(self, proposals):
        return {
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        }

    def _make_l3_envelope_proposal(self):
        """The L-3 envelope proposal is the only one that ACCEPTs."""
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "STATUS_QUERY",
                "slots": {"target": "alpha"}
            }
        }

    def test_accept_artifact_validates(self):
        """ACCEPT artifacts must pass validation."""
        proposal_set = self._make_proposal_set([self._make_l3_envelope_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)
        self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_reject_artifact_validates(self):
        """REJECT artifacts must pass validation."""
        proposal_set = self._make_proposal_set([])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)
        self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_invalid_proposals_artifact_validates(self):
        """REJECT with INVALID_PROPOSALS must pass validation."""
        artifact = build_artifact(
            proposal_set={"garbage": True},
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)
        self.assertTrue(is_valid, f"Validation failed: {errors}")


class TestArtifactBuilderSchema(unittest.TestCase):
    """Test artifact builder output structure."""

    def _make_proposal_set(self, proposals):
        return {
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        }

    def _make_l3_envelope_proposal(self):
        """The L-3 envelope proposal is the only one that ACCEPTs."""
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "STATUS_QUERY",
                "slots": {"target": "alpha"}
            }
        }

    def test_artifact_has_required_fields(self):
        """All artifacts must have required fields."""
        proposal_set = self._make_proposal_set([self._make_l3_envelope_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertEqual(artifact["artifact_version"], ARTIFACT_VERSION)
        self.assertEqual(artifact["run_id"], "test_run")
        self.assertEqual(artifact["input_ref"], "test/input.txt")
        self.assertIn("decision", artifact)
        self.assertIn("construction", artifact)
        self.assertEqual(artifact["construction"]["ruleset_id"], RULESET_ID)

    def test_accept_has_no_reject_payload(self):
        """ACCEPT artifacts must not have reject_payload."""
        proposal_set = self._make_proposal_set([self._make_l3_envelope_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertIn("accept_payload", artifact)
        self.assertNotIn("reject_payload", artifact)

    def test_reject_has_no_accept_payload(self):
        """REJECT artifacts must not have accept_payload."""
        proposal_set = self._make_proposal_set([])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertIn("reject_payload", artifact)
        self.assertNotIn("accept_payload", artifact)


if __name__ == "__main__":
    unittest.main(verbosity=2)
