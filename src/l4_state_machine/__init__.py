"""
Phase L-4: Deterministic Stateful Workflow - State Machine Module

This module exports the L-4 order processing state machine components.
"""

from .states import (
    OrderState,
    VALID_STATES,
    TERMINAL_STATES,
    INITIAL_STATE,
    DEMO_ORDER_ID,
)

from .events import (
    EventToken,
    VALID_EVENT_TOKENS,
    EVENT_TOKEN_TRANSITIONS,
)

from .transitions import (
    ALLOWED_TRANSITIONS,
    is_valid_transition,
    apply_transition,
    TransitionResult,
)

__all__ = [
    # States
    'OrderState',
    'VALID_STATES',
    'TERMINAL_STATES',
    'INITIAL_STATE',
    'DEMO_ORDER_ID',
    # Events
    'EventToken',
    'VALID_EVENT_TOKENS',
    'EVENT_TOKEN_TRANSITIONS',
    # Transitions
    'ALLOWED_TRANSITIONS',
    'is_valid_transition',
    'apply_transition',
    'TransitionResult',
]
