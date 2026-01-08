# Phase S-5: Weak Semantic Equivalence

**Status:** COMPLETE (Hardened v0.1.1)

---

## Description

Phase S-5 adds a read-only CLI tool that evaluates "equivalence under an explicitly declared rule" by comparing existing `stdout.raw.kv` files.

This is a derived, observational capability. It does not execute PoC v2 or modify any files.

---

## Deliverables

| File | Purpose |
|------|---------|
| `semantic/scripts/semantic_equivalence.sh` | CLI tool for Rule V1 evaluation |
| `semantic/equivalence/WSE_RULES.md` | Rule definitions and semantics |
| `semantic/equivalence/CLI_USAGE.md` | Usage documentation |
| `semantic/equivalence/test_semantic_equivalence.sh` | Acceptance test harness |
| `semantic/evidence/phase_s_5/PHASE_S_5_CLOSURE.md` | Phase closure document |
| `semantic/phases/PHASE_S_5_PLACEHOLDER.md` | This file |

---

## What S-5 Does

- Compares existing `stdout.raw.kv` files under Rule V1
- Evaluates (status, intent_id, n_slots) for exact string equality
- Produces one of three outcome labels:
  - `EQUIVALENT_UNDER_RULE_V1`
  - `NOT_EQUIVALENT_UNDER_RULE_V1`
  - `UNDECIDABLE_UNDER_RULE_V1`
- Exits 0 on successful evaluation (regardless of outcome)
- Exits non-zero only on operational failure (including duplicate keys)

---

## What S-5 Does NOT Do

- Execute PoC v2
- Modify any files
- Imply semantic correctness
- Replace determinism checks
- Provide quality signals
- Normalize or fuzzy-match values
- Claim understanding or meaning equivalence

---

## Limitations

- Paths must not contain spaces
- Run IDs are resolved via filesystem lookup under `artifacts/run/` only

---

## Rule V1 Summary

**Compared:** `status`, `intent_id`, `n_slots` (exact string equality of compared key values)

**Ignored:** `dispatch`, all other keys

Only the explicitly listed keys are compared. All other keys are ignored.

---

## Determinism vs Equivalence

| Concept | Definition |
|---------|------------|
| **Determinism** | The same input produces the same bytes |
| **Equivalence under rule** | Different inputs produce the same derived signature |

These are distinct concepts. Determinism is a runtime guarantee. Equivalence under rule is a derived classification.

---

## Terminology Constraints

Only these outcome labels are permitted:

- `EQUIVALENT_UNDER_RULE_V1`
- `NOT_EQUIVALENT_UNDER_RULE_V1`
- `UNDECIDABLE_UNDER_RULE_V1`

Never use: SAME, UNDERSTOOD, MEANING MATCH, CORRECT, EQUAL, IDENTICAL.

---

## References

- Rule Documentation: [WSE_RULES.md](../equivalence/WSE_RULES.md)
- CLI Usage: [CLI_USAGE.md](../equivalence/CLI_USAGE.md)
- Phase Closure: [PHASE_S_5_CLOSURE.md](../evidence/phase_s_5/PHASE_S_5_CLOSURE.md)
- Phase S-0 Contract: [PHASE_S_0_SCOPE_LOCK.md](../contract/PHASE_S_0_SCOPE_LOCK.md)

---

*Phase S-5: Weak Semantic Equivalence*
*Semantic Capability Layer — brok-clu-runtime-demo*
