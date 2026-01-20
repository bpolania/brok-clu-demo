"""
LLM Proposal Engine - Local In-Process Inference (Minimal Shell)

Phase L-10 Activation:
This module is a minimal shell that invokes local LLM inference exactly once
per call via the vendored inference_engine module.

CONTRACT:
- Input: opaque raw_input_bytes (no parsing/inspection at boundary)
- Output: opaque proposalset_bytes (may be empty)
- Execution: exactly one inference call per invocation
- Failure: any error collapses to empty bytes b""

IMPORTANT: This engine is NON-AUTHORITATIVE.
The artifact layer is sole authority for ACCEPT/REJECT decisions.

CRITICAL CONSTRAINTS:
- No runtime configuration (no env vars, no flags, no config files)
- No retries, no exponential delays, no multiple calls
- Single inference call per invocation
- All failures collapse to empty bytes
- No network calls
- Output is opaque bytes (no parsing/inspection)

AUTHORIZATION:
Local LLM inference via inference_engine.py, vendored from brok-llm-proposals
under explicit Phase L-10 Prompt 2C authorization.
"""

from artifact_layer.inference_engine import inference_engine


def _invoke_local_llm(raw_input_bytes: bytes) -> bytes:
    """
    Invoke the local LLM inference engine.

    This is the single adapter boundary between llm_engine and the
    vendored inference_engine module. It exists to provide a clear
    call boundary for Phase L-10.

    CONTRACT:
    - Input: opaque raw_input_bytes
    - Output: opaque bytes from inference_engine
    - Execution: called exactly once (no retries)
    - Failure: propagates to caller (collapsed there)

    Args:
        raw_input_bytes: Opaque input bytes

    Returns:
        Proposal bytes (opaque, may be empty)
    """
    return inference_engine(raw_input_bytes)


def llm_engine(raw_input_bytes: bytes) -> bytes:
    """
    Local LLM proposal engine (NON-AUTHORITATIVE).

    Minimal shell that invokes local LLM inference exactly once via
    _invoke_local_llm. The output is treated as opaque bytes.

    Phase L-10 Contract:
    - Calls _invoke_local_llm exactly once
    - Returns result as opaque bytes
    - Any failure collapses to empty bytes b""
    - Does NOT make authoritative decisions

    Args:
        raw_input_bytes: Raw bytes from user input file

    Returns:
        Proposal bytes (opaque).
        On ANY failure, returns empty bytes b"".

    Guarantees:
        - Single inference call, no retries
        - All exceptions collapse to empty bytes
        - No output parsing/inspection
        - No external service calls
        - No runtime configuration required
        - Does NOT make authoritative decisions
    """
    try:
        return _invoke_local_llm(raw_input_bytes)
    except Exception:
        # All failures collapse to empty bytes
        # This ensures REJECT-safe behavior downstream
        return b""
