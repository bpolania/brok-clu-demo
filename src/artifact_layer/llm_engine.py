"""
LLM Proposal Engine - Offline Nondeterministic Proposal Generation

This module implements an offline nondeterministic proposal engine that conforms to:
    acquire_proposal_set(raw_input_bytes: bytes) -> bytes

Phase L-2 Activation Stand-In:
This engine demonstrates LLM-style nondeterminism without requiring external
services, API keys, or network access. It uses OS randomness to produce
variable proposals across runs while maintaining the same contract.

Phase L-3 Extension - Controlled Acceptance Demonstration:
This engine produces the L-3 demo envelope proposal when input matches the
canonical demo trigger. For all other inputs, it produces unmapped proposals
that fail validation.

Phase L-4 Extension - Stateful Workflow Demonstration:
This engine recognizes L-4 event tokens and produces STATE_TRANSITION_REQUEST
proposals. The artifact layer validates these against the frozen state machine.

IMPORTANT: This engine is NON-AUTHORITATIVE.

The AUTHORITATIVE gates are in artifact/src/builder.py:
- L-3 envelope gate: checks exact proposal structure for L-3 demo
- L-4 state machine gate: validates transitions against frozen state machine

This engine does NOT validate transition legality. It only maps inputs to
event tokens. The artifact layer is sole authority for ACCEPT/REJECT.

CRITICAL CONSTRAINTS:
- No runtime configuration (no env vars, no flags, no config files)
- No retries, no exponential delays, no multiple calls
- No external service dependencies
- This engine does NOT make authoritative decisions

The engine produces proposals with UNMAPPED values (outside closed domain)
for non-demo inputs:
- Intents: UNMAPPED_INTENT_* (not in valid set)
- Targets: unmapped_target_* (not in valid set)

These unmapped proposals fail validation -> REJECT (INVALID_PROPOSALS).

Nondeterminism source: OS randomness via secrets module (cryptographically secure).
"""

import json
import os
import re
import secrets
import sys

# Add src to path for L-4 imports
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_SCRIPT_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Schema version must match proposal layer
SCHEMA_VERSION = "m1.0"

# =============================================================================
# Phase L-3: Demo Trigger Definition
# =============================================================================
# Canonical demo trigger: "status of alpha subsystem"
#
# Matching rules (case-insensitive, whitespace-tolerant):
# - Must contain "status" followed by "alpha" (with optional words between)
# - Specifically matches patterns like:
#   - "status of alpha subsystem"
#   - "status of alpha"
#   - "STATUS OF ALPHA SUBSYSTEM"
#   - "  status   of   alpha  " (extra whitespace)
#
# This engine produces the L3_DEMO_ENVELOPE when input matches the demo trigger.
# This is a PROPOSAL GENERATOR CONVENIENCE, not an authoritative gate.
#
# The AUTHORITATIVE L-3 envelope gate is in artifact/src/builder.py.
# It enforces that ONLY this exact envelope can ACCEPT:
#   - kind == "ROUTE_CANDIDATE"
#   - payload.intent == "STATUS_QUERY"
#   - payload.slots == {"target": "alpha"} exactly
#
# Schema-valid alternatives are REJECTED by the authoritative gate.
# =============================================================================

# Pattern for the demo trigger (case-insensitive, whitespace-tolerant)
# Matches: "status" + optional words + "alpha"
# Examples: "status of alpha subsystem", "status alpha", "STATUS OF ALPHA"
_DEMO_TRIGGER_PATTERN = re.compile(
    r'^\s*status\s+(?:of\s+)?alpha(?:\s+subsystem)?\s*$',
    re.IGNORECASE
)

L3_DEMO_ENVELOPE = {
    "kind": "ROUTE_CANDIDATE",
    "payload": {
        "intent": "STATUS_QUERY",
        "slots": {
            "target": "alpha"
        }
    }
}


def _generate_nonce() -> str:
    """Generate a random nonce for proposal variability."""
    return secrets.token_hex(4)


def _generate_unmapped_proposal() -> dict:
    """
    Generate a structurally valid but unmapped proposal.

    The proposal has correct structure but uses field values
    OUTSIDE the closed domain, guaranteeing validation failure
    and REJECT decision under frozen artifact rules.

    Variability comes from:
    - Random nonce in unmapped intent name
    - Random nonce in unmapped target name

    Returns proposal dict with unmapped values.
    """
    nonce = _generate_nonce()

    # Use values OUTSIDE the valid enums
    # Valid intents: RESTART_SUBSYSTEM, STOP_SUBSYSTEM, STATUS_QUERY
    # Valid targets: alpha, beta, gamma
    # By using "UNMAPPED_*" we guarantee validation failure
    unmapped_intent = f"UNMAPPED_INTENT_{nonce}"
    unmapped_target = f"unmapped_target_{nonce}"

    return {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": unmapped_intent,
            "slots": {
                "target": unmapped_target
            }
        }
    }


def _is_demo_trigger(input_text: str) -> bool:
    """
    Check if input text matches the L-3 demo trigger.

    This is a PROPOSAL GENERATOR CONVENIENCE check, not an authoritative gate.
    It controls whether the engine emits a valid proposal (demo trigger) or
    an unmapped proposal (all other inputs).

    The demo trigger is "status of alpha subsystem" (case-insensitive,
    whitespace-tolerant). Close alternatives like "status of beta" do NOT match.

    Args:
        input_text: Decoded UTF-8 input string

    Returns:
        True if input matches the demo trigger pattern.
        False otherwise.
    """
    return bool(_DEMO_TRIGGER_PATTERN.match(input_text))


def llm_engine(raw_input_bytes: bytes) -> bytes:
    """
    Offline nondeterministic proposal engine (NON-AUTHORITATIVE).

    This engine demonstrates LLM-style nondeterminism without requiring
    external services. It uses OS randomness to produce variable proposals.

    Phase L-3 Demo Behavior:
    When input matches the demo trigger ("status of alpha subsystem"),
    the engine produces a valid L-3 envelope proposal.
    For all other inputs, it produces unmapped proposals that fail validation.

    IMPORTANT: This engine is NON-AUTHORITATIVE. The authoritative decision
    is made by the artifact builder based on ProposalSet structure alone.

    Args:
        raw_input_bytes: Raw bytes from user input file

    Returns:
        ProposalSet as JSON bytes.
        On ANY failure, returns empty bytes b"".

    Guarantees:
        - Single interpretation pass, no retries
        - All exceptions collapse to empty bytes
        - Output conforms to ProposalSet schema structure
        - No external service calls
        - No runtime configuration required
        - Does NOT make authoritative decisions
    """
    try:
        # Decode input
        try:
            input_text = raw_input_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Non-UTF8 input: return empty proposal set -> REJECT (NO_PROPOSALS)
            return _make_proposal_set_bytes("", [])

        # Empty input: return empty proposal set -> REJECT (NO_PROPOSALS)
        if not input_text or input_text.isspace():
            return _make_proposal_set_bytes(input_text, [])

        # Phase L-4: Check for L-4 event trigger first
        # L-4 inputs are mapped to STATE_TRANSITION_REQUEST proposals
        try:
            from l4_state_machine.proposal_mapper import (
                is_l4_input,
                map_input_to_event_token,
                create_l4_proposal
            )
            if is_l4_input(input_text):
                event_token = map_input_to_event_token(input_text)
                if event_token is not None:
                    proposal = create_l4_proposal(event_token)
                    return _make_proposal_set_bytes(input_text, [proposal])
        except ImportError:
            # L-4 module not available - fall through to L-3/unmapped
            pass

        # Phase L-3: Demo trigger check (PROPOSAL GENERATOR CONVENIENCE)
        # This controls which proposal the engine emits, not the decision
        if _is_demo_trigger(input_text):
            # Produce the L-3 envelope proposal for demo purposes
            return _make_proposal_set_bytes(input_text, [L3_DEMO_ENVELOPE])

        # All other inputs: generate unmapped proposal (nondeterministic via nonce)
        # The proposal has valid structure but unmapped field values
        # This guarantees REJECT (INVALID_PROPOSALS) under frozen rules
        proposal = _generate_unmapped_proposal()

        return _make_proposal_set_bytes(input_text, [proposal])

    except Exception:
        # All failures collapse to empty bytes
        # This ensures REJECT-safe behavior downstream
        return b""


def _make_proposal_set_bytes(input_raw: str, proposals: list) -> bytes:
    """Create ProposalSet JSON bytes."""
    proposal_set = {
        "schema_version": SCHEMA_VERSION,
        "input": {"raw": input_raw},
        "proposals": proposals
    }
    # Deterministic JSON serialization
    return json.dumps(proposal_set, sort_keys=True, separators=(',', ':')).encode('utf-8')
