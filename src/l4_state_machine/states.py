"""
Phase L-4: Order Processing States (Frozen, Closed Set)

This module defines the frozen set of order processing states for L-4.
These states are immutable and form a closed domain.

Constraints:
- States are exactly one enum value from the frozen set
- No extra counters, timestamps, or metadata
- State exists only within a single run (no persistence)
- Initial state is fixed: CREATED
- One canonical order instance: "demo-order-1"
"""

from enum import Enum
from typing import FrozenSet


class OrderState(str, Enum):
    """
    Frozen set of order processing states.

    This enum is CLOSED and IMMUTABLE for L-4.
    All valid states are explicitly enumerated.
    """
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAID = "PAID"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# Frozen set of all valid states
VALID_STATES: FrozenSet[OrderState] = frozenset(OrderState)

# Terminal states (no further transitions allowed)
TERMINAL_STATES: FrozenSet[OrderState] = frozenset([
    OrderState.DELIVERED,
    OrderState.CANCELLED,
])

# Fixed initial state for L-4 demo
INITIAL_STATE: OrderState = OrderState.CREATED

# Fixed order ID for L-4 demo (single order instance)
DEMO_ORDER_ID: str = "demo-order-1"
