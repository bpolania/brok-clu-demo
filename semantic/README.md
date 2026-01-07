# Semantic Capability Layer

This directory contains documentation and artifacts for the **Semantic Capability Layer** (Layer 1) of the brok-clu-runtime-demo.

---

## Purpose

The Semantic Capability Layer demonstrates what a compiled Constrained Language Understanding system can do at the language level:

- **Paraphrase collapse** — multiple surface forms resolving to identical semantic output
- **Intent routing** — input classification into defined intent categories
- **Slot consistency** — deterministic extraction of structured values
- **Deterministic rejection** — predictable rejection of invalid or out-of-scope inputs

This layer is **illustrative**, not a system proof. It shows product-level capabilities for understanding, not exhaustive linguistic coverage.

---

## Non-Claims (Explicit)

The Semantic Capability Layer explicitly does **NOT** claim:

- General language understanding
- Paraphrase completeness
- Production readiness
- Multilingual robustness
- Typo tolerance
- Domain invariance
- Stability across future compiled artifacts

These non-claims are binding and must be preserved in all downstream phases and documentation.

---

## Inheritance Constraints

All Semantic Layer phases inherit and must respect these constraints:

| Constraint | Description |
|------------|-------------|
| **PoC v2 only executable** | The only CLU artifact that may be executed is the vendored PoC v2 bundle |
| **Verification mandatory** | Verification must pass before any execution; no bypass permitted |
| **stdout.raw.kv authoritative** | The only authoritative output is `stdout.raw.kv`; all derived views are non-authoritative |
| **Determinism inherited** | Semantic layer inherits but does not re-prove runtime determinism guarantees |
| **Runtime immutable** | No modifications to PoC v2, verification wiring, or execution scripts |

---

## Contract

The authoritative scope lock for this layer is defined in:

**[Phase S-0: Scope Lock & Contract Definition](contract/PHASE_S_0_SCOPE_LOCK.md)**

All phases execute under S-0 constraints and cannot weaken them.

---

## Phase Map

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| S-0 | Scope Lock & Contract Definition | **LOCKED** | Defines constraints, non-claims, and contract for all semantic phases |
| S-1 | Semantic Suite Execution | **COMPLETE** | Execute frozen input suite against PoC v2, capture outputs |
| S-2 | Curated Product Demonstration | **COMPLETE** | Present illustrative semantic capabilities for product understanding |
| S-3 | Optional Semantic Regression Gate | NOT STARTED | Optional regression gate for semantic consistency (future) |

---

## Directory Structure

```
semantic/
├── README.md                         # This file
├── contract/
│   └── PHASE_S_0_SCOPE_LOCK.md       # Authoritative scope lock contract
├── phases/
│   ├── PHASE_S_1_PLACEHOLDER.md      # Semantic Suite Execution (complete)
│   ├── PHASE_S_2_PLACEHOLDER.md      # Curated Product Demonstration (complete)
│   └── PHASE_S_3_PLACEHOLDER.md      # Optional Semantic Regression Gate (not started)
├── suites/
│   └── SES_001_restart_alpha.yaml    # SES definitions
├── scripts/
│   └── run_semantic_suite.sh         # Suite runner
├── artifacts/                        # Generated (derived, non-authoritative)
│   ├── SES_SUMMARY.md
│   └── ses_001/
│       ├── execution_index.md
│       └── runs/input_*/runtime_ref.txt
├── demo/                             # Phase S-2 curated demonstration
│   ├── DEMO_SET.yaml                 # Curated input set definition
│   ├── PRODUCT_DEMO.md               # Product-facing narrative
│   ├── explanations/                 # Per-input explanation pages
│   └── runs/INDEX.md                 # Demo run index
└── evidence/
    ├── phase_s_1/
    │   └── PHASE_S_1_CLOSURE.md      # Phase S-1 closure attestation
    └── phase_s_2/
        └── PHASE_S_2_CLOSURE.md      # Phase S-2 closure attestation
```

---

*Semantic Capability Layer — brok-clu-runtime-demo*
