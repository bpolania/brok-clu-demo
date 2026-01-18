"""
Seam Provider - acquire_proposal_set

This module provides the single integration seam for proposal acquisition.

Frozen Contract:
    acquire_proposal_set(raw_input_bytes: bytes) -> bytes

Constraints:
- Input: raw bytes from user input file
- Output: opaque proposal bytes (JSON-serialized ProposalSet)
- Single call per run (no retries)
- All failures collapse to empty bytes
- No parsing, filtering, or enrichment of proposals
- No runtime switching or configurability
"""

from .engine_binding import get_bound_engine


def acquire_proposal_set(raw_input_bytes: bytes) -> bytes:
    """
    Acquire proposal set from the bound engine.

    This is the ONLY integration seam for proposal generation.

    Args:
        raw_input_bytes: Raw bytes from user input file

    Returns:
        Proposal set as bytes (JSON-serialized).
        On ANY failure, returns empty bytes b"" which will
        deterministically collapse to REJECT downstream.

    Guarantees:
        - Single call, no retries
        - All exceptions collapse to empty bytes
        - No parsing or interpretation of input
        - No filtering or modification of output
    """
    # Get the bound engine (build-time selection)
    engine = get_bound_engine()

    if engine is None:
        # No engine bound: return empty bytes -> REJECT downstream
        return b""

    try:
        # Single attempt, no retries
        result = engine(raw_input_bytes)

        # Validate result type
        if not isinstance(result, bytes):
            return b""

        return result

    except Exception:
        # All failures collapse to empty bytes
        return b""
