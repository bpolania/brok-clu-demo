# Phase S-3: Optional Semantic Regression Gate

**DERIVED, NON-AUTHORITATIVE**

> This report is derived, observational, and non-authoritative. It detects byte-level changes in observed outputs only. It makes no semantic claims.

---

## Purpose

This directory contains the optional regression gate for the Semantic Capability Layer. The regression check re-runs existing inputs and compares current outputs against established baselines using **byte-for-byte comparison only**.

---

## What This Is

The regression gate is an **observational tool** that detects changes in runtime output. It:

1. Re-runs each input from the curated demo set through the PoC v2 runtime
2. Compares the new `stdout.raw.kv` against the baseline `stdout.raw.kv`
3. Reports REGRESSION or NO-REGRESSION per input
4. Aggregates results into a summary report

---

## What This Is NOT

The regression gate explicitly does **NOT**:

| Non-Claim | Explanation |
|-----------|-------------|
| Semantic analysis | No parsing or interpretation of output content |
| Tolerance matching | No fuzzy comparison, normalization, or equivalence logic |
| Quality assertion | REGRESSION does not mean "broken", NO-REGRESSION does not mean "correct" |
| Blocking gate | Exit code 0 even if regressions detected (observational only) |
| Production CI | This is illustrative tooling, not hardened CI infrastructure |

---

## Comparison Method

**Byte-for-byte comparison using SHA-256 checksums.**

```sh
# Baseline checksum
sha256sum baseline.stdout.raw.kv

# Current checksum
sha256sum current.stdout.raw.kv

# If checksums match: NO-REGRESSION
# If checksums differ: REGRESSION
```

No normalization. No semantic interpretation. No tolerance.

---

## Directory Structure

```
semantic/regression/
├── README.md                    # This file
├── run_regression_check.sh      # POSIX shell runner
├── baselines/
│   └── BASELINES.json           # Baseline references (derived from S-1/S-2)
├── runs/
│   └── run_<UTC_TIMESTAMP>/     # Per-run artifacts
│       ├── INDEX.md             # Run index
│       ├── per_input/           # Per-input comparison results
│       │   └── input_XX.json    # Individual comparison result
│       └── SUMMARY.json         # Aggregated results
└── reports/
    ├── per_input_comparison.md  # Human-readable comparison table
    └── regression_matrix.md     # Matrix of all inputs vs baseline status
```

---

## Running the Regression Check

```sh
./semantic/regression/run_regression_check.sh
```

The script will:
1. Read baseline references from `BASELINES.json`
2. Re-run each input through the PoC v2 runtime
3. Compare outputs byte-for-byte (SHA-256)
4. Generate artifacts under `runs/run_<timestamp>/`
5. Generate reports under `reports/`
6. Exit 0 regardless of regression status

---

## Baseline Source

Baselines are `stdout.raw.kv` files from Phase S-1 execution runs:

| Input | Baseline Source |
|-------|-----------------|
| demo_input_01 | `artifacts/run/run_20260107T222101Z/stdout.raw.kv` |
| demo_input_02 | `artifacts/run/run_20260107T222104Z/stdout.raw.kv` |
| demo_input_03 | `artifacts/run/run_20260107T222106Z/stdout.raw.kv` |

Baselines are treated as opaque bytes. No content inspection is performed.

---

## Contract Reference

This phase operates under: **[Phase S-0: Scope Lock & Contract Definition](../contract/PHASE_S_0_SCOPE_LOCK.md)**

---

## Binding Constraints

Phase S-3 adheres to all constraints from Phase S-0:

- Does NOT modify PoC v2 binaries, scripts, or artifacts
- Does NOT apply semantic normalization or tolerance
- Does NOT claim semantic correctness or equivalence
- Does NOT block execution based on regression status
- All outputs are DERIVED and NON-AUTHORITATIVE

---

*Phase S-3: Optional Semantic Regression Gate*
*Semantic Capability Layer — brok-clu-runtime-demo*
