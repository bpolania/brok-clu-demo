# Phase L-4: Deterministic Stateful Workflow Demonstration - Scope Lock

## Purpose

This document defines the scope constraints and governing rules for Phase L-4.
L-4 demonstrates a deterministic stateful workflow using a frozen order processing
state machine. On ACCEPT, execution applies exactly one transition and emits
structured authoritative output via stdout.raw.kv.

## Critical Clarifications

### What L-4 Is

L-4 is a **demonstration** of the wrapper architecture's ability to:

1. Validate state transitions against a frozen state machine
2. ACCEPT only legal transitions from the fixed initial state (CREATED)
3. Produce deterministic, structured execution output
4. Maintain strict authority boundaries (artifact layer decides, execution applies)

### What L-4 Is NOT

L-4 is **NOT**:

- A production-ready order management system
- A multi-order or multi-run persistent system
- Evidence that "AI decides state transitions"
- An endorsement of autonomous state management
- A system with configurable state or transitions

The LLM output remains **non-authoritative**. The artifact validation layer
is the sole ACCEPT/REJECT gate.

## Frozen State Machine

### States (Closed Set, 12 Total)

| State | Description |
|-------|-------------|
| CREATED | Order created, initial state |
| PAYMENT_PENDING | Awaiting payment |
| PAYMENT_FAILED | Payment attempt failed |
| PAID | Payment received |
| FRAUD_REVIEW | Under fraud investigation |
| INVENTORY_RESERVED | Stock allocated |
| PICKING | Order being picked |
| PACKED | Order packed |
| SHIPPED | Handed to carrier |
| IN_TRANSIT | In delivery |
| DELIVERED | Delivered (terminal) |
| CANCELLED | Cancelled (terminal) |

### Terminal States

- DELIVERED
- CANCELLED

No further transitions allowed from terminal states.

### Fixed Demo Parameters

| Parameter | Value |
|-----------|-------|
| Initial State | CREATED |
| Order ID | "demo-order-1" |

## Allowed Transitions (Closed Set, 17 Edges)

### Standard Transitions (13)

| From State | Event Token | To State |
|------------|-------------|----------|
| CREATED | create_payment | PAYMENT_PENDING |
| PAYMENT_PENDING | payment_succeeded | PAID |
| PAYMENT_PENDING | payment_failed | PAYMENT_FAILED |
| PAYMENT_FAILED | retry_payment | PAYMENT_PENDING |
| PAID | flag_fraud | FRAUD_REVIEW |
| PAID | reserve_inventory | INVENTORY_RESERVED |
| FRAUD_REVIEW | approve_fraud | INVENTORY_RESERVED |
| FRAUD_REVIEW | reject_fraud | CANCELLED |
| INVENTORY_RESERVED | start_picking | PICKING |
| PICKING | pack_order | PACKED |
| PACKED | ship_order | SHIPPED |
| SHIPPED | mark_in_transit | IN_TRANSIT |
| IN_TRANSIT | confirm_delivery | DELIVERED |

### Cancellation Edges (4)

| From State | Event Token | To State |
|------------|-------------|----------|
| CREATED | cancel_order | CANCELLED |
| PAYMENT_PENDING | cancel_order | CANCELLED |
| PAID | cancel_order | CANCELLED |
| INVENTORY_RESERVED | cancel_order | CANCELLED |

## Event Tokens (Closed Set, 14 Total)

| Event Token | Description |
|-------------|-------------|
| create_payment | Initiate payment |
| payment_succeeded | Payment confirmed |
| payment_failed | Payment failed |
| retry_payment | Retry failed payment |
| flag_fraud | Flag for fraud review |
| approve_fraud | Clear fraud review |
| reject_fraud | Cancel due to fraud |
| reserve_inventory | Reserve stock |
| start_picking | Begin order picking |
| pack_order | Pack the order |
| ship_order | Ship the order |
| mark_in_transit | Mark as in transit |
| confirm_delivery | Confirm delivery |
| cancel_order | Cancel the order |

## REJECT Reason Codes (L-4 Specific)

| Reason Code | Description |
|-------------|-------------|
| INVALID_EVENT_TOKEN | Event token not in closed set |
| ILLEGAL_TRANSITION | Event token recognized but not legal from current state |
| INVALID_CURRENT_STATE | Totality guard (should not occur normally) |

## Authority Model

| Layer | Authority | Location |
|-------|-----------|----------|
| Proposal (LLM) | Non-authoritative | `src/artifact_layer/llm_engine.py` |
| L-4 State Machine Gate | AUTHORITATIVE | `artifact/src/builder.py` |
| Artifact Builder | AUTHORITATIVE | `artifact/src/builder.py` |
| Execution | Sealed, deterministic | `m3/src/gateway.py` |
| stdout.raw.kv | Only authoritative output | Runtime |

## Authoritative Execution Output

On ACCEPT, execution emits stdout.raw.kv with:

```
order_id=demo-order-1
previous_state=CREATED
event=<event_token>
current_state=<next_state>
terminal=<true|false>
```

Output is:
- Deterministic (byte-identical for identical inputs)
- Canonically serialized (stable key ordering)
- The sole authoritative execution output

## What L-4 Does NOT Do

- Does NOT add new CLI flags or commands
- Does NOT add persistence across runs
- Does NOT add multiple orders
- Does NOT add configuration files
- Does NOT add concurrency or retries
- Does NOT add clocks or timestamps in output
- Does NOT add randomness
- Does NOT add external I/O or network access
- Does NOT modify frozen M-0..M-4 or L-0..L-3 contracts

## Determinism Guarantees

| Given | Result |
|-------|--------|
| Same input text | Same event token mapping |
| Same ProposalSet bytes | Same ACCEPT/REJECT decision |
| Same ACCEPT artifact | Same stdout.raw.kv output |

## Verification Requirements

Before L-4 closure:

1. CLI surface unchanged (`./brok --input <file>` only)
2. Legal transitions from CREATED ACCEPT
3. Illegal transitions REJECT with appropriate reason code
4. Cancellation edges verified
5. Determinism verified
6. stdout.raw.kv present for ACCEPT runs with correct fields
7. All existing tests pass

## Files Changed in L-4

| File | Change |
|------|--------|
| `src/l4_state_machine/states.py` | Frozen state definitions |
| `src/l4_state_machine/events.py` | Frozen event token definitions |
| `src/l4_state_machine/transitions.py` | Deterministic transition function |
| `src/l4_state_machine/proposal_mapper.py` | Input to event token mapping |
| `src/artifact_layer/llm_engine.py` | L-4 proposal generation |
| `artifact/src/builder.py` | L-4 state machine gate |
| `artifact/src/validator.py` | L-4 artifact validation |
| `proposal/src/validator.py` | STATE_TRANSITION_REQUEST kind |
| `m3/src/gateway.py` | L-4 execution path |
| `tests/l4/test_l4_state_machine.py` | L-4 test suite |

## Non-Goals

- Multi-order support
- Persistence across runs
- Runtime configuration
- Production-ready system
- Modifying frozen invariants

## Document Control

| Attribute | Value |
|-----------|-------|
| Status | BINDING |
| Phase | L-4 |
| Supersedes | None |
| Amended By | None (immutable after closure) |
