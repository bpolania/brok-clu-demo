# SES_001: Execution Index

**DERIVED, NON-AUTHORITATIVE VIEW**

> Authoritative output is `stdout.raw.kv` only.
> This report is for illustration and traceability purposes.
> Do not use this report to assert correctness.

---

## SES Metadata

| Field | Value |
|-------|-------|
| SES ID | SES_001 |
| Title | Restart Alpha Graceful - Paraphrase Set |
| Input Count | 3 |
| Suite Run | 20260107T222101Z |

## Description

Demonstrates that multiple surface forms expressing the same semantic

---

## Input Runs

| Input | String | Runtime Reference |
|-------|--------|-------------------|
| 01 | `restart alpha subsystem gracefully` | [runtime_ref.txt](runs/input_01/runtime_ref.txt) |
| 02 | `graceful restart of alpha` | [runtime_ref.txt](runs/input_02/runtime_ref.txt) |
| 03 | `please restart the alpha subsystem in graceful mode` | [runtime_ref.txt](runs/input_03/runtime_ref.txt) |

---

## Comparison Results (cmp byte-for-byte)

Comparison method: `cmp -s` (byte-for-byte equality on `stdout.raw.kv`)

| Input | Result vs Baseline |
|-------|-------------------|
| input_01 | BASELINE |
| input_02 | DIFFER |
| input_03 | DIFFER |

---

## Classification

**DIVERGENT**

Inputs produced differing `stdout.raw.kv` outputs.

---

*Generated: 20260107T222101Z*
*Phase S-1 Semantic Suite Execution*
