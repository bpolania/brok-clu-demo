"""
LLM Proposal Engine - Offline Nondeterministic Proposal Generation

This module implements an offline nondeterministic proposal engine that conforms to:
    acquire_proposal_set(raw_input_bytes: bytes) -> bytes

Phase L-2 Activation Stand-In:
This engine demonstrates LLM-style nondeterminism without requiring external
services, API keys, or network access. It uses OS randomness to produce
variable proposals across runs while maintaining the same contract.

CRITICAL L-2 CONSTRAINT:
The engine produces "unmapped" proposals that are structurally valid but contain
field values OUTSIDE the closed domain. This guarantees REJECT under frozen
artifact rules (INVALID_PROPOSALS) while demonstrating proposal byte variability.

Constraints (Phase L-2 binding):
- Probabilistic output: same input may produce different proposals across runs
- Structurally non-authoritative: no downstream access, no decision influence
- REJECT-safe: any failure collapses to empty bytes
- REJECT-guaranteed: all outputs lead to REJECT (unmapped proposals)
- No retries, no exponential delays, no multiple calls
- No runtime configuration (no env vars, no flags, no config files)
- No external service dependencies

The engine produces proposals with UNMAPPED values (outside closed domain):
- Intents: UNMAPPED_INTENT_* (not in valid set)
- Targets: unmapped_target_* (not in valid set)

These unmapped proposals fail validation → REJECT (INVALID_PROPOSALS).

Nondeterminism source: OS randomness via secrets module (cryptographically secure).
"""

import json
import secrets

# Schema version must match proposal layer
SCHEMA_VERSION = "m1.0"


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


def llm_engine(raw_input_bytes: bytes) -> bytes:
    """
    Offline nondeterministic proposal engine.

    This engine demonstrates LLM-style nondeterminism without requiring
    external services. It uses OS randomness to produce variable proposals.

    CRITICAL: All proposals are "unmapped" - they contain field values
    OUTSIDE the closed domain, guaranteeing REJECT under frozen artifact
    rules (INVALID_PROPOSALS) while demonstrating byte variability.

    Args:
        raw_input_bytes: Raw bytes from user input file

    Returns:
        ProposalSet as JSON bytes.
        On ANY failure, returns empty bytes b"".

    Guarantees:
        - Single interpretation pass, no retries
        - All exceptions collapse to empty bytes
        - Output conforms to ProposalSet schema structure
        - Proposals contain unmapped values → REJECT guaranteed
        - No external service calls
        - No runtime configuration required
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

        # Generate unmapped proposal (nondeterministic via nonce)
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
