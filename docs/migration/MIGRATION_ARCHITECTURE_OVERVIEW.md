# Migration Architecture Overview

## Purpose

This document describes the target conceptual flow for the migration architecture. It is a structural clarification and does not require runtime behavior changes.

---

## Conceptual Flow

```
user input → proposal → artifact → deterministic execution
```

Each stage has defined responsibilities and forbidden behaviors. Authority flows forward only.

---

## Layer Responsibilities

### Proposal Layer

| Responsibility | Description |
|----------------|-------------|
| Input analysis | Examine user input |
| Suggestion generation | Emit zero or more proposals |
| Advisory output | Proposals are suggestions only |

| Forbidden Behavior | Rationale |
|--------------------|-----------|
| Side effects | Proposals must not alter state |
| Authority claims | Proposals are non-authoritative |
| Binding output | Proposals do not commit the artifact layer |

### Artifact Layer

| Responsibility | Description |
|----------------|-------------|
| Decision recording | Record explicit ACCEPT or REJECT |
| Auditability | Maintain sealed decision record |
| Deterministic construction | Build artifacts from deterministic rules |

| Forbidden Behavior | Rationale |
|--------------------|-----------|
| Implicit decisions | All decisions must be explicit |
| Probabilistic outcomes | Decision space must be enumerable |
| Outcome recording | Artifacts record decisions, not execution results |

### Execution Layer

| Responsibility | Description |
|----------------|-------------|
| Artifact execution | Execute what artifacts specify |
| Deterministic output | Produce identical output for identical input |
| Truth production | Generate `stdout.raw.kv` as sole authoritative output |

| Forbidden Behavior | Rationale |
|--------------------|-----------|
| Inference | Execution must not interpret beyond artifact |
| Authority creation | Execution enforces, never creates authority |
| Output override | Runtime output cannot be overridden by other layers |

---

## Authority Distinction

### Wrapper Decision Authority

The artifact layer holds wrapper decision authority:

- Records whether input is ACCEPT or REJECT
- Decision is explicit and auditable
- Decision record is distinct from execution outcome

### Execution Truth

`stdout.raw.kv` is the sole execution truth:

- Produced by the execution layer
- Byte-for-byte deterministic
- Cannot be overridden by proposals or artifacts
- All other outputs are derived

### Key Distinction

| Concept | Layer | Scope |
|---------|-------|-------|
| Wrapper decision authority | Artifact | What decision was made |
| Execution truth | Execution | What the runtime produced |

These are distinct. An artifact records a decision. Execution produces authoritative output. Neither overrides the other; they operate in sequence.

---

## Structural Clarification Statement

This architecture is a structural clarification of the existing system. It does not:

- Require changes to runtime behavior
- Alter the determinism guarantees
- Modify the verification boundary
- Change the authoritative status of `stdout.raw.kv`

The purpose is to define clear boundaries for migration phases, not to introduce new runtime requirements.

---

## References

| Document | Purpose |
|----------|---------|
| `PHASE_M_0_SCOPE_LOCK.md` | Authority model and constraints |
| `M_0_GLOSSARY.md` | Term definitions |
| `M_0_BINDING_CONSTRAINTS.md` | Constraint checklist |
