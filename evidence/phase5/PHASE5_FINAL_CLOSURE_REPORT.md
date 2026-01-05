# Phase 5 — Determinism Validation & Repeatability (Complete)

## Status

- **Phase:** 5
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Determinism Invocation Form

```
./run.sh --determinism-test --input <file> --runs <N>
```

Where:
- `<file>` is the input file path
- `<N>` is the number of repeated runs (positive integer)

---

## Artifact Paths Produced

| Artifact | Path |
|----------|------|
| Per-run raw output | `artifacts/determinism/run_001/output.raw.kv` |
| Per-run raw output | `artifacts/determinism/run_002/output.raw.kv` |
| ... | ... |
| Summary | `artifacts/determinism/summary.txt` |

---

## 1. Artifact Exclusion from Version Control

### .gitignore Contents (Verbatim)

The complete `.gitignore` file contains exactly:

```
# Demo-layer output artifacts (generated at runtime)
artifacts/
```

### Analysis

- The rule `artifacts/` matches any directory named `artifacts` and all contents recursively.
- This covers `artifacts/determinism/**` and `artifacts/last_run/**`.
- **No negation rules (`!`) exist** in the file that could re-include `artifacts/determinism/**`.

### Conclusion

Determinism artifacts under `artifacts/determinism/` cannot appear as untracked files in `git status`. The existing rule is sufficient; no changes required.

---

## 2. Failure Detection Mechanism (Implementation-Tied)

### Baseline File

The baseline is the first run's raw output:
- Variable: `FIRST_OUTPUT`
- Path: `artifacts/determinism/run_001/output.raw.kv`
- Set at: `run.sh` line 241

### Comparison Method

Byte-for-byte comparison using:
```sh
diff -q "$FIRST_OUTPUT" "$RUN_DIR/output.raw.kv"
```
(Line 244 of `run.sh`)

### Mismatch Definition

A mismatch occurs when `diff -q` returns non-zero exit code, meaning the files differ in any byte.

### First Mismatch Recording

When a mismatch is detected:
```sh
if [ "$DETERMINISM_PASS" -eq 1 ]; then
    FIRST_MISMATCH_A=1
    FIRST_MISMATCH_B=$i
fi
DETERMINISM_PASS=0
```
(Lines 248-252 of `run.sh`)

The first mismatch is recorded as "run 1 vs run $i" and written to `summary.txt`.

### Exit Code on Mismatch

```sh
exit 1
```
(Line 289 of `run.sh`)

---

## 3. Mixed Success/Failure Handling (Implementation-Tied)

### Failure Detection

If a run fails to produce output (no `artifacts/last_run/output.raw.kv` created):
```sh
if [ -f "$RAW_OUTPUT" ]; then
    cp "$RAW_OUTPUT" "$RUN_DIR/output.raw.kv"
else
    FAILED_RUNS="$FAILED_RUNS $i"
    DETERMINISM_PASS=0
    echo "  Run $i: FAILED (no output)"
    continue
fi
```
(Lines 223-231 of `run.sh`)

### Recording Failed Run Indices

Failed run indices are appended to `FAILED_RUNS` variable (space-separated list).

### Exit Code on Any Failure

```sh
if [ "$DETERMINISM_PASS" -eq 1 ]; then
    echo ""
    echo "DETERMINISM TEST PASSED"
    exit 0
else
    echo ""
    echo "DETERMINISM TEST FAILED"
    exit 1
fi
```
(Lines 282-290 of `run.sh`)

### No Partial Success States

- `DETERMINISM_PASS` starts at 1
- Any mismatch or failure sets `DETERMINISM_PASS=0`
- Final exit is binary: `exit 0` (all identical) or `exit 1` (any failure)
- No intermediate states exist

---

## 4. Runtime Invocation Invariance

### Attestation

Determinism mode does **not** change the runtime invocation.

### The Only Runtime Command Executed

In both single-run and determinism modes, the only command that invokes the runtime is:

```sh
"$BINARY" --input "$INPUT_FILE"
```
(Line 129 of `run.sh`)

Where `BINARY` is defined as:
```sh
BINARY="$BUNDLE_DIR/bin/macos-arm64/cmd_interpreter"
```
(Line 7 of `run.sh`)

This expands to:
```
bundles/poc_v1/bin/macos-arm64/cmd_interpreter --input <file>
```

### What Determinism Mode Does

Determinism mode:
1. Calls the unchanged `run_single_execution` function N times in a loop
2. Copies `artifacts/last_run/output.raw.kv` to `artifacts/determinism/run_XXX/output.raw.kv` after each run
3. Compares each run's output against the baseline using `diff -q`

It does **not**:
- Change runtime invocation flags
- Manipulate environment variables
- Alter verification logic
- Modify execution wiring
- Change output handling semantics

---

## Semantics Preservation Statement

The following semantics from prior phases were NOT modified:

- **Verification logic** (Phase 3): Unchanged. Runs once before any execution.
- **Execution wiring** (Phase 3): Unchanged. Invocation: `cmd_interpreter --input <file>`
- **Output handling** (Phase 4): Unchanged. `artifacts/last_run/output.raw.kv` and `output.derived.json` behavior preserved.
- **Exit code behavior** (Phase 3): Unchanged. Passthrough of runtime exit codes in single-run mode.

---

## How to Reproduce

```sh
# Single-run mode (unchanged from Phase 4)
./run.sh examples/inputs/accept_restart_alpha_1.txt

# Determinism test mode (Phase 5)
./run.sh --determinism-test --input examples/inputs/accept_restart_alpha_1.txt --runs 5

# Inspect results
cat artifacts/determinism/summary.txt
diff artifacts/determinism/run_001/output.raw.kv artifacts/determinism/run_002/output.raw.kv
```

---

## Closure

Phase 5 is complete. All four audit questions are explicitly answered with implementation references. Determinism validation is operational. Verification, execution, and output semantics remain unchanged from prior phases.
