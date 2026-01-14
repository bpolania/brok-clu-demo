#!/usr/bin/env python3
"""
Phase M-4: Pipeline Observability

Integrates manifest and trace writing with the pipeline.
Provides a clean interface for recording observability data
without affecting pipeline behavior.

All outputs are DERIVED and non-authoritative.
"""

import os
import sys
from typing import Optional

from utils import sha256_file, to_rel_path, PathSafetyError
from manifest import ManifestBuilder
from trace import TraceWriter


class PipelineObserver:
    """
    Observes and records pipeline execution.

    This class wraps ManifestBuilder and TraceWriter to provide
    a unified interface for recording observability data.

    All methods are observational - they do not affect pipeline behavior.
    """

    def __init__(self, repo_root: str):
        """
        Initialize pipeline observer.

        Args:
            repo_root: Absolute path to repository root
        """
        self.repo_root = os.path.abspath(repo_root)
        self.manifest = ManifestBuilder(repo_root)
        self.trace = TraceWriter(repo_root)
        self._run_id: Optional[str] = None
        self._output_dir: Optional[str] = None

    def start_run(self, input_path: str) -> None:
        """
        Record run start.

        Args:
            input_path: Path to input file (may be external to repo)

        Note: This method does NOT copy or modify the input file.
        For external inputs, it records "[external]:<basename>" as the path
        but still hashes the actual file content.
        """
        # Always hash the actual input file (observation only)
        input_sha = sha256_file(input_path)

        # Record input - manifest handles external paths with marker
        self.manifest.set_input(input_path)
        self.trace.run_start(input_path, input_sha)

    def record_proposal(
        self,
        proposal_path: str,
        proposal_count: int
    ) -> None:
        """
        Record proposal generation.

        Args:
            proposal_path: Path to proposal_set.json
            proposal_count: Number of proposals generated
        """
        if os.path.isfile(proposal_path):
            self.manifest.add_artifact(proposal_path, "proposal_set", authoritative=False)

        status = "OK" if proposal_count > 0 else "SKIP"
        outputs = [proposal_path] if os.path.isfile(proposal_path) else []
        self.manifest.add_stage("PROPOSAL", status, outputs)

        self.trace.proposal_generated(proposal_path, proposal_count)

    def record_artifact(self, artifact_path: str, decision: str) -> None:
        """
        Record artifact construction.

        Args:
            artifact_path: Path to artifact.json
            decision: Artifact decision (ACCEPT/REJECT)
        """
        if os.path.isfile(artifact_path):
            self.manifest.add_artifact(artifact_path, "artifact", authoritative=False)

        self.manifest.add_stage("ARTIFACT", "OK", [artifact_path])
        self.trace.artifact_written(artifact_path, decision)

    def record_gate_decision(self, decision: str, reason_code: Optional[str] = None) -> None:
        """
        Record execution gate decision.

        Args:
            decision: Gate decision (ACCEPT/REJECT)
            reason_code: Reason code if REJECT
        """
        self.trace.gate_decision(decision, reason_code)

    def record_execution_start(self) -> None:
        """Record that execution is starting."""
        self.trace.execution_started()

    def record_execution_skip(self, reason: str) -> None:
        """
        Record that execution was skipped.

        Args:
            reason: Reason for skipping (should be a stable token, not freeform)
        """
        self.manifest.record_execution(executed=False)
        self.manifest.add_stage("EXECUTION", "SKIP")
        self.trace.execution_skipped(reason)

    def record_execution_complete(
        self,
        run_directory: Optional[str],
        exit_code: int
    ) -> None:
        """
        Record execution completion.

        Args:
            run_directory: Path to PoC v2 run directory (may contain timestamps)
            exit_code: Exit code from execution

        Note: We do NOT record the run_directory path as it contains timestamps.
        We only record the hash of stdout.raw.kv (authoritative output).
        """
        self.manifest.record_execution(executed=True)
        status = "OK" if exit_code == 0 else "FAIL"
        stdout_path = None

        if run_directory:
            stdout_path = os.path.join(run_directory, "stdout.raw.kv")
            if os.path.isfile(stdout_path):
                # Record stdout.raw.kv with hash only (omit timestamped path)
                self.manifest.add_artifact(
                    stdout_path,
                    "stdout.raw.kv",
                    authoritative=True,
                    omit_path=True
                )

        # Don't record outputs with timestamped paths
        self.manifest.add_stage("EXECUTION", status, omit_outputs=True)
        self.trace.execution_complete(stdout_path, exit_code)

    def finalize(self) -> str:
        """
        Finalize observability data and write to disk.

        Returns:
            Run ID for this execution
        """
        self._run_id = self.manifest.get_run_id()
        self._output_dir = os.path.join(
            self.repo_root, 'artifacts', 'run', self._run_id
        )

        # Record completion
        self.trace.run_complete(self._run_id)

        # Write manifest and trace
        self.manifest.write(self._output_dir)
        self.trace.write(self._output_dir)

        return self._run_id

    def print_summary(self, output=sys.stderr) -> None:
        """
        Print a human-readable observability summary to stderr.

        Args:
            output: Output stream (default stderr)
        """
        if not self._run_id:
            return

        rel_output_dir = to_rel_path(self.repo_root, self._output_dir)

        print("\n" + "=" * 72, file=output)
        print("[DERIVED] M-4 Observability Summary", file=output)
        print("=" * 72, file=output)
        print(f"  Run ID: {self._run_id}", file=output)
        print(f"  Manifest: {rel_output_dir}/manifest.json", file=output)
        print(f"  Trace: {rel_output_dir}/trace.jsonl", file=output)
        print("", file=output)
        print("  NOTE: This summary is DERIVED and non-authoritative.", file=output)
        print("        Only stdout.raw.kv is authoritative for runtime truth.", file=output)
        print("=" * 72 + "\n", file=output)
