# Integrated Product Demo: Brok-CLU Runtime + Semantic Layer

**Primary entrypoint for the complete demo experience.**

> **Disclaimer**: Runtime guarantees apply only to execution and byte-level equality. Semantic material is observational and non-authoritative.

---

## Product Summary

Brok-CLU is a compiled Constrained Language Understanding system that produces verified, deterministic outputs from natural language inputs.

This demo shows behavior, not correctness of meaning.

---

## Problem Statement

- Language processing systems typically lack verifiable determinism
- Runtime outputs are difficult to audit
- Semantic behavior is often hidden or inconsistent
- Regression detection requires semantic tolerance (fuzzy matching)

---

## What This Demo Provides vs Typical LLM Demos

| This Demo | Typical LLM Demo |
|-----------|------------------|
| Mandatory verification before execution | Optional or no verification |
| Byte-for-byte deterministic output | Statistical/probabilistic output |
| Single authoritative output file | Multiple derived views |
| No hidden state | Opaque model state |
| Byte-level regression detection | Semantic similarity thresholds |
| Divergence shown openly | Differences hidden or normalized |

---

## Authoritative vs Derived Outputs

**The only authoritative output is `stdout.raw.kv`.**

| Label | Output Type | Example |
|-------|-------------|---------|
| **AUTHORITATIVE (runtime)** | PoC v2 execution output | `artifacts/run/run_<timestamp>/stdout.raw.kv` |
| **DERIVED (semantic)** | Semantic suite summaries | `semantic/artifacts/SES_SUMMARY.md` |
| **DERIVED (semantic)** | Execution indexes | `semantic/artifacts/ses_001/execution_index.md` |
| **DERIVED (semantic)** | Regression reports | `semantic/regression/reports/*.md` |
| **DERIVED (semantic)** | This documentation | All markdown files |

**Derived artifacts are illustrative only.** The following are all derived and non-authoritative:

- JSON views (`stdout.derived.json`)
- Semantic summaries and indexes
- Regression reports and matrices
- Runtime reference files
- All markdown documentation

**Rule**: Only `stdout.raw.kv` is authoritative. Everything else is derived, observational, and non-authoritative.

---

## No Semantic Claims

This demo explicitly does NOT claim:

- Semantic correctness or understanding
- Paraphrase completeness or equivalence
- Typo tolerance
- Domain generality
- Production readiness
- Multilingual robustness

Divergence between inputs is shown openly, not hidden.

---

## Demo Sections

### A. Verified Deterministic Runtime Execution (AUTHORITATIVE)

**What it demonstrates:**
- PoC v2 bundle integrity verification
- Gated execution (verification must pass)
- Deterministic output production
- Byte-identical outputs for identical inputs

**Commands:**

```sh
# Verify PoC v2 bundle integrity
./scripts/verify_poc_v2.sh

# Execute with an input
./scripts/run_poc_v2.sh --input <input_file>
```

**Output locations:**
- Verification artifacts: `artifacts/verify/run_<timestamp>/`
- Execution artifacts: `artifacts/run/run_<timestamp>/`
- Authoritative output: `artifacts/run/run_<timestamp>/stdout.raw.kv`

**Guarantees (runtime layer):**
- Verification gating (execution blocked on failure)
- Deterministic execution
- Byte-for-byte identical output
- No hidden state
- Full relocatability

---

### B. Semantic Behavior Surfacing (DERIVED, observational)

This demo shows behavior, not correctness of meaning.

**What it demonstrates:**
- Curated inputs processed through PoC v2
- Output variability across paraphrased inputs
- Byte-for-byte comparison results (CONSISTENT vs DIVERGENT)

**Commands:**

```sh
# Run the semantic suite
./semantic/scripts/run_semantic_suite.sh
```

**Output locations:**
- Suite summary: `semantic/artifacts/SES_SUMMARY.md`
- Per-SES index: `semantic/artifacts/ses_001/execution_index.md`
- Runtime references: `semantic/artifacts/ses_001/runs/input_*/runtime_ref.txt`

**Non-guarantees (semantic layer):**
- No paraphrase equivalence
- No semantic correctness claims
- No typo tolerance
- No domain generality

See: [PRODUCT_DEMO.md](PRODUCT_DEMO.md) for detailed semantic demo.

---

### C. Regression Visibility (DERIVED, observational)

**What it demonstrates:**
- Byte-level change detection between runs
- SHA-256 comparison of `stdout.raw.kv` files
- REGRESSION vs NO-REGRESSION classification
- Non-blocking observational reporting

**Commands:**

```sh
# Run regression check
./semantic/regression/run_regression_check.sh
```

**Output locations:**
- Run summary: `semantic/regression/runs/run_<timestamp>/SUMMARY.json`
- Per-input results: `semantic/regression/runs/run_<timestamp>/per_input/*.json`
- Comparison report: `semantic/regression/reports/per_input_comparison.md`
- Regression matrix: `semantic/regression/reports/regression_matrix.md`

**Properties:**
- Exit code 0 regardless of regression status (observational only)
- No semantic analysis or interpretation
- No tolerance or fuzzy matching
- Divergence reported openly

See: [Regression README](../regression/README.md) for details.

---

## Step-by-Step Walkthrough

See: [INTEGRATED_WALKTHROUGH.md](INTEGRATED_WALKTHROUGH.md) for a linear copy/paste command sequence.

---

## How to Read This Demo

### For Engineers

1. Start with Section A (runtime verification + execution)
2. Review `scripts/verify_poc_v2.sh` and `scripts/run_poc_v2.sh`
3. Inspect `stdout.raw.kv` output format
4. Run Section B to see semantic suite execution
5. Run Section C to observe regression detection

### For Product

1. Read this summary document
2. Focus on "What This Demo Provides" table
3. Review Section B walkthrough scenes
4. Note the explicit non-guarantees

### For Investors

1. Read Product Summary and Problem Statement
2. Review "What This Demo Provides" comparison table
3. Note the audit-grade artifact capture
4. Review authoritative vs derived output labels

### For Auditors

1. Verify PoC v2 bundle SHA-256: `7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a`
2. Review [Phase S-0 Contract](../contract/PHASE_S_0_SCOPE_LOCK.md)
3. Confirm `stdout.raw.kv` is the only authoritative output
4. Verify byte-for-byte comparison methods (SHA-256, `cmp -s`)
5. Review regression gate constraints (no semantic tolerance)

---

## Glossary

### intent_id

`intent_id` is an internal identifier used for traceability within the compiled CLU artifact.

- Its numeric value has no semantic meaning guarantee.
- Equality or inequality of `intent_id` values across runs does not imply correctness or incorrectness.
- It is not a quality signal.
- It should not be used to infer semantic behavior.

### dispatch=unknown

`dispatch=unknown` is a field value that may appear in output.

- It is not an error.
- It indicates no explicit dispatch classification was applied.
- It does not affect runtime guarantees (verification, execution, determinism).
- No semantic interpretation should be drawn from this value.

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| [Phase S-0 Contract](../contract/PHASE_S_0_SCOPE_LOCK.md) | Authoritative constraints |
| [Phase S-4 Scope Lock](../contract/PHASE_S_4_SCOPE_LOCK.md) | This phase's scope |
| [PRODUCT_DEMO.md](PRODUCT_DEMO.md) | Semantic demo details (S-2) |
| [Regression README](../regression/README.md) | Regression gate details (S-3) |
| [WSE_RULES.md](../equivalence/WSE_RULES.md) | Semantic equivalence rules (S-5) |
| [INTEGRATED_WALKTHROUGH.md](INTEGRATED_WALKTHROUGH.md) | Copy/paste command sequence |

---

## Layer Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME LAYER (V2)                       │
│                    AUTHORITATIVE                            │
│                                                             │
│  PoC v2 Bundle → Verification → Execution → stdout.raw.kv  │
│                                                             │
│  Guarantees: determinism, verification gating, byte-exact   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ produces
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   SEMANTIC LAYER (S-*)                      │
│                   DERIVED, OBSERVATIONAL                    │
│                                                             │
│  Semantic Suite → Comparison → Regression → Reports        │
│                                                             │
│  No guarantees: observational, non-authoritative            │
└─────────────────────────────────────────────────────────────┘
```

---

*Phase S-4: Integrated Product Demo Planning*
*Semantic Capability Layer — brok-clu-runtime-demo*
