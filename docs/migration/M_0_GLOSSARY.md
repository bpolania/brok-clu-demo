# M-0 Glossary

## Purpose

This glossary defines terms used in migration documentation. Each term includes a classification label indicating its category.

---

## Classification Labels

| Label | Meaning |
|-------|---------|
| Authoritative | Source of truth; cannot be overridden |
| Derived | Produced from authoritative sources; non-binding |
| Process term | Describes a process, action, or constraint |

---

## Terms

### Authoritative Output

**Classification**: Authoritative

The sole source of execution truth. In this system, `stdout.raw.kv` is the authoritative output. All other outputs are derived. Authoritative output cannot be overridden by proposals, artifacts, or metadata.

---

### Derived Artifact

**Classification**: Derived

Any output produced from authoritative sources that does not itself hold authority. Examples include log files, diagnostic messages, and timing information. Derived artifacts may be useful but must not be treated as sources of truth.

---

### Proposal

**Classification**: Derived

A non-authoritative suggestion emitted by the proposal layer. Proposals may be accepted, rejected, or ignored by the artifact layer. A proposal does not bind any downstream layer. Zero proposals is a valid output.

---

### Artifact (Decision Record)

**Classification**: Authoritative

A sealed record of an explicit wrapper decision. An artifact records that a specific decision (ACCEPT or REJECT) was made. Artifacts hold wrapper decision authority but do not record execution outcomes. The decision record must be auditable and reproducible.

---

### ACCEPT

**Classification**: Process term

An explicit wrapper decision indicating that input satisfies acceptance criteria. ACCEPT is recorded in the artifact layer. ACCEPT does not guarantee any particular execution outcome; it indicates the wrapper's decision only.

---

### REJECT

**Classification**: Process term

An explicit wrapper decision indicating that input does not satisfy acceptance criteria. REJECT is recorded in the artifact layer. REJECT terminates processing for that input at the wrapper level.

---

### Execution

**Classification**: Process term

The process of running the sealed runtime against input as specified by artifacts. Execution is deterministic and produces authoritative output (`stdout.raw.kv`). Execution enforces authority; it does not create authority.

---

### Verification Gate

**Classification**: Process term

A mandatory check that must pass before execution proceeds. Verification confirms integrity of sealed components (e.g., checksum validation of vendored bundles). If verification fails, execution is blocked. Verification is not optional.

---

### Determinism

**Classification**: Process term

The property that identical inputs produce identical outputs. In this system, determinism is defined as byte-for-byte identity of `stdout.raw.kv` across executions given identical input and environment. Determinism is a hard requirement, not a goal.

---

### Relocatability

**Classification**: Process term

The property that the system functions correctly regardless of its absolute filesystem location. Relocatability requires: no absolute paths in committed files, no environment variable path dependencies, all paths relative to repository root. Relocatability is a hard constraint.

---

## References

| Document | Purpose |
|----------|---------|
| `PHASE_M_0_SCOPE_LOCK.md` | Authority model and constraints |
| `MIGRATION_ARCHITECTURE_OVERVIEW.md` | Structural overview |
| `M_0_BINDING_CONSTRAINTS.md` | Constraint checklist |
