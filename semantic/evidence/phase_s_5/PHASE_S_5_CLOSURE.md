# Phase S-5 Closure: Weak Semantic Equivalence

**Status:** COMPLETE (Hardened v0.1.1)

---

## Phase Summary

Phase S-5 adds a read-only CLI tool that evaluates "equivalence under an explicitly declared rule" by comparing existing `stdout.raw.kv` files.

**Key Constraint:** This tool is DERIVED and NON-AUTHORITATIVE. It does not execute PoC v2, does not modify any files, and does not imply semantic correctness.

---

## Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| CLI Script | `semantic/scripts/semantic_equivalence.sh` | ✓ Complete (v0.1.1) |
| Rule Documentation | `semantic/equivalence/WSE_RULES.md` | ✓ Complete |
| Usage Documentation | `semantic/equivalence/CLI_USAGE.md` | ✓ Complete |
| Acceptance Tests | `semantic/equivalence/test_semantic_equivalence.sh` | ✓ Complete |
| Phase Placeholder | `semantic/phases/PHASE_S_5_PLACEHOLDER.md` | ✓ Complete |

---

## Rule V1: Coarse Functional Equivalence

### Compared Keys

| Key | Description |
|-----|-------------|
| `status` | Execution status field |
| `intent_id` | Internal traceability identifier |
| `n_slots` | Slot count field |

### Ignored Keys

Only the explicitly listed keys are compared. All other keys are ignored:
- `dispatch`
- All other keys (paths, timestamps, etc.)

### Outcome Labels

| Label | Condition |
|-------|-----------|
| `EQUIVALENT_UNDER_RULE_V1` | All runs have matching derived signatures |
| `NOT_EQUIVALENT_UNDER_RULE_V1` | At least one run has a different derived signature |
| `UNDECIDABLE_UNDER_RULE_V1` | At least one run is missing any compared key |

**UNDECIDABLE dominates**: If any compared key is missing from any run, the result is UNDECIDABLE regardless of other values.

---

## Exit Code Semantics

| Exit Code | Meaning |
|-----------|---------|
| 0 | Evaluation completed (result produced, regardless of outcome) |
| Non-zero | Operational failure (invalid input, missing files, duplicate keys) |

---

## Acceptance Test Results

```
Tests run:    17
Tests passed: 17
Tests failed: 0
RESULT: PASSED
```

Test coverage:
- ✓ Matching signatures → EQUIVALENT_UNDER_RULE_V1, exit 0
- ✓ Differing signature → NOT_EQUIVALENT_UNDER_RULE_V1, exit 0
- ✓ Missing key → UNDECIDABLE_UNDER_RULE_V1, exit 0
- ✓ Invalid path → exit non-zero
- ✓ Single input → exit non-zero
- ✓ Duplicate compared key → exit non-zero (operational failure)
- ✓ Dispatch key ignored
- ✓ Extra keys ignored
- ✓ Disclaimer present in output
- ✓ Determinism vs equivalence distinction present

---

## Attestations

### A-1: No Execution

> The CLI does not execute PoC v2. It reads existing `stdout.raw.kv` files only.

### A-2: No Modification

> The CLI does not modify any files. It is strictly read-only.

### A-3: Derived Classification

> Equivalence under rule is a derived, observational classification. It is not an authoritative runtime guarantee.

### A-4: No Semantic Claims

> This tool does not claim semantic correctness, understanding, or paraphrase equivalence. It performs exact string comparison of selected fields only.

### A-5: Rule Declared

> The comparison rule (V1) is explicitly declared in all output and documentation.

### A-6: Determinism Distinction

> Every invocation includes the disclaimer distinguishing determinism (same input → same bytes) from semantic equivalence (different inputs → same derived signature under rule).

---

## Non-Goals (Explicit)

This phase explicitly does NOT:

- Replace determinism checks (byte-level equality is the runtime guarantee)
- Imply semantic correctness
- Provide quality signals
- Normalize or fuzzy-match values
- Score or rank outputs
- Parse deeper structure beyond key=value lines

---

## Limitations

- Paths must not contain spaces
- Run IDs are resolved via filesystem lookup under `artifacts/run/` only

---

## Contract Compliance

This phase operates under [Phase S-0: Scope Lock & Contract Definition](../../contract/PHASE_S_0_SCOPE_LOCK.md).

All S-0 constraints remain binding.

---

## Disclaimers

Every invocation of the CLI prints:

> Equivalence here is defined by rule, not by meaning.

> Derived, non-authoritative. Does not imply correctness.

> Determinism means the same input produces the same bytes.
> Semantic equivalence means different inputs produce the same derived signature under this rule.

---

## Terminology Constraints

Only these outcome labels are permitted:

- `EQUIVALENT_UNDER_RULE_V1`
- `NOT_EQUIVALENT_UNDER_RULE_V1`
- `UNDECIDABLE_UNDER_RULE_V1`

Never use: SAME, UNDERSTOOD, MEANING MATCH, CORRECT, EQUAL, IDENTICAL.

---

*Phase S-5: Weak Semantic Equivalence*
*Semantic Capability Layer — brok-clu-runtime-demo*
