# Semantic Equivalence CLI Usage

**DERIVED, NON-AUTHORITATIVE**

> Equivalence here is defined by rule, not by meaning.

---

## Overview

The `semantic_equivalence.sh` CLI compares multiple existing `stdout.raw.kv` files under Rule V1 (Coarse Functional Equivalence).

**This tool is read-only.** It does not execute PoC v2 or modify any files.

---

## Location

```
semantic/scripts/semantic_equivalence.sh
```

---

## Synopsis

```sh
./semantic/scripts/semantic_equivalence.sh <run_ref_1> <run_ref_2> [run_ref_3 ...]
```

Requires at least 2 run references.

---

## Input Reference Types

A run reference may be:

| Type | Example |
|------|---------|
| Direct path to stdout.raw.kv | `artifacts/run/run_20260107T222101Z/stdout.raw.kv` |
| Path to run directory | `artifacts/run/run_20260107T222101Z` |
| Run ID with prefix | `run_20260107T222101Z` |
| Run ID without prefix | `20260107T222101Z` |

The CLI resolves each reference to an actual `stdout.raw.kv` file path via filesystem lookup under `artifacts/run/`.

---

## Limitations

- **Paths must not contain spaces.** This is a shell handling limitation.
- Run IDs are resolved via filesystem lookup only.

---

## Examples

### Compare Two Runs by Directory Path

```sh
./semantic/scripts/semantic_equivalence.sh \
    artifacts/run/run_20260107T222101Z \
    artifacts/run/run_20260107T222104Z
```

### Compare Three Runs by Direct File Path

```sh
./semantic/scripts/semantic_equivalence.sh \
    artifacts/run/run_20260107T222101Z/stdout.raw.kv \
    artifacts/run/run_20260107T222104Z/stdout.raw.kv \
    artifacts/run/run_20260107T222106Z/stdout.raw.kv
```

### Compare by Run ID

```sh
./semantic/scripts/semantic_equivalence.sh \
    run_20260107T222101Z \
    run_20260107T222104Z
```

---

## Sample Output Format

```
========================================================================
SEMANTIC EQUIVALENCE RESULT: EQUIVALENT_UNDER_RULE_V1
========================================================================

Rule: RULE_V1
Tool Version: 0.1.1
Compared Keys: status, intent_id, n_slots
Ignored: dispatch, all other keys
Comparison: exact string equality of compared key values

------------------------------------------------------------------------
Per-Run Details
------------------------------------------------------------------------

Run 1:
  Authoritative path: /path/to/artifacts/run/run_20260107T222101Z/stdout.raw.kv
  Compared values:
    status    = OK
    intent_id = 14
    n_slots   = 0

Run 2:
  Authoritative path: /path/to/artifacts/run/run_20260107T222104Z/stdout.raw.kv
  Compared values:
    status    = OK
    intent_id = 14
    n_slots   = 0

------------------------------------------------------------------------
Interpretation Disclaimer
------------------------------------------------------------------------

Equivalence here is defined by rule, not by meaning.
Derived, non-authoritative. Does not imply correctness.

Determinism means the same input produces the same bytes.
Semantic equivalence means different inputs produce the same derived
signature under this rule.

========================================================================
```

---

## Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Evaluation completed successfully (result produced) |
| Non-zero | Operational failure |

**Exit 0 is returned for all three outcome labels:**
- `EQUIVALENT_UNDER_RULE_V1` → Exit 0
- `NOT_EQUIVALENT_UNDER_RULE_V1` → Exit 0
- `UNDECIDABLE_UNDER_RULE_V1` → Exit 0

---

## Operational Failures (Exit Non-Zero)

| Condition | Exit Code |
|-----------|-----------|
| Fewer than 2 inputs | Non-zero |
| Invalid or unresolvable path | Non-zero |
| Cannot read file | Non-zero |
| Duplicate compared keys in a file | Non-zero |

---

## UNDECIDABLE Conditions

The result is `UNDECIDABLE_UNDER_RULE_V1` (exit 0) when:

- Any input file is missing the `status` key
- Any input file is missing the `intent_id` key
- Any input file is missing the `n_slots` key

**UNDECIDABLE dominates**: If any compared key is missing from any run, the result is UNDECIDABLE regardless of other values.

This is not an operational failure. The evaluation completed, but the rule cannot determine equivalence due to incomplete data.

---

## Terminology Constraints

Only these outcome labels are used:

| Label | Meaning |
|-------|---------|
| `EQUIVALENT_UNDER_RULE_V1` | All compared fields match under the rule |
| `NOT_EQUIVALENT_UNDER_RULE_V1` | At least one field differs |
| `UNDECIDABLE_UNDER_RULE_V1` | Missing required field(s) |

Never printed: SAME, UNDERSTOOD, MEANING MATCH, CORRECT, EQUAL, IDENTICAL.

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

## Disclaimers

Every invocation prints:

> Equivalence here is defined by rule, not by meaning.

> Derived, non-authoritative. Does not imply correctness.

> Determinism means the same input produces the same bytes.
> Semantic equivalence means different inputs produce the same derived signature under this rule.

---

## See Also

- [WSE_RULES.md](WSE_RULES.md) — Rule definitions
- [Phase S-0 Contract](../contract/PHASE_S_0_SCOPE_LOCK.md) — Authoritative constraints

---

*Phase S-5: Weak Semantic Equivalence*
*Semantic Capability Layer — brok-clu-runtime-demo*
