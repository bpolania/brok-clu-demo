#!/usr/bin/env python3
"""
Phase M-2 Artifact Builder (with L-3 and L-4 Gates)

Constructs authoritative wrapper-level decision records (Artifacts) from
non-authoritative ProposalSets (M-1 output).

Uses Python standard library only (no external dependencies).

Construction follows M2_RULESET_V1 with L-3 and L-4 Gates:
1. If ProposalSet is invalid: REJECT with INVALID_PROPOSALS
2. If ProposalSet has zero proposals: REJECT with NO_PROPOSALS
3. If ProposalSet has exactly one proposal:
   a. If L4_ENABLED and proposal is STATE_TRANSITION_REQUEST:
      - Validate against frozen state machine
      - ACCEPT with STATE_TRANSITION payload if legal
      - REJECT with L4_* reason code if illegal
   b. If L3_ENVELOPE_ENABLED and proposal matches L-3 envelope: ACCEPT
   c. If L3_ENVELOPE_ENABLED and proposal does NOT match: REJECT (L3_ENVELOPE_MISMATCH)
   d. If not L3_ENVELOPE_ENABLED: ACCEPT (original M2 behavior)
4. If ProposalSet has 2+ proposals: REJECT with AMBIGUOUS_PROPOSALS

L-3 Envelope Gate:
The L-3 demo requires exactly ONE explicitly enumerated ACCEPT envelope.
Schema-valid alternatives (e.g., STATUS_QUERY on beta) are REJECTED.

L-4 State Machine Gate:
The L-4 demo validates state transitions against a frozen order processing
state machine. Event tokens are validated against the current state (fixed
to CREATED for L-4 demo). Only legal transitions ACCEPT.

Both gates are AUTHORITATIVE and do not depend on LLM engine behavior.

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

# =============================================================================
# Phase L-3: Single ACCEPT Envelope Gate (Authoritative)
# =============================================================================
# L-3 demonstrates exactly ONE explicitly enumerated ACCEPT envelope.
# All schema-valid alternatives outside this envelope are REJECTED.
#
# This gate is AUTHORITATIVE and runs in the artifact decision path.
# It is NOT dependent on LLM engine behavior.
#
# Single Envelope Definition:
#   - ProposalSet contains exactly 1 proposal
#   - kind == "ROUTE_CANDIDATE"
#   - payload.intent == "STATUS_QUERY"
#   - payload.slots == {"target": "alpha"} (no mode, no extra keys)
# =============================================================================

L3_ENVELOPE_ENABLED = True  # L-3 demo gate active

L3_ENVELOPE = {
    "kind": "ROUTE_CANDIDATE",
    "intent": "STATUS_QUERY",
    "slots": {"target": "alpha"}  # Exact match required, no extra keys
}


def _check_l3_envelope(proposal: Dict) -> bool:
    """
    Check if a proposal matches the L-3 single ACCEPT envelope exactly.

    This is an AUTHORITATIVE check in the artifact decision path.
    It ensures only the explicitly enumerated envelope can ACCEPT.

    Returns:
        True if proposal matches the L-3 envelope exactly.
        False otherwise (even if schema-valid).
    """
    if not isinstance(proposal, dict):
        return False

    # Check kind
    if proposal.get("kind") != L3_ENVELOPE["kind"]:
        return False

    # Check payload exists and is dict
    payload = proposal.get("payload")
    if not isinstance(payload, dict):
        return False

    # Check intent
    if payload.get("intent") != L3_ENVELOPE["intent"]:
        return False

    # Check slots exists and is dict
    slots = payload.get("slots")
    if not isinstance(slots, dict):
        return False

    # Check slots match EXACTLY (no extra keys like "mode")
    if slots != L3_ENVELOPE["slots"]:
        return False

    # Check no extra keys in payload (only intent and slots allowed)
    if set(payload.keys()) != {"intent", "slots"}:
        return False

    # Check no extra keys in proposal (only kind and payload allowed)
    if set(proposal.keys()) != {"kind", "payload"}:
        return False

    return True


# =============================================================================
# Phase L-4: State Machine Gate (Authoritative)
# =============================================================================
# L-4 validates state transitions against a frozen order processing state
# machine. The initial state is fixed to CREATED for the demo.
#
# This gate is AUTHORITATIVE and runs in the artifact decision path.
# It is NOT dependent on LLM engine behavior.
#
# L-4 Proposal Kind: "STATE_TRANSITION_REQUEST"
# Payload must contain: event_token (string from closed set)
#
# L-4 REJECT Reason Codes:
#   - INVALID_EVENT_TOKEN: event_token not in closed set
#   - ILLEGAL_TRANSITION: event_token recognized but not legal from current_state
#   - INVALID_CURRENT_STATE: totality guard (should not occur in normal flow)
# =============================================================================

L4_ENABLED = True  # L-4 demo gate active
L4_PROPOSAL_KIND = "STATE_TRANSITION_REQUEST"


def _check_l4_proposal(proposal: Dict) -> bool:
    """
    Check if a proposal is an L-4 STATE_TRANSITION_REQUEST.

    Returns:
        True if proposal has kind == "STATE_TRANSITION_REQUEST".
    """
    if not isinstance(proposal, dict):
        return False
    return proposal.get("kind") == L4_PROPOSAL_KIND


def _validate_l4_transition(proposal: Dict) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Validate an L-4 state transition proposal against the frozen state machine.

    This is an AUTHORITATIVE check in the artifact decision path.
    It determines whether the transition is legal from the fixed initial state.

    Args:
        proposal: The STATE_TRANSITION_REQUEST proposal

    Returns:
        Tuple of (is_valid, transition_payload, reject_reason_code)
        - If valid: (True, transition_payload_dict, None)
        - If invalid: (False, None, reason_code_string)
    """
    try:
        # Import L-4 state machine components
        _src_path = os.path.join(_REPO_ROOT, 'src')
        if _src_path not in sys.path:
            sys.path.insert(0, _src_path)

        from l4_state_machine.states import (
            OrderState,
            INITIAL_STATE,
            TERMINAL_STATES,
            DEMO_ORDER_ID,
        )
        from l4_state_machine.events import EventToken, VALID_EVENT_TOKENS
        from l4_state_machine.transitions import apply_transition

        # Extract event_token from proposal
        payload = proposal.get("payload")
        if not isinstance(payload, dict):
            return (False, None, "INVALID_EVENT_TOKEN")

        event_token_str = payload.get("event_token")
        if not isinstance(event_token_str, str):
            return (False, None, "INVALID_EVENT_TOKEN")

        # Validate event_token is in closed set
        try:
            event_token = EventToken(event_token_str)
        except ValueError:
            return (False, None, "INVALID_EVENT_TOKEN")

        # Apply transition from fixed initial state (CREATED)
        current_state = INITIAL_STATE
        result = apply_transition(current_state, event_token)

        if not result.valid:
            # Map error code to L-4 reject reason
            if result.error_code == "INVALID_EVENT_TOKEN":
                return (False, None, "INVALID_EVENT_TOKEN")
            elif result.error_code == "ILLEGAL_TRANSITION":
                return (False, None, "ILLEGAL_TRANSITION")
            elif result.error_code == "INVALID_CURRENT_STATE":
                return (False, None, "INVALID_CURRENT_STATE")
            else:
                return (False, None, "ILLEGAL_TRANSITION")

        # Build transition payload
        next_state = result.next_state
        is_terminal = next_state in TERMINAL_STATES

        transition_payload = {
            "order_id": DEMO_ORDER_ID,
            "previous_state": current_state.value,
            "event": event_token.value,
            "current_state": next_state.value,
            "terminal": is_terminal,
        }

        return (True, transition_payload, None)

    except ImportError:
        # L-4 module not available
        return (False, None, "INVALID_EVENT_TOKEN")
    except Exception:
        # Any other error
        return (False, None, "INVALID_EVENT_TOKEN")


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

        # L-4 State Machine Gate (Authoritative)
        # Check if this is an L-4 STATE_TRANSITION_REQUEST proposal
        if L4_ENABLED and _check_l4_proposal(proposal):
            is_valid, transition_payload, reject_reason = _validate_l4_transition(proposal)

            if is_valid:
                return _build_l4_accept_artifact(
                    run_id=run_id,
                    input_ref=input_ref,
                    proposal_set_ref=proposal_set_ref,
                    transition=transition_payload,
                    selected_proposal_index=0,
                    proposal_count=1
                )
            else:
                # L-4 transition not legal → REJECT with L-4 reason code
                return _build_reject_artifact(
                    run_id=run_id,
                    input_ref=input_ref,
                    proposal_set_ref=proposal_set_ref,
                    reason_code=reject_reason,
                    proposal_count=1,
                    validator_errors=[],
                    notes=[f"L4_REJECT:{reject_reason}"]
                )

        # L-3 Envelope Gate (Authoritative)
        # When enabled, only the explicitly enumerated envelope can ACCEPT.
        # Schema-valid alternatives outside the envelope are REJECTED.
        if L3_ENVELOPE_ENABLED:
            if not _check_l3_envelope(proposal):
                # Schema-valid but outside L-3 envelope → REJECT
                return _build_reject_artifact(
                    run_id=run_id,
                    input_ref=input_ref,
                    proposal_set_ref=proposal_set_ref,
                    reason_code="INVALID_PROPOSALS",
                    proposal_count=1,
                    validator_errors=[],
                    notes=["L3_ENVELOPE_MISMATCH"]
                )

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
    """Build an ACCEPT artifact for L-3 ROUTE."""
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


def _build_l4_accept_artifact(
    run_id: str,
    input_ref: str,
    proposal_set_ref: str,
    transition: Dict,
    selected_proposal_index: int,
    proposal_count: int
) -> Dict:
    """Build an ACCEPT artifact for L-4 STATE_TRANSITION."""
    return {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run_id,
        "input_ref": input_ref,
        "proposal_set_ref": proposal_set_ref,
        "decision": "ACCEPT",
        "accept_payload": {
            "kind": "STATE_TRANSITION",
            "transition": transition
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
