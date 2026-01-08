# Integrated Demo Walkthrough

**Linear copy/paste command sequence.**

> **Disclaimer**: Runtime guarantees apply only to execution and byte-level equality. Semantic material is observational and non-authoritative.

---

## Output Authority

**`stdout.raw.kv` is the only authoritative output.** All other views (JSON, summaries, reports, indexes) are derived and non-authoritative.

For terminology clarification, see [Glossary](INTEGRATED_PRODUCT_DEMO.md#glossary).

---

## Before You Start

Ensure you are in the repository root:

```sh
cd /path/to/brok-clu-runtime-demo
```

---

## Part A: Runtime Verification and Execution (AUTHORITATIVE)

### Step A.1: Verify PoC v2 Bundle Integrity

```sh
./scripts/verify_poc_v2.sh
```

**Expected exit code:** `0` (verification passed)

**Artifacts created:**
- `artifacts/verify/run_<timestamp>/`

### Step A.2: Execute with a Test Input

Create a test input file:

```sh
echo "restart alpha subsystem gracefully" > /tmp/test_input.txt
```

Run execution:

```sh
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
```

**Expected exit code:** `0` (execution succeeded)

**Artifacts created:**
- `artifacts/run/run_<timestamp>/`
- `artifacts/run/run_<timestamp>/stdout.raw.kv` — **AUTHORITATIVE (runtime)**

### Step A.3: Locate Authoritative Output

Find the most recent run:

```sh
ls -1dt artifacts/run/run_* | head -1
```

View the authoritative output:

```sh
cat "$(ls -1dt artifacts/run/run_* | head -1)/stdout.raw.kv"
```

**Note:** `stdout.raw.kv` is the only authoritative output. All other files are derived.

---

## Part B: Semantic Suite Execution (DERIVED)

### Step B.1: Run the Semantic Suite

```sh
./semantic/scripts/run_semantic_suite.sh
```

**Expected exit code:** `0`

**Artifacts created (generated at runtime, not committed to repository):**
- `semantic/artifacts/SES_SUMMARY.md` — **DERIVED (semantic)**
- `semantic/artifacts/ses_001/execution_index.md` — **DERIVED (semantic)**
- `semantic/artifacts/ses_001/runs/input_*/runtime_ref.txt` — **DERIVED (semantic)**
- `artifacts/run/run_<timestamp>/stdout.raw.kv` — **AUTHORITATIVE (runtime)** (one per input)

### Step B.2: View Suite Summary

```sh
cat semantic/artifacts/SES_SUMMARY.md
```

### Step B.3: View Per-Input Runtime References

```sh
cat semantic/artifacts/ses_001/runs/input_01/runtime_ref.txt
cat semantic/artifacts/ses_001/runs/input_02/runtime_ref.txt
cat semantic/artifacts/ses_001/runs/input_03/runtime_ref.txt
```

**Note:** These reference files are DERIVED. The authoritative output is at the `runtime_run_path` listed in each file.

---

## Part C: Regression Visibility Gate (DERIVED)

### Step C.1: Run Regression Check

```sh
./semantic/regression/run_regression_check.sh
```

**Expected exit code:** `0` (observational only, exits 0 regardless of regression status)

**Artifacts created (generated at runtime, not committed to repository):**
- `semantic/regression/runs/run_<timestamp>/SUMMARY.json` — **DERIVED (semantic)**
- `semantic/regression/runs/run_<timestamp>/INDEX.md` — **DERIVED (semantic)**
- `semantic/regression/runs/run_<timestamp>/per_input/*.json` — **DERIVED (semantic)**
- `semantic/regression/reports/per_input_comparison.md` — **DERIVED (semantic)**
- `semantic/regression/reports/regression_matrix.md` — **DERIVED (semantic)**

### Step C.2: View Regression Summary

Find the most recent regression run:

```sh
ls -1dt semantic/regression/runs/run_* | head -1
```

View summary:

```sh
cat "$(ls -1dt semantic/regression/runs/run_* | head -1)/SUMMARY.json"
```

### Step C.3: View Per-Input Comparison Report

```sh
cat semantic/regression/reports/per_input_comparison.md
```

### Step C.4: View Regression Matrix

```sh
cat semantic/regression/reports/regression_matrix.md
```

---

## Part D: Semantic Equivalence Evaluation (DERIVED)

### Step D.1: Compare Two Runs

Given two existing run directories, compare them under Rule V1:

```sh
./semantic/scripts/semantic_equivalence.sh \
    artifacts/run/run_<timestamp_1> \
    artifacts/run/run_<timestamp_2>
```

**Expected exit code:** `0` (evaluation completed, regardless of outcome)

**Possible outcomes:**
- `EQUIVALENT_UNDER_RULE_V1` — All compared fields match
- `NOT_EQUIVALENT_UNDER_RULE_V1` — At least one field differs
- `UNDECIDABLE_UNDER_RULE_V1` — Missing required field(s)

### Step D.2: Compare Multiple Runs

```sh
./semantic/scripts/semantic_equivalence.sh \
    artifacts/run/run_<timestamp_1> \
    artifacts/run/run_<timestamp_2> \
    artifacts/run/run_<timestamp_3>
```

**Note:** This tool is read-only. It does not execute PoC v2 or modify any files.

See: [CLI_USAGE.md](../equivalence/CLI_USAGE.md) for full usage documentation.

---

## Summary of Output Locations

### Authoritative (Runtime)

| Location | Description |
|----------|-------------|
| `artifacts/run/run_<timestamp>/stdout.raw.kv` | Execution output |

### Derived (Semantic)

| Location | Description |
|----------|-------------|
| `semantic/artifacts/SES_SUMMARY.md` | Suite summary |
| `semantic/artifacts/ses_001/execution_index.md` | Per-SES execution index |
| `semantic/artifacts/ses_001/runs/input_*/runtime_ref.txt` | Runtime references |
| `semantic/regression/runs/run_<timestamp>/SUMMARY.json` | Regression summary |
| `semantic/regression/reports/per_input_comparison.md` | Comparison table |
| `semantic/regression/reports/regression_matrix.md` | Regression matrix |

---

## Exit Codes Reference

| Script | Exit 0 | Exit Non-Zero |
|--------|--------|---------------|
| `verify_poc_v2.sh` | Verification passed | Verification failed or operational error |
| `run_poc_v2.sh` | Execution succeeded | Execution failed or operational error |
| `run_semantic_suite.sh` | Suite completed | Operational error |
| `run_regression_check.sh` | Always (observational) | Operational error (missing baselines, zero eligible) |
| `semantic_equivalence.sh` | Evaluation completed (any outcome) | Operational error (invalid paths, < 2 inputs) |

---

## Notes

- All commands should be run from the repository root
- Timestamps are UTC in format `YYYYMMDDTHHMMSSZ`
- `stdout.raw.kv` is the ONLY authoritative output
- All other outputs are DERIVED and NON-AUTHORITATIVE
- Regression detection is byte-level (SHA-256 comparison)
- No semantic content is expected or validated by this walkthrough

---

*Phase S-4: Integrated Product Demo Planning*
*Semantic Capability Layer — brok-clu-runtime-demo*
