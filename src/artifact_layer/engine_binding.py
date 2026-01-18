"""
Engine Binding - Build/Package-Time Engine Selection

This module defines which proposal engine is bound at build/package time.
There is NO runtime selection mechanism. The bound engine is fixed.

To change the engine, modify BOUND_ENGINE_NAME and rebuild/repackage.

Constraints:
- No environment variables
- No runtime flags
- No config files
- No dynamic selection
"""

import os
import sys

# Build-time binding: select which engine to use
# Change this value and rebuild to switch engines
# Phase L-2: LLM engine activated (non-authoritative, REJECT-safe)
BOUND_ENGINE_NAME = "llm"

# Engine registry (populated at import time)
_ENGINES = {}


def _register_deterministic_engine():
    """Register the deterministic proposal engine (existing M-1 generator)."""
    # Resolve paths at import time
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    proposal_src = os.path.join(repo_root, 'proposal', 'src')

    if proposal_src not in sys.path:
        sys.path.insert(0, proposal_src)

    try:
        from generator import generate_proposal_set, proposal_set_to_json
        from validator import validate_and_normalize

        def deterministic_engine(raw_input_bytes: bytes) -> bytes:
            """
            Deterministic proposal engine wrapping M-1 generator.

            Args:
                raw_input_bytes: Raw input file content as bytes

            Returns:
                Proposal set as JSON bytes
            """
            try:
                # Decode input bytes to string
                input_text = raw_input_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # Non-UTF8 input produces empty proposal set
                return b'{"schema_version":"m1.0","input":{"raw":""},"proposals":[]}'

            # Generate proposals using deterministic M-1 generator
            proposal_set = generate_proposal_set(input_text)

            # Validate and normalize
            validated = validate_and_normalize(proposal_set)

            # Serialize to JSON bytes
            return proposal_set_to_json(validated).encode('utf-8')

        _ENGINES["deterministic"] = deterministic_engine

    except ImportError:
        # If generator is not available, engine registration fails silently
        # get_bound_engine() will return None
        pass


def get_bound_engine():
    """
    Get the engine bound at build/package time.

    Returns:
        Engine function or None if binding failed.

    The returned function has signature:
        engine(raw_input_bytes: bytes) -> bytes
    """
    return _ENGINES.get(BOUND_ENGINE_NAME)


def _register_llm_engine():
    """Register the LLM-backed proposal engine (Phase L-2)."""
    try:
        from .llm_engine import llm_engine
        _ENGINES["llm"] = llm_engine
    except ImportError:
        # If LLM engine module is not available, registration fails silently
        # get_bound_engine() will return None, collapsing to REJECT
        pass


# Register engines at import time (build/package time selection)
_register_deterministic_engine()
_register_llm_engine()
