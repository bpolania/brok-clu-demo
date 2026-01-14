#!/usr/bin/env python3
"""
Phase M-2 Artifact Validator

Performs spec-aligned structural validation of Artifact documents.
Uses Python standard library only (no external dependencies).

The JSON Schema file (artifact/schema/artifact.schema.json) serves as the
specification reference. This validator implements explicit structural checks
equivalent to those schema constraints:

- Required fields and types
- String length and pattern bounds
- Array item limits
- Closed enum membership
- Additional properties rejection (unknown fields rejected at all levels)
- Decision/payload exclusivity (ACCEPT requires accept_payload, REJECT requires reject_payload)

Implementation note: This is NOT a JSON Schema validation engine. It performs
deterministic, explicit checks that enforce the same constraints as the schema.

Guarantees:
- Deterministic: same input always produces same validation result
- No environment variables or time dependencies
- Bounded error output (max 16 error codes)
"""

import re
from typing import List, Tuple

# Schema constants (must match artifact.schema.json)
ARTIFACT_VERSION = "artifact_v1"
RULESET_ID = "M2_RULESET_V1"

MAX_RUN_ID_LENGTH = 64
MAX_REF_LENGTH = 512
MAX_NOTES = 8
MAX_NOTE_LENGTH = 128
MAX_VALIDATOR_ERRORS = 16
MAX_ERROR_LENGTH = 256
MAX_PROPOSALS = 8

# Valid enums
VALID_DECISIONS = frozenset(["ACCEPT", "REJECT"])
VALID_ACCEPT_KINDS = frozenset(["ROUTE"])
VALID_INTENTS = frozenset(["RESTART_SUBSYSTEM", "STOP_SUBSYSTEM", "STATUS_QUERY"])
VALID_TARGETS = frozenset(["alpha", "beta", "gamma"])
VALID_MODES = frozenset(["graceful", "immediate"])
VALID_REASON_CODES = frozenset(["NO_PROPOSALS", "AMBIGUOUS_PROPOSALS", "INVALID_PROPOSALS"])

# Patterns
RUN_ID_PATTERN = re.compile(r'^[A-Za-z0-9._-]+$')
NOTE_PATTERN = re.compile(r'^[A-Z0-9_:]+$')
# Windows absolute path patterns (drive letter or UNC)
WINDOWS_DRIVE_PATTERN = re.compile(r'^[A-Za-z]:[\\/]')
WINDOWS_UNC_PATTERN = re.compile(r'^\\\\')


def _is_absolute_path(path: str) -> bool:
    """Check if path is absolute (Unix or Windows style)."""
    if path.startswith('/'):
        return True
    if WINDOWS_DRIVE_PATTERN.match(path):
        return True
    if WINDOWS_UNC_PATTERN.match(path):
        return True
    return False


def validate_artifact(data: dict) -> Tuple[bool, List[str]]:
    """
    Validate an Artifact dict against the artifact_v1 schema.

    Args:
        data: Artifact dict to validate

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
    required = ["artifact_version", "run_id", "input_ref", "proposal_set_ref", "decision", "construction"]
    for field in required:
        if field not in data:
            errors.append(f"MISSING_REQUIRED_FIELD:{field}")

    if errors:
        return False, errors

    # Check no additional properties at root (allow accept_payload or reject_payload based on decision)
    decision = data.get("decision")
    allowed_root = {"artifact_version", "run_id", "input_ref", "proposal_set_ref", "decision", "construction"}
    if decision == "ACCEPT":
        allowed_root.add("accept_payload")
    elif decision == "REJECT":
        allowed_root.add("reject_payload")

    extra = set(data.keys()) - allowed_root
    if extra:
        errors.append(f"UNEXPECTED_ROOT_FIELDS:{','.join(sorted(extra))}")

    # Validate artifact_version
    if data["artifact_version"] != ARTIFACT_VERSION:
        errors.append(f"INVALID_ARTIFACT_VERSION:expected={ARTIFACT_VERSION}")

    # Validate run_id
    run_id = data["run_id"]
    if not isinstance(run_id, str):
        errors.append("RUN_ID_NOT_STRING")
    elif len(run_id) > MAX_RUN_ID_LENGTH:
        errors.append(f"RUN_ID_TOO_LONG:max={MAX_RUN_ID_LENGTH}")
    elif not RUN_ID_PATTERN.match(run_id):
        errors.append("RUN_ID_INVALID_PATTERN")

    # Validate input_ref
    input_ref = data["input_ref"]
    if not isinstance(input_ref, str):
        errors.append("INPUT_REF_NOT_STRING")
    elif len(input_ref) > MAX_REF_LENGTH:
        errors.append(f"INPUT_REF_TOO_LONG:max={MAX_REF_LENGTH}")
    elif _is_absolute_path(input_ref):
        errors.append("INPUT_REF_ABSOLUTE_PATH")

    # Validate proposal_set_ref
    proposal_set_ref = data["proposal_set_ref"]
    if not isinstance(proposal_set_ref, str):
        errors.append("PROPOSAL_SET_REF_NOT_STRING")
    elif len(proposal_set_ref) > MAX_REF_LENGTH:
        errors.append(f"PROPOSAL_SET_REF_TOO_LONG:max={MAX_REF_LENGTH}")
    elif _is_absolute_path(proposal_set_ref):
        errors.append("PROPOSAL_SET_REF_ABSOLUTE_PATH")

    # Validate decision
    if not isinstance(decision, str):
        errors.append("DECISION_NOT_STRING")
    elif decision not in VALID_DECISIONS:
        errors.append(f"INVALID_DECISION:{decision}")
    else:
        # Validate payload exclusivity
        if decision == "ACCEPT":
            if "accept_payload" not in data:
                errors.append("ACCEPT_MISSING_ACCEPT_PAYLOAD")
            else:
                payload_errors = _validate_accept_payload(data["accept_payload"])
                errors.extend(payload_errors)
            if "reject_payload" in data:
                errors.append("ACCEPT_HAS_REJECT_PAYLOAD")
        elif decision == "REJECT":
            if "reject_payload" not in data:
                errors.append("REJECT_MISSING_REJECT_PAYLOAD")
            else:
                payload_errors = _validate_reject_payload(data["reject_payload"])
                errors.extend(payload_errors)
            if "accept_payload" in data:
                errors.append("REJECT_HAS_ACCEPT_PAYLOAD")

    # Validate construction
    construction = data["construction"]
    if not isinstance(construction, dict):
        errors.append("CONSTRUCTION_NOT_OBJECT")
    else:
        construction_errors = _validate_construction(construction)
        errors.extend(construction_errors)

    return len(errors) == 0, errors


def _validate_accept_payload(payload: dict) -> List[str]:
    """Validate accept_payload object."""
    errors = []

    if not isinstance(payload, dict):
        return ["ACCEPT_PAYLOAD_NOT_OBJECT"]

    # Check required fields
    if "kind" not in payload:
        errors.append("ACCEPT_PAYLOAD_MISSING_KIND")
    if "route" not in payload:
        errors.append("ACCEPT_PAYLOAD_MISSING_ROUTE")

    if errors:
        return errors

    # Check no additional properties
    allowed = {"kind", "route"}
    extra = set(payload.keys()) - allowed
    if extra:
        errors.append(f"ACCEPT_PAYLOAD_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate kind
    kind = payload["kind"]
    if not isinstance(kind, str):
        errors.append("ACCEPT_PAYLOAD_KIND_NOT_STRING")
    elif kind not in VALID_ACCEPT_KINDS:
        errors.append(f"ACCEPT_PAYLOAD_INVALID_KIND:{kind}")

    # Validate route
    route = payload["route"]
    if not isinstance(route, dict):
        errors.append("ROUTE_NOT_OBJECT")
    else:
        route_errors = _validate_route(route)
        errors.extend(route_errors)

    return errors


def _validate_route(route: dict) -> List[str]:
    """Validate route object."""
    errors = []

    # Check required fields
    if "intent" not in route:
        errors.append("ROUTE_MISSING_INTENT")
    if "target" not in route:
        errors.append("ROUTE_MISSING_TARGET")

    if errors:
        return errors

    # Check no additional properties
    allowed = {"intent", "target", "mode"}
    extra = set(route.keys()) - allowed
    if extra:
        errors.append(f"ROUTE_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate intent
    intent = route["intent"]
    if not isinstance(intent, str):
        errors.append("ROUTE_INTENT_NOT_STRING")
    elif intent not in VALID_INTENTS:
        errors.append(f"ROUTE_INVALID_INTENT:{intent}")

    # Validate target
    target = route["target"]
    if not isinstance(target, str):
        errors.append("ROUTE_TARGET_NOT_STRING")
    elif target not in VALID_TARGETS:
        errors.append(f"ROUTE_INVALID_TARGET:{target}")

    # Validate mode if present
    if "mode" in route:
        mode = route["mode"]
        if not isinstance(mode, str):
            errors.append("ROUTE_MODE_NOT_STRING")
        elif mode not in VALID_MODES:
            errors.append(f"ROUTE_INVALID_MODE:{mode}")

    return errors


def _validate_reject_payload(payload: dict) -> List[str]:
    """Validate reject_payload object."""
    errors = []

    if not isinstance(payload, dict):
        return ["REJECT_PAYLOAD_NOT_OBJECT"]

    # Check required fields
    if "reason_code" not in payload:
        errors.append("REJECT_PAYLOAD_MISSING_REASON_CODE")
        return errors

    # Check no additional properties
    allowed = {"reason_code", "notes"}
    extra = set(payload.keys()) - allowed
    if extra:
        errors.append(f"REJECT_PAYLOAD_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate reason_code
    reason_code = payload["reason_code"]
    if not isinstance(reason_code, str):
        errors.append("REJECT_PAYLOAD_REASON_CODE_NOT_STRING")
    elif reason_code not in VALID_REASON_CODES:
        errors.append(f"REJECT_PAYLOAD_INVALID_REASON_CODE:{reason_code}")

    # Validate notes if present
    if "notes" in payload:
        notes = payload["notes"]
        if not isinstance(notes, list):
            errors.append("NOTES_NOT_ARRAY")
        else:
            if len(notes) > MAX_NOTES:
                errors.append(f"TOO_MANY_NOTES:max={MAX_NOTES}")
            for i, note in enumerate(notes):
                if not isinstance(note, str):
                    errors.append(f"NOTE_{i}_NOT_STRING")
                elif len(note) > MAX_NOTE_LENGTH:
                    errors.append(f"NOTE_{i}_TOO_LONG:max={MAX_NOTE_LENGTH}")
                elif not NOTE_PATTERN.match(note):
                    errors.append(f"NOTE_{i}_INVALID_PATTERN")

    return errors


def _validate_construction(construction: dict) -> List[str]:
    """Validate construction object."""
    errors = []

    # Check required fields
    if "ruleset_id" not in construction:
        errors.append("CONSTRUCTION_MISSING_RULESET_ID")
    if "proposal_count" not in construction:
        errors.append("CONSTRUCTION_MISSING_PROPOSAL_COUNT")

    if errors:
        return errors

    # Check no additional properties
    allowed = {"ruleset_id", "selected_proposal_index", "proposal_count", "validator_errors"}
    extra = set(construction.keys()) - allowed
    if extra:
        errors.append(f"CONSTRUCTION_UNEXPECTED_FIELDS:{','.join(sorted(extra))}")

    # Validate ruleset_id
    ruleset_id = construction["ruleset_id"]
    if not isinstance(ruleset_id, str):
        errors.append("CONSTRUCTION_RULESET_ID_NOT_STRING")
    elif ruleset_id != RULESET_ID:
        errors.append(f"CONSTRUCTION_INVALID_RULESET_ID:expected={RULESET_ID}")

    # Validate selected_proposal_index if present
    if "selected_proposal_index" in construction:
        idx = construction["selected_proposal_index"]
        if idx is not None:
            if not isinstance(idx, int):
                errors.append("SELECTED_PROPOSAL_INDEX_NOT_INT")
            elif idx < 0 or idx > 7:
                errors.append(f"SELECTED_PROPOSAL_INDEX_OUT_OF_RANGE:{idx}")

    # Validate proposal_count
    proposal_count = construction["proposal_count"]
    if not isinstance(proposal_count, int):
        errors.append("PROPOSAL_COUNT_NOT_INT")
    elif proposal_count < 0 or proposal_count > MAX_PROPOSALS:
        errors.append(f"PROPOSAL_COUNT_OUT_OF_RANGE:{proposal_count}")

    # Validate validator_errors if present
    if "validator_errors" in construction:
        validator_errors = construction["validator_errors"]
        if not isinstance(validator_errors, list):
            errors.append("VALIDATOR_ERRORS_NOT_ARRAY")
        else:
            if len(validator_errors) > MAX_VALIDATOR_ERRORS:
                errors.append(f"TOO_MANY_VALIDATOR_ERRORS:max={MAX_VALIDATOR_ERRORS}")
            for i, err in enumerate(validator_errors):
                if not isinstance(err, str):
                    errors.append(f"VALIDATOR_ERROR_{i}_NOT_STRING")
                elif len(err) > MAX_ERROR_LENGTH:
                    errors.append(f"VALIDATOR_ERROR_{i}_TOO_LONG:max={MAX_ERROR_LENGTH}")

    return errors


if __name__ == "__main__":
    import json
    import sys

    # Read JSON from stdin or file argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    is_valid, errors = validate_artifact(data)

    if is_valid:
        print("VALID")
        sys.exit(0)
    else:
        print("INVALID")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
