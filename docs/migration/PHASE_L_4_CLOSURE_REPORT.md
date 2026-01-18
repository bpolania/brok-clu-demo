# Phase L-4: Deterministic Stateful Workflow Demonstration - Closure Report

## Summary

Phase L-4 implements a deterministic stateful workflow demonstration using a frozen
order processing state machine. On ACCEPT, execution applies exactly one transition
and emits structured authoritative output via stdout.raw.kv.

**Key Properties:**
- 12 frozen states, 17 allowed transitions
- Initial state fixed to CREATED
- Single canonical order: demo-order-1
- Deterministic: same input produces byte-identical output
- No persistence across runs

---

## File-by-File Change List

### New Files

| File | Description |
|------|-------------|
| `src/l4_state_machine/__init__.py` | L-4 module exports |
| `src/l4_state_machine/states.py` | Frozen state definitions (12 states) |
| `src/l4_state_machine/events.py` | Frozen event token definitions (14 tokens) |
| `src/l4_state_machine/transitions.py` | Deterministic transition function |
| `src/l4_state_machine/proposal_mapper.py` | Input to event token mapping |
| `tests/l4/__init__.py` | L-4 tests package |
| `tests/l4/test_l4_state_machine.py` | 126 tests for L-4 functionality |
| `inputs/l4/create_payment.txt` | ACCEPT demo input |
| `inputs/l4/cancel_order.txt` | Terminal state demo input |
| `inputs/l4/illegal_payment_succeeded.txt` | REJECT demo input |
| `docs/migration/PHASE_L_4_SCOPE_LOCK.md` | L-4 scope constraints |
| `docs/migration/evidence/l4/accept_run.txt` | ACCEPT evidence |
| `docs/migration/evidence/l4/reject_run.txt` | REJECT evidence |
| `docs/migration/evidence/l4/terminal_state_run.txt` | Terminal state evidence |
| `docs/migration/evidence/l4/determinism_proof.txt` | Determinism evidence |
| `docs/migration/evidence/l4/test_results.txt` | Test results |

### Modified Files

| File | Change |
|------|--------|
| `src/artifact_layer/llm_engine.py` | Added L-4 demo trigger and proposal generation |
| `artifact/src/builder.py` | Added L-4 state machine gate and STATE_TRANSITION artifacts |
| `artifact/src/validator.py` | Added STATE_TRANSITION validation and L-4 reason codes |
| `proposal/src/validator.py` | Added STATE_TRANSITION_REQUEST kind |
| `m3/src/gateway.py` | Added L-4 execution path for STATE_TRANSITION artifacts |

---

## Authority Boundaries Preserved

| Layer | Authority | Preserved |
|-------|-----------|-----------|
| Proposal (LLM) | Non-authoritative | YES - only maps input to event tokens |
| L-4 State Machine Gate | Authoritative | YES - `builder.py:_validate_l4_transition()` |
| Artifact Builder | Authoritative | YES - sole ACCEPT/REJECT decision maker |
| Execution | Sealed, deterministic | YES - only applies validated transitions |
| stdout.raw.kv | Authoritative output | YES - sole execution truth |

The proposal layer does NOT validate transition legality. It only maps input text
to event tokens. The artifact layer's `_validate_l4_transition()` function is
the AUTHORITATIVE gate that checks transitions against the frozen state machine.

---

## Exact Event Tokens (14 Total)

| Event Token | Transition |
|-------------|------------|
| create_payment | CREATED → PAYMENT_PENDING |
| payment_succeeded | PAYMENT_PENDING → PAID |
| payment_failed | PAYMENT_PENDING → PAYMENT_FAILED |
| retry_payment | PAYMENT_FAILED → PAYMENT_PENDING |
| flag_fraud | PAID → FRAUD_REVIEW |
| approve_fraud | FRAUD_REVIEW → INVENTORY_RESERVED |
| reject_fraud | FRAUD_REVIEW → CANCELLED |
| reserve_inventory | PAID → INVENTORY_RESERVED |
| start_picking | INVENTORY_RESERVED → PICKING |
| pack_order | PICKING → PACKED |
| ship_order | PACKED → SHIPPED |
| mark_in_transit | SHIPPED → IN_TRANSIT |
| confirm_delivery | IN_TRANSIT → DELIVERED |
| cancel_order | CREATED\|PAYMENT_PENDING\|PAID\|INVENTORY_RESERVED → CANCELLED |

---

## Transition Table (17 Edges)

### Standard Transitions (13)

```
CREATED -> PAYMENT_PENDING (create_payment)
PAYMENT_PENDING -> PAID (payment_succeeded)
PAYMENT_PENDING -> PAYMENT_FAILED (payment_failed)
PAYMENT_FAILED -> PAYMENT_PENDING (retry_payment)
PAID -> FRAUD_REVIEW (flag_fraud)
PAID -> INVENTORY_RESERVED (reserve_inventory)
FRAUD_REVIEW -> INVENTORY_RESERVED (approve_fraud)
FRAUD_REVIEW -> CANCELLED (reject_fraud)
INVENTORY_RESERVED -> PICKING (start_picking)
PICKING -> PACKED (pack_order)
PACKED -> SHIPPED (ship_order)
SHIPPED -> IN_TRANSIT (mark_in_transit)
IN_TRANSIT -> DELIVERED (confirm_delivery)
```

### Cancellation Edges (4)

```
CREATED -> CANCELLED (cancel_order)
PAYMENT_PENDING -> CANCELLED (cancel_order)
PAID -> CANCELLED (cancel_order)
INVENTORY_RESERVED -> CANCELLED (cancel_order)
```

---

## Test Commands and Results

### L-4 State Machine Tests

```bash
python3 tests/l4/test_l4_state_machine.py
```

**Result: 126/126 tests PASSED**

Test coverage:
- State machine determinism
- Transition legality for all states
- Cancellation edge verification
- Proposal mapper functionality
- Artifact builder L-4 handling
- Output schema validation
- Allowed transitions set verification

### Existing Tests (Regression)

```bash
python3 tests/l3/test_l3_acceptance.py
python3 artifact/tests/test_artifact_builder.py
python3 m3/tests/test_invariants.py
```

**All existing tests PASS**

---

## Evidence Artifacts

| Path | Description |
|------|-------------|
| `docs/migration/evidence/l4/accept_run.txt` | ACCEPT run: create_payment |
| `docs/migration/evidence/l4/reject_run.txt` | REJECT run: ILLEGAL_TRANSITION |
| `docs/migration/evidence/l4/terminal_state_run.txt` | Terminal state: cancel_order |
| `docs/migration/evidence/l4/determinism_proof.txt` | SHA-256 hash comparison |
| `docs/migration/evidence/l4/test_results.txt` | Full test output |

---

## Verification Checklist

| Requirement | Status |
|-------------|--------|
| Public CLI surface unchanged | PASS |
| No new flags, config files, or invocation forms | PASS |
| Proposal layer remains derived and non-authoritative | PASS |
| Artifact layer is sole ACCEPT/REJECT authority | PASS |
| Execution only runs on ACCEPT | PASS |
| State is explicit, finite, and non-persistent | PASS |
| Transition table matches frozen list (17 edges) | PASS |
| Authoritative output via stdout.raw.kv only | PASS |
| All tests pass | PASS |

---

## Deviations from Prompt

**None.**

All requirements from the implementation prompt were followed exactly:
- Hard stops and boundaries respected
- No L-5 scaffolding
- No new CLI surfaces
- No persistence, configuration, concurrency, retries, or external I/O
- Authority model preserved
- Frozen M-0..M-4 and L-0..L-3 contracts unchanged
- Transition table matches frozen specification
- All REJECT reason codes implemented
- Tests prove determinism, legality, cancellation, non-execution, and schema

---

## Conclusion

Phase L-4 is complete. The deterministic stateful workflow demonstration:
- Implements a 12-state, 17-transition frozen order processing state machine
- Preserves strict authority boundaries
- Produces deterministic, structured authoritative output
- Passes all 126 L-4 tests and all existing regression tests

**This is a demonstration, not a production system.**
