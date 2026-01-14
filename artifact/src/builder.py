#!/usr/bin/env python3
"""
Phase M-2 Artifact Builder

Constructs authoritative wrapper-level decision records (Artifacts) from
non-authoritative ProposalSets (M-1 output).

Uses Python standard library only (no external dependencies).

Construction follows M2_RULESET_V1:
1. If ProposalSet is invalid: REJECT with INVALID_PROPOSALS
2. If ProposalSet has zero proposals: REJECT with NO_PROPOSALS
3. If ProposalSet has exactly one proposal: ACCEPT with route from proposal
4. If ProposalSet has 2+ proposals: REJECT with AMBIGUOUS_PROPOSALS

Guarantees:
- Deterministic: same input always produces byte-identical output
- Bounded: respects all schema bounds
- No timestamps, random values, or environment-dependent content
- Artifacts are decision records only; they do not override execution truth
"""

import json
import sys
import os
from typing import Dict, List, Tuple, Optional, Any

# Add proposal/src to path for validation reuse
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'proposal', 'src'))

from validator import validate_proposal_set

# Artifact schema constants
ARTIFACT_VERSION = "artifact_v1"
RULESET_ID = "M2_RULESET_V1"
MAX_PROPOSALS = 8
MAX_VALIDATOR_ERRORS = 16
MAX_NOTES = 8

# Valid enums (aligned with M-1)
VALID_INTENTS = frozenset(["RESTART_SUBSYSTEM", "STOP_SUBSYSTEM", "STATUS_QUERY"])
VALID_TARGETS = frozenset(["alpha", "beta", "gamma"])
VALID_MODES = frozenset(["graceful", "immediate"])


def build_artifact(
    proposal_set: Any,
    run_id: str,
    input_ref: str,
    proposal_set_ref: str
) -> Dict:
    """
    Build an Artifact from a ProposalSet following M2_RULESET_V1.

    Args:
        proposal_set: ProposalSet dict (may be invalid)
        run_id: User-provided run identifier
        input_ref: Repo-relative path to input file
        proposal_set_ref: Repo-relative path to proposal_set.json

    Returns:
        Artifact dict conforming to artifact_v1 schema

    Guarantees:
        - Deterministic: same inputs produce byte-identical output
        - Bounded: respects all schema bounds
        - No timestamps or environment-dependent values
    """
    # Step 1: Validate ProposalSet against M-1 schema
    is_valid, validation_errors = _validate_proposal_set_safe(proposal_set)

    if not is_valid:
        # REJECT with INVALID_PROPOSALS
        return _build_reject_artifact(
            run_id=run_id,
            input_ref=input_ref,
            proposal_set_ref=proposal_set_ref,
            reason_code="INVALID_PROPOSALS",
            proposal_count=_safe_proposal_count(proposal_set),
            validator_errors=validation_errors[:MAX_VALIDATOR_ERRORS]
        )

    proposals = proposal_set.get("proposals", [])
    proposal_count = len(proposals)

    # Step 2: Check for zero proposals
    if proposal_count == 0:
        return _build_reject_artifact(
            run_id=run_id,
            input_ref=input_ref,
            proposal_set_ref=proposal_set_ref,
            reason_code="NO_PROPOSALS",
            proposal_count=0,
            validator_errors=[]
        )

    # Step 3: Check for exactly one proposal
    if proposal_count == 1:
        proposal = proposals[0]
        route = _extract_route(proposal)
        return _build_accept_artifact(
            run_id=run_id,
            input_ref=input_ref,
            proposal_set_ref=proposal_set_ref,
            route=route,
            selected_proposal_index=0,
            proposal_count=1
        )

    # Step 4: Multiple proposals (2-8) -> REJECT with AMBIGUOUS_PROPOSALS
    return _build_reject_artifact(
        run_id=run_id,
        input_ref=input_ref,
        proposal_set_ref=proposal_set_ref,
        reason_code="AMBIGUOUS_PROPOSALS",
        proposal_count=proposal_count,
        validator_errors=[],
        notes=[f"PROPOSAL_COUNT:{proposal_count}"]
    )


def _validate_proposal_set_safe(proposal_set: Any) -> Tuple[bool, List[str]]:
    """
    Safely validate a ProposalSet, catching any exceptions.

    Returns:
        Tuple of (is_valid, error_codes)
    """
    try:
        if not isinstance(proposal_set, dict):
            return False, ["PROPOSAL_SET_NOT_OBJECT"]
        return validate_proposal_set(proposal_set)
    except Exception as e:
        # Catch any validation errors and return bounded error code
        error_type = type(e).__name__
        return False, [f"VALIDATION_EXCEPTION:{error_type}"]


def _safe_proposal_count(proposal_set: Any) -> int:
    """Safely extract proposal count from potentially invalid data."""
    try:
        if isinstance(proposal_set, dict):
            proposals = proposal_set.get("proposals")
            if isinstance(proposals, list):
                return min(len(proposals), MAX_PROPOSALS)
    except Exception:
        pass
    return 0


def _extract_route(proposal: Dict) -> Dict:
    """
    Extract route from a validated ROUTE_CANDIDATE proposal.

    Returns route dict with intent, target, and optionally mode.
    """
    payload = proposal["payload"]
    slots = payload["slots"]

    route = {
        "intent": payload["intent"],
        "target": slots["target"]
    }

    # Include mode if present
    if "mode" in slots:
        route["mode"] = slots["mode"]

    return route


def _build_accept_artifact(
    run_id: str,
    input_ref: str,
    proposal_set_ref: str,
    route: Dict,
    selected_proposal_index: int,
    proposal_count: int
) -> Dict:
    """Build an ACCEPT artifact."""
    return {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run_id,
        "input_ref": input_ref,
        "proposal_set_ref": proposal_set_ref,
        "decision": "ACCEPT",
        "accept_payload": {
            "kind": "ROUTE",
            "route": route
        },
        "construction": {
            "ruleset_id": RULESET_ID,
            "selected_proposal_index": selected_proposal_index,
            "proposal_count": proposal_count
        }
    }


def _build_reject_artifact(
    run_id: str,
    input_ref: str,
    proposal_set_ref: str,
    reason_code: str,
    proposal_count: int,
    validator_errors: List[str],
    notes: Optional[List[str]] = None
) -> Dict:
    """Build a REJECT artifact."""
    reject_payload = {
        "reason_code": reason_code
    }

    if notes:
        reject_payload["notes"] = notes[:MAX_NOTES]

    construction = {
        "ruleset_id": RULESET_ID,
        "selected_proposal_index": None,
        "proposal_count": proposal_count
    }

    if validator_errors:
        construction["validator_errors"] = validator_errors[:MAX_VALIDATOR_ERRORS]

    return {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run_id,
        "input_ref": input_ref,
        "proposal_set_ref": proposal_set_ref,
        "decision": "REJECT",
        "reject_payload": reject_payload,
        "construction": construction
    }


def artifact_to_json(artifact: Dict) -> str:
    """
    Serialize Artifact to deterministic JSON string.

    Uses sorted keys and consistent formatting for byte-for-byte reproducibility.
    """
    return json.dumps(artifact, sort_keys=True, indent=2)


def load_proposal_set(path: str) -> Tuple[Any, Optional[str]]:
    """
    Load a ProposalSet from a file path.

    Args:
        path: Path to proposal_set.json file

    Returns:
        Tuple of (proposal_set_data, error_message)
        If successful, error_message is None
        If failed, proposal_set_data is None
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, None
    except FileNotFoundError:
        return None, "FILE_NOT_FOUND"
    except json.JSONDecodeError as e:
        return None, f"JSON_DECODE_ERROR:{e.msg}"
    except Exception as e:
        return None, f"LOAD_ERROR:{type(e).__name__}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build artifact from proposal set")
    parser.add_argument("--proposal-set", required=True, help="Path to proposal_set.json")
    parser.add_argument("--run-id", required=True, help="Run identifier")
    parser.add_argument("--input-ref", required=True, help="Repo-relative path to input file")

    args = parser.parse_args()

    # Load proposal set
    proposal_set, load_error = load_proposal_set(args.proposal_set)

    if load_error:
        # Build artifact with load error
        artifact = _build_reject_artifact(
            run_id=args.run_id,
            input_ref=args.input_ref,
            proposal_set_ref=args.proposal_set,
            reason_code="INVALID_PROPOSALS",
            proposal_count=0,
            validator_errors=[load_error]
        )
    else:
        artifact = build_artifact(
            proposal_set=proposal_set,
            run_id=args.run_id,
            input_ref=args.input_ref,
            proposal_set_ref=args.proposal_set
        )

    print(artifact_to_json(artifact))
