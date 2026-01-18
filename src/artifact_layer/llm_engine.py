"""
LLM Proposal Engine - Offline Nondeterministic Proposal Generation

This module implements an offline nondeterministic proposal engine that conforms to:
    acquire_proposal_set(raw_input_bytes: bytes) -> bytes

Phase L-2 Activation Stand-In:
This engine demonstrates LLM-style nondeterminism without requiring external
services, API keys, or network access. It uses OS randomness to produce
variable proposals across runs while maintaining the same contract.

Phase L-3 Extension - Controlled Acceptance Demonstration:
As a PROPOSAL GENERATOR CONVENIENCE, this engine produces the L-3 demo envelope
proposal when input matches the demo file. For all other inputs, it produces
unmapped proposals that fail validation.

IMPORTANT: This engine is NON-AUTHORITATIVE.

The AUTHORITATIVE L-3 acceptance gate is in artifact/src/builder.py:
- The L-3 envelope gate checks if the single proposal matches EXACTLY:
  - kind == "ROUTE_CANDIDATE"
  - payload.intent == "STATUS_QUERY"
  - payload.slots == {"target": "alpha"} (no mode, no extra keys)
- Schema-valid alternatives (e.g., STATUS_QUERY on beta) are REJECTED by the
  authoritative gate, NOT by this engine.
- Even if this engine emitted a schema-valid alternative proposal, the
  authoritative gate would REJECT it.

CRITICAL CONSTRAINTS:
- No runtime configuration (no env vars, no flags, no config files)
- No retries, no exponential delays, no multiple calls
- No external service dependencies
- This engine does NOT make authoritative decisions

The engine produces proposals with UNMAPPED values (outside closed domain)
for non-demo inputs:
- Intents: UNMAPPED_INTENT_* (not in valid set)
- Targets: unmapped_target_* (not in valid set)

These unmapped proposals fail validation → REJECT (INVALID_PROPOSALS).

Nondeterminism source: OS randomness via secrets module (cryptographically secure).
"""

import json
import secrets

# Schema version must match proposal layer
SCHEMA_VERSION = "m1.0"

# =============================================================================
# Phase L-3: Demo Envelope (Proposal Generator Convenience)
# =============================================================================
# Demo input file: inputs/l3_accept_demo.txt
# Content: "status alpha\n" (exactly 13 bytes)
# SHA256: 86347beb4d214b9a72e918e3a95c57b7bada3537e0eb9e1246f658aeefbc88ff
#
# This engine produces the L3_DEMO_ENVELOPE when input matches the demo file.
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

L3_CANONICAL_INPUT = b"status alpha\n"

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


def _is_demo_input(raw_input_bytes: bytes) -> bool:
    """
    Check if input bytes match the L-3 demo input.

    This is a PROPOSAL GENERATOR CONVENIENCE check, not an authoritative gate.
    It controls whether the engine emits a valid proposal (demo input) or
    an unmapped proposal (all other inputs).

    This is a byte-identical comparison. Any difference results in False.
    """
    return raw_input_bytes == L3_CANONICAL_INPUT


def llm_engine(raw_input_bytes: bytes) -> bytes:
    """
    Offline nondeterministic proposal engine (NON-AUTHORITATIVE).

    This engine demonstrates LLM-style nondeterminism without requiring
    external services. It uses OS randomness to produce variable proposals.

    Phase L-3 Demo Behavior:
    When input matches the L-3 demo file, the engine produces a valid proposal.
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
            # Non-UTF8 input: return empty proposal set → REJECT (NO_PROPOSALS)
            return _make_proposal_set_bytes("", [])

        # Empty input: return empty proposal set → REJECT (NO_PROPOSALS)
        if not input_text or input_text.isspace():
            return _make_proposal_set_bytes(input_text, [])

        # Phase L-3: Demo input check (PROPOSAL GENERATOR CONVENIENCE)
        # This controls which proposal the engine emits, not the decision
        if _is_demo_input(raw_input_bytes):
            # Produce a valid proposal for demo purposes
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
