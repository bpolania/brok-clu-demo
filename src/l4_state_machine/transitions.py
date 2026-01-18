"""
Phase L-4: State Transition Function (Pure, Deterministic)

This module defines the deterministic transition function for L-4.
The function is PURE: no I/O, no randomness, no time, no external dependencies.

Constraints:
- Transition table exactly matches the frozen specification
- Function returns next_state or indicates invalid transition
- No side effects
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple, Set
from .states import OrderState, TERMINAL_STATES
from .events import EventToken, EVENT_TOKEN_TRANSITIONS, CANCELLATION_ALLOWED_FROM


@dataclass(frozen=True)
class TransitionResult:
    """
    Result of a transition attempt.

    Attributes:
        valid: Whether the transition is legal
        next_state: The resulting state if valid, None otherwise
        error_code: Error code if invalid, None otherwise
    """
    valid: bool
    next_state: Optional[OrderState]
    error_code: Optional[str]


# Complete allowed transitions set: (from_state, to_state)
# Built from EVENT_TOKEN_TRANSITIONS plus cancellation edges
ALLOWED_TRANSITIONS: FrozenSet[Tuple[OrderState, OrderState]] = frozenset([
    # Standard transitions from EVENT_TOKEN_TRANSITIONS
    (OrderState.CREATED, OrderState.PAYMENT_PENDING),
    (OrderState.PAYMENT_PENDING, OrderState.PAID),
    (OrderState.PAYMENT_PENDING, OrderState.PAYMENT_FAILED),
    (OrderState.PAYMENT_FAILED, OrderState.PAYMENT_PENDING),
    (OrderState.PAID, OrderState.FRAUD_REVIEW),
    (OrderState.PAID, OrderState.INVENTORY_RESERVED),
    (OrderState.FRAUD_REVIEW, OrderState.INVENTORY_RESERVED),
    (OrderState.FRAUD_REVIEW, OrderState.CANCELLED),
    (OrderState.INVENTORY_RESERVED, OrderState.PICKING),
    (OrderState.PICKING, OrderState.PACKED),
    (OrderState.PACKED, OrderState.SHIPPED),
    (OrderState.SHIPPED, OrderState.IN_TRANSIT),
    (OrderState.IN_TRANSIT, OrderState.DELIVERED),
    # Cancellation edges
    (OrderState.CREATED, OrderState.CANCELLED),
    (OrderState.PAYMENT_PENDING, OrderState.CANCELLED),
    (OrderState.PAID, OrderState.CANCELLED),
    (OrderState.INVENTORY_RESERVED, OrderState.CANCELLED),
])


def is_valid_transition(from_state: OrderState, to_state: OrderState) -> bool:
    """
    Check if a state transition is allowed.

    Args:
        from_state: Current state
        to_state: Target state

    Returns:
        True if (from_state, to_state) is in ALLOWED_TRANSITIONS.
    """
    return (from_state, to_state) in ALLOWED_TRANSITIONS


def apply_transition(
    current_state: OrderState,
    event_token: EventToken
) -> TransitionResult:
    """
    Apply a state transition (pure, deterministic).

    This function determines whether the transition is legal and,
    if so, returns the next state.

    Args:
        current_state: The current order state
        event_token: The event token to apply

    Returns:
        TransitionResult indicating success/failure and next state.

    Error codes:
        INVALID_EVENT_TOKEN: event_token not in closed set
        ILLEGAL_TRANSITION: event_token recognized but not allowed from current_state
        INVALID_CURRENT_STATE: current_state not in valid states (totality guard)
    """
    # Guard: Validate current_state is in valid set
    try:
        if not isinstance(current_state, OrderState):
            return TransitionResult(
                valid=False,
                next_state=None,
                error_code="INVALID_CURRENT_STATE"
            )
    except Exception:
        return TransitionResult(
            valid=False,
            next_state=None,
            error_code="INVALID_CURRENT_STATE"
        )

    # Guard: Validate event_token is in valid set
    try:
        if not isinstance(event_token, EventToken):
            return TransitionResult(
                valid=False,
                next_state=None,
                error_code="INVALID_EVENT_TOKEN"
            )
    except Exception:
        return TransitionResult(
            valid=False,
            next_state=None,
            error_code="INVALID_EVENT_TOKEN"
        )

    # Handle cancel_order specially (multiple allowed from_states)
    if event_token == EventToken.CANCEL_ORDER:
        if current_state in CANCELLATION_ALLOWED_FROM:
            return TransitionResult(
                valid=True,
                next_state=OrderState.CANCELLED,
                error_code=None
            )
        else:
            return TransitionResult(
                valid=False,
                next_state=None,
                error_code="ILLEGAL_TRANSITION"
            )

    # Standard event tokens
    if event_token not in EVENT_TOKEN_TRANSITIONS:
        # Should not happen if EventToken enum is complete
        return TransitionResult(
            valid=False,
            next_state=None,
            error_code="INVALID_EVENT_TOKEN"
        )

    expected_from, next_state = EVENT_TOKEN_TRANSITIONS[event_token]

    if current_state != expected_from:
        return TransitionResult(
            valid=False,
            next_state=None,
            error_code="ILLEGAL_TRANSITION"
        )

    return TransitionResult(
        valid=True,
        next_state=next_state,
        error_code=None
    )


def get_allowed_events_from(state: OrderState) -> Set[EventToken]:
    """
    Get all event tokens that are valid from a given state.

    This is a utility function for testing and documentation.

    Args:
        state: The current state

    Returns:
        Set of EventToken values that can be applied from this state.
    """
    allowed = set()

    # Check standard transitions
    for event_token, (from_state, _) in EVENT_TOKEN_TRANSITIONS.items():
        if from_state == state:
            allowed.add(event_token)

    # Check cancellation
    if state in CANCELLATION_ALLOWED_FROM:
        allowed.add(EventToken.CANCEL_ORDER)

    return allowed
