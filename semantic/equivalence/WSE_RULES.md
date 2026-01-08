# Weak Semantic Equivalence Rules

**DERIVED, NON-AUTHORITATIVE**

> Equivalence here is defined by rule, not by meaning.

---

## Purpose

This document defines the rules for evaluating "equivalence under an explicitly declared rule" using existing authoritative `stdout.raw.kv` outputs.

This is a **derived, observational** capability. It does not:
- Execute PoC v2
- Modify any runtime artifacts
- Imply semantic correctness
- Replace byte-level determinism checks

---

## What Is "Equivalence Under Rule"

Equivalence under rule is a **derived classification** that compares selected fields from multiple `stdout.raw.kv` files using exact string equality of compared key values.

- It is NOT byte-for-byte equality (that is determinism)
- It is NOT semantic understanding
- It is NOT a quality signal
- It is a rule-based field comparison only

---

## Determinism vs Equivalence

| Concept | Definition | Scope |
|---------|------------|-------|
| **Determinism** | The same input produces the same bytes in `stdout.raw.kv` | Runtime guarantee |
| **Equivalence under rule** | Different inputs produce the same derived signature for selected fields | Derived classification |

Determinism is an **authoritative runtime guarantee**.

Equivalence under rule is a **derived, non-authoritative observation**.

---

## Rule V1: Coarse Functional Equivalence

### Compared Keys

Rule V1 compares these keys by **exact string equality of compared key values**:

| Key | Description |
|-----|-------------|
| `status` | Execution status field |
| `intent_id` | Internal traceability identifier |
| `n_slots` | Slot count field |

### Ignored Keys

Only the explicitly listed keys are compared. All other keys are ignored:

| Ignored | Reason |
|---------|--------|
| `dispatch` | Not in compare list |
| Paths | Not in compare list |
| Timestamps | Not in compare list |
| All other keys | Not in compare list |

### Classification Outcomes

| Outcome | Condition |
|---------|-----------|
| `EQUIVALENT_UNDER_RULE_V1` | All runs have matching derived signatures (status, intent_id, n_slots) |
| `NOT_EQUIVALENT_UNDER_RULE_V1` | At least one run has a different derived signature |
| `UNDECIDABLE_UNDER_RULE_V1` | At least one run is missing any compared key |

**UNDECIDABLE dominates**: If any compared key is missing from any run, the result is UNDECIDABLE regardless of other values.

### Extraction Method

- `stdout.raw.kv` is treated as opaque key-value lines
- Only lines matching `^key=` for compared keys are extracted
- Values are taken verbatim (no trimming, no normalization)
- Duplicate keys in a single file cause operational failure (not UNDECIDABLE)

---

## Non-Goals

Rule V1 explicitly does NOT:

| Non-Goal | Explanation |
|----------|-------------|
| Imply semantic correctness | Field equality does not mean "understood correctly" |
| Replace determinism checks | Byte-level equality is the runtime guarantee |
| Provide quality signals | EQUIVALENT does not mean "good" |
| Normalize values | No fuzzy matching, no trimming, no case folding |
| Score or rank | No numeric scoring or confidence |
| Parse deeper structure | Only key=value lines, nothing else |

---

## Failure Cases

### Operational Failures (Exit Non-Zero)

| Failure | Cause |
|---------|-------|
| Fewer than 2 inputs | Cannot compare |
| Invalid path | File does not exist |
| Cannot resolve run ID | Not found in artifacts/run/ |
| Cannot read file | Permission or I/O error |
| Duplicate keys | A compared key appears multiple times in one file |

### UNDECIDABLE (Exit 0)

| Condition | Result |
|-----------|--------|
| Any run missing `status` | UNDECIDABLE_UNDER_RULE_V1 |
| Any run missing `intent_id` | UNDECIDABLE_UNDER_RULE_V1 |
| Any run missing `n_slots` | UNDECIDABLE_UNDER_RULE_V1 |

---

## Interpretation Constraints

Every evaluation must include these disclaimers:

> Equivalence here is defined by rule, not by meaning.

> Derived, non-authoritative. Does not imply correctness.

> Determinism means the same input produces the same bytes.
> Semantic equivalence means different inputs produce the same derived signature under this rule.

---

## Allowed Terminology

Only these outcome labels are permitted:

- `EQUIVALENT_UNDER_RULE_V1`
- `NOT_EQUIVALENT_UNDER_RULE_V1`
- `UNDECIDABLE_UNDER_RULE_V1`

Never use: SAME, UNDERSTOOD, MEANING MATCH, CORRECT, EQUAL, IDENTICAL (for this classification).

---

## Authority Model

| Artifact | Authority |
|----------|-----------|
| `stdout.raw.kv` | AUTHORITATIVE (runtime) |
| Equivalence results | DERIVED (semantic) |
| This documentation | DERIVED (semantic) |

---

## Limitations

- Paths must not contain spaces
- Run IDs are resolved via filesystem lookup under `artifacts/run/` only

---

## Contract Reference

This rule operates under: **[Phase S-0: Scope Lock & Contract Definition](../contract/PHASE_S_0_SCOPE_LOCK.md)**

All S-0 constraints remain binding.

---

*Phase S-5: Weak Semantic Equivalence*
*Semantic Capability Layer — brok-clu-runtime-demo*
