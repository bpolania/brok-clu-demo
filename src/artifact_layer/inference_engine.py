"""
Local Inference Engine (Vendored from brok-llm-proposals)

Phase L-10 Integration:
This module provides the local LLM inference entrypoint called by llm_engine.py.

CONTRACT:
- Input: exactly one raw_input_bytes (opaque)
- Output: exactly one proposalset_bytes (opaque bytes; may be empty)
- Execution: exactly one inference call per invocation
- Failure semantics: any failure collapses to empty bytes, silently

VENDORED MODEL CONTRACT (Phase L-10 Prompt 1):
- Fixed path: models/local_llm/model.bin (hard-coded, non-configurable)
- No env vars, CLI flags, or config files can override this path
- Missing/invalid model collapses to empty bytes silently
- No download or fallback attempts

INPUT TRANSPORT (BASE64 ENCODING):
raw_input_bytes are transported to the LLM via base64 encoding:
- Base64 encoding is TOTAL: never fails for any input bytes
- Base64 encoding is REVERSIBLE: identical bytes produce identical prompts
- NO UTF-8 decoding of raw_input_bytes (would be partial/lossy)

OUTPUT HANDLING (NO DECODING):
Model output is treated as OPAQUE BYTES:
- Model output text is encoded to UTF-8 bytes
- NO parsing or inspection of model output structure
- Output is bounded by MAX_PROPOSAL_BYTES (size check only)
- Oversized output collapses to empty

FAILURE-TO-EMPTY COLLAPSE:
All failure modes collapse to empty bytes.

AUTHORIZATION:
Vendored from brok-llm-proposals under explicit Phase L-10 Prompt 2C
authorization. Fixed-path contract established per Prompt 1.
"""

import base64
from pathlib import Path

# =============================================================================
# FIXED-PATH MODEL CONTRACT (Phase L-10 Prompt 1)
# =============================================================================

# Hard-coded model path - NO CONFIGURATION SURFACE
# This path is relative to the repository root.
# NO env vars, CLI flags, or config files can override this.
_MODEL_RELATIVE_PATH: str = "models/local_llm/model.bin"


def _get_model_path() -> Path:
    """
    Get the fixed model path.

    FIXED-PATH CONTRACT:
    - Path is hard-coded as models/local_llm/model.bin
    - No configuration surface (no env/CLI/config override)
    - Path is resolved relative to repository root

    Returns:
        Absolute path to the vendored model file.
    """
    # Resolve repository root from this module's location
    # This file is at: src/artifact_layer/inference_engine.py
    # Repository root is two directories up
    module_dir = Path(__file__).parent
    repo_root = module_dir.parent.parent
    return repo_root / _MODEL_RELATIVE_PATH


# Maximum proposal bytes (1MB bound)
MAX_PROPOSAL_BYTES: int = 1048576


# =============================================================================
# LLM INSTANCE (module-level, lazy-loaded)
# =============================================================================

# Lazy-loaded LLM instance
# This is a cache for performance only - does NOT encode failure history
# Load is attempted whenever _llm_instance is None
_llm_instance = None


def _get_llm():
    """
    Get the LLM instance, loading it lazily on first use.

    FIXED-PATH CONTRACT (Phase L-10 Prompt 1):
    Model path is: models/local_llm/model.bin (hard-coded, non-configurable)
    See _get_model_path() for path resolution.

    ACTIVATION STATUS:
    Model loading is NOT YET ACTIVATED in this prompt.
    This function currently returns None, causing collapse to empty bytes.
    Activation will occur in a subsequent L-10 prompt.

    STATE ISOLATION:
    - Load is attempted whenever _llm_instance is None
    - Failures do NOT poison subsequent invocations
    - If load fails, returns None (collapses to empty bytes)
    - Next invocation will attempt load again if _llm_instance is still None

    Returns None if LLM is not available (which collapses to empty bytes).
    """
    global _llm_instance

    # If already loaded, return cached instance
    if _llm_instance is not None:
        return _llm_instance

    # Attempt to load - no failure flag, so next call will retry if this fails
    try:
        # Import llama_cpp here to allow the module to load even if
        # llama-cpp-python is not installed (for tests that mock)
        from llama_cpp import Llama  # noqa: F401

        # PHASE L-10 PROMPT 1: Path constant established but NOT ACTIVATED
        # The fixed model path is: models/local_llm/model.bin
        # Actual model loading will be activated in a subsequent prompt.
        # For now, return None to maintain collapse-to-empty behavior.
        # model_path = _get_model_path()  # Available but not used yet
        return None

    except ImportError:
        # llama-cpp-python not installed - collapse to empty
        return None
    except Exception:
        # Any other failure - collapse to empty
        return None


# =============================================================================
# INFERENCE ENGINE (PUBLIC INTERFACE)
# =============================================================================

def inference_engine(raw_input_bytes: bytes) -> bytes:
    """
    Local inference-backed proposal engine.

    Generates proposalset_bytes from raw_input_bytes via a single
    LLM forward pass.

    CONTRACT:
    - Input: opaque raw_input_bytes (no parsing/inspection at boundary)
    - Output: opaque proposalset_bytes (may be empty; bounded by MAX_PROPOSAL_BYTES)
    - Execution: exactly one inference call (no retries)
    - Failure: any error collapses to empty bytes, silently

    INPUT TRANSPORT:
    - raw_input_bytes are base64 encoded to produce prompt string
    - Base64 encoding is TOTAL (never fails for any bytes)
    - NO UTF-8 decoding of raw_input_bytes

    OUTPUT HANDLING:
    - Model output is treated as opaque bytes
    - NO decoding or parsing of model output
    - Size enforcement via byte length only

    Args:
        raw_input_bytes: Opaque input bytes

    Returns:
        proposalset_bytes: Opaque output bytes (may be empty)
    """
    try:
        # =================================================================
        # STEP 1: GET LLM INSTANCE
        # =================================================================
        llm = _get_llm()
        if llm is None:
            # No LLM available - collapse to empty
            return b""

        # =================================================================
        # STEP 2: PREPARE INPUT (BASE64 TRANSPORT)
        # =================================================================
        # Base64 encode input bytes to produce prompt string.
        # This is TOTAL: never fails for any input bytes.
        # NO UTF-8 decoding - base64 is used as transport encoding.
        prompt = base64.b64encode(raw_input_bytes).decode('ascii')

        # =================================================================
        # STEP 3: SINGLE INFERENCE CALL (exactly once)
        # =================================================================
        # Call the LLM exactly once.
        # No retries, no fallbacks, no loops.
        output = llm(
            prompt,
            max_tokens=128,
            echo=False,
            stop=None
        )

        # =================================================================
        # STEP 4: EXTRACT OUTPUT TEXT
        # =================================================================
        # The output is a dict with 'choices' containing generated text
        if not isinstance(output, dict):
            return b""

        choices = output.get('choices', [])
        if not choices:
            return b""

        text = choices[0].get('text', '')
        if not isinstance(text, str):
            return b""

        # =================================================================
        # STEP 5: ENCODE OUTPUT TO BYTES (NO DECODING)
        # =================================================================
        # Encode output text to UTF-8 bytes
        # The output bytes are opaque - we don't parse or decode them
        output_bytes = text.encode('utf-8')

        # =================================================================
        # STEP 6: SIZE ENFORCEMENT (byte length only)
        # =================================================================
        # Check output size against MAX_PROPOSAL_BYTES.
        # If exceeded, collapse to empty (not truncate).
        if len(output_bytes) > MAX_PROPOSAL_BYTES:
            return b""

        return output_bytes

    except Exception:
        # =================================================================
        # FAILURE COLLAPSE
        # =================================================================
        # Any exception collapses to empty bytes, silently.
        # No error details are propagated.
        return b""
