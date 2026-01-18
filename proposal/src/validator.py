#!/usr/bin/env python3
"""
Phase M-1 Proposal Validator

Performs spec-aligned structural validation of ProposalSet documents.
Uses Python standard library only (no external dependencies).

The JSON Schema file (proposal/schema/proposal_set.schema.json) serves as the
specification reference. This validator implements explicit structural checks
equivalent to those schema constraints:

- Required fields and types
- String length bounds (input.raw max 4096, error entries max 256)
- Array item limits (proposals max 8, errors max 16)
- Closed enum membership (kind, intent, target, mode)
- Additional properties rejection (unknown fields rejected at all levels)

Implementation note: This is NOT a JSON Schema validation engine. It performs
deterministic, explicit checks that enforce the same constraints as the schema.

Guarantees:
- Deterministic: same input always produces same validation result
- No environment variables or time dependencies
- Bounded error output (max 16 error codes)
- Error codes are non-authoritative (do not imply decisions)
"""

from typing import List, Tuple

# Schema constants (must match proposal_set.schema.json)
SCHEMA_VERSION = "m1.0"
MAX_INPUT_LENGTH = 4096
MAX_PROPOSALS = 8
MAX_ERRORS = 16
MAX_ERROR_LENGTH = 256

VALID_INTENTS = frozenset(["RESTART_SUBSYSTEM", "STOP_SUBSYSTEM", "STATUS_QUERY"])
VALID_TARGETS = frozenset(["alpha", "beta", "gamma"])
VALID_MODES = frozenset(["graceful", "immediate"])
VALID_KINDS = frozenset(["ROUTE_CANDIDATE", "STATE_TRANSITION_REQUEST"])  # L-4 adds STATE_TRANSITION_REQUEST


def validate_proposal_set(data: dict) -> Tuple[bool, List[str]]:
    """
    Validate a ProposalSet dict against the m1.0 schema.

    Args:
        data: ProposalSet dict to validate

    Returns:
        Tuple of (is_valid, error_messages)
        is_valid: True if data conforms to schema
        error_messages: List of validation error descriptions (empty if valid)

    Guarantees:
        - Deterministic: same input always produces same result
        - No environment or time dependencies
    """
    errors = []

    # Check top-level type
    if not isinstance(data, dict):
        return False, ["ROOT_NOT_OBJECT"]

    # Check required fields
    required = ["schema_version", "input", "proposals"]
    for field in required:
        if field not in data:
            errors.append(f"MISSING_REQUIRED_FIELD:{field}")

    if errors:
        return False, errors

    # Check no additional properties at root
    allowed_root = {"schema_version", "input", "proposals", "errors"}
    extra = set(data.keys()) - allowed_root
    if extra:
        errors.append(f"UNEXPECTED_ROOT_FIELDS:{','.join(sorted(extra))}")

    # Validate schema_version
    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"INVALID_SCHEMA_VERSION:expected={SCHEMA_VERSION}")

    # Validate input
    input_obj = data["input"]
    if not isinstance(input_obj, dict):
        errors.append("INPUT_NOT_OBJECT")
    else:
        if "raw" not in input_obj:
            errors.append("MISSING_INPUT_RAW")
        elif not isinstance(input_obj["raw"], str):
            errors.append("INPUT_RAW_NOT_STRING")
        elif len(input_obj["raw"]) > MAX_INPUT_LENGTH:
            errors.append(f"INPUT_RAW_TOO_LONG:max={MAX_INPUT_LENGTH}")

        # Check no additional properties in input
        allowed_input = {"raw"}
        extra_input = set(input_obj.keys()) - allowed_input
        if extra_input:
            errors.append(f"UNEXPECTED_INPUT_FIELDS:{','.join(sorted(extra_input))}")

    # Validate proposals
    proposals = data["proposals"]
    if not isinstance(proposals, list):
        errors.append("PROPOSALS_NOT_ARRAY")
    else:
        if len(proposals) > MAX_PROPOSALS:
            errors.append(f"TOO_MANY_PROPOSALS:max={MAX_PROPOSALS}")

        for i, proposal in enumerate(proposals):
            proposal_errors = _validate_proposal(proposal, i)
            errors.extend(proposal_errors)

    # Validate errors field (optional)
    if "errors" in data:
        err_array = data["errors"]
        if not isinstance(err_array, list):
            errors.append("ERRORS_NOT_ARRAY")
        else:
            if len(err_array) > MAX_ERRORS:
                errors.append(f"TOO_MANY_ERROR_ENTRIES:max={MAX_ERRORS}")
            for i, err in enumerate(err_array):
                if not isinstance(err, str):
                    errors.append(f"ERROR_ENTRY_{i}_NOT_STRING")
                elif len(err) > MAX_ERROR_LENGTH:
                    errors.append(f"ERROR_ENTRY_{i}_TOO_LONG:max={MAX_ERROR_LENGTH}")

    return len(errors) == 0, errors


def _validate_proposal(proposal: dict, index: int) -> List[str]:
    """Validate a single proposal object."""
    errors = []
    prefix = f"PROPOSAL_{index}"

    if not isinstance(proposal, dict):
        return [f"{prefix}_NOT_OBJECT"]

    # Check required fields
    if "kind" not in proposal:
        errors.append(f"{prefix}_MISSING_KIND")
    if "payload" not in proposal:
        errors.append(f"{prefix}_MISSING_PAYLOAD")

    if errors:
        return errors

    # Check no additional properties
    allowed = {"kind", "payload"}
    extra = set(proposal.keys()) - allowed
    if extra:
        errors.append(f"{prefix}_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate kind
    kind = proposal["kind"]
    if not isinstance(kind, str):
        errors.append(f"{prefix}_KIND_NOT_STRING")
    elif kind not in VALID_KINDS:
        errors.append(f"{prefix}_INVALID_KIND:{kind}")

    # Validate payload based on kind
    payload = proposal["payload"]
    if kind == "ROUTE_CANDIDATE":
        payload_errors = _validate_route_candidate_payload(payload, prefix)
        errors.extend(payload_errors)
    elif kind == "STATE_TRANSITION_REQUEST":
        payload_errors = _validate_state_transition_request_payload(payload, prefix)
        errors.extend(payload_errors)

    return errors


def _validate_route_candidate_payload(payload: dict, prefix: str) -> List[str]:
    """Validate ROUTE_CANDIDATE payload."""
    errors = []

    if not isinstance(payload, dict):
        return [f"{prefix}_PAYLOAD_NOT_OBJECT"]

    # Check required fields
    if "intent" not in payload:
        errors.append(f"{prefix}_PAYLOAD_MISSING_INTENT")
    if "slots" not in payload:
        errors.append(f"{prefix}_PAYLOAD_MISSING_SLOTS")

    if errors:
        return errors

    # Check no additional properties
    allowed = {"intent", "slots"}
    extra = set(payload.keys()) - allowed
    if extra:
        errors.append(f"{prefix}_PAYLOAD_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate intent
    intent = payload["intent"]
    if not isinstance(intent, str):
        errors.append(f"{prefix}_INTENT_NOT_STRING")
    elif intent not in VALID_INTENTS:
        errors.append(f"{prefix}_INVALID_INTENT:{intent}")

    # Validate slots
    slots = payload["slots"]
    if not isinstance(slots, dict):
        errors.append(f"{prefix}_SLOTS_NOT_OBJECT")
    else:
        # Check no additional properties in slots
        allowed_slots = {"target", "mode"}
        extra_slots = set(slots.keys()) - allowed_slots
        if extra_slots:
            errors.append(f"{prefix}_SLOTS_UNEXPECTED_FIELDS:{','.join(sorted(extra_slots))}")

        # Validate target if present
        if "target" in slots:
            target = slots["target"]
            if not isinstance(target, str):
                errors.append(f"{prefix}_TARGET_NOT_STRING")
            elif target not in VALID_TARGETS:
                errors.append(f"{prefix}_INVALID_TARGET:{target}")

        # Validate mode if present
        if "mode" in slots:
            mode = slots["mode"]
            if not isinstance(mode, str):
                errors.append(f"{prefix}_MODE_NOT_STRING")
            elif mode not in VALID_MODES:
                errors.append(f"{prefix}_INVALID_MODE:{mode}")

    return errors


def _validate_state_transition_request_payload(payload: dict, prefix: str) -> List[str]:
    """Validate STATE_TRANSITION_REQUEST payload (L-4)."""
    errors = []

    if not isinstance(payload, dict):
        return [f"{prefix}_PAYLOAD_NOT_OBJECT"]

    # Check required fields
    if "event_token" not in payload:
        errors.append(f"{prefix}_PAYLOAD_MISSING_EVENT_TOKEN")
        return errors

    # Check no additional properties
    allowed = {"event_token"}
    extra = set(payload.keys()) - allowed
    if extra:
        errors.append(f"{prefix}_PAYLOAD_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate event_token is a string
    event_token = payload["event_token"]
    if not isinstance(event_token, str):
        errors.append(f"{prefix}_EVENT_TOKEN_NOT_STRING")

    # Note: We don't validate the event_token value here.
    # The artifact builder's L-4 gate validates against the closed set.

    return errors


def validate_and_normalize(data: dict) -> dict:
    """
    Validate a ProposalSet and return a normalized result.

    If validation fails, returns a ProposalSet with zero proposals
    and error codes in the errors field.

    Args:
        data: ProposalSet dict to validate

    Returns:
        Valid ProposalSet dict (either original if valid, or empty with errors)
    """
    is_valid, errors = validate_proposal_set(data)

    if is_valid:
        return data

    # Validation failed: return empty ProposalSet with error codes
    # Preserve input.raw if possible for debugging
    input_raw = ""
    if isinstance(data, dict) and isinstance(data.get("input"), dict):
        raw = data["input"].get("raw", "")
        if isinstance(raw, str):
            input_raw = raw[:MAX_INPUT_LENGTH]

    return {
        "schema_version": SCHEMA_VERSION,
        "input": {"raw": input_raw},
        "proposals": [],
        "errors": errors[:MAX_ERRORS]
    }


if __name__ == "__main__":
    import json
    import sys

    # Read JSON from stdin or file argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    is_valid, errors = validate_proposal_set(data)

    if is_valid:
        print("VALID")
        sys.exit(0)
    else:
        print("INVALID")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
