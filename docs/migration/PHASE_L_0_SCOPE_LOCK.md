# Phase L-0: LLM Proposal Engine Integration — Scope Lock

## 1. Phase Identity

| Attribute | Value |
|-----------|-------|
| Phase | L-0 |
| Phase Name | LLM Proposal Engine Integration: Scope Lock & Authority Preservation |
| Repository | `brok-clu-demo` |
| Reference Tag | `brok-demo-v1` |
| Phase Type | Documentation-only governance phase |
| Prerequisite | M-0 through M-4 closed and immutable |

This phase establishes binding governance constraints for integrating a probabilistic (LLM-based) proposal engine into the Brok CLI demo. No implementation occurs in L-0; only binding contracts are defined.

---

## 2. Canonical Context (Immutable, Binding)

### 2.1 Closed Phases

The following phases are closed and immutable:

| Phase | Status | Scope |
|-------|--------|-------|
| M-0 | CLOSED | Authority contracts, scope lock |
| M-1 | CLOSED | Explicit Proposal Layer |
| M-2 | CLOSED | Artifact Layer with deterministic ruleset |
| M-3 | CLOSED | Single canonical entrypoint, execution gating |
| M-4 | CLOSED | Derived observability (non-authoritative) |

**No changes to M-0..M-4 artifacts, semantics, or contracts are permitted.**

### 2.2 Canonical CLI Surface

The single canonical CLI invocation is:

```
./brok --input <file>
```

This surface is frozen. No additional flags, arguments, or modes may be introduced.

### 2.3 Reference Baseline

All L-phase work references tag `brok-demo-v1` as the frozen baseline. Any deviation from this baseline's behavior (other than the allowed proposal generator swap) constitutes a violation.

---

## 3. Frozen Architecture Snapshot

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BROK CLI PIPELINE                              │
│                         (Feedforward Only — No Feedback)                    │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │  RAW INPUT   │  User-provided file via --input
     │   (bytes)    │
     └──────┬───────┘
            │
            ▼
┌───────────────────────────────────────┐
│         PROPOSAL LAYER                │  ◄─── INTEGRATION POINT (L-phase)
│   (derived, non-authoritative)        │
│                                       │
│   acquire_proposal_set(bytes) → bytes │
│                                       │
│   • May be deterministic or           │
│     probabilistic                     │
│   • Owns ZERO authority               │
│   • May fail arbitrarily              │
│   • Failures collapse to empty bytes  │
└───────────────────────────────────────┘
            │
            │ ProposalSet bytes (opaque)
            ▼
┌───────────────────────────────────────┐
│         ARTIFACT LAYER                │
│   (authoritative wrapper decision)    │
│                                       │
│   • Deterministic validation          │
│   • Count-based ambiguity handling    │
│   • Produces ACCEPT or REJECT         │
│   • artifact.json = decision record   │
└───────────────────────────────────────┘
            │
            │ ACCEPT only
            ▼
┌───────────────────────────────────────┐
│         EXECUTION LAYER               │
│   (sealed, deterministic runtime)     │
│                                       │
│   • Executes artifacts exactly        │
│   • No inference, no interpretation   │
│   • stdout.raw.kv = sole authority    │
└───────────────────────────────────────┘
            │
            ▼
     ┌──────────────┐
     │ stdout.raw.kv│  SOLE AUTHORITATIVE RUNTIME OUTPUT
     └──────────────┘
```

**Data flow is feedforward only. No feedback edges exist or may be introduced.**

---

## 4. Integration Scope (Allowed Change)

### 4.1 Permitted

The L-phase integration permits exactly one structural change:

> **Swap the proposal generator behind the fixed seam.**

The seam signature is frozen:

```python
acquire_proposal_set(raw_input_bytes: bytes) -> bytes
```

A probabilistic inference engine (e.g., LLM) may be bound behind this seam to generate ProposalSet bytes. The binding occurs at packaging time, not runtime.

### 4.2 Seam Properties (Invariant)

- Exactly one call per run
- No retries within a single run
- No feedback from downstream layers
- No side effects beyond returning bytes
- Any exception collapses to empty bytes
- Harness cannot distinguish error from empty output

### 4.3 Downstream Unchanged

Everything downstream of the seam remains frozen:

- Artifact validation logic
- ACCEPT/REJECT decision rules
- Execution gating (ACCEPT-only)
- Exit codes (REJECT = 0, not error)
- stdout.raw.kv handling
- Observability contracts

---

## 5. Explicit Non-Goals (Hard Prohibitions)

The following are explicitly forbidden in L-phase work:

| Prohibition | Rationale |
|-------------|-----------|
| Scoring, ranking, or confidence metrics | Authority is binary (ACCEPT/REJECT) |
| Retries, self-correction, or feedback loops | Seam is single-call, no iteration |
| New CLI flags or arguments | CLI surface is frozen |
| Runtime engine selection toggles | Binding is packaging-level only |
| Environment variable behavior switches | No runtime configuration |
| Semantic interpretation of stdout.raw.kv | Wrapper must not parse authoritative output |
| Optimization to increase ACCEPT rate | REJECT is a valid, expected outcome |
| Quality metrics or success thresholds | Non-authoritative; must not affect behavior |
| Production readiness claims | Demo remains bounded demonstration |
| Agent, planner, or optimizer patterns | System is feedforward pipeline, not agent |

---

## 6. Acceptance Criteria (For L-0 Closure)

Phase L-0 is complete when:

1. **Binding documents exist**: This document, `LLM_INTEGRATION_CONTRACT.md`, and `L_0_BINDING_CONSTRAINTS.md` are committed.

2. **Zero ambiguity**: Future implementation can proceed mechanically with no authority debates or scope negotiations.

3. **Regression criteria defined**: Clear, testable conditions for detecting violations.

4. **Forbidden changes enumerated**: Explicit list prevents scope creep.

5. **No code changes**: L-0 is documentation-only; no implementation artifacts.

---

## 7. Final Binding Statement

**Probabilistic inference may be introduced upstream of the artifact layer.**

The following remain absolutely fixed:

- Authority is downstream (artifact decision, execution output)
- Execution enforces authority; it never creates it
- The seam is the sole integration point
- REJECT is a valid, correct outcome
- The CLI surface is `./brok --input <file>` only
- stdout.raw.kv is the sole authoritative runtime truth

Any implementation that violates these constraints is non-compliant regardless of perceived utility.

---

## Document Control

| Attribute | Value |
|-----------|-------|
| Status | BINDING |
| Phase | L-0 |
| Supersedes | None |
| Amended By | None (immutable after closure) |
