"""
Phase L-4: Event Tokens (Frozen, Closed Set)

This module defines the frozen set of event tokens for L-4.
Each event token maps to exactly one state transition edge.

Constraints:
- Event tokens are string constants
- The set is CLOSED and IMMUTABLE
- Each token corresponds to exactly one (from_state, to_state) edge
- cancel_order is allowed from multiple states (special case)
"""

from enum import Enum
from typing import FrozenSet, Dict, Tuple
from .states import OrderState


class EventToken(str, Enum):
    """
    Frozen set of event tokens.

    This enum is CLOSED and IMMUTABLE for L-4.
    All valid event tokens are explicitly enumerated.
    """
    # Payment flow
    CREATE_PAYMENT = "create_payment"           # CREATED -> PAYMENT_PENDING
    PAYMENT_SUCCEEDED = "payment_succeeded"     # PAYMENT_PENDING -> PAID
    PAYMENT_FAILED = "payment_failed"           # PAYMENT_PENDING -> PAYMENT_FAILED
    RETRY_PAYMENT = "retry_payment"             # PAYMENT_FAILED -> PAYMENT_PENDING

    # Fraud review flow
    FLAG_FRAUD = "flag_fraud"                   # PAID -> FRAUD_REVIEW
    APPROVE_FRAUD = "approve_fraud"             # FRAUD_REVIEW -> INVENTORY_RESERVED
    REJECT_FRAUD = "reject_fraud"               # FRAUD_REVIEW -> CANCELLED

    # Fulfillment flow
    RESERVE_INVENTORY = "reserve_inventory"     # PAID -> INVENTORY_RESERVED
    START_PICKING = "start_picking"             # INVENTORY_RESERVED -> PICKING
    PACK_ORDER = "pack_order"                   # PICKING -> PACKED
    SHIP_ORDER = "ship_order"                   # PACKED -> SHIPPED
    MARK_IN_TRANSIT = "mark_in_transit"         # SHIPPED -> IN_TRANSIT
    CONFIRM_DELIVERY = "confirm_delivery"       # IN_TRANSIT -> DELIVERED

    # Cancellation (multi-source)
    CANCEL_ORDER = "cancel_order"               # CREATED|PAYMENT_PENDING|PAID|INVENTORY_RESERVED -> CANCELLED


# Frozen set of all valid event tokens
VALID_EVENT_TOKENS: FrozenSet[EventToken] = frozenset(EventToken)


# Mapping from event token to its allowed (from_state, to_state) transitions
# cancel_order has multiple allowed from_states, handled separately
EVENT_TOKEN_TRANSITIONS: Dict[EventToken, Tuple[OrderState, OrderState]] = {
    EventToken.CREATE_PAYMENT: (OrderState.CREATED, OrderState.PAYMENT_PENDING),
    EventToken.PAYMENT_SUCCEEDED: (OrderState.PAYMENT_PENDING, OrderState.PAID),
    EventToken.PAYMENT_FAILED: (OrderState.PAYMENT_PENDING, OrderState.PAYMENT_FAILED),
    EventToken.RETRY_PAYMENT: (OrderState.PAYMENT_FAILED, OrderState.PAYMENT_PENDING),
    EventToken.FLAG_FRAUD: (OrderState.PAID, OrderState.FRAUD_REVIEW),
    EventToken.APPROVE_FRAUD: (OrderState.FRAUD_REVIEW, OrderState.INVENTORY_RESERVED),
    EventToken.REJECT_FRAUD: (OrderState.FRAUD_REVIEW, OrderState.CANCELLED),
    EventToken.RESERVE_INVENTORY: (OrderState.PAID, OrderState.INVENTORY_RESERVED),
    EventToken.START_PICKING: (OrderState.INVENTORY_RESERVED, OrderState.PICKING),
    EventToken.PACK_ORDER: (OrderState.PICKING, OrderState.PACKED),
    EventToken.SHIP_ORDER: (OrderState.PACKED, OrderState.SHIPPED),
    EventToken.MARK_IN_TRANSIT: (OrderState.SHIPPED, OrderState.IN_TRANSIT),
    EventToken.CONFIRM_DELIVERY: (OrderState.IN_TRANSIT, OrderState.DELIVERED),
    # cancel_order is special - see CANCELLATION_ALLOWED_FROM
}

# States from which cancel_order is allowed
CANCELLATION_ALLOWED_FROM: FrozenSet[OrderState] = frozenset([
    OrderState.CREATED,
    OrderState.PAYMENT_PENDING,
    OrderState.PAID,
    OrderState.INVENTORY_RESERVED,
])
