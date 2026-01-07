# demo_input_02: Paraphrase Variant (Divergent)

**ILLUSTRATIVE ONLY — DERIVED, NON-AUTHORITATIVE**

---

## Input Details

| Field | Value |
|-------|-------|
| ID | demo_input_02 |
| Source | SES_001/input_02 |
| Category | paraphrase_diverge |
| Input String | `graceful restart of alpha` |

---

## Intended Meaning Note

Alternate phrasing for restarting alpha subsystem gracefully.

*Note: This describes the apparent intent of the input text, not a claim that the system "understands" the meaning.*

---

## What Actually Happened

The input was processed through the PoC v2 runtime:

1. **Verification**: Passed (exit code 0)
2. **Execution**: Completed (exit code 0)
3. **Output produced**: Authoritative `stdout.raw.kv` captured

### Authoritative Output Path

```
artifacts/run/run_20260107T231005Z/stdout.raw.kv
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

| Line | Baseline (demo_input_01) | This Input (demo_input_02) |
|------|--------------------------|----------------------------|
| 4 | `Input:  /var/.../tmp.9S3GalHcRB` | `Input:  /var/.../tmp.k1F4KREz23` |

### Analysis

- The difference is in the **temp file path** embedded in the output header
- This path varies because each input is written to a unique temp file before execution
- The **semantic key-value output** (lines 20-23) is **identical** to the baseline

### Important Note

This divergence is reported honestly. The S-1 comparison is strict and byte-for-byte. The files are literally different files, so they are correctly classified as DIFFER.

---

## Demo Point

Shows that paraphrased inputs may produce differing authoritative outputs, even when the semantic result (status, intent_id, etc.) is identical. The divergence is in output metadata, not semantic content.

---

*Illustrative only — Phase S-2 Curated Product Demonstration*
