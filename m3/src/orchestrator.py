#!/usr/bin/env python3
"""
Phase M-3: Pipeline Orchestrator

Orchestrates the full pipeline with structured output and enforced boundaries:
1. PROPOSAL generation (M-1, non-authoritative)
2. ARTIFACT construction (M-2, authoritative wrapper decision)
3. EXECUTION gating (via gateway, frozen PoC v2)

This module uses the ExecutionGateway to enforce that execution
can only occur with a validated ACCEPT artifact.

Phase M-4 observability is integrated to provide deterministic traceability.

Usage:
    python3 -m m3.src.orchestrator --input <file> --run-id <id>
"""

import os
import sys
import json
import hashlib
import argparse
from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from m4.src.observability import PipelineObserver
    from artifact_layer.run_context import RunContext

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


def get_input_ref(
    input_file: str,
    repo_root: str
) -> str:
    """
    Get a reference string for the input file.

    If input is within repo, returns repo-relative path.
    If input is external, returns "[external]:<basename>" marker.

    This function does NOT copy files. It only computes the reference.

    Returns:
        Reference string for artifact input_ref field
    """
    input_abs = os.path.abspath(input_file)
    repo_root_abs = os.path.abspath(repo_root)

    if input_abs.startswith(repo_root_abs + os.sep):
        # Input is within repo - use relative path
        return os.path.relpath(input_abs, repo_root_abs).replace(os.sep, '/')
    else:
        # Input is outside repo - use marker (no copying)
        return f"[external]:{os.path.basename(input_file)}"


def run_proposal_generator(
    input_file: str,
    run_id: str,
    repo_root: str,
    run_ctx: "RunContext" = None
) -> Tuple[Optional[Dict], str, Optional[str]]:
    """
    Run the proposal generator via acquire_proposal_set seam.

    Args:
        input_file: Path to input file
        run_id: Run identifier
        repo_root: Repository root path
        run_ctx: Optional RunContext for enforcing single-call invariant

    Returns:
        Tuple of (proposal_set, proposal_set_path, error_message)
    """
    proposal_dir = os.path.join(repo_root, 'artifacts', 'proposals', run_id)
    os.makedirs(proposal_dir, exist_ok=True)
    proposal_set_path = os.path.join(proposal_dir, 'proposal_set.json')

    try:
        # Read input file as raw bytes
        with open(input_file, 'rb') as f:
            raw_input_bytes = f.read()

        # Call the seam (single call, no retries)
        # Import here to ensure path setup is complete
        src_path = os.path.join(repo_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from artifact_layer.seam_provider import acquire_proposal_set

        # Seam returns OpaqueProposalBytes - extract at artifact layer boundary
        opaque_result = acquire_proposal_set(raw_input_bytes, run_ctx)
        proposal_bytes = opaque_result.to_bytes()

        # Empty bytes -> create empty proposal set for REJECT path
        if not proposal_bytes:
            proposal_set = {
                "schema_version": "m1.0",
                "input": {"raw": ""},
                "proposals": []
            }
            proposal_json = json.dumps(proposal_set, sort_keys=True)
        else:
            # Artifact layer boundary: decode and parse opaque bytes here
            proposal_json = proposal_bytes.decode('utf-8')
            proposal_set = json.loads(proposal_json)

        # Write proposal set to disk
        with open(proposal_set_path, 'w', encoding='utf-8') as f:
            f.write(proposal_json)

        return proposal_set, proposal_set_path, None

    except Exception as e:
        # Any failure produces empty proposal set -> REJECT downstream
        proposal_set = {
            "schema_version": "m1.0",
            "input": {"raw": ""},
            "proposals": []
        }
        proposal_json = json.dumps(proposal_set, sort_keys=True)
        with open(proposal_set_path, 'w', encoding='utf-8') as f:
            f.write(proposal_json)
        return proposal_set, proposal_set_path, None


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


def _get_observer(repo_root: str) -> Optional["PipelineObserver"]:
    """
    Get M-4 observer if available.

    Returns None if M-4 module is not available (graceful degradation).
    """
    try:
        m4_src = os.path.join(repo_root, 'm4', 'src')
        if os.path.isdir(m4_src):
            sys.path.insert(0, m4_src)
            from observability import PipelineObserver
            return PipelineObserver(repo_root)
    except ImportError:
        pass
    return None


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
    # Initialize M-4 observability (optional, does not affect behavior)
    observer = _get_observer(repo_root)

    # Create run context for Seam S enforcement
    # Import here to ensure path setup is complete
    src_path = os.path.join(repo_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from artifact_layer.run_context import RunContext
    run_ctx = RunContext()

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

    # Get input reference for artifact (repo-relative or [external]:basename marker)
    # This does NOT copy files - observation without interference
    input_ref = get_input_ref(input_file, repo_root)

    # M-4: Record run start with the ORIGINAL input file path
    # Observer handles external paths by recording "[external]:<basename>" marker
    if observer:
        observer.start_run(input_file)

    # === Stage 1: Proposal Generation ===
    proposal_set, proposal_set_path, error = run_proposal_generator(
        input_file, run_id, repo_root, run_ctx
    )

    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Make proposal_set_ref repo-relative
    proposal_set_ref = os.path.relpath(proposal_set_path, repo_root)

    # M-4: Record proposal generation
    proposal_count = len(proposal_set.get("proposals", [])) if proposal_set else 0
    if observer:
        observer.record_proposal(proposal_set_path, proposal_count)

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

    # M-4: Record artifact construction
    decision = artifact.get("decision")
    if observer:
        observer.record_artifact(artifact_path, decision)

    if verbose:
        format_artifact_section(artifact, artifact_ref)

    # === Stage 3: Execution (via Gateway) ===
    reject_payload = artifact.get("reject_payload", {})
    reason_code = reject_payload.get("reason_code")

    # M-4: Record gate decision
    if observer:
        observer.record_gate_decision(decision, reason_code)

    gateway = ExecutionGateway(repo_root)

    try:
        result = gateway.execute_if_accepted(artifact, input_file)

        # M-4: Record execution outcome
        if observer:
            if result.executed:
                observer.record_execution_start()
                observer.record_execution_complete(
                    result.run_directory,
                    result.exit_code or 0
                )
            else:
                observer.record_execution_skip(
                    f"decision={decision}" if decision == "REJECT" else "execution_failed"
                )

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

        # M-4: Finalize and print summary
        if observer:
            observer.finalize()
            if verbose:
                observer.print_summary()

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
