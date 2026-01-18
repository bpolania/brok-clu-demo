"""
Phase L-4: Proposal to Event Token Mapper (Derived, Non-Authoritative)

This module maps natural language input to L-4 event tokens.
The mapping is:
- Closed-set: only recognizes frozen event vocabulary
- Deterministic: same input always produces same event token
- Non-authoritative: does NOT encode transition legality

The mapper produces derived proposals. The artifact layer is sole
authority for ACCEPT/REJECT decisions based on state machine rules.

Constraints:
- No I/O
- No randomness
- No time dependencies
- No external dependencies
- Must NOT validate transition legality (that's artifact layer's job)
"""

import re
from typing import Optional, Tuple
from .events import EventToken


# Closed-set mapping from input patterns to event tokens
# Patterns are case-insensitive and whitespace-tolerant
# Each pattern maps to exactly one EventToken

L4_EVENT_PATTERNS: list[Tuple[re.Pattern, EventToken]] = [
    # Payment flow
    (re.compile(r'^\s*create\s+payment\s*$', re.IGNORECASE), EventToken.CREATE_PAYMENT),
    (re.compile(r'^\s*payment\s+succeeded\s*$', re.IGNORECASE), EventToken.PAYMENT_SUCCEEDED),
    (re.compile(r'^\s*payment\s+failed\s*$', re.IGNORECASE), EventToken.PAYMENT_FAILED),
    (re.compile(r'^\s*retry\s+payment\s*$', re.IGNORECASE), EventToken.RETRY_PAYMENT),

    # Fraud review flow
    (re.compile(r'^\s*flag\s+fraud\s*$', re.IGNORECASE), EventToken.FLAG_FRAUD),
    (re.compile(r'^\s*approve\s+fraud\s*$', re.IGNORECASE), EventToken.APPROVE_FRAUD),
    (re.compile(r'^\s*reject\s+fraud\s*$', re.IGNORECASE), EventToken.REJECT_FRAUD),

    # Fulfillment flow
    (re.compile(r'^\s*reserve\s+inventory\s*$', re.IGNORECASE), EventToken.RESERVE_INVENTORY),
    (re.compile(r'^\s*start\s+picking\s*$', re.IGNORECASE), EventToken.START_PICKING),
    (re.compile(r'^\s*pack\s+order\s*$', re.IGNORECASE), EventToken.PACK_ORDER),
    (re.compile(r'^\s*ship\s+order\s*$', re.IGNORECASE), EventToken.SHIP_ORDER),
    (re.compile(r'^\s*mark\s+in\s+transit\s*$', re.IGNORECASE), EventToken.MARK_IN_TRANSIT),
    (re.compile(r'^\s*confirm\s+delivery\s*$', re.IGNORECASE), EventToken.CONFIRM_DELIVERY),

    # Cancellation
    (re.compile(r'^\s*cancel\s+order\s*$', re.IGNORECASE), EventToken.CANCEL_ORDER),
]


def map_input_to_event_token(input_text: str) -> Optional[EventToken]:
    """
    Map input text to an L-4 event token.

    This is a DERIVED, NON-AUTHORITATIVE mapping.
    It does NOT validate whether the transition is legal from
    any particular state. That is the artifact layer's responsibility.

    Args:
        input_text: Raw input string from user

    Returns:
        EventToken if input matches a known pattern, None otherwise.
    """
    for pattern, event_token in L4_EVENT_PATTERNS:
        if pattern.match(input_text):
            return event_token
    return None


def is_l4_input(input_text: str) -> bool:
    """
    Check if input text is an L-4 event trigger.

    Args:
        input_text: Raw input string

    Returns:
        True if input matches any L-4 event pattern.
    """
    return map_input_to_event_token(input_text) is not None


# Proposal kind for L-4 state transition proposals
L4_PROPOSAL_KIND = "STATE_TRANSITION_REQUEST"


def create_l4_proposal(event_token: EventToken) -> dict:
    """
    Create an L-4 proposal from an event token.

    The proposal has a specific structure that the artifact layer
    will validate against the state machine.

    Args:
        event_token: The mapped event token

    Returns:
        Proposal dict with L-4 structure.
    """
    return {
        "kind": L4_PROPOSAL_KIND,
        "payload": {
            "event_token": event_token.value,
        }
    }
