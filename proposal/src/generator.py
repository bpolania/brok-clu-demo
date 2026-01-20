#!/usr/bin/env python3
"""
Phase M-1 Proposal Generator

Generates non-authoritative proposals from raw user input.
Proposals have no authority and do not imply execution outcomes.

Determinism: Same input always produces byte-for-byte identical output.
Boundedness: Maximum 8 proposals per input. Input limited to 4096 chars.
Failure: Invalid/unmapped input produces zero proposals (not fallback).

NOTE: This generator is the DETERMINISTIC engine path.
Under current build (BOUND_ENGINE_NAME = "llm"), this path is NOT executed.
L-9 language acceptance expansion is integrated at the LLM engine path ONLY.
See: src/artifact_layer/llm_engine.py for L-9 integration.
"""

import re
from typing import Optional

# Schema version - must match proposal_set.schema.json
SCHEMA_VERSION = "m1.0"

# Bounds from schema
MAX_INPUT_LENGTH = 4096
MAX_PROPOSALS = 8

# Closed sets from domain
VALID_INTENTS = frozenset(["RESTART_SUBSYSTEM", "STOP_SUBSYSTEM", "STATUS_QUERY"])
VALID_TARGETS = frozenset(["alpha", "beta", "gamma"])
VALID_MODES = frozenset(["graceful", "immediate"])

# Pattern definitions for deterministic matching
# These patterns are conservative and map only clear, unambiguous inputs
PATTERNS = [
    # "restart <target> subsystem gracefully" / "restart <target> subsystem immediately"
    {
        "regex": re.compile(
            r"^restart\s+(alpha|beta|gamma)\s+subsystem\s+(gracefully|immediately)$",
            re.IGNORECASE
        ),
        "intent": "RESTART_SUBSYSTEM",
        "groups": {"target": 1, "mode": 2},
        "mode_map": {"gracefully": "graceful", "immediately": "immediate"}
    },
    # "graceful restart of <target>"
    {
        "regex": re.compile(
            r"^graceful\s+restart\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "RESTART_SUBSYSTEM",
        "groups": {"target": 1},
        "fixed_mode": "graceful"
    },
    # "immediate restart of <target>"
    {
        "regex": re.compile(
            r"^immediate\s+restart\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "RESTART_SUBSYSTEM",
        "groups": {"target": 1},
        "fixed_mode": "immediate"
    },
    # "stop <target> subsystem gracefully" / "stop <target> subsystem immediately"
    {
        "regex": re.compile(
            r"^stop\s+(alpha|beta|gamma)\s+subsystem\s+(gracefully|immediately)$",
            re.IGNORECASE
        ),
        "intent": "STOP_SUBSYSTEM",
        "groups": {"target": 1, "mode": 2},
        "mode_map": {"gracefully": "graceful", "immediately": "immediate"}
    },
    # "graceful stop of <target>"
    {
        "regex": re.compile(
            r"^graceful\s+stop\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "STOP_SUBSYSTEM",
        "groups": {"target": 1},
        "fixed_mode": "graceful"
    },
    # "immediate stop of <target>"
    {
        "regex": re.compile(
            r"^immediate\s+stop\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "STOP_SUBSYSTEM",
        "groups": {"target": 1},
        "fixed_mode": "immediate"
    },
    # "status of <target>"
    {
        "regex": re.compile(
            r"^status\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "STATUS_QUERY",
        "groups": {"target": 1}
    },
    # "query status of <target>"
    {
        "regex": re.compile(
            r"^query\s+status\s+of\s+(alpha|beta|gamma)$",
            re.IGNORECASE
        ),
        "intent": "STATUS_QUERY",
        "groups": {"target": 1}
    },
    # "<target> status"
    {
        "regex": re.compile(
            r"^(alpha|beta|gamma)\s+status$",
            re.IGNORECASE
        ),
        "intent": "STATUS_QUERY",
        "groups": {"target": 1}
    },
]


def _match_pattern(input_text: str, pattern: dict) -> Optional[dict]:
    """
    Attempt to match input against a single pattern.
    Returns proposal payload dict or None if no match.
    """
    match = pattern["regex"].match(input_text)
    if not match:
        return None

    groups = pattern["groups"]
    target = match.group(groups["target"]).lower()

    # Validate target is in closed set
    if target not in VALID_TARGETS:
        return None

    slots = {"target": target}

    # Handle mode extraction
    if "mode" in groups:
        raw_mode = match.group(groups["mode"]).lower()
        mode_map = pattern.get("mode_map", {})
        mode = mode_map.get(raw_mode, raw_mode)
        if mode not in VALID_MODES:
            return None
        slots["mode"] = mode
    elif "fixed_mode" in pattern:
        slots["mode"] = pattern["fixed_mode"]
    # STATUS_QUERY does not require mode

    return {
        "kind": "ROUTE_CANDIDATE",
        "payload": {
            "intent": pattern["intent"],
            "slots": slots
        }
    }


def generate_proposal_set(input_raw: str) -> dict:
    """
    Generate a ProposalSet from raw user input.

    Args:
        input_raw: Exact user input string. No trimming applied.
                   Empty string is valid. Whitespace-only is preserved.

    Returns:
        ProposalSet dict with schema_version, input, proposals, and optional errors.

    Guarantees:
        - Deterministic: same input always produces identical output
        - Bounded: max 8 proposals, input max 4096 chars
        - Non-authoritative: proposals do not imply decisions or outcomes
        - Zero proposals is valid for unmapped/invalid input
    """
    errors = []
    proposals = []

    # Validate input length (bound check)
    if len(input_raw) > MAX_INPUT_LENGTH:
        errors.append("INPUT_TOO_LONG")
        # Return zero proposals for overlong input
        return {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": input_raw[:MAX_INPUT_LENGTH]},  # Truncate for storage only
            "proposals": [],
            "errors": errors
        }

    # Empty or whitespace-only input: valid but produces zero proposals
    if not input_raw or input_raw.isspace():
        return {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": input_raw},
            "proposals": []
        }

    # Normalize for matching (but preserve original in output)
    # Only strip leading/trailing whitespace for pattern matching
    # NOTE: L-9 language acceptance is NOT applied here.
    # Under current build, this path is not executed (BOUND_ENGINE_NAME = "llm").
    normalized = input_raw.strip()

    # Attempt pattern matching - deterministic order
    for pattern in PATTERNS:
        proposal = _match_pattern(normalized, pattern)
        if proposal is not None:
            proposals.append(proposal)
            # For this implementation, we emit at most one proposal per input
            # (conservative approach - no ambiguous multi-proposal emission)
            break

    # Enforce max proposals bound (defensive)
    proposals = proposals[:MAX_PROPOSALS]

    result = {
        "schema_version": SCHEMA_VERSION,
        "input": {"raw": input_raw},
        "proposals": proposals
    }

    if errors:
        result["errors"] = errors

    return result


def proposal_set_to_json(proposal_set: dict) -> str:
    """
    Serialize ProposalSet to deterministic JSON string.

    Uses sorted keys and consistent formatting for byte-for-byte reproducibility.
    """
    import json
    return json.dumps(proposal_set, sort_keys=True, separators=(',', ':'))


if __name__ == "__main__":
    # Simple test when run directly
    import sys
    if len(sys.argv) > 1:
        test_input = sys.argv[1]
    else:
        test_input = sys.stdin.read()

    result = generate_proposal_set(test_input)
    print(proposal_set_to_json(result))
