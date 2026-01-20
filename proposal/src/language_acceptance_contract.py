"""
Phase L-9: Language Acceptance Contract

This module implements a closed, explicit phrase-mapping contract for
expanding the accepted language of the proposal engine.

CONTRACT RULES (Freeze-Grade):
1. Mapping table is STATIC and LITERAL (no generation, no runtime config)
2. Normalization is TRIVIAL: trim whitespace, collapse internal whitespace, lowercase ASCII ONLY
3. Lookup is EXACT: normalized input must exactly match a key
4. No chaining: mapped output is NEVER re-mapped
5. No fallbacks, retries, scoring, ranking, or heuristics
6. Unknown inputs pass through UNCHANGED
7. No punctuation stripping (beyond whitespace handling)

FROZEN CONTRACT:
    normalize_and_map(raw_input: str) -> str

    Returns:
        - Canonical phrase if normalized input matches a key EXACTLY
        - Original raw_input UNCHANGED if no match

INVARIANTS:
    - L9-I1: Deterministic - same raw input always produces same output
    - L9-I2: Identity preservation - unknown inputs returned verbatim
    - L9-I3: No side effects - pure function, no state mutation
    - L9-I4: Single-pass - no chaining or recursive mapping

INTEGRATION (Dual Entry Points - Mutually Exclusive):
    L-9 mapping is applied in two proposal engine entry points:
    1. src/artifact_layer/llm_engine.py - LLM engine path
    2. proposal/src/generator.py - Deterministic generator path

    These paths are MUTUALLY EXCLUSIVE by build-time binding:
    - engine_binding.BOUND_ENGINE_NAME determines which engine is used
    - Only ONE engine is ever called per run
    - L-9 mapping is applied exactly ONCE per run

    Proof of mutual exclusivity:
    - seam_provider.acquire_proposal_set() calls get_bound_engine() once
    - get_bound_engine() returns exactly one engine based on BOUND_ENGINE_NAME
    - No code path exists where both engines are invoked

ALLOWED TRANSFORMATIONS:
    - Strip leading/trailing whitespace
    - Collapse consecutive whitespace to single space
    - Lowercase ASCII letters (A-Z -> a-z) only

FORBIDDEN BEHAVIORS:
    - Pattern/regex/wildcard matching
    - Fuzzy matching or edit distance
    - Scoring, ranking, or "best match"
    - Chaining (re-mapping canonical values)
    - Punctuation removal (e.g., "submit-payment" stays unchanged)
    - Non-ASCII case conversion
    - Any fallback or heuristic behavior
"""

import re
from typing import Dict, Optional


# =============================================================================
# STATIC MAPPING TABLE (Phase L-9)
# =============================================================================
# This table maps expanded phrases to their canonical forms.
# ALL keys must be pre-normalized (lowercase, single spaces, trimmed).
# DO NOT add runtime-generated mappings.
# DO NOT chain mappings (canonical values should not be keys).
#
# Format: "expanded phrase (normalized)" -> "canonical phrase"
# =============================================================================

PHRASE_MAPPING_TABLE: Dict[str, str] = {
    # === Payment creation synonyms (L-9 minimal set) ===
    # These are the ONLY authorized mappings for Phase L-9.
    # Do NOT add additional mappings without explicit phase authorization.
    "submit payment": "create payment",
    "new payment": "create payment",
    "make a payment": "create payment",
}


def _ascii_lowercase(s: str) -> str:
    """
    Lowercase ASCII letters only (A-Z -> a-z).

    Non-ASCII characters are preserved unchanged.
    This is intentionally more restrictive than Python's str.lower().
    """
    result = []
    for c in s:
        if 'A' <= c <= 'Z':
            result.append(chr(ord(c) + 32))
        else:
            result.append(c)
    return ''.join(result)


def _trivial_normalize(raw: str) -> str:
    """
    Apply trivial normalization for lookup purposes ONLY.

    Normalization steps (in order):
    1. Strip leading/trailing whitespace
    2. Collapse internal whitespace to single spaces
    3. Lowercase ASCII letters only (A-Z -> a-z)

    This normalization is ONLY used for table lookup.
    The original input is preserved if no match is found.

    IMPORTANT: Only ASCII letters are lowercased. Non-ASCII characters
    (including accented letters like É, Ñ) are preserved unchanged.
    No punctuation is stripped beyond whitespace handling.

    Args:
        raw: Raw input string

    Returns:
        Normalized string for lookup (not for output)
    """
    # Step 1: Strip leading/trailing whitespace
    s = raw.strip()

    # Step 2: Collapse internal whitespace to single spaces
    s = re.sub(r'\s+', ' ', s)

    # Step 3: Lowercase ASCII letters only
    s = _ascii_lowercase(s)

    return s


def normalize_and_map(raw_input: str) -> str:
    """
    Apply the L-9 language acceptance contract.

    This is the ONLY exported function for the L-9 contract.

    Behavior:
    1. Normalize the input (trim, collapse whitespace, lowercase)
    2. Look up the normalized form in the static mapping table
    3. If EXACT match found: return the canonical phrase
    4. If no match: return the ORIGINAL raw_input UNCHANGED

    Args:
        raw_input: Raw user input string

    Returns:
        Canonical phrase if match found, else original raw_input unchanged

    Guarantees:
        - Deterministic (same input -> same output)
        - Pure function (no side effects)
        - Single-pass (no chaining)
        - Identity preservation (unknown inputs unchanged)
    """
    # Normalize for lookup only
    normalized = _trivial_normalize(raw_input)

    # Exact lookup in static table
    canonical = PHRASE_MAPPING_TABLE.get(normalized)

    if canonical is not None:
        # Match found: return canonical phrase
        return canonical
    else:
        # No match: return original input UNCHANGED
        return raw_input


def get_mapping_table_snapshot() -> Dict[str, str]:
    """
    Return a copy of the mapping table for inspection/testing.

    This function exists ONLY for testing and documentation.
    The returned dict is a COPY - modifications do not affect the contract.

    Returns:
        Copy of PHRASE_MAPPING_TABLE
    """
    return dict(PHRASE_MAPPING_TABLE)


def is_canonical_phrase(phrase: str) -> bool:
    """
    Check if a phrase is a canonical form (i.e., a value in the mapping table).

    This function exists ONLY for testing and validation.

    Args:
        phrase: Phrase to check

    Returns:
        True if phrase is a canonical form in the mapping table
    """
    return phrase in PHRASE_MAPPING_TABLE.values()
