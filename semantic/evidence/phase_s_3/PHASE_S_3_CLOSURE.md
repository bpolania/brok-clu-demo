# Phase S-3: Optional Semantic Regression Gate — Closure Attestation

**Status:** IMPLEMENTED (mutable until explicit closure)

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

---

## Phase Identity

| Field | Value |
|-------|-------|
| Phase | S-3 |
| Name | Optional Semantic Regression Gate |
| Implementation Date | 2026-01-07 |
| Status | IMPLEMENTED |

---

## Files Added/Modified by Phase S-3

Phase S-3 added files **only** under `semantic/regression/` and `semantic/evidence/phase_s_3/`:

| File | Purpose |
|------|---------|
| `semantic/regression/README.md` | Regression gate documentation |
| `semantic/regression/run_regression_check.sh` | POSIX shell runner script |
| `semantic/regression/baselines/BASELINES.json` | Baseline references |
| `semantic/regression/runs/run_<timestamp>/INDEX.md` | Run index |
| `semantic/regression/runs/run_<timestamp>/SUMMARY.json` | Run summary |
| `semantic/regression/runs/run_<timestamp>/per_input/*.json` | Per-input comparison results |
| `semantic/regression/reports/per_input_comparison.md` | Human-readable comparison table |
| `semantic/regression/reports/regression_matrix.md` | Matrix of all inputs vs baseline status |
| `semantic/evidence/phase_s_3/PHASE_S_3_CLOSURE.md` | This file |
| `semantic/phases/PHASE_S_3_PLACEHOLDER.md` | Placeholder update (status only) |

---

## Files NOT Modified by Phase S-3

Phase S-3 explicitly did **NOT** modify:

| Path | Constraint |
|------|------------|
| `vendor/` | PoC v2 bundle is immutable |
| `bundles/` | Runtime bundles are immutable |
| `scripts/` | Runtime scripts are immutable |
| `semantic/scripts/run_semantic_suite.sh` | S-1 runner must remain unchanged |
| `semantic/artifacts/*` | S-1 execution artifacts are frozen |
| `semantic/demo/*` | S-2 demo artifacts are frozen |
| `semantic/README.md` | Layer documentation owned by S-0/S-1 |
| `semantic/suites/*` | SES definitions owned by S-1 |

---

## Attestations

### 1. PoC v2 Binaries/Scripts/Artifacts Unchanged

**ATTESTED**

No modifications were made to:
- `vendor/poc_v2/` (PoC v2 bundle)
- `scripts/run_poc_v2.sh` (runtime wrapper)
- `scripts/verify_poc_v2.sh` (verification script)
- Any existing runtime artifacts

### 2. Byte-for-Byte Comparison Only

**ATTESTED**

The regression check uses **SHA-256 checksums** for comparison:
- No normalization applied
- No semantic parsing applied
- No tolerance or fuzzy matching applied
- No heuristic or probabilistic comparison applied
- No content inspection of `stdout.raw.kv` performed

Comparison method: `shasum -a 256` on `stdout.raw.kv` files treated as opaque bytes.

### 3. REGRESSION vs NO-REGRESSION Classification

**ATTESTED**

The regression check reports:
- `NO-REGRESSION`: Checksums match (byte-identical)
- `REGRESSION`: Checksums differ (any byte-level difference)

No interpretation is applied to the classification.

### 4. Exit Code Behavior

**ATTESTED**

The regression check script:
- Exits 0 when regressions are detected (observational, non-blocking)
- Exits non-zero only for operational failures (missing baselines, failed commands, zero eligible baselines)

### 5. Baselines Reference stdout.raw.kv Directly

**ATTESTED**

Baselines point directly to `stdout.raw.kv` files:

| Input | Baseline Source |
|-------|-----------------|
| demo_input_01 | `artifacts/run/run_20260107T222101Z/stdout.raw.kv` |
| demo_input_02 | `artifacts/run/run_20260107T222104Z/stdout.raw.kv` |
| demo_input_03 | `artifacts/run/run_20260107T222106Z/stdout.raw.kv` |

Baselines are treated as opaque bytes. No content inspection is performed.

---

## Binding Constraints Compliance

| Constraint | Status |
|------------|--------|
| Do NOT modify PoC v2 binaries, scripts, or artifacts | COMPLIED |
| Do NOT modify or reinterpret runtime guarantees | COMPLIED |
| Do NOT modify Phase S-1 or S-2 artifacts | COMPLIED |
| Do NOT add semantic normalization, tolerance, or equivalence logic | COMPLIED |
| Do NOT introduce probabilistic or heuristic comparisons | COMPLIED |
| Do NOT claim semantic robustness or correctness | COMPLIED |
| Do NOT hide or soften regression results | COMPLIED |
| Do NOT use non-zero exit codes for regression detection | COMPLIED |
| Do NOT treat regression artifacts as authoritative outputs | COMPLIED |
| Do NOT inspect stdout.raw.kv content beyond hashing | COMPLIED |
| All new files under semantic/regression/ and clearly labeled | COMPLIED |

---

## Regression Check Results

### Run Summary

| Metric | Value |
|--------|-------|
| Run Timestamp | (regenerated each run) |
| Total Inputs | 3 |
| NO-REGRESSION | (varies) |
| REGRESSION | (varies) |
| Errors | (varies) |
| Overall Status | (varies) |

### Per-Input Results

| Input ID | Status |
|----------|--------|
| demo_input_01 | (varies per run) |
| demo_input_02 | (varies per run) |
| demo_input_03 | (varies per run) |

### Note

Byte-level change detected between baseline and current `stdout.raw.kv`. No further analysis is performed.

---

## Key Properties

1. **Observational only**: Reports byte-level differences without interpretation
2. **Exit code 0 on regression**: Non-blocking gate
3. **All artifacts generated**: INDEX.md, SUMMARY.json, per_input/*.json, reports/*.md
4. **No semantic claims**: Only byte-level difference detection
5. **No content inspection**: `stdout.raw.kv` treated as opaque bytes

---

## Contract Reference

This phase was executed under: **[Phase S-0: Scope Lock & Contract Definition](../../contract/PHASE_S_0_SCOPE_LOCK.md)**

---

*Phase S-3 Closure Attestation (Draft — Mutable Until Explicit Closure)*
*Semantic Capability Layer — brok-clu-runtime-demo*
