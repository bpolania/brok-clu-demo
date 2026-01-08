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
| S-3 | Optional Semantic Regression Gate | **COMPLETE** | Byte-level regression detection (observational) |
| S-4 | Integrated Product Demo Planning | **COMPLETE** | Unified demo surface composing runtime + semantic layers |
| S-5 | Weak Semantic Equivalence | **COMPLETE** | Rule-based equivalence CLI tool |

**Recommended starting point:** [Integrated Product Demo](demo/INTEGRATED_PRODUCT_DEMO.md)

---

## Directory Structure

```
semantic/
├── README.md                         # This file
├── contract/
│   ├── PHASE_S_0_SCOPE_LOCK.md       # Authoritative scope lock contract
│   └── PHASE_S_4_SCOPE_LOCK.md       # S-4 scope lock
├── demo/
│   ├── INTEGRATED_PRODUCT_DEMO.md    # Primary entrypoint (S-4)
│   ├── INTEGRATED_WALKTHROUGH.md     # Command sequence (S-4)
│   ├── PRODUCT_DEMO.md               # Semantic demo (S-2)
│   └── DEMO_SET.yaml                 # Demo input definitions
├── regression/
│   ├── README.md                     # Regression gate docs (S-3)
│   ├── run_regression_check.sh       # Regression runner
│   └── baselines/BASELINES.json      # Baseline references
├── suites/
│   └── SES_001_restart_alpha.yaml    # SES definitions
├── scripts/
│   ├── run_semantic_suite.sh         # Suite runner
│   └── semantic_equivalence.sh       # S-5 equivalence CLI
├── equivalence/
│   ├── WSE_RULES.md                  # Rule V1 documentation
│   ├── CLI_USAGE.md                  # CLI usage docs
│   └── test_semantic_equivalence.sh  # Acceptance tests
├── evidence/
│   └── phase_s_5/PHASE_S_5_CLOSURE.md
├── artifacts/                        # Generated at runtime (gitignored)
└── regression/runs/                  # Generated at runtime (gitignored)
```

---

*Semantic Capability Layer — brok-clu-runtime-demo*
