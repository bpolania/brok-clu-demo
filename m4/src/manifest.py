#!/usr/bin/env python3
"""
Phase M-4: Run Manifest Writer

Creates a deterministic manifest.json documenting:
- Input file reference and hash
- All artifacts produced (with hashes and relative paths)
- Stage execution status
- Authority boundary declarations

All outputs are DERIVED and non-authoritative.
The manifest is purely observational and does not affect behavior.
"""

import os
from typing import Any, Dict, List, Optional

from utils import (
    sha256_file,
    to_rel_path,
    stable_json_write,
    derive_run_id,
    validate_no_absolute_paths,
    validate_no_timestamps,
)


# Manifest schema version
MANIFEST_SCHEMA_VERSION = "m4.0"


class ManifestBuilder:
    """
    Builds a deterministic run manifest.

    The manifest records what happened during a pipeline run without
    interpreting semantics or affecting behavior.
    """

    def __init__(self, repo_root: str):
        """
        Initialize manifest builder.

        Args:
            repo_root: Absolute path to repository root
        """
        self.repo_root = os.path.abspath(repo_root)
        self._input_path_rel: Optional[str] = None
        self._input_sha256: Optional[str] = None
        self._artifacts: List[Dict[str, str]] = []
        self._stages: List[Dict[str, Any]] = []
        self._authoritative_outputs: List[str] = []
        self._derived_outputs: List[str] = []
        self._execution_recorded: bool = False
        self._executed: bool = False

    def set_input(self, input_path: str) -> None:
        """
        Record the input file.

        Args:
            input_path: Path to input file (may be external to repo)

        Note: For external inputs (outside repo), records "[external]:<basename>"
        as the path marker. Always hashes the actual file content.
        """
        # Use allow_external=True to get "[external]:<basename>" for external paths
        self._input_path_rel = to_rel_path(self.repo_root, input_path, allow_external=True)
        self._input_sha256 = sha256_file(input_path)

    def add_artifact(
        self,
        path: str,
        artifact_type: str,
        authoritative: bool = False,
        omit_path: bool = False
    ) -> None:
        """
        Record an artifact produced during the run.

        Args:
            path: Path to artifact file
            artifact_type: Type identifier (e.g., "proposal_set", "artifact", "stdout.raw.kv")
            authoritative: Whether this is an authoritative output
            omit_path: If True, record only the hash (for artifacts with non-deterministic paths)
        """
        if not os.path.isfile(path):
            return  # Skip non-existent artifacts

        sha = sha256_file(path)

        if omit_path:
            # For stdout.raw.kv: record only type and hash, no path
            # This avoids embedding timestamped M-3 run directory paths
            self._artifacts.append({
                "type": artifact_type,
                "sha256": sha
            })
            # W1 FIX: For authoritative path-omitted artifacts, use type as identifier
            # This ensures authority_boundary.authoritative_outputs correctly reflects
            # that stdout.raw.kv was produced even when we can't record its path
            if authoritative:
                self._authoritative_outputs.append(artifact_type)
        else:
            rel_path = to_rel_path(self.repo_root, path)
            self._artifacts.append({
                "type": artifact_type,
                "path": rel_path,
                "sha256": sha
            })

            if authoritative:
                self._authoritative_outputs.append(rel_path)
            else:
                self._derived_outputs.append(rel_path)

    def add_stage(
        self,
        name: str,
        status: str,
        outputs: Optional[List[str]] = None,
        omit_outputs: bool = False
    ) -> None:
        """
        Record a stage execution.

        Args:
            name: Stage name (e.g., "PROPOSAL", "ARTIFACT", "EXECUTION")
            status: Status code (OK, SKIP, FAIL)
            outputs: List of output paths (relative)
            omit_outputs: If True, don't record output paths (for non-deterministic paths)
        """
        stage_record = {
            "name": name,
            "status": status
        }
        if outputs and not omit_outputs:
            stage_record["outputs"] = [
                to_rel_path(self.repo_root, p) if os.path.isabs(p) else p
                for p in outputs
            ]
        self._stages.append(stage_record)

    def record_execution(self, executed: bool) -> None:
        """
        Record whether execution occurred.

        Args:
            executed: True if PoC v2 was invoked, False if skipped
        """
        self._execution_recorded = True
        self._executed = executed

    def get_run_id(self) -> str:
        """
        Get the deterministic run ID for this manifest.

        Returns:
            Run ID derived from input and artifact hashes
        """
        proposal_sha = None
        artifact_sha = None

        for art in self._artifacts:
            if art["type"] == "proposal_set":
                proposal_sha = art["sha256"]
            elif art["type"] == "artifact":
                artifact_sha = art["sha256"]

        return derive_run_id(
            self._input_sha256 or "",
            proposal_sha,
            artifact_sha
        )

    def build(self) -> Dict[str, Any]:
        """
        Build the manifest data structure.

        Returns:
            Manifest dict ready for serialization
        """
        run_id = self.get_run_id()

        # Sort artifacts by type (path may be missing for stdout.raw.kv)
        sorted_artifacts = sorted(
            self._artifacts,
            key=lambda x: (x["type"], x.get("path", ""))
        )

        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "run_id": run_id,
            "inputs": {
                "input_path_rel": self._input_path_rel,
                "input_sha256": self._input_sha256
            },
            "artifacts": sorted_artifacts,
            "stages": self._stages,  # Keep insertion order
            "authority_boundary": {
                "authoritative_outputs": sorted(self._authoritative_outputs),
                "derived_outputs": sorted(self._derived_outputs)
            },
            "determinism": {
                "no_timestamps": True,
                "no_absolute_paths": True
            }
        }

        # Add execution field if recorded
        if self._execution_recorded:
            manifest["execution"] = {"executed": self._executed}

        # Validate manifest before returning
        path_errors = validate_no_absolute_paths(manifest)
        if path_errors:
            raise ValueError(f"Manifest contains absolute paths: {path_errors}")

        timestamp_errors = validate_no_timestamps(manifest)
        if timestamp_errors:
            raise ValueError(f"Manifest contains timestamps: {timestamp_errors}")

        return manifest

    def write(self, output_dir: str) -> str:
        """
        Write manifest to file.

        Args:
            output_dir: Directory to write manifest.json

        Returns:
            Path to written manifest file
        """
        manifest = self.build()
        os.makedirs(output_dir, exist_ok=True)
        manifest_path = os.path.join(output_dir, "manifest.json")
        stable_json_write(manifest_path, manifest)
        return manifest_path
