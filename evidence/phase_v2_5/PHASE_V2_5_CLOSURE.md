# Phase V2-5 — Determinism Validation (Closure)

## Status

- **Phase:** V2-5
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Objective

Phase V2-5 makes PoC v2's determinism **observable, testable, and auditable** at the demo-wrapper level, without modifying or reinterpreting PoC v2 behavior.

This phase introduces repeat execution and comparison only. It does not introduce new guarantees; it exposes an existing one.

---

## Determinism Validation Model

### Invocation

```sh
scripts/determinism_test_v2.sh --input <PATH_TO_INPUT_FILE> --runs <N>
```

Where:
- `<PATH_TO_INPUT_FILE>` is the input to test
- `<N>` is the number of runs (minimum 2)

### Run Count Handling

- Minimum: 2 runs required
- Each run uses the unchanged Phase V2-3 single-run path
- Each run performs full verification and execution (no caching)
- No flags, environment changes, or alternate code paths per run

### Baseline Selection

- The first successful run becomes the baseline
- Baseline `stdout.raw.kv` is copied to `baseline/` directory
- All subsequent runs are compared against this baseline

### Comparison Rules

**Comparison target (authoritative):**
- ONLY `stdout.raw.kv` is compared

**NOT compared:**
- `stderr.raw.txt`
- `exit_code.txt` (beyond success/failure)
- `execution.meta.json`
- `stdout.derived.json`
- Timestamps or paths

**Comparison method:**
- Byte-for-byte comparison using `cmp`
- No normalization
- No trimming
- No semantic interpretation
- Any byte difference constitutes a failure

---

## Exit Codes and Failure Semantics

| Exit Code | Meaning |
|-----------|---------|
| 0 | **PASS**: All runs produced identical `stdout.raw.kv` |
| 1 | **FAIL**: Output mismatch detected |
| 2 | Usage error |
| 3 | **FAIL**: Verification or execution error (mixed success/failure) |

### Failure Definitions

**PASS (exit 0):**
- All N runs completed successfully (verification passed, execution completed)
- All N `stdout.raw.kv` files are byte-identical

**FAIL - Output Mismatch (exit 1):**
- All runs completed successfully
- At least one `stdout.raw.kv` differs from baseline
- First mismatch run is identified and reported

**FAIL - Verification/Execution Error (exit 3):**
- At least one run failed verification or execution
- Mixed success/failure is not allowed
- First failing run is identified and reported

**Usage Error (exit 2):**
- Invalid arguments
- Missing required options
- Run count < 2

### No Silent Failures

- Every run's status is recorded
- First observed failure is explicitly identified
- Summary and result files always indicate pass/fail with reason

---

## Determinism Artifact Layout

For each test, artifacts are created under:
```
artifacts/determinism/test_<UTC_TIMESTAMP>/
```

### Directory Structure

```
artifacts/determinism/test_<UTC_TIMESTAMP>/
├── baseline/
│   ├── stdout.raw.kv              # First successful run output (authoritative)
│   └── stdout.raw.kv.sha256       # SHA-256 hash for auditing
├── run_001/
│   ├── stdout.raw.kv              # Run 1 output copy
│   ├── stdout.raw.kv.sha256       # SHA-256 hash
│   ├── exit_code.txt              # Wrapper exit code
│   ├── source_run_dir.txt         # Path to original run directory
│   ├── wrapper_stdout.txt         # Wrapper console output
│   └── wrapper_stderr.txt         # Wrapper console errors
├── run_002/
│   └── ... (same structure)
├── run_NNN/
│   └── ... (same structure)
├── summary.txt                    # Human-readable summary
└── result.txt                     # PASS or FAIL with reason
```

### Summary File Contents

```
Determinism Test Summary
========================
Test directory: <path>
Input file: <path>
Run count: <N>
Started: <UTC timestamp>

Comparison target: stdout.raw.kv (byte-for-byte, no normalization)
Comparison method: cmp (binary comparison)

Run 001: completed (exit_code=0, sha256=<hash>)

Baseline: run_001 (sha256=<hash>)

Run 002: completed (exit_code=0, sha256=<hash>)
Run 003: completed (exit_code=0, sha256=<hash>)
...

Completed: <UTC timestamp>

RESULT: PASS
All N runs produced identical stdout.raw.kv
```

### Result File Contents

Single line:
- `PASS: All N runs produced identical stdout.raw.kv`
- `FAIL: Output mismatch detected (first at run N)`
- `FAIL: Verification or execution error (run N: <reason>)`

---

## Attestations

### No Execution Changes
- The Phase V2-3 single-run execution path is reused verbatim
- No flags, environment changes, or alternate code paths per run
- Each iteration runs full verification (no caching)

### No Output Reinterpretation
- No parsing of key=value content
- No inference of ACCEPT/REJECT meaning
- No comparison of derived outputs
- Byte-for-byte comparison only

### No Performance Metrics
- No timing recorded
- No benchmarking
- No duration comparisons

### Failure Coupling
- If any run fails verification or execution while others succeed, determinism test fails
- Mixed success/failure is not allowed

### Comparison Method Unambiguous
- `cmp` binary comparison
- Any byte difference = failure
- No normalization or interpretation

### Prior Phase Constraints Preserved
- Phase V2-2 verification remains mandatory per run
- Phase V2-3 execution semantics unchanged
- Phase V2-4 output schema unchanged
- PoC v2 not modified

---

## Verification Procedure (for auditors)

### 1. Run determinism test

```sh
echo "turn on the lights" > /tmp/test_input.txt
./scripts/determinism_test_v2.sh --input /tmp/test_input.txt --runs 5
echo "Exit code: $?"
```

### 2. Locate test directory

```sh
TEST_DIR=$(ls -td artifacts/determinism/test_* | head -1)
```

### 3. Verify artifacts exist

```sh
ls -la "$TEST_DIR"
ls -la "$TEST_DIR/baseline"
ls -la "$TEST_DIR/run_001"
```

### 4. Verify all stdout.raw.kv are identical

```sh
for f in "$TEST_DIR"/run_*/stdout.raw.kv; do
    cmp -s "$TEST_DIR/baseline/stdout.raw.kv" "$f" && echo "OK: $f" || echo "MISMATCH: $f"
done
```

### 5. Verify SHA-256 hashes match

```sh
cat "$TEST_DIR/baseline/stdout.raw.kv.sha256"
for f in "$TEST_DIR"/run_*/stdout.raw.kv.sha256; do cat "$f"; done
```

### 6. Review summary and result

```sh
cat "$TEST_DIR/summary.txt"
cat "$TEST_DIR/result.txt"
```

---

## Files Added

| File | Purpose |
|------|---------|
| `scripts/determinism_test_v2.sh` | Determinism validation script |
| `evidence/phase_v2_5/PHASE_V2_5_CLOSURE.md` | Phase closure attestation |

---

## Test Evidence

### PASS Case (3 runs)

```
determinism_test: directory=artifacts/determinism/test_20260107T163709Z
determinism_test: input=/tmp/test_input.txt
determinism_test: runs=3

determinism_test: run 1 of 3
determinism_test: run 1 completed (exit_code=0)
determinism_test: baseline set from run 1

determinism_test: run 2 of 3
determinism_test: run 2 completed (exit_code=0)

determinism_test: run 3 of 3
determinism_test: run 3 completed (exit_code=0)

determinism_test: PASS (all 3 runs identical)
Exit code: 0
```

### FAIL Case (verification error)

```
determinism_test: run 1 FAILED - verification failed
determinism_test: run 2 FAILED - verification failed
determinism_test: FAIL (verification/execution error at run 1)
Exit code: 3
```

---

## Closure

Phase V2-5 complete and frozen.

Determinism validation is operational:
1. Users can run determinism tests from any directory
2. Identical inputs produce identical `stdout.raw.kv` across all runs
3. Any deviation produces a clear, reproducible failure
4. Determinism results are inspectable and auditable on disk
5. There is no ambiguity about what was compared or why it passed or failed

**Comparison method:** Byte-for-byte via `cmp`
**Comparison target:** `stdout.raw.kv` only
**No semantic interpretation introduced**
**No execution, verification, or output semantics changed**
