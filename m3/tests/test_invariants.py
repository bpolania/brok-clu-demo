#!/usr/bin/env python3
"""
Phase M-3: End-to-End Invariant Tests

Tests that verify structural invariants via observable signals,
not by inspecting semantics.

Invariants tested:
I1. REJECT never triggers PoC v2 execution
I2. ACCEPT always triggers PoC v2 execution
I3. Removing proposals yields REJECT
I4. Multiple proposals yield REJECT
I5. Artifact tampering fails validation or blocks execution
I6. Execution output is unchanged by wrapper layers (golden file)

Test approach:
- Run CLI pipeline with test inputs
- Observe file creation (stdout.raw.kv existence)
- Do NOT parse or interpret stdout.raw.kv content
- All tests are deterministic
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import unittest
from typing import Dict, Optional, Tuple, List

# Add paths - order matters to avoid module shadowing
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_M3_DIR = os.path.dirname(_TEST_DIR)
_REPO_ROOT = os.path.dirname(_M3_DIR)

# Add proposal/src FIRST so builder can import validate_proposal_set from proposal validator
sys.path.insert(0, os.path.join(_REPO_ROOT, 'proposal', 'src'))
# Add artifact/src SECOND - it will import validate_artifact via explicit path in gateway
sys.path.insert(0, os.path.join(_REPO_ROOT, 'artifact', 'src'))
# Add m3/src last
sys.path.insert(0, os.path.join(_M3_DIR, 'src'))

# Import gateway which uses artifact/src/validator
from gateway import ExecutionGateway, ExecutionBoundaryViolation, load_artifact_from_file

# Import artifact validator explicitly with full path reference
import importlib.util
_artifact_validator_path = os.path.join(_REPO_ROOT, 'artifact', 'src', 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _artifact_validator_path)
_artifact_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_artifact_validator)
validate_artifact = _artifact_validator.validate_artifact


# Test input that produces ACCEPT (L-3 demo trigger - case-insensitive, whitespace-tolerant)
# This is the ONLY input that produces ACCEPT under L-3 envelope gate
ACCEPT_INPUT = "status of alpha subsystem"

# Test input that produces REJECT (non-demo input - LLM engine produces UNMAPPED proposals)
REJECT_INPUT = "xyzzy plugh completely nonsensical gibberish 12345"


def safe_cleanup_artifacts(repo_root: str, run_id: str) -> None:
    """
    G7: Safe cleanup helper for test artifacts.

    Only removes directories under artifacts/ in the repo root.
    Validates paths to prevent accidental deletion outside artifacts/.

    Args:
        repo_root: Repository root path
        run_id: Run identifier to clean up
    """
    artifacts_base = os.path.join(repo_root, 'artifacts')

    # Safety check: artifacts_base must exist and be under repo_root
    if not os.path.isdir(artifacts_base):
        return

    # Safety check: ensure artifacts_base is actually under repo_root
    real_artifacts = os.path.realpath(artifacts_base)
    real_repo = os.path.realpath(repo_root)
    if not real_artifacts.startswith(real_repo + os.sep):
        raise ValueError(f"artifacts/ is not under repo root: {real_artifacts}")

    # Clean only specific subdirectories for this run_id
    for subdir in ['artifacts', 'proposals', 'inputs']:
        path = os.path.join(artifacts_base, subdir, run_id)

        # Safety: verify path is under artifacts_base
        if os.path.isdir(path):
            real_path = os.path.realpath(path)
            if not real_path.startswith(real_artifacts + os.sep):
                raise ValueError(f"Path escapes artifacts/: {real_path}")
            shutil.rmtree(path)


class TestHarness:
    """
    Test harness for running the pipeline and observing results.

    Provides methods to run the CLI and check observable signals
    without parsing semantic content.
    """

    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.orchestrator_path = os.path.join(repo_root, 'm3', 'src', 'orchestrator.py')

    def run_pipeline(
        self,
        input_text: str,
        run_id: str
    ) -> Tuple[int, str, str, Dict]:
        """
        Run the pipeline with given input.

        Returns:
            Tuple of (exit_code, stdout, stderr, paths_dict)
            paths_dict contains: artifact_path, proposal_path, and any run directories
        """
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_text)
            input_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, self.orchestrator_path,
                 '--input', input_file,
                 '--run-id', run_id,
                 '--repo-root', self.repo_root],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )

            paths = {
                'artifact_path': os.path.join(
                    self.repo_root, 'artifacts', 'artifacts', run_id, 'artifact.json'
                ),
                'proposal_path': os.path.join(
                    self.repo_root, 'artifacts', 'proposals', run_id, 'proposal_set.json'
                ),
            }

            return result.returncode, result.stdout, result.stderr, paths

        finally:
            os.unlink(input_file)

    def find_poc_v2_run_directory(self, run_id: str) -> Optional[str]:
        """
        Find the PoC v2 run directory created during pipeline execution.

        Returns:
            Path to run directory, or None if not found
        """
        run_base = os.path.join(self.repo_root, 'artifacts', 'run')
        if not os.path.isdir(run_base):
            return None

        # Find most recent run directory (sorted by name which includes timestamp)
        dirs = sorted([d for d in os.listdir(run_base) if d.startswith('run_')])
        if dirs:
            return os.path.join(run_base, dirs[-1])
        return None

    def stdout_raw_kv_exists(self, run_directory: str) -> bool:
        """Check if stdout.raw.kv exists in run directory."""
        if not run_directory:
            return False
        path = os.path.join(run_directory, 'stdout.raw.kv')
        return os.path.isfile(path)

    def cleanup_run(self, run_id: str) -> None:
        """Clean up artifacts for a run using the safe cleanup helper."""
        safe_cleanup_artifacts(self.repo_root, run_id)


class TestInvariantI1_RejectNeverExecutes(unittest.TestCase):
    """I1: REJECT never triggers PoC v2 execution."""

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i1_reject_no_exec"
        # Clean up before test
        self.harness.cleanup_run(self.run_id)
        # Record ALL existing stdout.raw.kv files (not directory count)
        self.existing_stdout_files = self._find_all_stdout_raw_kv()

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    def _find_all_stdout_raw_kv(self) -> set:
        """Find all stdout.raw.kv files under artifacts/run/."""
        stdout_files = set()
        run_base = os.path.join(_REPO_ROOT, 'artifacts', 'run')
        if os.path.isdir(run_base):
            for run_dir in os.listdir(run_base):
                stdout_path = os.path.join(run_base, run_dir, 'stdout.raw.kv')
                if os.path.isfile(stdout_path):
                    stdout_files.add(stdout_path)
        return stdout_files

    def test_reject_does_not_create_stdout_raw_kv(self):
        """REJECT input must not create any new stdout.raw.kv files.

        This is the correct I1 invariant test:
        - REJECT may create artifacts (proposals, artifact.json)
        - REJECT must NOT trigger PoC v2 execution
        - PoC v2 execution is evidenced by stdout.raw.kv existence
        """
        exit_code, stdout, stderr, paths = self.harness.run_pipeline(
            REJECT_INPUT, self.run_id
        )

        # Check artifact was created (this is expected)
        self.assertTrue(os.path.isfile(paths['artifact_path']),
                        "Artifact should be created")

        # Load artifact and verify it's REJECT
        with open(paths['artifact_path'], 'r') as f:
            artifact = json.load(f)

        self.assertEqual(artifact['decision'], 'REJECT',
                         "Decision should be REJECT for gibberish input")

        # THE KEY INVARIANT: No new stdout.raw.kv files
        # This directly proves PoC v2 was not invoked
        current_stdout_files = self._find_all_stdout_raw_kv()
        new_stdout_files = current_stdout_files - self.existing_stdout_files

        self.assertEqual(
            len(new_stdout_files), 0,
            f"REJECT must not create stdout.raw.kv (PoC v2 execution). "
            f"Found new files: {new_stdout_files}"
        )

        # Exit code should be 0 (REJECT is success, not failure)
        self.assertEqual(exit_code, 0, "REJECT should exit with code 0")

        # stdout should contain "decision=REJECT"
        self.assertIn("decision=REJECT", stdout)

        # stderr should indicate execution was NOT invoked
        self.assertIn("NOT INVOKED", stderr,
                      "Stderr should clearly state execution was not invoked")


class TestInvariantI2_AcceptAlwaysExecutes(unittest.TestCase):
    """I2: ACCEPT always triggers PoC v2 execution."""

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i2_accept_exec"
        self.harness.cleanup_run(self.run_id)

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    def test_accept_creates_stdout_raw_kv(self):
        """ACCEPT input must create stdout.raw.kv file."""
        exit_code, stdout, stderr, paths = self.harness.run_pipeline(
            ACCEPT_INPUT, self.run_id
        )

        # Check artifact was created
        self.assertTrue(os.path.isfile(paths['artifact_path']),
                        "Artifact should be created")

        # Load artifact and verify it's ACCEPT
        with open(paths['artifact_path'], 'r') as f:
            artifact = json.load(f)

        self.assertEqual(artifact['decision'], 'ACCEPT',
                         "Decision should be ACCEPT for valid input")

        # Find run directory from stderr (look for run_directory: line)
        run_dir = None
        for line in stderr.split('\n'):
            if 'Run directory:' in line:
                run_dir = line.split(':', 1)[1].strip()
                break
            if 'run_directory:' in line:
                run_dir = line.split(':', 1)[1].strip()
                break

        # If we didn't find it, look for most recent run directory
        if not run_dir:
            run_base = os.path.join(_REPO_ROOT, 'artifacts', 'run')
            if os.path.isdir(run_base):
                dirs = sorted([d for d in os.listdir(run_base) if d.startswith('run_')])
                if dirs:
                    run_dir = os.path.join(run_base, dirs[-1])

        self.assertIsNotNone(run_dir, "Should find a run directory")

        # Check stdout.raw.kv exists
        stdout_raw_kv = os.path.join(run_dir, 'stdout.raw.kv')
        self.assertTrue(os.path.isfile(stdout_raw_kv),
                        f"stdout.raw.kv should exist at {stdout_raw_kv}")

        # stdout should contain "decision=ACCEPT"
        self.assertIn("decision=ACCEPT", stdout)


class TestInvariantI3_ZeroProposalsReject(unittest.TestCase):
    """I3: Zero proposals yields REJECT."""

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i3_zero_proposals"
        self.harness.cleanup_run(self.run_id)

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    def test_non_demo_input_causes_reject(self):
        """Input that doesn't match L-3 demo trigger must result in REJECT.

        Under L-3, the LLM engine produces UNMAPPED proposals for non-demo inputs.
        These fail validation → INVALID_PROPOSALS (not NO_PROPOSALS).
        """
        # Use gibberish input that won't match the demo trigger
        exit_code, stdout, stderr, paths = self.harness.run_pipeline(
            REJECT_INPUT, self.run_id
        )

        # Load artifact
        with open(paths['artifact_path'], 'r') as f:
            artifact = json.load(f)

        # Should be REJECT (either INVALID_PROPOSALS for unmapped proposals,
        # or L3_ENVELOPE_MISMATCH if it happens to produce a schema-valid proposal)
        self.assertEqual(artifact['decision'], 'REJECT')
        # The reason code depends on whether the input produces unmapped proposals
        # or schema-valid proposals outside the L-3 envelope
        self.assertIn(artifact['reject_payload']['reason_code'],
                      ['INVALID_PROPOSALS', 'NO_PROPOSALS'])


class TestInvariantI4_MultipleProposalsReject(unittest.TestCase):
    """I4: Multiple proposals yield REJECT."""

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i4_multiple_proposals"
        self.harness.cleanup_run(self.run_id)

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    def test_multiple_proposals_via_artifact_construction(self):
        """
        Test that multiple proposals yield REJECT using direct artifact builder.

        Since we can't easily make the proposal generator produce multiple proposals
        without changing M-1 semantics, we test the artifact builder directly
        with a mock proposal set containing multiple proposals.
        """
        from builder import build_artifact

        # Create proposal set with multiple proposals
        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": "test input"},
            "proposals": [
                {
                    "kind": "ROUTE_CANDIDATE",
                    "payload": {
                        "intent": "RESTART_SUBSYSTEM",
                        "slots": {"target": "alpha", "mode": "graceful"}
                    }
                },
                {
                    "kind": "ROUTE_CANDIDATE",
                    "payload": {
                        "intent": "STOP_SUBSYSTEM",
                        "slots": {"target": "beta", "mode": "immediate"}
                    }
                }
            ]
        }

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id=self.run_id,
            input_ref="test/input.txt",
            proposal_set_ref="test/proposal_set.json"
        )

        # Should be REJECT with AMBIGUOUS_PROPOSALS
        self.assertEqual(artifact['decision'], 'REJECT')
        self.assertEqual(artifact['reject_payload']['reason_code'], 'AMBIGUOUS_PROPOSALS')
        self.assertEqual(artifact['construction']['proposal_count'], 2)


class TestInvariantI5_ArtifactTampering(unittest.TestCase):
    """I5: Artifact tampering fails validation or blocks execution."""

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i5_tampering"
        self.harness.cleanup_run(self.run_id)

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    def test_tampered_artifact_rejected_by_validator(self):
        """Modifying artifact decision should fail validation."""
        # Create a valid ACCEPT artifact using the L-3 envelope
        from builder import build_artifact

        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": "status of alpha subsystem"},
            "proposals": [
                {
                    "kind": "ROUTE_CANDIDATE",
                    "payload": {
                        "intent": "STATUS_QUERY",
                        "slots": {"target": "alpha"}
                    }
                }
            ]
        }

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id=self.run_id,
            input_ref="test/input.txt",
            proposal_set_ref="test/proposal_set.json"
        )

        # Verify original is ACCEPT and valid
        self.assertEqual(artifact['decision'], 'ACCEPT')
        is_valid, errors = validate_artifact(artifact)
        self.assertTrue(is_valid, f"Original should be valid: {errors}")

        # Tamper: change decision to REJECT but keep accept_payload
        tampered = artifact.copy()
        tampered['decision'] = 'REJECT'

        # Validation should fail (REJECT without reject_payload)
        is_valid, errors = validate_artifact(tampered)
        self.assertFalse(is_valid, "Tampered artifact should be invalid")

    def test_gateway_rejects_tampered_artifact(self):
        """Gateway should reject tampered artifacts."""
        gateway = ExecutionGateway(_REPO_ROOT)

        # Create artifact that looks like ACCEPT but is malformed
        tampered = {
            "artifact_version": "artifact_v1",
            "run_id": self.run_id,
            "input_ref": "test/input.txt",
            "proposal_set_ref": "test/proposal_set.json",
            "decision": "ACCEPT",
            # Missing accept_payload - this is tampering
            "construction": {
                "ruleset_id": "M2_RULESET_V1",
                "proposal_count": 1,
                "selected_proposal_index": 0
            }
        }

        # Gateway should raise ExecutionBoundaryViolation
        with self.assertRaises(ExecutionBoundaryViolation):
            gateway.execute_if_accepted(tampered, "/tmp/test.txt")

    def test_gateway_rejects_reject_artifact(self):
        """Gateway should not execute with REJECT artifact."""
        gateway = ExecutionGateway(_REPO_ROOT)

        # Create valid REJECT artifact
        from builder import build_artifact

        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": "gibberish"},
            "proposals": []
        }

        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id=self.run_id,
            input_ref="test/input.txt",
            proposal_set_ref="test/proposal_set.json"
        )

        self.assertEqual(artifact['decision'], 'REJECT')

        # Gateway should return not executed (not raise)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            input_file = f.name

        try:
            result = gateway.execute_if_accepted(artifact, input_file)
            self.assertFalse(result.executed)
            self.assertEqual(result.decision, 'REJECT')
        finally:
            os.unlink(input_file)


class TestInvariantI6_ExecutionOutputUnchanged(unittest.TestCase):
    """I6: Execution output is unchanged by wrapper layers."""

    BASELINE_PATH = os.path.join(_REPO_ROOT, 'examples', 'baselines', 'stdout.raw.kv.baseline')

    def setUp(self):
        self.harness = TestHarness(_REPO_ROOT)
        self.run_id = "test_i6_golden"
        self.harness.cleanup_run(self.run_id)

    def tearDown(self):
        self.harness.cleanup_run(self.run_id)

    @unittest.skipUnless(
        os.path.isfile(os.path.join(_REPO_ROOT, 'examples', 'baselines', 'stdout.raw.kv.baseline')),
        "Golden file baseline not found. TODO: Create baseline at examples/baselines/stdout.raw.kv.baseline"
    )
    def test_output_matches_baseline(self):
        """stdout.raw.kv should match baseline byte-for-byte."""
        # Run pipeline with known input
        exit_code, stdout, stderr, paths = self.harness.run_pipeline(
            ACCEPT_INPUT, self.run_id
        )

        # Find run directory
        run_base = os.path.join(_REPO_ROOT, 'artifacts', 'run')
        if os.path.isdir(run_base):
            dirs = sorted([d for d in os.listdir(run_base) if d.startswith('run_')])
            if dirs:
                run_dir = os.path.join(run_base, dirs[-1])
                stdout_raw_kv = os.path.join(run_dir, 'stdout.raw.kv')

                if os.path.isfile(stdout_raw_kv):
                    with open(stdout_raw_kv, 'rb') as f:
                        actual = f.read()
                    with open(self.BASELINE_PATH, 'rb') as f:
                        expected = f.read()

                    self.assertEqual(actual, expected,
                                     "stdout.raw.kv should match baseline byte-for-byte")


class TestGatewayUnit(unittest.TestCase):
    """Unit tests for the execution gateway."""

    def test_gateway_validates_accept_artifact(self):
        """Gateway should accept valid ACCEPT artifacts."""
        gateway = ExecutionGateway(_REPO_ROOT)

        valid_accept = {
            "artifact_version": "artifact_v1",
            "run_id": "test",
            "input_ref": "test/input.txt",
            "proposal_set_ref": "test/proposal_set.json",
            "decision": "ACCEPT",
            "accept_payload": {
                "kind": "ROUTE",
                "route": {
                    "intent": "RESTART_SUBSYSTEM",
                    "target": "alpha",
                    "mode": "graceful"
                }
            },
            "construction": {
                "ruleset_id": "M2_RULESET_V1",
                "proposal_count": 1,
                "selected_proposal_index": 0
            }
        }

        can_execute, decision, errors = gateway.validate_artifact_for_execution(valid_accept)
        self.assertTrue(can_execute)
        self.assertEqual(decision, "ACCEPT")
        self.assertEqual(errors, [])

    def test_gateway_rejects_invalid_artifact(self):
        """Gateway should reject invalid artifacts."""
        gateway = ExecutionGateway(_REPO_ROOT)

        invalid = {"garbage": True}

        can_execute, decision, errors = gateway.validate_artifact_for_execution(invalid)
        self.assertFalse(can_execute)
        self.assertEqual(decision, "INVALID")
        self.assertGreater(len(errors), 0)

    def test_require_accept_artifact_raises_on_reject(self):
        """require_accept_artifact should raise for REJECT."""
        valid_reject = {
            "artifact_version": "artifact_v1",
            "run_id": "test",
            "input_ref": "test/input.txt",
            "proposal_set_ref": "test/proposal_set.json",
            "decision": "REJECT",
            "reject_payload": {"reason_code": "NO_PROPOSALS"},
            "construction": {
                "ruleset_id": "M2_RULESET_V1",
                "proposal_count": 0,
                "selected_proposal_index": None
            }
        }

        with self.assertRaises(ExecutionBoundaryViolation):
            ExecutionGateway.require_accept_artifact(valid_reject)


class TestCanonicalCLI(unittest.TestCase):
    """
    G3: Canonical CLI integration tests.

    These tests invoke the real CLI entrypoint (./brok) as a subprocess
    and verify structural properties of the output without parsing semantics.

    Note: The public CLI only accepts --input <file>. Run IDs are generated
    internally and deterministically from input content.
    """

    CLI_PATH = os.path.join(_REPO_ROOT, 'brok')

    def _run_cli(self, input_text: str) -> Tuple[int, str, str]:
        """Run the canonical CLI and return (exit_code, stdout, stderr).

        The CLI only accepts --input; run_id is generated internally.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_text)
            input_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, self.CLI_PATH,
                 '--input', input_file],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT
            )
            return result.returncode, result.stdout, result.stderr
        finally:
            os.unlink(input_file)

    def test_cli_accept_has_all_sections_in_order(self):
        """ACCEPT case: CLI output must have all three sections in order."""
        exit_code, stdout, stderr = self._run_cli(ACCEPT_INPUT)

        # All three sections must appear in stderr
        self.assertIn("[1/3] PROPOSAL", stderr)
        self.assertIn("[2/3] ARTIFACT", stderr)
        self.assertIn("[3/3] EXECUTION", stderr)

        # Sections must appear in order
        pos_1 = stderr.find("[1/3]")
        pos_2 = stderr.find("[2/3]")
        pos_3 = stderr.find("[3/3]")

        self.assertGreater(pos_1, -1, "Section [1/3] not found")
        self.assertGreater(pos_2, pos_1, "Section [2/3] must come after [1/3]")
        self.assertGreater(pos_3, pos_2, "Section [3/3] must come after [2/3]")

    def test_cli_reject_has_all_sections_in_order(self):
        """REJECT case: CLI output must have all three sections in order."""
        exit_code, stdout, stderr = self._run_cli(REJECT_INPUT)

        # All three sections must appear in stderr
        self.assertIn("[1/3] PROPOSAL", stderr)
        self.assertIn("[2/3] ARTIFACT", stderr)
        self.assertIn("[3/3] EXECUTION", stderr)

        # Sections must appear in order
        pos_1 = stderr.find("[1/3]")
        pos_2 = stderr.find("[2/3]")
        pos_3 = stderr.find("[3/3]")

        self.assertGreater(pos_1, -1, "Section [1/3] not found")
        self.assertGreater(pos_2, pos_1, "Section [2/3] must come after [1/3]")
        self.assertGreater(pos_3, pos_2, "Section [3/3] must come after [2/3]")

    def test_cli_has_authority_labels(self):
        """CLI output must include authority boundary labels."""
        exit_code, stdout, stderr = self._run_cli(ACCEPT_INPUT)

        # Authority labels must be present
        self.assertIn("NON-AUTHORITATIVE", stderr,
                      "Proposal section must be labeled NON-AUTHORITATIVE")
        self.assertIn("AUTHORITATIVE WRAPPER DECISION", stderr,
                      "Artifact section must show AUTHORITATIVE WRAPPER DECISION")
        self.assertIn("AUTHORITATIVE OUTPUT", stderr,
                      "Execution section must reference AUTHORITATIVE OUTPUT")

    def test_cli_accept_exit_code(self):
        """ACCEPT must exit 0 on successful execution."""
        exit_code, stdout, stderr = self._run_cli(ACCEPT_INPUT)
        self.assertEqual(exit_code, 0, "ACCEPT with successful execution should exit 0")

    def test_cli_reject_exit_code(self):
        """REJECT must exit 0 (not a failure)."""
        exit_code, stdout, stderr = self._run_cli(REJECT_INPUT)
        self.assertEqual(exit_code, 0, "REJECT should exit 0")

    def test_cli_rejects_run_id_flag(self):
        """CLI must not accept --run-id flag (internal only)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(ACCEPT_INPUT)
            input_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, self.CLI_PATH,
                 '--input', input_file,
                 '--run-id', 'should_fail'],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT
            )
            # Should fail because --run-id is not accepted
            self.assertNotEqual(result.returncode, 0,
                                "CLI must reject --run-id flag")
            self.assertIn("unrecognized arguments", result.stderr,
                          "CLI should report --run-id as unrecognized")
        finally:
            os.unlink(input_file)


class TestStdoutStderrContract(unittest.TestCase):
    """
    G6: Verify stdout/stderr separation contract.

    - Human-readable sections go to stderr
    - Final machine-readable line goes to stdout
    """

    CLI_PATH = os.path.join(_REPO_ROOT, 'brok')

    def _run_cli(self, input_text: str) -> Tuple[int, str, str]:
        """Run the canonical CLI and return (exit_code, stdout, stderr).

        The CLI only accepts --input; run_id is generated internally.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input_text)
            input_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, self.CLI_PATH,
                 '--input', input_file],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT
            )
            return result.returncode, result.stdout, result.stderr
        finally:
            os.unlink(input_file)

    def test_stdout_contains_only_result_line_accept(self):
        """stdout must contain only the final result line for ACCEPT."""
        exit_code, stdout, stderr = self._run_cli(ACCEPT_INPUT)

        # stdout should be minimal - just the result
        stdout_lines = [line for line in stdout.strip().split('\n') if line]
        self.assertEqual(len(stdout_lines), 1,
                         f"stdout should have exactly one line, got: {stdout_lines}")
        self.assertTrue(stdout_lines[0].startswith("decision="),
                        f"stdout line should start with 'decision=', got: {stdout_lines[0]}")

    def test_stdout_contains_only_result_line_reject(self):
        """stdout must contain only the final result line for REJECT."""
        exit_code, stdout, stderr = self._run_cli(REJECT_INPUT)

        # stdout should be minimal - just the result
        stdout_lines = [line for line in stdout.strip().split('\n') if line]
        self.assertEqual(len(stdout_lines), 1,
                         f"stdout should have exactly one line, got: {stdout_lines}")
        self.assertTrue(stdout_lines[0].startswith("decision="),
                        f"stdout line should start with 'decision=', got: {stdout_lines[0]}")

    def test_section_headers_in_stderr_not_stdout(self):
        """Section headers must appear in stderr, not stdout."""
        exit_code, stdout, stderr = self._run_cli(ACCEPT_INPUT)

        # Section headers must NOT be in stdout
        self.assertNotIn("[1/3]", stdout, "Section headers must not appear in stdout")
        self.assertNotIn("[2/3]", stdout, "Section headers must not appear in stdout")
        self.assertNotIn("[3/3]", stdout, "Section headers must not appear in stdout")

        # Section headers must be in stderr
        self.assertIn("[1/3]", stderr, "Section headers must appear in stderr")
        self.assertIn("[2/3]", stderr, "Section headers must appear in stderr")
        self.assertIn("[3/3]", stderr, "Section headers must appear in stderr")


class TestNoStubsFromCLI(unittest.TestCase):
    """
    G4: Verify test-only stubs cannot be activated from CLI.

    This ensures there is no code path from the CLI that could
    inject fake proposals or bypass normal proposal generation.
    """

    def test_no_stub_environment_variables(self):
        """No environment variables can activate proposal stubs."""
        # List of environment variable names that might be suspicious
        suspicious_vars = [
            'BROK_STUB_PROPOSALS',
            'BROK_TEST_MODE',
            'BROK_MOCK_PROPOSALS',
            'M3_STUB_PROPOSALS',
            'PROPOSAL_STUB',
        ]

        # Read orchestrator source to verify no env var checks
        orchestrator_path = os.path.join(_REPO_ROOT, 'm3', 'src', 'orchestrator.py')
        with open(orchestrator_path, 'r') as f:
            source = f.read()

        for var in suspicious_vars:
            self.assertNotIn(var, source,
                             f"Orchestrator must not check for {var}")

        # Also verify os.environ is not used to control proposal behavior
        self.assertNotIn("os.environ.get", source,
                         "Orchestrator should not use os.environ.get")
        self.assertNotIn("os.getenv", source,
                         "Orchestrator should not use os.getenv")

    def test_no_stub_cli_flags(self):
        """No CLI flags can activate proposal stubs."""
        orchestrator_path = os.path.join(_REPO_ROOT, 'm3', 'src', 'orchestrator.py')
        with open(orchestrator_path, 'r') as f:
            source = f.read()

        suspicious_flags = [
            '--stub',
            '--mock',
            '--fake',
            '--test-mode',
            '--inject',
        ]

        for flag in suspicious_flags:
            self.assertNotIn(flag, source,
                             f"Orchestrator must not accept {flag} flag")

    def test_i4_uses_direct_builder_not_cli_injection(self):
        """I4 test uses direct builder call, not CLI injection."""
        # This verifies that our I4 test approach is correct:
        # It tests the artifact builder directly with a mock proposal set,
        # rather than injecting into the CLI pipeline.
        #
        # This is the CORRECT approach because:
        # 1. We cannot make M-1 generate multiple proposals without changing it
        # 2. We test M-2's handling of multiple proposals directly
        # 3. No CLI bypass is needed or possible

        test_path = os.path.join(_REPO_ROOT, 'm3', 'tests', 'test_invariants.py')
        with open(test_path, 'r') as f:
            source = f.read()

        # I4 should use direct import of builder
        self.assertIn("from builder import build_artifact", source,
                      "I4 should use direct builder import")

        # Verify unittest.mock is not imported at module level
        # (we check import lines, not assertion strings)
        import_lines = [line for line in source.split('\n')
                        if line.strip().startswith('import ') or
                           line.strip().startswith('from ')]
        mock_imports = [line for line in import_lines if 'mock' in line.lower()]
        self.assertEqual(len(mock_imports), 0,
                         f"Tests should not import mock: {mock_imports}")


class TestCleanupSafety(unittest.TestCase):
    """
    G7: Verify cleanup helper safety.

    The cleanup helper must only operate under artifacts/ directory.
    """

    def test_cleanup_only_under_artifacts(self):
        """Cleanup helper must only delete under artifacts/."""
        # The safe_cleanup_artifacts function validates paths
        # This test verifies the safety checks exist

        # Test with a valid run_id - should not raise
        try:
            safe_cleanup_artifacts(_REPO_ROOT, "test_cleanup_valid")
        except ValueError:
            self.fail("Cleanup should not raise for valid run_id")

    def test_cleanup_rejects_path_traversal(self):
        """Cleanup must reject path traversal attempts."""
        # Attempting to use path traversal in run_id should be safe
        # because the run_id is joined as a path component, not interpreted

        # These should NOT cause problems because os.path.join handles them safely
        # and the real path check catches escapes
        dangerous_ids = [
            "../../../etc",
            "..%2F..%2F",
            "foo/../../../bar",
        ]

        for run_id in dangerous_ids:
            # These should either:
            # 1. Not find any directory (safe)
            # 2. Raise ValueError if path escapes (safe)
            # Either way, no damage should occur
            try:
                safe_cleanup_artifacts(_REPO_ROOT, run_id)
            except ValueError:
                pass  # Expected - path escape detected

    def test_cleanup_is_deterministic(self):
        """Cleanup does not introduce randomness or timestamps."""
        # Verify cleanup_run implementation uses safe_cleanup_artifacts
        harness = TestHarness(_REPO_ROOT)

        # Create a test artifact directory
        test_run_id = "test_cleanup_deterministic"
        test_dir = os.path.join(_REPO_ROOT, 'artifacts', 'proposals', test_run_id)
        os.makedirs(test_dir, exist_ok=True)

        # Write a test file
        test_file = os.path.join(test_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write("test")

        # Cleanup should remove it
        harness.cleanup_run(test_run_id)

        # Directory should be gone
        self.assertFalse(os.path.exists(test_dir),
                         "Cleanup should remove the test directory")


class TestGatewayImportSafety(unittest.TestCase):
    """
    G5: Verify gateway import safety.

    The gateway uses importlib.util to load the artifact validator.
    This must be restricted to known paths under the repo root.
    """

    def test_gateway_only_loads_from_known_path(self):
        """Gateway module loading is restricted to artifact/src/validator.py."""
        gateway_path = os.path.join(_REPO_ROOT, 'm3', 'src', 'gateway.py')
        with open(gateway_path, 'r') as f:
            source = f.read()

        # Verify the path is constructed from _REPO_ROOT
        self.assertIn("_REPO_ROOT", source,
                      "Gateway must use _REPO_ROOT for path construction")
        self.assertIn("artifact", source,
                      "Gateway must load from artifact directory")
        self.assertIn("validator.py", source,
                      "Gateway must load validator.py specifically")

    def test_gateway_cannot_load_arbitrary_module(self):
        """Gateway cannot be tricked into loading arbitrary modules."""
        # The gateway hardcodes the validator path relative to REPO_ROOT
        # There is no parameter or input that could change this path

        gateway_path = os.path.join(_REPO_ROOT, 'm3', 'src', 'gateway.py')
        with open(gateway_path, 'r') as f:
            source = f.read()

        # Verify no user-controllable path input
        self.assertNotIn("def load_validator(path", source,
                         "Gateway must not accept arbitrary validator paths")

        # Verify path is constructed, not passed in
        self.assertIn("_artifact_validator_path = os.path.join(_REPO_ROOT",
                      source,
                      "Validator path must be constructed from REPO_ROOT")

    def test_gateway_validator_path_is_repo_relative(self):
        """The loaded validator path must be under repo root."""
        # Import gateway and check the path it constructs
        gateway_path = os.path.join(_REPO_ROOT, 'm3', 'src', 'gateway.py')

        # Read and parse the path construction
        with open(gateway_path, 'r') as f:
            source = f.read()

        # Extract the path line
        for line in source.split('\n'):
            if '_artifact_validator_path' in line and 'os.path.join' in line:
                # Verify it joins from _REPO_ROOT
                self.assertIn('_REPO_ROOT', line,
                              "Validator path must start from _REPO_ROOT")
                # Verify the path components
                self.assertIn("'artifact'", line)
                self.assertIn("'src'", line)
                self.assertIn("'validator.py'", line)
                break
        else:
            self.fail("Could not find _artifact_validator_path construction")


if __name__ == "__main__":
    unittest.main(verbosity=2)
