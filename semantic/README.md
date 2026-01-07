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
| S-1 | Input Suite & Equivalence Classes | NOT STARTED | Creates frozen input suite grouped into semantic equivalence classes |
| S-2 | Signature Extraction & Comparison | NOT STARTED | Implements mechanical signature extraction and equivalence comparison |
| S-3 | Presentation & Summary | NOT STARTED | Produces audit-grade summaries and PASS/FAIL results |

---

## Directory Structure

```
semantic/
├── README.md                         # This file
├── contract/
│   └── PHASE_S_0_SCOPE_LOCK.md       # Authoritative scope lock contract
└── phases/
    ├── PHASE_S_1_PLACEHOLDER.md      # Input suite phase (not started)
    ├── PHASE_S_2_PLACEHOLDER.md      # Signature extraction phase (not started)
    └── PHASE_S_3_PLACEHOLDER.md      # Presentation phase (not started)
```

---

*Semantic Capability Layer — brok-clu-runtime-demo*
