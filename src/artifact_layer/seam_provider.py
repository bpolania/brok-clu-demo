"""
Seam Provider - acquire_proposal_set

This module provides the single integration seam for proposal acquisition.

Frozen Contract:
    acquire_proposal_set(raw_input_bytes: bytes, ctx: RunContext) -> OpaqueProposalBytes

Constraints:
- Input: opaque bytes from user input file
- Output: opaque proposal bytes (content is NOT inspected)
- Single call per run (enforced by RunContext)
- All failures collapse to empty bytes
- No parsing, filtering, or enrichment of proposals
- No runtime switching or configurability

Freeze-Grade Enforcement:
- RunContext enforces exactly-one-call at runtime
- OpaqueProposalBytes prevents accidental inspection by construction
"""

from typing import Optional

from .engine_binding import get_bound_engine
from .run_context import RunContext, SeamSViolation
from .opaque_bytes import OpaqueProposalBytes


def acquire_proposal_set(
    raw_input_bytes: bytes,
    ctx: Optional[RunContext] = None
) -> OpaqueProposalBytes:
    """
    Acquire proposal set from the bound engine.

    This is the ONLY integration seam for proposal generation.

    Args:
        raw_input_bytes: Opaque bytes from user input file
        ctx: Run context for enforcing single-call invariant.
             If provided, raises SeamSViolation on second call.

    Returns:
        OpaqueProposalBytes wrapping the proposal output.
        On ANY failure, returns OpaqueProposalBytes(b"") which will
        deterministically collapse to REJECT downstream.

    Raises:
        SeamSViolation: If called more than once with the same RunContext.

    Guarantees:
        - Single call per run (when ctx provided)
        - All exceptions collapse to empty bytes
        - No parsing or interpretation of input
        - No filtering or modification of output
        - Output is opaque by construction
    """
    # Enforce exactly-one-call if context provided
    if ctx is not None:
        ctx.mark_seam_s_called()

    # Get the bound engine (build-time selection)
    engine = get_bound_engine()

    if engine is None:
        # No engine bound: return empty bytes -> REJECT downstream
        return OpaqueProposalBytes(b"")

    try:
        # Single attempt, no retries
        result = engine(raw_input_bytes)

        # Validate result type
        if not isinstance(result, bytes):
            return OpaqueProposalBytes(b"")

        return OpaqueProposalBytes(result)

    except Exception:
        # All failures collapse to empty bytes
        return OpaqueProposalBytes(b"")
