#!/usr/bin/env python3
"""
Phase M-3: Execution Gateway

This module is the ONLY allowed gateway to PoC v2 execution.
It enforces the structural invariant: no execution without a validated ACCEPT artifact.

Authority model:
- Artifact layer (M-2) owns wrapper-level decision authority
- Execution layer (PoC v2) is frozen and produces stdout.raw.kv as authoritative output
- This gateway enforces the boundary: execution cannot proceed without ACCEPT

Usage:
    from m3.src.gateway import ExecutionGateway, ExecutionResult

    gateway = ExecutionGateway(repo_root="/path/to/repo")
    result = gateway.execute_if_accepted(artifact, input_file_path)

    if result.executed:
        print(f"Output at: {result.run_directory}")
    else:
        print(f"Blocked: {result.error}")

Guarantees:
- REJECT artifacts never trigger execution
- Invalid artifacts never trigger execution
- All boundary violations produce non-zero exit with clear error message
"""

import os
import sys
import json
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

# Setup paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))

# Import artifact validator explicitly to avoid module name collision with proposal/src/validator
import importlib.util
_artifact_validator_path = os.path.join(_REPO_ROOT, 'artifact', 'src', 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _artifact_validator_path)
_artifact_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_artifact_validator)
validate_artifact = _artifact_validator.validate_artifact


class ExecutionBoundaryViolation(Exception):
    """
    Raised when code attempts to bypass the artifact layer.

    This is a structural violation - execution was attempted without
    a valid ACCEPT artifact. This should never happen in correct usage.
    """
    pass


@dataclass
class ExecutionResult:
    """Result of an execution attempt through the gateway."""
    executed: bool
    decision: str  # "ACCEPT", "REJECT", or "INVALID"
    run_directory: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    validation_errors: Optional[List[str]] = None


class ExecutionGateway:
    """
    The sole gateway to PoC v2 execution.

    This class enforces the structural invariant that execution
    can only occur with a validated ACCEPT artifact.

    All code paths that invoke PoC v2 MUST go through this gateway.
    Direct invocation of run_poc_v2.sh outside this gateway is forbidden.
    """

    def __init__(self, repo_root: str):
        """
        Initialize the gateway.

        Args:
            repo_root: Absolute path to repository root
        """
        self.repo_root = repo_root
        self.poc_v2_script = os.path.join(repo_root, 'scripts', 'run_poc_v2.sh')

        if not os.path.isfile(self.poc_v2_script):
            raise FileNotFoundError(f"PoC v2 script not found: {self.poc_v2_script}")

    def validate_artifact_for_execution(self, artifact: Dict) -> Tuple[bool, str, List[str]]:
        """
        Validate that an artifact permits execution.

        Returns:
            Tuple of (can_execute, decision, validation_errors)
            - can_execute: True only if artifact is valid AND decision is ACCEPT
            - decision: "ACCEPT", "REJECT", or "INVALID"
            - validation_errors: List of validation errors (empty if valid)
        """
        # First, validate artifact structure
        is_valid, errors = validate_artifact(artifact)

        if not is_valid:
            return False, "INVALID", errors

        # Check decision
        decision = artifact.get("decision")

        if decision == "ACCEPT":
            return True, "ACCEPT", []
        elif decision == "REJECT":
            return False, "REJECT", []
        else:
            return False, "INVALID", [f"UNKNOWN_DECISION:{decision}"]

    def execute_if_accepted(
        self,
        artifact: Dict,
        input_file_path: str
    ) -> ExecutionResult:
        """
        Execute PoC v2 if and only if the artifact decision is ACCEPT.

        This is the ONLY method that should invoke PoC v2.

        Args:
            artifact: The artifact dict (must be validated ACCEPT)
            input_file_path: Path to the input file for PoC v2

        Returns:
            ExecutionResult with execution details

        Raises:
            ExecutionBoundaryViolation: If called with invalid artifact
                (indicates a programming error - boundary bypass attempt)
        """
        can_execute, decision, errors = self.validate_artifact_for_execution(artifact)

        if decision == "INVALID":
            # This is a structural violation - should not happen in correct code
            raise ExecutionBoundaryViolation(
                f"Attempted execution with invalid artifact. "
                f"Validation errors: {errors}"
            )

        if decision == "REJECT":
            # Normal path - artifact says don't execute
            return ExecutionResult(
                executed=False,
                decision="REJECT",
                error="Artifact decision is REJECT - execution not permitted"
            )

        # decision == "ACCEPT" - proceed with execution
        if not os.path.isfile(input_file_path):
            return ExecutionResult(
                executed=False,
                decision="ACCEPT",
                error=f"Input file not found: {input_file_path}"
            )

        # Invoke PoC v2
        try:
            result = subprocess.run(
                [self.poc_v2_script, '--input', input_file_path],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )

            # Parse run directory from output
            run_directory = self._parse_run_directory(result.stdout + result.stderr)

            return ExecutionResult(
                executed=True,
                decision="ACCEPT",
                run_directory=run_directory,
                exit_code=result.returncode
            )

        except Exception as e:
            return ExecutionResult(
                executed=False,
                decision="ACCEPT",
                error=f"Execution failed: {type(e).__name__}: {e}"
            )

    def _parse_run_directory(self, output: str) -> Optional[str]:
        """Extract run directory from PoC v2 output."""
        for line in output.split('\n'):
            if 'run_directory:' in line:
                parts = line.split('run_directory:', 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None

    @staticmethod
    def require_accept_artifact(artifact: Dict) -> None:
        """
        Guard function that raises if artifact is not a valid ACCEPT.

        Use this at any code boundary where execution would be invoked
        to ensure structural enforcement.

        Raises:
            ExecutionBoundaryViolation: If artifact is not valid ACCEPT
        """
        is_valid, errors = validate_artifact(artifact)

        if not is_valid:
            raise ExecutionBoundaryViolation(
                f"Execution guard failed: Invalid artifact. Errors: {errors}"
            )

        if artifact.get("decision") != "ACCEPT":
            raise ExecutionBoundaryViolation(
                f"Execution guard failed: Artifact decision is "
                f"'{artifact.get('decision')}', not 'ACCEPT'"
            )


def load_artifact_from_file(path: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Load an artifact from a JSON file.

    Args:
        path: Path to artifact.json

    Returns:
        Tuple of (artifact_dict, error_message)
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"Artifact file not found: {path}"
    except json.JSONDecodeError as e:
        return None, f"Artifact JSON decode error: {e.msg}"
    except Exception as e:
        return None, f"Artifact load error: {type(e).__name__}: {e}"


if __name__ == "__main__":
    # Simple test/demo
    import argparse

    parser = argparse.ArgumentParser(description="Execution gateway CLI")
    parser.add_argument("--artifact", required=True, help="Path to artifact.json")
    parser.add_argument("--input", required=True, help="Path to input file")
    parser.add_argument("--repo-root", default=_REPO_ROOT, help="Repository root")

    args = parser.parse_args()

    artifact, error = load_artifact_from_file(args.artifact)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    gateway = ExecutionGateway(args.repo_root)

    try:
        result = gateway.execute_if_accepted(artifact, args.input)

        if result.executed:
            print(f"EXECUTED: run_directory={result.run_directory} exit_code={result.exit_code}")
            sys.exit(result.exit_code or 0)
        else:
            print(f"NOT_EXECUTED: decision={result.decision} error={result.error}")
            sys.exit(0 if result.decision == "REJECT" else 1)

    except ExecutionBoundaryViolation as e:
        print(f"BOUNDARY_VIOLATION: {e}", file=sys.stderr)
        sys.exit(2)
