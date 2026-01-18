#!/usr/bin/env python3
"""
Phase M-2 Determinism Tests for Artifact Builder

Tests verify that artifact construction is deterministic:
- Same input always produces byte-for-byte identical output
- No timestamps, random values, or environment-dependent content

These tests are isolated from PoC v2 tests.
"""

import sys
import os
import unittest

# Add artifact/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from builder import build_artifact, artifact_to_json


class TestArtifactDeterminism(unittest.TestCase):
    """Test that artifact construction is deterministic."""

    def _make_proposal_set(self, proposals):
        return {
            "schema_version": "m1.0",
            "input": {"raw": "test input"},
            "proposals": proposals
        }

    def _make_proposal(self, intent="RESTART_SUBSYSTEM", target="alpha", mode="graceful"):
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

    def test_identical_output_for_identical_input_accept(self):
        """Same ACCEPT input must produce byte-for-byte identical JSON output."""
        proposal_set = self._make_proposal_set([self._make_proposal()])

        outputs = []
        for _ in range(10):
            artifact = build_artifact(
                proposal_set=proposal_set,
                run_id="test_run",
                input_ref="test/input.txt",
                proposal_set_ref="artifacts/proposals/test/proposal_set.json"
            )
            json_output = artifact_to_json(artifact)
            outputs.append(json_output)

        first = outputs[0]
        for i, output in enumerate(outputs[1:], 2):
            self.assertEqual(first, output,
                f"Run {i} produced different output than run 1")

    def test_identical_output_for_identical_input_reject(self):
        """Same REJECT input must produce byte-for-byte identical JSON output."""
        proposal_set = self._make_proposal_set([])

        outputs = []
        for _ in range(10):
            artifact = build_artifact(
                proposal_set=proposal_set,
                run_id="test_run",
                input_ref="test/input.txt",
                proposal_set_ref="artifacts/proposals/test/proposal_set.json"
            )
            json_output = artifact_to_json(artifact)
            outputs.append(json_output)

        first = outputs[0]
        for i, output in enumerate(outputs[1:], 2):
            self.assertEqual(first, output,
                f"Run {i} produced different output than run 1")

    def test_determinism_across_various_inputs(self):
        """Determinism must hold for various input types."""
        test_cases = [
            # Zero proposals
            self._make_proposal_set([]),
            # One proposal
            self._make_proposal_set([self._make_proposal()]),
            # Multiple proposals
            self._make_proposal_set([
                self._make_proposal(target="alpha"),
                self._make_proposal(target="beta")
            ]),
            # Invalid proposal set
            {"garbage": True},
            # Different intents
            self._make_proposal_set([
                self._make_proposal(intent="STATUS_QUERY", target="gamma")
            ]),
        ]

        for proposal_set in test_cases:
            with self.subTest(proposals=str(proposal_set)[:50]):
                result1 = artifact_to_json(build_artifact(
                    proposal_set=proposal_set,
                    run_id="test_run",
                    input_ref="test/input.txt",
                    proposal_set_ref="artifacts/proposals/test/proposal_set.json"
                ))
                result2 = artifact_to_json(build_artifact(
                    proposal_set=proposal_set,
                    run_id="test_run",
                    input_ref="test/input.txt",
                    proposal_set_ref="artifacts/proposals/test/proposal_set.json"
                ))
                self.assertEqual(result1, result2)

    def test_no_timestamps_in_output(self):
        """Artifact output must not contain timestamps."""
        proposal_set = self._make_proposal_set([self._make_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        json_output = artifact_to_json(artifact)

        # Check for common timestamp patterns
        import re
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # ISO date
            r'\d{4}/\d{2}/\d{2}',  # Alt date
            r'\d{2}:\d{2}:\d{2}',  # Time
            r'T\d{2}:\d{2}',        # ISO time separator
        ]

        for pattern in timestamp_patterns:
            matches = re.findall(pattern, json_output)
            self.assertEqual(len(matches), 0,
                f"Found timestamp-like pattern '{pattern}' in output: {matches}")

    def test_json_output_stable_ordering(self):
        """JSON keys must be in stable (sorted) order."""
        proposal_set = self._make_proposal_set([self._make_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        json_output1 = artifact_to_json(artifact)
        json_output2 = artifact_to_json(artifact)

        # Should be identical since keys are sorted
        self.assertEqual(json_output1, json_output2)

        # Verify keys appear in sorted order in the JSON string
        import json
        parsed = json.loads(json_output1)
        # Re-serialize with sort_keys to verify
        reserialized = json.dumps(parsed, sort_keys=True, indent=2)
        self.assertEqual(json_output1, reserialized)


class TestArtifactBoundedness(unittest.TestCase):
    """Test artifact boundedness constraints."""

    def _make_proposal_set(self, proposals):
        return {
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        }

    def _make_proposal(self, target="alpha"):
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "RESTART_SUBSYSTEM",
                "slots": {"target": target, "mode": "graceful"}
            }
        }

    def test_max_proposals_handled(self):
        """Maximum number of proposals (8) should be handled correctly."""
        proposals = [self._make_proposal() for _ in range(8)]
        proposal_set = self._make_proposal_set(proposals)

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        self.assertEqual(artifact["reject_payload"]["reason_code"], "AMBIGUOUS_PROPOSALS")
        self.assertEqual(artifact["construction"]["proposal_count"], 8)

    def test_validator_errors_bounded(self):
        """Validator errors in artifact must be bounded."""
        # Create a very malformed proposal set that generates many errors
        malformed = {
            "schema_version": "wrong",
            "input": "not_object",
            "proposals": "not_array",
            "extra1": 1, "extra2": 2, "extra3": 3
        }

        artifact = build_artifact(
            proposal_set=malformed,
            run_id="test_run",
            input_ref="test/input.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertEqual(artifact["decision"], "REJECT")
        if "validator_errors" in artifact["construction"]:
            self.assertLessEqual(len(artifact["construction"]["validator_errors"]), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
