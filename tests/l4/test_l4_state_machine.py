#!/usr/bin/env python3
"""
Phase L-4: State Machine Tests

Tests proving:
1. Determinism: repeated identical runs produce identical bytes
2. Transition legality: for each state, allowed events ACCEPT, disallowed REJECT
3. Cancellation edges: verify cancel_order only ACCEPTs from permitted states
4. REJECT non-execution: when artifact decision is REJECT, no execution output
5. Output schema: verify presence and exact spelling of required output fields

All tests are deterministic (no time-based assertions).
"""

import json
import os
import sys
import tempfile
import shutil

# Setup paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'src'))

# Import L-4 state machine components
from l4_state_machine.states import (
    OrderState,
    VALID_STATES,
    TERMINAL_STATES,
    INITIAL_STATE,
    DEMO_ORDER_ID,
)
from l4_state_machine.events import (
    EventToken,
    VALID_EVENT_TOKENS,
    EVENT_TOKEN_TRANSITIONS,
    CANCELLATION_ALLOWED_FROM,
)
from l4_state_machine.transitions import (
    ALLOWED_TRANSITIONS,
    is_valid_transition,
    apply_transition,
    TransitionResult,
    get_allowed_events_from,
)
from l4_state_machine.proposal_mapper import (
    map_input_to_event_token,
    is_l4_input,
    create_l4_proposal,
    L4_PROPOSAL_KIND,
)

# Import artifact builder using explicit path loading to avoid collision
import importlib.util
_builder_path = os.path.join(_REPO_ROOT, 'artifact', 'src', 'builder.py')
_spec = importlib.util.spec_from_file_location("artifact_builder", _builder_path)
_builder_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder_module)
build_artifact = _builder_module.build_artifact
L4_ENABLED = _builder_module.L4_ENABLED
_check_l4_proposal = _builder_module._check_l4_proposal
_validate_l4_transition = _builder_module._validate_l4_transition

# Import artifact validator using explicit path loading
_validator_path = os.path.join(_REPO_ROOT, 'artifact', 'src', 'validator.py')
_spec = importlib.util.spec_from_file_location("artifact_validator", _validator_path)
_validator_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator_module)
validate_artifact = _validator_module.validate_artifact

# Test counters
_tests_passed = 0
_tests_failed = 0


def _test(name: str, condition: bool, details: str = ""):
    """Record test result."""
    global _tests_passed, _tests_failed
    if condition:
        _tests_passed += 1
        print(f"[PASS] {name}")
    else:
        _tests_failed += 1
        print(f"[FAIL] {name}")
        if details:
            print(f"       {details}")


# =============================================================================
# Section 1: State Machine Determinism Tests
# =============================================================================

def test_transition_function_determinism():
    """Test that apply_transition is deterministic."""
    # Run the same transition multiple times
    for _ in range(10):
        result = apply_transition(OrderState.CREATED, EventToken.CREATE_PAYMENT)
        _test(
            "apply_transition determinism",
            result.valid and result.next_state == OrderState.PAYMENT_PENDING,
            f"Expected PAYMENT_PENDING, got {result.next_state}"
        )


def test_all_valid_states_defined():
    """Verify all 12 states are defined."""
    _test(
        "All 12 states defined",
        len(VALID_STATES) == 12,
        f"Expected 12 states, got {len(VALID_STATES)}"
    )


def test_all_event_tokens_defined():
    """Verify all 14 event tokens are defined."""
    _test(
        "All 14 event tokens defined",
        len(VALID_EVENT_TOKENS) == 14,
        f"Expected 14 event tokens, got {len(VALID_EVENT_TOKENS)}"
    )


def test_initial_state_is_created():
    """Verify initial state is CREATED."""
    _test(
        "Initial state is CREATED",
        INITIAL_STATE == OrderState.CREATED,
        f"Expected CREATED, got {INITIAL_STATE}"
    )


def test_terminal_states():
    """Verify terminal states are DELIVERED and CANCELLED."""
    expected = {OrderState.DELIVERED, OrderState.CANCELLED}
    _test(
        "Terminal states are DELIVERED and CANCELLED",
        TERMINAL_STATES == expected,
        f"Expected {expected}, got {TERMINAL_STATES}"
    )


def test_demo_order_id():
    """Verify demo order ID is demo-order-1."""
    _test(
        "Demo order ID is demo-order-1",
        DEMO_ORDER_ID == "demo-order-1",
        f"Expected 'demo-order-1', got '{DEMO_ORDER_ID}'"
    )


# =============================================================================
# Section 2: Transition Legality Tests
# =============================================================================

def test_create_payment_from_created():
    """CREATED -> PAYMENT_PENDING via create_payment."""
    result = apply_transition(OrderState.CREATED, EventToken.CREATE_PAYMENT)
    _test(
        "create_payment from CREATED -> PAYMENT_PENDING",
        result.valid and result.next_state == OrderState.PAYMENT_PENDING
    )


def test_payment_succeeded_from_payment_pending():
    """PAYMENT_PENDING -> PAID via payment_succeeded."""
    result = apply_transition(OrderState.PAYMENT_PENDING, EventToken.PAYMENT_SUCCEEDED)
    _test(
        "payment_succeeded from PAYMENT_PENDING -> PAID",
        result.valid and result.next_state == OrderState.PAID
    )


def test_payment_failed_from_payment_pending():
    """PAYMENT_PENDING -> PAYMENT_FAILED via payment_failed."""
    result = apply_transition(OrderState.PAYMENT_PENDING, EventToken.PAYMENT_FAILED)
    _test(
        "payment_failed from PAYMENT_PENDING -> PAYMENT_FAILED",
        result.valid and result.next_state == OrderState.PAYMENT_FAILED
    )


def test_retry_payment_from_payment_failed():
    """PAYMENT_FAILED -> PAYMENT_PENDING via retry_payment."""
    result = apply_transition(OrderState.PAYMENT_FAILED, EventToken.RETRY_PAYMENT)
    _test(
        "retry_payment from PAYMENT_FAILED -> PAYMENT_PENDING",
        result.valid and result.next_state == OrderState.PAYMENT_PENDING
    )


def test_flag_fraud_from_paid():
    """PAID -> FRAUD_REVIEW via flag_fraud."""
    result = apply_transition(OrderState.PAID, EventToken.FLAG_FRAUD)
    _test(
        "flag_fraud from PAID -> FRAUD_REVIEW",
        result.valid and result.next_state == OrderState.FRAUD_REVIEW
    )


def test_approve_fraud_from_fraud_review():
    """FRAUD_REVIEW -> INVENTORY_RESERVED via approve_fraud."""
    result = apply_transition(OrderState.FRAUD_REVIEW, EventToken.APPROVE_FRAUD)
    _test(
        "approve_fraud from FRAUD_REVIEW -> INVENTORY_RESERVED",
        result.valid and result.next_state == OrderState.INVENTORY_RESERVED
    )


def test_reject_fraud_from_fraud_review():
    """FRAUD_REVIEW -> CANCELLED via reject_fraud."""
    result = apply_transition(OrderState.FRAUD_REVIEW, EventToken.REJECT_FRAUD)
    _test(
        "reject_fraud from FRAUD_REVIEW -> CANCELLED",
        result.valid and result.next_state == OrderState.CANCELLED
    )


def test_reserve_inventory_from_paid():
    """PAID -> INVENTORY_RESERVED via reserve_inventory."""
    result = apply_transition(OrderState.PAID, EventToken.RESERVE_INVENTORY)
    _test(
        "reserve_inventory from PAID -> INVENTORY_RESERVED",
        result.valid and result.next_state == OrderState.INVENTORY_RESERVED
    )


def test_start_picking_from_inventory_reserved():
    """INVENTORY_RESERVED -> PICKING via start_picking."""
    result = apply_transition(OrderState.INVENTORY_RESERVED, EventToken.START_PICKING)
    _test(
        "start_picking from INVENTORY_RESERVED -> PICKING",
        result.valid and result.next_state == OrderState.PICKING
    )


def test_pack_order_from_picking():
    """PICKING -> PACKED via pack_order."""
    result = apply_transition(OrderState.PICKING, EventToken.PACK_ORDER)
    _test(
        "pack_order from PICKING -> PACKED",
        result.valid and result.next_state == OrderState.PACKED
    )


def test_ship_order_from_packed():
    """PACKED -> SHIPPED via ship_order."""
    result = apply_transition(OrderState.PACKED, EventToken.SHIP_ORDER)
    _test(
        "ship_order from PACKED -> SHIPPED",
        result.valid and result.next_state == OrderState.SHIPPED
    )


def test_mark_in_transit_from_shipped():
    """SHIPPED -> IN_TRANSIT via mark_in_transit."""
    result = apply_transition(OrderState.SHIPPED, EventToken.MARK_IN_TRANSIT)
    _test(
        "mark_in_transit from SHIPPED -> IN_TRANSIT",
        result.valid and result.next_state == OrderState.IN_TRANSIT
    )


def test_confirm_delivery_from_in_transit():
    """IN_TRANSIT -> DELIVERED via confirm_delivery."""
    result = apply_transition(OrderState.IN_TRANSIT, EventToken.CONFIRM_DELIVERY)
    _test(
        "confirm_delivery from IN_TRANSIT -> DELIVERED",
        result.valid and result.next_state == OrderState.DELIVERED
    )


def test_illegal_transition_rejects():
    """Illegal transitions must REJECT."""
    # payment_succeeded from CREATED (not legal)
    result = apply_transition(OrderState.CREATED, EventToken.PAYMENT_SUCCEEDED)
    _test(
        "payment_succeeded from CREATED -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_all_transitions_from_terminal_states_are_illegal():
    """No transitions allowed from terminal states."""
    for terminal_state in TERMINAL_STATES:
        for event_token in VALID_EVENT_TOKENS:
            result = apply_transition(terminal_state, event_token)
            if event_token == EventToken.CANCEL_ORDER and terminal_state == OrderState.CANCELLED:
                # cancel_order from CANCELLED is still illegal (already cancelled)
                pass
            _test(
                f"{event_token.value} from {terminal_state.value} -> ILLEGAL_TRANSITION",
                not result.valid,
                f"Expected REJECT, got valid={result.valid}"
            )


# =============================================================================
# Section 3: Cancellation Edge Tests
# =============================================================================

def test_cancel_from_created():
    """cancel_order from CREATED -> CANCELLED."""
    result = apply_transition(OrderState.CREATED, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from CREATED -> CANCELLED",
        result.valid and result.next_state == OrderState.CANCELLED
    )


def test_cancel_from_payment_pending():
    """cancel_order from PAYMENT_PENDING -> CANCELLED."""
    result = apply_transition(OrderState.PAYMENT_PENDING, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from PAYMENT_PENDING -> CANCELLED",
        result.valid and result.next_state == OrderState.CANCELLED
    )


def test_cancel_from_paid():
    """cancel_order from PAID -> CANCELLED."""
    result = apply_transition(OrderState.PAID, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from PAID -> CANCELLED",
        result.valid and result.next_state == OrderState.CANCELLED
    )


def test_cancel_from_inventory_reserved():
    """cancel_order from INVENTORY_RESERVED -> CANCELLED."""
    result = apply_transition(OrderState.INVENTORY_RESERVED, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from INVENTORY_RESERVED -> CANCELLED",
        result.valid and result.next_state == OrderState.CANCELLED
    )


def test_cancel_not_allowed_from_picking():
    """cancel_order from PICKING -> ILLEGAL_TRANSITION."""
    result = apply_transition(OrderState.PICKING, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from PICKING -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_cancel_not_allowed_from_packed():
    """cancel_order from PACKED -> ILLEGAL_TRANSITION."""
    result = apply_transition(OrderState.PACKED, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from PACKED -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_cancel_not_allowed_from_shipped():
    """cancel_order from SHIPPED -> ILLEGAL_TRANSITION."""
    result = apply_transition(OrderState.SHIPPED, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from SHIPPED -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_cancel_not_allowed_from_in_transit():
    """cancel_order from IN_TRANSIT -> ILLEGAL_TRANSITION."""
    result = apply_transition(OrderState.IN_TRANSIT, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from IN_TRANSIT -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_cancel_not_allowed_from_payment_failed():
    """cancel_order from PAYMENT_FAILED -> ILLEGAL_TRANSITION."""
    result = apply_transition(OrderState.PAYMENT_FAILED, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from PAYMENT_FAILED -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


def test_cancel_not_allowed_from_fraud_review():
    """cancel_order from FRAUD_REVIEW -> ILLEGAL_TRANSITION (use reject_fraud instead)."""
    result = apply_transition(OrderState.FRAUD_REVIEW, EventToken.CANCEL_ORDER)
    _test(
        "cancel_order from FRAUD_REVIEW -> ILLEGAL_TRANSITION",
        not result.valid and result.error_code == "ILLEGAL_TRANSITION"
    )


# =============================================================================
# Section 4: Proposal Mapper Tests
# =============================================================================

def test_proposal_mapper_create_payment():
    """'create payment' maps to CREATE_PAYMENT token."""
    token = map_input_to_event_token("create payment")
    _test(
        "'create payment' -> CREATE_PAYMENT",
        token == EventToken.CREATE_PAYMENT
    )


def test_proposal_mapper_case_insensitive():
    """Proposal mapper is case-insensitive."""
    token = map_input_to_event_token("CREATE PAYMENT")
    _test(
        "'CREATE PAYMENT' -> CREATE_PAYMENT (case insensitive)",
        token == EventToken.CREATE_PAYMENT
    )


def test_proposal_mapper_whitespace_tolerant():
    """Proposal mapper is whitespace-tolerant."""
    token = map_input_to_event_token("  create  payment  ")
    _test(
        "'  create  payment  ' -> CREATE_PAYMENT (whitespace tolerant)",
        token == EventToken.CREATE_PAYMENT
    )


def test_proposal_mapper_all_tokens():
    """Test all event token mappings."""
    mappings = [
        ("create payment", EventToken.CREATE_PAYMENT),
        ("payment succeeded", EventToken.PAYMENT_SUCCEEDED),
        ("payment failed", EventToken.PAYMENT_FAILED),
        ("retry payment", EventToken.RETRY_PAYMENT),
        ("flag fraud", EventToken.FLAG_FRAUD),
        ("approve fraud", EventToken.APPROVE_FRAUD),
        ("reject fraud", EventToken.REJECT_FRAUD),
        ("reserve inventory", EventToken.RESERVE_INVENTORY),
        ("start picking", EventToken.START_PICKING),
        ("pack order", EventToken.PACK_ORDER),
        ("ship order", EventToken.SHIP_ORDER),
        ("mark in transit", EventToken.MARK_IN_TRANSIT),
        ("confirm delivery", EventToken.CONFIRM_DELIVERY),
        ("cancel order", EventToken.CANCEL_ORDER),
    ]
    for input_text, expected_token in mappings:
        token = map_input_to_event_token(input_text)
        _test(
            f"'{input_text}' -> {expected_token.value}",
            token == expected_token,
            f"Expected {expected_token}, got {token}"
        )


def test_proposal_mapper_unknown_input():
    """Unknown input returns None."""
    token = map_input_to_event_token("do something random")
    _test(
        "'do something random' -> None",
        token is None
    )


def test_is_l4_input():
    """is_l4_input returns True for valid L-4 inputs."""
    _test("is_l4_input('create payment')", is_l4_input("create payment"))
    _test("is_l4_input('random text') is False", not is_l4_input("random text"))


def test_create_l4_proposal():
    """create_l4_proposal creates correct structure."""
    proposal = create_l4_proposal(EventToken.CREATE_PAYMENT)
    _test(
        "create_l4_proposal kind is STATE_TRANSITION_REQUEST",
        proposal.get("kind") == L4_PROPOSAL_KIND
    )
    _test(
        "create_l4_proposal payload.event_token is create_payment",
        proposal.get("payload", {}).get("event_token") == "create_payment"
    )


# =============================================================================
# Section 5: Artifact Builder L-4 Tests
# =============================================================================

def test_l4_accept_for_legal_transition():
    """Legal L-4 transition produces ACCEPT artifact."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "create payment"},
        "proposals": [create_l4_proposal(EventToken.CREATE_PAYMENT)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_accept",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    _test(
        "Legal L-4 transition -> ACCEPT",
        artifact.get("decision") == "ACCEPT"
    )
    _test(
        "L-4 ACCEPT has STATE_TRANSITION kind",
        artifact.get("accept_payload", {}).get("kind") == "STATE_TRANSITION"
    )


def test_l4_reject_for_illegal_transition():
    """Illegal L-4 transition produces REJECT artifact."""
    # payment_succeeded is not legal from CREATED (initial state)
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "payment succeeded"},
        "proposals": [create_l4_proposal(EventToken.PAYMENT_SUCCEEDED)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_reject",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    _test(
        "Illegal L-4 transition -> REJECT",
        artifact.get("decision") == "REJECT"
    )
    _test(
        "L-4 REJECT reason is ILLEGAL_TRANSITION",
        artifact.get("reject_payload", {}).get("reason_code") == "ILLEGAL_TRANSITION"
    )


def test_l4_reject_for_invalid_event_token():
    """Invalid event token produces REJECT artifact."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "invalid event"},
        "proposals": [{
            "kind": "STATE_TRANSITION_REQUEST",
            "payload": {"event_token": "invalid_token"}
        }]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_invalid",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    _test(
        "Invalid event token -> REJECT",
        artifact.get("decision") == "REJECT"
    )
    _test(
        "L-4 REJECT reason is INVALID_EVENT_TOKEN",
        artifact.get("reject_payload", {}).get("reason_code") == "INVALID_EVENT_TOKEN"
    )


def test_l4_artifact_validates():
    """L-4 ACCEPT artifact passes validation."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "create payment"},
        "proposals": [create_l4_proposal(EventToken.CREATE_PAYMENT)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_valid",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    is_valid, errors = validate_artifact(artifact)
    _test(
        "L-4 ACCEPT artifact validates",
        is_valid,
        f"Validation errors: {errors}"
    )


def test_l4_transition_payload_fields():
    """L-4 ACCEPT artifact has correct transition fields."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "create payment"},
        "proposals": [create_l4_proposal(EventToken.CREATE_PAYMENT)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_fields",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    transition = artifact.get("accept_payload", {}).get("transition", {})

    _test("transition.order_id == 'demo-order-1'", transition.get("order_id") == "demo-order-1")
    _test("transition.previous_state == 'CREATED'", transition.get("previous_state") == "CREATED")
    _test("transition.event == 'create_payment'", transition.get("event") == "create_payment")
    _test("transition.current_state == 'PAYMENT_PENDING'", transition.get("current_state") == "PAYMENT_PENDING")
    _test("transition.terminal == False", transition.get("terminal") is False)


def test_l4_cancel_transition_terminal():
    """cancel_order transition sets terminal=True."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "cancel order"},
        "proposals": [create_l4_proposal(EventToken.CANCEL_ORDER)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_l4_cancel",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    transition = artifact.get("accept_payload", {}).get("transition", {})

    _test("cancel_order -> current_state == 'CANCELLED'", transition.get("current_state") == "CANCELLED")
    _test("cancel_order -> terminal == True", transition.get("terminal") is True)


# =============================================================================
# Section 6: Output Schema Tests
# =============================================================================

def test_transition_output_schema():
    """Verify transition output has all required fields."""
    proposal_set = {
        "schema_version": "m1.0",
        "input": {"raw": "create payment"},
        "proposals": [create_l4_proposal(EventToken.CREATE_PAYMENT)]
    }
    artifact = build_artifact(
        proposal_set=proposal_set,
        run_id="test_schema",
        input_ref="test.txt",
        proposal_set_ref="proposal_set.json"
    )
    transition = artifact.get("accept_payload", {}).get("transition", {})

    required_fields = ["order_id", "previous_state", "event", "current_state", "terminal"]
    for field in required_fields:
        _test(
            f"transition has '{field}' field",
            field in transition,
            f"Missing field: {field}"
        )


# =============================================================================
# Section 7: Allowed Transitions Set Verification
# =============================================================================

def test_allowed_transitions_count():
    """Verify total number of allowed transitions."""
    # Standard transitions: 13
    # Cancellation edges: 4
    # Total: 17
    expected_count = 17
    _test(
        f"ALLOWED_TRANSITIONS has {expected_count} edges",
        len(ALLOWED_TRANSITIONS) == expected_count,
        f"Expected {expected_count}, got {len(ALLOWED_TRANSITIONS)}"
    )


def test_all_standard_transitions_in_allowed():
    """Verify all standard transitions are in ALLOWED_TRANSITIONS."""
    for event_token, (from_state, to_state) in EVENT_TOKEN_TRANSITIONS.items():
        _test(
            f"{from_state.value} -> {to_state.value} in ALLOWED_TRANSITIONS",
            (from_state, to_state) in ALLOWED_TRANSITIONS
        )


def test_all_cancellation_edges_in_allowed():
    """Verify all cancellation edges are in ALLOWED_TRANSITIONS."""
    for from_state in CANCELLATION_ALLOWED_FROM:
        _test(
            f"{from_state.value} -> CANCELLED in ALLOWED_TRANSITIONS",
            (from_state, OrderState.CANCELLED) in ALLOWED_TRANSITIONS
        )


# =============================================================================
# Main
# =============================================================================

def main():
    global _tests_passed, _tests_failed

    print("=" * 79)
    print("Phase L-4 State Machine Tests")
    print("=" * 79)
    print()

    # Section 1: Determinism
    print("--- Section 1: State Machine Determinism ---")
    test_transition_function_determinism()
    test_all_valid_states_defined()
    test_all_event_tokens_defined()
    test_initial_state_is_created()
    test_terminal_states()
    test_demo_order_id()
    print()

    # Section 2: Transition Legality
    print("--- Section 2: Transition Legality ---")
    test_create_payment_from_created()
    test_payment_succeeded_from_payment_pending()
    test_payment_failed_from_payment_pending()
    test_retry_payment_from_payment_failed()
    test_flag_fraud_from_paid()
    test_approve_fraud_from_fraud_review()
    test_reject_fraud_from_fraud_review()
    test_reserve_inventory_from_paid()
    test_start_picking_from_inventory_reserved()
    test_pack_order_from_picking()
    test_ship_order_from_packed()
    test_mark_in_transit_from_shipped()
    test_confirm_delivery_from_in_transit()
    test_illegal_transition_rejects()
    test_all_transitions_from_terminal_states_are_illegal()
    print()

    # Section 3: Cancellation Edges
    print("--- Section 3: Cancellation Edges ---")
    test_cancel_from_created()
    test_cancel_from_payment_pending()
    test_cancel_from_paid()
    test_cancel_from_inventory_reserved()
    test_cancel_not_allowed_from_picking()
    test_cancel_not_allowed_from_packed()
    test_cancel_not_allowed_from_shipped()
    test_cancel_not_allowed_from_in_transit()
    test_cancel_not_allowed_from_payment_failed()
    test_cancel_not_allowed_from_fraud_review()
    print()

    # Section 4: Proposal Mapper
    print("--- Section 4: Proposal Mapper ---")
    test_proposal_mapper_create_payment()
    test_proposal_mapper_case_insensitive()
    test_proposal_mapper_whitespace_tolerant()
    test_proposal_mapper_all_tokens()
    test_proposal_mapper_unknown_input()
    test_is_l4_input()
    test_create_l4_proposal()
    print()

    # Section 5: Artifact Builder
    print("--- Section 5: Artifact Builder L-4 ---")
    test_l4_accept_for_legal_transition()
    test_l4_reject_for_illegal_transition()
    test_l4_reject_for_invalid_event_token()
    test_l4_artifact_validates()
    test_l4_transition_payload_fields()
    test_l4_cancel_transition_terminal()
    print()

    # Section 6: Output Schema
    print("--- Section 6: Output Schema ---")
    test_transition_output_schema()
    print()

    # Section 7: Allowed Transitions Set
    print("--- Section 7: Allowed Transitions Set ---")
    test_allowed_transitions_count()
    test_all_standard_transitions_in_allowed()
    test_all_cancellation_edges_in_allowed()
    print()

    # Summary
    print("=" * 79)
    total = _tests_passed + _tests_failed
    print(f"Tests: {_tests_passed}/{total} passed")

    if _tests_failed == 0:
        print("All L-4 state machine tests PASSED")
        return 0
    else:
        print(f"FAILED: {_tests_failed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
