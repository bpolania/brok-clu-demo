# Phase M-0: Scope Lock

## 1. Phase Identity

| Property | Value |
|----------|-------|
| Phase | M-0 |
| Repository | brok-clu-runtime-demo |
| Type | Planning and contract-definition only |
| Binding | For Phase M-1 and all subsequent phases |

This document defines the authority model, layer boundaries, and constraints that govern all migration phases. This scope lock must not be reinterpreted by any future phase.

---

## 2. Fixed Truth Assumptions

The following conditions are fixed and must be treated as invariant:

1. The repository is public and cleaned
2. PoC v2 is complete and frozen on the `main` branch
3. S-phase (Semantic Capability Layer) tooling is derived and non-authoritative
4. The following components are immutable and must not be modified:

### Immutable Components

| Component | Path |
|-----------|------|
| PoC v2 bundle | `vendor/poc_v2/poc_v2.tar.gz` |
| Vendor checksum | `vendor/poc_v2/SHA256SUMS.vendor` |
| Provenance record | `vendor/poc_v2/PROVENANCE.txt` |
| Verification script | `scripts/verify_poc_v2.sh` |
| Execution script | `scripts/run_poc_v2.sh` |
| Determinism test | `scripts/determinism_test_v2.sh` |

---

## 3. Prohibited Actions

The following actions are forbidden in all migration phases:

| Prohibition | Rationale |
|-------------|-----------|
| Modification to PoC v2 bundle | Runtime authority is sealed |
| Weakening of verification | Trust boundary must not degrade |
| Reinterpretation of runtime output | Output semantics are fixed |
| Creation of new execution authority | Authority flows from artifacts, not inference |
| Changes to determinism test pass criteria | Determinism definition is fixed |
| Changes to CLI flags for existing scripts | Interface stability required |

---

## 4. Authority Model Contract

### 4.1 Where Authority Exists

| Location | Authority Type |
|----------|----------------|
| `stdout.raw.kv` | Sole authoritative execution output |
| Artifact layer | Wrapper decision authority (ACCEPT/REJECT) |
| `vendor/poc_v2/` | Sealed runtime definition |

### 4.2 Where Authority Does Not Exist

| Location | Status |
|----------|--------|
| Proposal layer | Non-authoritative; advisory only |
| Semantic Capability Layer outputs | Derived; non-authoritative |
| Log files, metadata, diagnostics | Derived; non-authoritative |

### 4.3 Authority Flow

```
artifact (decision record) → execution (runtime) → stdout.raw.kv (truth)
```

Authority flows unidirectionally from decision to execution to output. No reverse flow is permitted.

### 4.4 Fundamental Rule

**Execution enforces authority, it never creates it.**

The runtime executes what artifacts specify. The runtime does not generate decisions, interpret intent, or extend authority beyond what is explicitly encoded in artifacts.

---

## 5. Layer Definitions

### 5.1 Proposal Layer

| Property | Value |
|----------|-------|
| Authority | None (non-authoritative) |
| Output | Zero or more proposals |
| Side effects | Forbidden |
| Binding | Proposals do not bind the artifact layer |

The proposal layer may emit suggestions. It must not emit side effects. It must not assume proposals will be accepted. An empty proposal set is valid.

### 5.2 Artifact Layer

| Property | Value |
|----------|-------|
| Authority | Sole wrapper decision authority |
| Decision space | Finite and enumerable |
| Decision values | ACCEPT or REJECT (explicit) |
| Record | Sealed and auditable |
| Construction | Deterministic rules only |

The artifact layer records explicit decisions. Each decision must be ACCEPT or REJECT. No implicit decisions, probabilistic outcomes, or deferred evaluation are permitted. The decision record must be auditable and reproducible given the same inputs and rules.

### 5.3 Execution Layer

| Property | Value |
|----------|-------|
| Authority | Executes artifacts exactly |
| Inference | Forbidden |
| Output | `stdout.raw.kv` (authoritative) |
| Determinism | Byte-for-byte identical on identical inputs |

The execution layer must not interpret, infer, or extend what artifacts specify. It executes deterministically. The only authoritative output is `stdout.raw.kv`.

---

## 6. Non-Goals

The following are explicitly excluded from migration scope:

| Non-Goal | Explanation |
|----------|-------------|
| LLM integration | No language models in the execution path |
| Semantic correctness claims | Runtime does not validate meaning |
| Fallback heuristics | No best-effort or degraded modes |
| Changes to determinism tests | Test semantics are fixed |
| Changes to PoC v2 runtime behavior | Runtime is sealed |
| Changes to CLI flags for existing scripts | Interface is stable |

---

## 7. Output Authority Rules

### 7.1 Authoritative Output

`stdout.raw.kv` is the sole authoritative execution output.

### 7.2 Derived Outputs

All other outputs are derived or metadata:

| Output Type | Status |
|-------------|--------|
| Log files | Derived |
| Diagnostic messages | Derived |
| Timing information | Derived |
| Artifact records | Decision records (not execution outcomes) |

### 7.3 Override Prohibition

Proposals and artifacts do not override runtime output. The artifact layer records wrapper decisions. The execution layer produces authoritative output. These are distinct.

### 7.4 Artifact Scope

Artifacts record decisions, not outcomes. An artifact records that a decision was made (ACCEPT or REJECT). The outcome of execution is recorded only in `stdout.raw.kv`.

---

## 8. Repository Constraints

### 8.1 Generated Output Location

All generated outputs must reside under `artifacts/` or existing evidence conventions already present in the repository.

### 8.2 Gitignore Policy

The following must be gitignored:

| Pattern | Rationale |
|---------|-----------|
| `artifacts/` | Generated outputs are ephemeral |
| `artifacts/exec_bundle/` | PoC v2 extraction during execution |
| `artifacts/poc_v2_extracted/` | PoC v2 extraction during verification |
| `semantic/regression/runs/` | Semantic regression test outputs |
| `semantic/artifacts/` | Semantic layer generated artifacts |

### 8.3 Commit Prohibition

The following must never be committed:

| Item | Rationale |
|------|-----------|
| Generated `stdout.raw.kv` files | Execution output, not source |
| Temporary extraction artifacts | Ephemeral state |
| Environment-specific paths | Relocatability violation |

### 8.4 Relocatability Requirements

| Requirement | Constraint |
|-------------|------------|
| Absolute paths | Forbidden in committed files |
| Environment variables for paths | Forbidden in committed logic |
| Path assumptions | Repository root only |

All path references in committed files must be relative to repository root. No absolute paths. No environment variable path dependencies.

---

## 9. Acceptance Criteria

Phase M-0 is complete when:

1. **M-1 Readiness**: Phase M-1 can design a proposal generator without debating authority boundaries or modifying runtime behavior
2. **M-2 Readiness**: Phase M-2 can design artifact construction without redefining execution semantics
3. **Stability**: No subsequent phase requires reinterpretation of M-0 language
4. **Immutability**: All immutable components remain untouched
5. **Boundary Clarity**: Authority, layer, and output boundaries are unambiguous

---

## References

| Document | Purpose |
|----------|---------|
| `M_0_GLOSSARY.md` | Term definitions |
| `M_0_BINDING_CONSTRAINTS.md` | Constraint checklist |
| `MIGRATION_ARCHITECTURE_OVERVIEW.md` | Structural overview |
