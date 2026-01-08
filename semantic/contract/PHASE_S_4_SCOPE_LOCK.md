# Phase S-4: Integrated Product Demo Planning — Scope Lock

**Status:** LOCKED
**Type:** Documentation and composition only

---

## 1. Purpose

Phase S-4 composes existing frozen phases into a single coherent product demo surface.

This phase adds documentation and framing. It does not add functionality, modify behavior, or introduce new guarantees.

---

## 2. What S-4 Builds

| Deliverable | Type | Purpose |
|-------------|------|---------|
| `INTEGRATED_PRODUCT_DEMO.md` | Documentation | Primary entrypoint presenting unified demo |
| `INTEGRATED_WALKTHROUGH.md` | Documentation | Linear copy/paste command sequence |
| `PHASE_S_4_SCOPE_LOCK.md` | Contract | This file |
| `PHASE_S_4_PLACEHOLDER.md` | Phase tracking | Status reference |
| Navigation updates | Links | Point existing docs to integrated demo |

All deliverables are markdown documentation. No scripts, no logic, no artifacts.

---

## 3. What S-4 Does NOT Build

Phase S-4 explicitly does NOT:

| Non-Goal | Rationale |
|----------|-----------|
| Modify PoC v2 bundle | Runtime is frozen |
| Modify verification/execution scripts | Behavior is frozen |
| Add semantic tolerance or normalization | Violates S-0 contract |
| Add new comparison logic | Violates S-0 contract |
| Claim semantic correctness | Violates S-0 contract |
| Hide or soften divergence | Violates S-0 contract |
| Merge authoritative and derived outputs | Violates output separation |
| Re-interpret earlier phase results | Phases are frozen |
| Add new executable functionality | Documentation only |

---

## 4. Binding Definitions

### Authority

**`stdout.raw.kv`** is the only authoritative output.

- Produced by PoC v2
- Captured verbatim
- Byte-for-byte preserved
- No normalization or inference

### Derived

All other outputs are **DERIVED (semantic)**:

- Semantic suite summaries
- Regression reports
- Execution indexes
- Comparison matrices
- This documentation

Derived outputs are observational and non-authoritative.

### Determinism

**Byte-for-byte equality.**

Given identical:
- Verification state (passed)
- Input file content

The output file `stdout.raw.kv` is byte-identical.

### Regression

**Byte-level change.**

If `sha256(baseline.stdout.raw.kv) != sha256(current.stdout.raw.kv)`, the result is REGRESSION.

No interpretation. No tolerance. No semantic analysis.

---

## 5. No Reinterpretation

Phase S-4 does NOT:

- Alter definitions from S-0
- Reevaluate results from S-1, S-2, or S-3
- Weaken any constraints
- Add new claims
- Override existing classifications

Earlier phases are frozen. S-4 presents them as-is.

---

## 6. Constraints Inherited from S-0

All S-0 constraints apply to S-4:

| Constraint | Status |
|------------|--------|
| PoC v2 is the only executable authority | Inherited |
| stdout.raw.kv is the only authoritative output | Inherited |
| Verification mandatory before execution | Inherited |
| Determinism is byte-for-byte | Inherited |
| No semantic tolerance/normalization/equivalence | Inherited |
| No claims of semantic correctness | Inherited |
| Divergence shown openly | Inherited |

---

## 7. Layer Boundary Labels

S-4 documentation must use consistent labels:

| Output Type | Label | Example |
|-------------|-------|---------|
| Runtime output | `AUTHORITATIVE (runtime)` | `stdout.raw.kv` |
| Semantic views | `DERIVED (semantic)` | Summaries, indexes, reports |
| Regression artifacts | `DERIVED (semantic)` | Comparison results, matrices |

These labels must appear in all integrated documentation.

---

## 8. Disclaimer Requirements

Each integrated document must include:

> **Disclaimer**: Runtime guarantees apply only to execution and byte-level equality. Semantic material is observational and non-authoritative.

---

## 9. Contract Reference

This phase operates under: **[Phase S-0: Scope Lock & Contract Definition](PHASE_S_0_SCOPE_LOCK.md)**

All S-0 constraints remain binding and non-negotiable.

---

*Phase S-4: Integrated Product Demo Planning*
*Semantic Capability Layer — brok-clu-runtime-demo*
