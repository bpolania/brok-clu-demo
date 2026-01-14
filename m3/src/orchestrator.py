#!/usr/bin/env python3
"""
Phase M-3: Pipeline Orchestrator

Orchestrates the full pipeline with structured output and enforced boundaries:
1. PROPOSAL generation (M-1, non-authoritative)
2. ARTIFACT construction (M-2, authoritative wrapper decision)
3. EXECUTION gating (via gateway, frozen PoC v2)

This module uses the ExecutionGateway to enforce that execution
can only occur with a validated ACCEPT artifact.

Usage:
    python3 -m m3.src.orchestrator --input <file> --run-id <id>
"""

import os
import sys
import json
import subprocess
import hashlib
import argparse
from typing import Dict, Optional, Tuple

# Setup paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))

# Add proposal/src FIRST so builder can import from proposal validator
sys.path.insert(0, os.path.join(_REPO_ROOT, 'proposal', 'src'))
# Add artifact/src for builder
sys.path.insert(0, os.path.join(_REPO_ROOT, 'artifact', 'src'))
# Add m3/src for local imports
sys.path.insert(0, _SCRIPT_DIR)

# Import from local m3/src modules
from gateway import ExecutionGateway, ExecutionBoundaryViolation, load_artifact_from_file
from cli_output import (
    format_proposal_section,
    format_artifact_section,
    format_execution_section,
    format_final_result,
    print_pipeline_header,
    print_pipeline_footer
)

# Import artifact validator explicitly to avoid module shadowing
import importlib.util
_artifact_validator_path = os.path.join(_REPO_ROOT, 'artifact', 'src', 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _artifact_validator_path)
_artifact_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_artifact_validator)
validate_artifact = _artifact_validator.validate_artifact

# Import builder (which depends on proposal/src being in path first)
from builder import build_artifact, artifact_to_json, load_proposal_set


# Run-ID generation salt (deterministic, not machine-specific)
RUN_ID_SALT = "M3_RUN_ID_V1"


def generate_deterministic_run_id(input_bytes: bytes, prefix: str = "run") -> str:
    """
    Generate a deterministic run ID from input bytes.

    The run ID is derived from a hash of the input content, ensuring:
    - Same input always produces same run ID
    - No timestamps or machine identifiers
    - Safe characters only

    Args:
        input_bytes: Raw input file content
        prefix: Optional prefix for the run ID

    Returns:
        Run ID string like "run_a1b2c3d4e5f6" (prefix + 12 hex chars)
    """
    hasher = hashlib.sha256()
    hasher.update(RUN_ID_SALT.encode('utf-8'))
    hasher.update(input_bytes)
    digest = hasher.hexdigest()[:12]
    return f"{prefix}_{digest}"


def validate_run_id(run_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate run ID format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not run_id:
        return False, "Run ID cannot be empty"
    if len(run_id) > 64:
        return False, "Run ID exceeds maximum length of 64 characters"
    import re
    if not re.match(r'^[A-Za-z0-9._-]+$', run_id):
        return False, "Run ID contains invalid characters. Allowed: A-Za-z0-9._-"
    return True, None


def ensure_input_in_artifacts(
    input_file: str,
    run_id: str,
    repo_root: str
) -> str:
    """
    Ensure input file is referenced from within artifacts/.

    If input is outside repo, copy to artifacts/inputs/<run-id>/input.raw.

    Returns:
        Repo-relative path to input
    """
    input_abs = os.path.abspath(input_file)

    if input_abs.startswith(repo_root + os.sep):
        # Input is within repo - use relative path
        return os.path.relpath(input_abs, repo_root)
    else:
        # Input is outside repo - copy to artifacts
        artifact_input_dir = os.path.join(repo_root, 'artifacts', 'inputs', run_id)
        os.makedirs(artifact_input_dir, exist_ok=True)
        dest_path = os.path.join(artifact_input_dir, 'input.raw')

        with open(input_file, 'rb') as src:
            content = src.read()
        with open(dest_path, 'wb') as dst:
            dst.write(content)

        return f"artifacts/inputs/{run_id}/input.raw"


def run_proposal_generator(
    input_file: str,
    run_id: str,
    repo_root: str
) -> Tuple[Optional[Dict], str, Optional[str]]:
    """
    Run the proposal generator (M-1).

    Returns:
        Tuple of (proposal_set, proposal_set_path, error_message)
    """
    proposal_dir = os.path.join(repo_root, 'artifacts', 'proposals', run_id)
    os.makedirs(proposal_dir, exist_ok=True)

    generator_script = os.path.join(repo_root, 'scripts', 'generate_proposals.sh')

    try:
        result = subprocess.run(
            [generator_script, '--input', input_file, '--run-id', run_id],
            capture_output=True,
            text=True,
            cwd=repo_root
        )

        proposal_set_path = os.path.join(proposal_dir, 'proposal_set.json')

        if not os.path.isfile(proposal_set_path):
            return None, proposal_set_path, "Proposal generation failed - no proposal_set.json"

        proposal_set, load_error = load_proposal_set(proposal_set_path)
        if load_error:
            return None, proposal_set_path, f"Failed to load proposals: {load_error}"

        return proposal_set, proposal_set_path, None

    except Exception as e:
        return None, "", f"Proposal generation error: {type(e).__name__}: {e}"


def build_and_save_artifact(
    proposal_set: Dict,
    run_id: str,
    input_ref: str,
    proposal_set_ref: str,
    repo_root: str
) -> Tuple[Optional[Dict], str, Optional[str]]:
    """
    Build artifact and save to disk.

    Returns:
        Tuple of (artifact, artifact_path, error_message)
    """
    artifact_dir = os.path.join(repo_root, 'artifacts', 'artifacts', run_id)
    os.makedirs(artifact_dir, exist_ok=True)
    artifact_path = os.path.join(artifact_dir, 'artifact.json')

    try:
        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id=run_id,
            input_ref=input_ref,
            proposal_set_ref=proposal_set_ref
        )

        # Save artifact
        artifact_json = artifact_to_json(artifact)
        with open(artifact_path, 'w', encoding='utf-8') as f:
            f.write(artifact_json)

        # Save hash
        hash_path = artifact_path + '.sha256'
        artifact_hash = hashlib.sha256(artifact_json.encode('utf-8')).hexdigest()
        with open(hash_path, 'w', encoding='utf-8') as f:
            f.write(artifact_hash)

        return artifact, artifact_path, None

    except Exception as e:
        return None, artifact_path, f"Artifact build error: {type(e).__name__}: {e}"


def run_pipeline(
    input_file: str,
    run_id: str,
    repo_root: str,
    verbose: bool = True
) -> int:
    """
    Run the full pipeline with structured output.

    Args:
        input_file: Path to input file
        run_id: Run identifier
        repo_root: Repository root path
        verbose: Whether to print verbose output

    Returns:
        Exit code (0 for success, non-zero for operational failure)
    """
    # Print header
    if verbose:
        print_pipeline_header()

    # Validate run ID
    valid, error = validate_run_id(run_id)
    if not valid:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Validate input file exists
    if not os.path.isfile(input_file):
        print(f"ERROR: Input file not found: {input_file}", file=sys.stderr)
        return 1

    # Ensure input is repo-relative
    input_ref = ensure_input_in_artifacts(input_file, run_id, repo_root)

    # === Stage 1: Proposal Generation ===
    proposal_set, proposal_set_path, error = run_proposal_generator(
        input_file, run_id, repo_root
    )

    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Make proposal_set_ref repo-relative
    proposal_set_ref = os.path.relpath(proposal_set_path, repo_root)

    if verbose:
        format_proposal_section(proposal_set, proposal_set_ref)

    # === Stage 2: Artifact Construction ===
    artifact, artifact_path, error = build_and_save_artifact(
        proposal_set, run_id, input_ref, proposal_set_ref, repo_root
    )

    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    artifact_ref = os.path.relpath(artifact_path, repo_root)

    if verbose:
        format_artifact_section(artifact, artifact_ref)

    # === Stage 3: Execution (via Gateway) ===
    decision = artifact.get("decision")
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")

    gateway = ExecutionGateway(repo_root)

    try:
        result = gateway.execute_if_accepted(artifact, input_file)

        if verbose:
            format_execution_section(
                decision=decision,
                executed=result.executed,
                run_directory=result.run_directory,
                exit_code=result.exit_code,
                error=result.error
            )

        # Print final result to stdout
        format_final_result(
            decision=decision,
            executed=result.executed,
            reason_code=reason_code
        )

        if verbose:
            print_pipeline_footer()

        # Return appropriate exit code
        if decision == "REJECT":
            return 0  # REJECT is not a failure
        elif result.executed:
            return result.exit_code or 0
        else:
            return 1  # ACCEPT but failed to execute is a failure

    except ExecutionBoundaryViolation as e:
        print(f"BOUNDARY VIOLATION: {e}", file=sys.stderr)
        return 2


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Brok-CLU Pipeline Orchestrator (Phase M-3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Authority model:
  - Proposals are DERIVED and NON-AUTHORITATIVE
  - Artifacts hold WRAPPER-LEVEL DECISION AUTHORITY
  - stdout.raw.kv is the ONLY AUTHORITATIVE EXECUTION OUTPUT

Exit codes:
  0  Success (including REJECT decisions)
  1  Operational failure (missing files, IO errors)
  2  Boundary violation (structural error)
"""
    )
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--run-id", help="Run identifier (auto-generated if not provided)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--repo-root", default=_REPO_ROOT, help="Repository root")

    args = parser.parse_args()

    # Auto-generate run ID if not provided
    if args.run_id:
        run_id = args.run_id
    else:
        with open(args.input, 'rb') as f:
            input_bytes = f.read()
        run_id = generate_deterministic_run_id(input_bytes)

    return run_pipeline(
        input_file=args.input,
        run_id=run_id,
        repo_root=args.repo_root,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    sys.exit(main())
