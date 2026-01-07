# Demo Runs Index

**DERIVED, NON-AUTHORITATIVE — References Only**

This index lists the demo runs performed for Phase S-2 and the exact authoritative output paths generated.

> No copying or rewriting of runtime artifacts.
> Authoritative outputs remain at their original paths under `artifacts/run/`.

---

## Demo Run Session

| Field | Value |
|-------|-------|
| Date | 2026-01-07 |
| Timestamp | 20260107T231003Z (suite start) |
| Runner | `semantic/scripts/run_semantic_suite.sh` (unchanged) |
| Suite | SES_001 |
| Classification | DIVERGENT |

---

## Authoritative Output Paths

| Demo Input | Input String | Authoritative Output Path |
|------------|--------------|---------------------------|
| demo_input_01 | `restart alpha subsystem gracefully` | `artifacts/run/run_20260107T231003Z/stdout.raw.kv` |
| demo_input_02 | `graceful restart of alpha` | `artifacts/run/run_20260107T231005Z/stdout.raw.kv` |
| demo_input_03 | `please restart the alpha subsystem in graceful mode` | `artifacts/run/run_20260107T231007Z/stdout.raw.kv` |

---

## Run Directory Contents

Each run directory (`artifacts/run/run_<timestamp>/`) contains:

| File | Description | Authority |
|------|-------------|-----------|
| `stdout.raw.kv` | Authoritative runtime output | **AUTHORITATIVE** |
| `stderr.raw.txt` | Runtime stderr capture | Supporting |
| `exit_code.txt` | Execution exit code | Supporting |
| `execution.meta.json` | Run metadata | Non-authoritative |
| `stdout.derived.json` | Derived JSON view | Non-authoritative |
| `verify/` | Verification artifacts | Supporting |

---

## Excerpts from Authoritative Outputs

The following are **short excerpts** from the authoritative `stdout.raw.kv` files, clearly labeled as excerpts.

### demo_input_01 — Semantic Key-Value Section (lines 20-23)

```
status=OK
intent_id=14
n_slots=0
dispatch=unknown
```

*Excerpt from: `artifacts/run/run_20260107T231003Z/stdout.raw.kv`*

### demo_input_02 — Semantic Key-Value Section (lines 20-23)

```
status=OK
intent_id=14
n_slots=0
dispatch=unknown
```

*Excerpt from: `artifacts/run/run_20260107T231005Z/stdout.raw.kv`*

### demo_input_03 — Semantic Key-Value Section (lines 20-23)

```
status=OK
intent_id=14
n_slots=0
dispatch=unknown
```

*Excerpt from: `artifacts/run/run_20260107T231007Z/stdout.raw.kv`*

---

## Divergence Evidence

The S-1 runner classified this suite as DIVERGENT because the full `stdout.raw.kv` files differ byte-for-byte.

**Observed difference location**: Line 4 (temp file path in output header)

**Semantic key-value output**: Identical across all inputs

See [PRODUCT_DEMO.md](../PRODUCT_DEMO.md) Section 7 for detailed divergence explanation.

---

## Verification

All runs passed verification:

| Demo Input | Verification Exit Code |
|------------|------------------------|
| demo_input_01 | 0 |
| demo_input_02 | 0 |
| demo_input_03 | 0 |

---

*Phase S-2 Demo Runs Index*
*Semantic Capability Layer — brok-clu-runtime-demo*
