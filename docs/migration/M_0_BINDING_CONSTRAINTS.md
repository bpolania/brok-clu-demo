# M-0 Binding Constraints

## Purpose

This document provides a standalone checklist of constraints that bind all migration phases. Each constraint is mandatory. Violation of any constraint invalidates the violating phase.

---

## 1. Runtime Immutability Constraints

- [ ] `vendor/poc_v2/poc_v2.tar.gz` must not be modified
- [ ] `vendor/poc_v2/SHA256SUMS.vendor` must not be modified
- [ ] `vendor/poc_v2/PROVENANCE.txt` must not be modified
- [ ] `scripts/verify_poc_v2.sh` must not be modified
- [ ] `scripts/run_poc_v2.sh` must not be modified
- [ ] `scripts/determinism_test_v2.sh` must not be modified
- [ ] CLI flags for existing scripts must not change
- [ ] Determinism test pass criteria must not change
- [ ] Runtime behavior must not be altered

---

## 2. Authority Boundary Constraints

- [ ] Proposal layer must not claim authority
- [ ] Proposal layer must not produce side effects
- [ ] Artifact layer must record explicit ACCEPT or REJECT only
- [ ] Artifact layer must not record implicit decisions
- [ ] Artifact layer must not record execution outcomes
- [ ] Execution layer must not infer beyond artifact specification
- [ ] Execution layer must not create authority
- [ ] Authority must flow unidirectionally: artifact → execution → output

---

## 3. Output Authority Constraints

- [ ] `stdout.raw.kv` must be the sole authoritative execution output
- [ ] All other outputs must be treated as derived
- [ ] Proposals must not override runtime output
- [ ] Artifacts must not override runtime output
- [ ] Artifacts must record decisions, not outcomes
- [ ] Determinism must be byte-for-byte on `stdout.raw.kv`

---

## 4. Repository Hygiene and Relocatability Constraints

- [ ] Generated outputs must reside under `artifacts/` or existing evidence conventions
- [ ] `artifacts/` must be gitignored
- [ ] Generated `stdout.raw.kv` files must not be committed
- [ ] Temporary extraction artifacts must not be committed
- [ ] Absolute paths must not appear in committed files
- [ ] Environment variable path dependencies must not appear in committed logic
- [ ] All committed path references must be relative to repository root

---

## 5. Invalidity Rule

**Any phase that violates any constraint in this document is invalid by definition.**

A phase is not valid merely because it produces output. A phase is valid only if:

1. All constraints in this document are satisfied
2. No immutable component is modified
3. No authority boundary is violated
4. No output authority rule is violated
5. No repository hygiene or relocatability constraint is violated

Partial compliance is not compliance. A single violation invalidates the entire phase.

---

## Verification

Before declaring a phase complete, verify:

1. Run `git diff` against immutable components — diff must be empty
2. Confirm no changes to `vendor/` directory
3. Confirm no changes to listed scripts
4. Confirm all generated outputs are in gitignored locations
5. Confirm no absolute paths in committed files

---

## References

| Document | Purpose |
|----------|---------|
| `PHASE_M_0_SCOPE_LOCK.md` | Authority model and full constraint definitions |
| `MIGRATION_ARCHITECTURE_OVERVIEW.md` | Structural overview |
| `M_0_GLOSSARY.md` | Term definitions |
