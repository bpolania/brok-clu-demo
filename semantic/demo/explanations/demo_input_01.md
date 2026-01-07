# demo_input_01: Baseline Happy Path

**ILLUSTRATIVE ONLY — DERIVED, NON-AUTHORITATIVE**

---

## Input Details

| Field | Value |
|-------|-------|
| ID | demo_input_01 |
| Source | SES_001/input_01 |
| Category | happy_path |
| Input String | `restart alpha subsystem gracefully` |

---

## Intended Meaning Note

Request to restart the alpha subsystem using graceful mode.

*Note: This describes the apparent intent of the input text, not a claim that the system "understands" the meaning.*

---

## What Actually Happened

The input was processed through the PoC v2 runtime:

1. **Verification**: Passed (exit code 0)
2. **Execution**: Completed (exit code 0)
3. **Output produced**: Authoritative `stdout.raw.kv` captured

### Authoritative Output Path

```
artifacts/run/run_20260107T231003Z/stdout.raw.kv
```

### Key-Value Output (excerpt from authoritative file, lines 20-23)

```
status=OK
intent_id=14
n_slots=0
dispatch=unknown
```

---

## Observed Divergence

**Role**: BASELINE

This input serves as the baseline for comparison. Other inputs in the curated set are compared against this output using byte-for-byte `cmp -s`.

No divergence to report for the baseline itself.

---

## Demo Point

Shows baseline runtime behavior with successful verification and execution. Establishes the reference output against which paraphrased inputs are compared.

---

*Illustrative only — Phase S-2 Curated Product Demonstration*
