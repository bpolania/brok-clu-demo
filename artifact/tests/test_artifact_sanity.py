#!/usr/bin/env python3
"""
Phase M-2 Sanity Tests for Artifact Layer

These tests verify constraints that MUST NOT regress:
1. Artifact JSON contains no absolute paths
2. Validator rejects absolute paths in refs
3. No machine-specific patterns in artifact output

These tests are isolated from PoC v2.
"""

import sys
import os
import re
import unittest

# Add artifact/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from builder import build_artifact, artifact_to_json

# Use importlib to load artifact validator (avoid collision with proposal validator)
import importlib.util
_ARTIFACT_SRC = os.path.join(os.path.dirname(__file__), '..', 'src')
_validator_path = os.path.join(_ARTIFACT_SRC, 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _validator_path)
_artifact_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_artifact_validator)
validate_artifact = _artifact_validator.validate_artifact


class TestArtifactNoAbsolutePaths(unittest.TestCase):
    """Test that artifact output contains no absolute paths."""

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
                "slots": {"target": target, "mode": mode}
            }
        }

    def test_no_absolute_paths_in_accept_artifact(self):
        """ACCEPT artifact must not contain absolute paths."""
        proposal_set = self._make_proposal_set([self._make_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="artifacts/inputs/test_run/input.raw",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )
        json_output = artifact_to_json(artifact)

        # Check for absolute path patterns
        self._assert_no_absolute_paths(json_output)

    def test_no_absolute_paths_in_reject_artifact(self):
        """REJECT artifact must not contain absolute paths."""
        proposal_set = self._make_proposal_set([])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="artifacts/inputs/test_run/input.raw",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )
        json_output = artifact_to_json(artifact)

        self._assert_no_absolute_paths(json_output)

    def test_no_machine_specific_patterns(self):
        """Artifact must not contain machine-specific patterns."""
        proposal_set = self._make_proposal_set([self._make_proposal()])

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id="test_run",
            input_ref="artifacts/inputs/test_run/input.raw",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )
        json_output = artifact_to_json(artifact)

        # Patterns that indicate machine-specific content
        machine_patterns = [
            r'/Users/',           # macOS home
            r'/home/',            # Linux home
            r'/tmp/',             # Temp directory
            r'/var/',             # Var directory
            r'C:\\',              # Windows drive
            r'D:\\',              # Windows drive
            r'/private/var',      # macOS private
        ]

        for pattern in machine_patterns:
            self.assertNotRegex(json_output, pattern,
                f"Found machine-specific pattern '{pattern}' in artifact")

    def _assert_no_absolute_paths(self, json_str):
        """Assert that JSON string contains no absolute paths."""
        # Pattern: string value starting with / (but not just a single char after colon)
        # We look for: ": "/..." pattern in JSON
        absolute_path_pattern = r'": "(/[^"]+)"'
        matches = re.findall(absolute_path_pattern, json_str)

        self.assertEqual(len(matches), 0,
            f"Found absolute path(s) in artifact JSON: {matches}")


class TestValidatorRejectsAbsolutePaths(unittest.TestCase):
    """Test that validator rejects artifacts with absolute paths."""

    def _make_artifact(self, input_ref, proposal_set_ref):
        return {
            "artifact_version": "artifact_v1",
            "run_id": "test_run",
            "input_ref": input_ref,
            "proposal_set_ref": proposal_set_ref,
            "decision": "REJECT",
            "reject_payload": {"reason_code": "NO_PROPOSALS"},
            "construction": {
                "ruleset_id": "M2_RULESET_V1",
                "proposal_count": 0,
                "selected_proposal_index": None
            }
        }

    def test_validator_rejects_absolute_input_ref(self):
        """Validator must reject absolute paths in input_ref."""
        artifact = self._make_artifact(
            input_ref="/tmp/in.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)

        self.assertFalse(is_valid)
        self.assertIn("INPUT_REF_ABSOLUTE_PATH", errors)

    def test_validator_rejects_absolute_proposal_set_ref(self):
        """Validator must reject absolute paths in proposal_set_ref."""
        artifact = self._make_artifact(
            input_ref="artifacts/inputs/test/input.raw",
            proposal_set_ref="/absolute/path/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)

        self.assertFalse(is_valid)
        self.assertIn("PROPOSAL_SET_REF_ABSOLUTE_PATH", errors)

    def test_validator_accepts_repo_relative_refs(self):
        """Validator must accept repo-relative refs."""
        artifact = self._make_artifact(
            input_ref="artifacts/inputs/test/input.raw",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        is_valid, errors = validate_artifact(artifact)

        self.assertTrue(is_valid, f"Unexpected errors: {errors}")


class TestArtifactRefsPattern(unittest.TestCase):
    """Test artifact refs patterns for various inputs."""

    def _make_proposal_set(self, proposals):
        return {
            "schema_version": "m1.0",
            "input": {"raw": "test"},
            "proposals": proposals
        }

    def _make_proposal(self):
        return {
            "kind": "ROUTE_CANDIDATE",
            "payload": {
                "intent": "RESTART_SUBSYSTEM",
                "slots": {"target": "alpha", "mode": "graceful"}
            }
        }

    def test_repo_relative_input_ref_preserved(self):
        """Repo-relative input_ref should be preserved as-is."""
        artifact = build_artifact(
            proposal_set=self._make_proposal_set([self._make_proposal()]),
            run_id="test_run",
            input_ref="examples/inputs/test.txt",
            proposal_set_ref="artifacts/proposals/test/proposal_set.json"
        )

        self.assertEqual(artifact["input_ref"], "examples/inputs/test.txt")
        self.assertFalse(artifact["input_ref"].startswith('/'))

    def test_artifacts_input_ref_pattern(self):
        """Input ref under artifacts/ should be valid."""
        artifact = build_artifact(
            proposal_set=self._make_proposal_set([self._make_proposal()]),
            run_id="test_run",
            input_ref="artifacts/inputs/test_run/input.raw",
            proposal_set_ref="artifacts/proposals/test_run/proposal_set.json"
        )

        self.assertEqual(artifact["input_ref"], "artifacts/inputs/test_run/input.raw")

        # Validate the artifact
        is_valid, errors = validate_artifact(artifact)
        self.assertTrue(is_valid, f"Unexpected errors: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
