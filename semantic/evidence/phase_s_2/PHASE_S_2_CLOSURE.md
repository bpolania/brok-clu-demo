# Phase S-2: Curated Product Demonstration — Closure Attestation

**Status:** IMPLEMENTED (mutable until explicit closure)

---

## Phase Identity

| Field | Value |
|-------|-------|
| Phase | S-2 |
| Name | Curated Product Demonstration |
| Implementation Date | 2026-01-07 |
| Status | IMPLEMENTED |

---

## Files Added/Modified by Phase S-2

Phase S-2 added files **only** under `semantic/demo/` and `semantic/evidence/phase_s_2/`:

| File | Purpose |
|------|---------|
| `semantic/demo/DEMO_SET.yaml` | Curated demo set definition (derived) |
| `semantic/demo/PRODUCT_DEMO.md` | Product-facing narrative documentation |
| `semantic/demo/explanations/demo_input_01.md` | Per-input explanation (baseline) |
| `semantic/demo/explanations/demo_input_02.md` | Per-input explanation (paraphrase diverge) |
| `semantic/demo/explanations/demo_input_03.md` | Per-input explanation (paraphrase diverge) |
| `semantic/demo/runs/INDEX.md` | Demo run index with authoritative output paths |
| `semantic/evidence/phase_s_2/PHASE_S_2_CLOSURE.md` | This file |
| `semantic/phases/PHASE_S_2_PLACEHOLDER.md` | Placeholder update (status only) |

---

## Files NOT Modified by Phase S-2

Phase S-2 explicitly did **NOT** modify:

| Path | Reason |
|------|--------|
| `vendor/` | PoC v2 bundle is immutable |
| `bundles/` | Runtime bundles are immutable |
| `scripts/` | Runtime scripts are immutable |
| `semantic/scripts/run_semantic_suite.sh` | S-1 runner must remain unchanged |
| `semantic/artifacts/*` | S-1 execution artifacts are frozen |
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

### 2. Semantic Suite Runner Unchanged

**ATTESTED**

The Phase S-1 runner was used **unchanged**:
- File: `semantic/scripts/run_semantic_suite.sh`
- No modifications to comparison logic
- No modifications to execution flow
- Runner was invoked as-is to generate demo run data

### 3. Outputs Remain Authoritative Only in artifacts/run/.../stdout.raw.kv

**ATTESTED**

All references to authoritative output point to:
```
artifacts/run/run_<timestamp>/stdout.raw.kv
```

No new authoritative claims were made. All demo documentation is clearly labeled as:
- DERIVED
- NON-AUTHORITATIVE
- ILLUSTRATIVE ONLY

### 4. Semantic Limitations and Divergences Visible

**ATTESTED**

The demo narrative includes:
- Explicit non-guarantees (Section 3 of PRODUCT_DEMO.md)
- Transparency callouts (Section 8 of PRODUCT_DEMO.md)
- Divergence explanation (Section 7 of PRODUCT_DEMO.md)
- Per-input divergence details (explanation pages)

The S-1 classification of **DIVERGENT** is preserved and explained, not hidden or softened.

---

## Binding Constraints Compliance

| Constraint | Status |
|------------|--------|
| Do NOT modify PoC v2 binaries, scripts, or artifacts | COMPLIED |
| Do NOT modify or reinterpret runtime guarantees | COMPLIED |
| Do NOT modify or reinterpret Phase S-1 results | COMPLIED |
| Do NOT add semantic normalization, tolerance, or equivalence logic | COMPLIED |
| Do NOT introduce probabilistic or heuristic comparisons | COMPLIED |
| Do NOT claim semantic robustness, paraphrase completeness, or language generality | COMPLIED |
| Do NOT hide or soften semantic divergence results | COMPLIED |
| Do NOT introduce new execution paths or bypass verification | COMPLIED |
| Do NOT treat semantic artifacts as authoritative outputs | COMPLIED |
| All new files under semantic/ and clearly labeled | COMPLIED |

---

## Key Demo Finding

The curated demo set (3 inputs from SES_001) demonstrates:

1. **Runtime guarantees work**: All inputs passed verification and executed successfully
2. **Semantic variability exists**: Byte-for-byte comparison shows DIVERGENT classification
3. **Divergence is in metadata**: The temp file path in stdout header varies per run
4. **Semantic results are consistent**: The key-value output (status, intent_id, etc.) is identical

This finding is reported honestly. The demo shows behavior, not correctness of meaning.

---

## Contract Reference

This phase was executed under: **[Phase S-0: Scope Lock & Contract Definition](../../contract/PHASE_S_0_SCOPE_LOCK.md)**

---

*Phase S-2 Closure Attestation (Draft — Mutable Until Explicit Closure)*
*Semantic Capability Layer — brok-clu-runtime-demo*
