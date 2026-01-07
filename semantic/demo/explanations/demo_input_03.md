# demo_input_03: Extended Paraphrase (Divergent)

**ILLUSTRATIVE ONLY — DERIVED, NON-AUTHORITATIVE**

---

## Input Details

| Field | Value |
|-------|-------|
| ID | demo_input_03 |
| Source | SES_001/input_03 |
| Category | paraphrase_diverge |
| Input String | `please restart the alpha subsystem in graceful mode` |

---

## Intended Meaning Note

Polite variant requesting graceful restart of alpha subsystem.

*Note: This describes the apparent intent of the input text, not a claim that the system "understands" the meaning.*

---

## What Actually Happened

The input was processed through the PoC v2 runtime:

1. **Verification**: Passed (exit code 0)
2. **Execution**: Completed (exit code 0)
3. **Output produced**: Authoritative `stdout.raw.kv` captured

### Authoritative Output Path

```
artifacts/run/run_20260107T231007Z/stdout.raw.kv
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

**Comparison Result vs Baseline**: DIFFER

### Concrete Difference

The byte-for-byte comparison (`cmp -s`) detected a difference on **line 4** of `stdout.raw.kv`:

| Line | Baseline (demo_input_01) | This Input (demo_input_03) |
|------|--------------------------|----------------------------|
| 4 | `Input:  /var/.../tmp.9S3GalHcRB` | `Input:  /var/.../tmp.<different>` |

### Analysis

- The difference is in the **temp file path** embedded in the output header
- This is the same divergence pattern as demo_input_02
- The **semantic key-value output** (lines 20-23) is **identical** to the baseline

### Important Note

This divergence is reported honestly. The byte-for-byte comparison correctly identifies that the full output files differ, even though the semantic content is the same.

---

## Demo Point

Shows semantic variability—same intended action, different output metadata. Demonstrates that extended or polite phrasing does not change the observed semantic result, but the full authoritative output still differs due to runtime metadata.

---

*Illustrative only — Phase S-2 Curated Product Demonstration*
