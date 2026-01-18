# LLM Integration Contract

## Purpose

This document defines the binding contract for integrating an LLM-based proposal engine into the Brok CLI demo. The contract specifies the seam interface, behavioral constraints, and prohibited patterns.

**This contract is immutable after L-0 closure.**

---

## 1. Frozen Seam Definition

### 1.1 Signature

```python
acquire_proposal_set(raw_input_bytes: bytes) -> bytes
```

### 1.2 Semantics

| Aspect | Specification |
|--------|---------------|
| Input | Opaque bytes from user-provided input file |
| Output | Opaque bytes representing ProposalSet (may be empty) |
| Call Count | Exactly one call per CLI invocation |
| Exceptions | Must not escape; collapse to empty bytes |
| Side Effects | None permitted |
| Return Type | Must be `bytes`; non-bytes returns collapse to empty |

### 1.3 Binding Level

Engine binding occurs at **packaging time**, not runtime. The shipped artifact contains exactly one bound engine. There is no runtime selection mechanism.

---

## 2. Seam Properties (Binding)

### 2.1 Single-Call Invariant

The seam is called exactly once per run. The following are forbidden:

- Retries on failure
- Multiple calls with varied parameters
- Iterative refinement loops
- Feedback from downstream validation

### 2.2 No Downstream Access

The engine behind the seam:

- Cannot read artifact layer state
- Cannot read execution layer state
- Cannot read previous run state
- Cannot access stdout.raw.kv
- Cannot influence downstream decisions except via returned bytes

### 2.3 Failure Collapse

All failures collapse to empty bytes:

| Condition | Result |
|-----------|--------|
| Engine is None | `b""` |
| Engine raises any exception | `b""` |
| Engine returns non-bytes type | `b""` |
| Engine succeeds | Engine output bytes |

The harness cannot distinguish error from intentionally empty output. This is by design.

### 2.4 Non-Authoritative

Proposal output is **derived and non-authoritative**:

- Proposals do not determine execution outcomes
- Proposals do not modify authority boundaries
- Proposals are untrusted input to the artifact layer
- The artifact layer decides ACCEPT/REJECT independent of proposal metadata

---

## 3. Allowed Output Space

The seam may return any byte sequence:

| Output Type | Permitted | Downstream Behavior |
|-------------|-----------|---------------------|
| Empty bytes | Yes | Deterministically collapses to REJECT |
| Malformed JSON | Yes | Deterministically collapses to REJECT |
| Valid but irrelevant proposals | Yes | Deterministically collapses to REJECT |
| Ambiguous (multiple) proposals | Yes | Deterministically collapses to REJECT |
| Single valid conformant proposal | Yes | May result in ACCEPT |
| Variable output across runs | Yes | Each run evaluated independently |

No part of the system may "help" proposals succeed. The artifact layer applies frozen rules without interpretation.

---

## 4. Failure Semantics

### 4.1 Exit Code Behavior (Unchanged)

| Outcome | Exit Code |
|---------|-----------|
| ACCEPT (execution succeeds) | 0 |
| REJECT (valid outcome) | 0 |
| CLI usage error | Non-zero |
| Internal operational failure | Non-zero |

**REJECT is not an error.** It is a valid, expected outcome that exits cleanly with code 0.

### 4.2 Authoritative Output on REJECT

On REJECT:

- No execution occurs
- No authoritative runtime output is produced
- stdout.raw.kv is not written (or is empty)
- Observability may emit derived records (non-authoritative)

### 4.3 No Recovery Attempts

The system does not:

- Retry on REJECT
- Prompt for clarification
- Attempt repair or normalization
- Log "suggestions" for improvement

REJECT is final for that invocation.

---

## 5. Determinism Boundary

### 5.1 Proposal Layer (May Be Probabilistic)

The proposal engine may exhibit non-deterministic behavior:

- Different outputs for identical inputs across runs
- Model sampling variation
- Temperature-based randomness
- Any other stochastic behavior

This is permitted because proposals are non-authoritative.

### 5.2 Artifact Layer (Must Be Deterministic)

Given identical ProposalSet bytes:

- Validation produces identical results
- ACCEPT/REJECT decision is identical
- Artifact content is byte-for-byte identical

### 5.3 Execution Layer (Must Be Deterministic)

Given identical artifact:

- Execution produces identical stdout.raw.kv
- No variation permitted

### 5.4 Boundary Location

```
PROBABILISTIC (permitted)     DETERMINISTIC (required)
         │                            │
         ▼                            ▼
    ┌─────────┐                 ┌───────────┐
    │ Proposal│ ──ProposalSet──▶│ Artifact  │──▶ Execution
    │  Layer  │     bytes       │  Layer    │
    └─────────┘                 └───────────┘
                                      │
                               BOUNDARY HERE
```

---

## 6. Prohibited Enhancements

The following patterns are explicitly forbidden:

### 6.1 Quality Optimization

- Scoring proposals
- Ranking candidates
- Confidence thresholds
- "Best effort" selection
- Success rate optimization

### 6.2 Iteration Patterns

- Retry on failure
- Self-correction loops
- Refinement passes
- Multi-turn generation

### 6.3 Runtime Configuration

- Engine selection flags
- Environment variable toggles
- Configuration files
- Feature flags

### 6.4 Downstream Influence

- Reading execution results
- Modifying artifact rules
- Adjusting based on history
- Learning from outcomes

### 6.5 Authority Violation

- Emitting confidence to downstream
- Adding metadata that influences decisions
- Creating side channels
- Parsing stdout.raw.kv

---

## 7. Compliance Verification

An implementation is compliant if and only if:

1. The seam signature matches exactly
2. The seam is called exactly once per run
3. No exceptions escape the seam boundary
4. No runtime engine selection exists
5. No retry logic exists
6. No feedback from downstream exists
7. REJECT exits with code 0
8. stdout.raw.kv is not parsed by wrapper
9. Observability (if present) is derived and inert

---

## Document Control

| Attribute | Value |
|-----------|-------|
| Status | BINDING |
| Phase | L-0 |
| Companion Documents | PHASE_L_0_SCOPE_LOCK.md, L_0_BINDING_CONSTRAINTS.md |
