# Phase L-3: Single-Envelope Controlled Acceptance - Scope Lock

## Purpose

This document defines the scope constraints and governing rules for Phase L-3.
L-3 demonstrates controlled acceptance through a **single explicitly enumerated
ACCEPT envelope**. Schema-valid alternatives REJECT.

## Critical Clarifications

### What L-3 Is

L-3 is a **demonstration** of the wrapper architecture's ability to gate
execution through an explicitly enumerated acceptance envelope:

1. ACCEPT occurs **only** when proposal matches the L-3 envelope EXACTLY
2. Schema-valid alternatives are intentionally REJECTED
3. Execution proceeds only through the artifact-validated path
4. The artifact builder is the sole ACCEPT/REJECT authority

### What L-3 Is NOT

L-3 is **NOT**:

- A production-ready system
- Evidence that "AI decides to run things"
- A general-purpose LLM integration
- An endorsement of autonomous execution
- An acceptance of all schema-valid proposals

The LLM output remains **non-authoritative**. The artifact validation layer
is the sole ACCEPT/REJECT gate.

## L-3 Single ACCEPT Envelope (Authoritative)

**The authoritative ACCEPT/REJECT decision is made by the artifact builder
(`artifact/src/builder.py`) using the L-3 envelope gate.**

The L-3 envelope gate accepts **exactly ONE explicitly enumerated proposal**:

```
L-3 ACCEPT Envelope:
  - kind == "ROUTE_CANDIDATE"
  - payload.intent == "STATUS_QUERY"
  - payload.slots == {"target": "alpha"}  # No mode, no extra keys
```

| Condition | Decision | Reason Code |
|-----------|----------|-------------|
| 0 proposals | REJECT | NO_PROPOSALS |
| 1 proposal matching L-3 envelope | ACCEPT | — |
| 1 proposal NOT matching L-3 envelope | REJECT | L3_ENVELOPE_MISMATCH |
| 2+ proposals | REJECT | AMBIGUOUS_PROPOSALS |
| Invalid proposal | REJECT | INVALID_PROPOSALS |

### Schema-Valid Alternatives REJECT

The following are schema-valid but intentionally REJECTED:

| Proposal | Reason |
|----------|--------|
| STATUS_QUERY target=beta | Wrong target |
| STATUS_QUERY target=gamma | Wrong target |
| STOP_SUBSYSTEM target=alpha | Wrong intent |
| RESTART_SUBSYSTEM target=alpha | Wrong intent |
| STATUS_QUERY target=alpha mode=graceful | Extra key in slots |

This is intentional. L-3 demonstrates that the wrapper can restrict acceptance
to an explicitly enumerated subset of schema-valid proposals.

## Proposal Engine Demo Convenience

The proposal engine (`src/artifact_layer/llm_engine.py`) includes a demo
convenience that emits a valid proposal when input matches the demo file.
This is **NOT** part of the authoritative acceptance predicate.

| Component | Authority |
|-----------|-----------|
| Proposal engine demo check | NON-AUTHORITATIVE (convenience) |
| L-3 Envelope Gate | AUTHORITATIVE |
| Artifact builder decision | AUTHORITATIVE |

## What L-3 Does NOT Do

- Does NOT add new intents (uses existing closed domain)
- Does NOT add new CLI flags or commands
- Does NOT add runtime configuration
- Does NOT add environment variable behavior
- Does NOT add retries, feedback loops, or multi-attempt inference
- Does NOT modify frozen validators
- Does NOT change execution semantics
- Does NOT interpret execution output
- Does NOT add new authoritative outputs
- Does NOT accept all schema-valid proposals (single envelope only)

## Authority Model

| Layer | Authority | Location |
|-------|-----------|----------|
| Proposal (LLM) | Non-authoritative | `src/artifact_layer/llm_engine.py` |
| L-3 Envelope Gate | AUTHORITATIVE | `artifact/src/builder.py:_check_l3_envelope()` |
| Artifact Builder | AUTHORITATIVE | `artifact/src/builder.py:build_artifact()` |
| Execution | Sealed, deterministic | `poc_v2.py` |
| stdout.raw.kv | Only authoritative output | Runtime |

## Determinism Guarantees

| Given | Result |
|-------|--------|
| Same ProposalSet bytes | Same ACCEPT/REJECT decision |
| Same artifact | Same execution outcome |

## REJECT Behavior

REJECT remains a clean, exit-0 outcome. REJECT is:

- Normal and expected for proposals outside the L-3 envelope
- Not an error condition
- Not a failure

## Verification Requirements

Before L-3 closure:

1. Exact L-3 envelope → ACCEPT → execution occurs
2. Schema-valid alternatives → REJECT (L3_ENVELOPE_MISMATCH)
3. CLI surface unchanged (`./brok --input <file>` only)
4. Artifact validators unchanged
5. Determinism verified
6. stdout.raw.kv present for ACCEPT runs

## Files Changed in L-3

| File | Change |
|------|--------|
| `artifact/src/builder.py` | Added L-3 envelope gate (AUTHORITATIVE) |
| `src/artifact_layer/llm_engine.py` | Updated docs (NON-AUTHORITATIVE) |
| `inputs/l3_accept_demo.txt` | Demo input file |
| `tests/l3/test_l3_acceptance.py` | 17 tests for single-envelope contract |
| `docs/migration/PHASE_L_3_SCOPE_LOCK.md` | This document |
| `docs/migration/PHASE_L_3_CLOSURE_REPORT.md` | Closure report |
| Evidence files in `docs/migration/evidence/l3/` | Test evidence |

## Non-Goals

- Accepting all schema-valid proposals
- Modifying frozen validators
- Adding new CLI flags
- Adding runtime configuration
- Creating a production-ready system
