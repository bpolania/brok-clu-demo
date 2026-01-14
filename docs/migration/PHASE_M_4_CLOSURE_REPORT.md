# Phase M-4 Closure Report

## Phase Identity

| Attribute | Value |
|-----------|-------|
| Phase ID | M-4 |
| Codename | Operational Observability and Deterministic Traceability |
| Objective | Add deterministic, derived observability without changing behavior |
| Surface | New `m4/` module, integration hooks in `m3/src/orchestrator.py` |

---

## Executive Summary

Phase M-4 adds operational observability to the Brok-CLU pipeline through deterministic manifest and trace files. All outputs are **DERIVED** and **non-authoritative**—they observe and document pipeline execution without affecting behavior.

**Key Deliverables:**

1. **Run Manifest** (`manifest.json`) - Documents inputs, artifacts, stages, and authority boundaries
2. **Stage Trace** (`trace.jsonl`) - Records stage transitions with monotonic sequence numbers
3. **Deterministic Utilities** - SHA-256 hashing, stable JSON serialization, path normalization
4. **Derived Summary** - Human-readable summary printed to stderr

**Hard Constraints Enforced:**

- No timestamps, machine identifiers, or randomness in outputs
- No absolute paths—all paths are repo-relative or marked `[external]:<basename>`
- No parsing of `stdout.raw.kv`—only hashing permitted (binary mode only)
- Public CLI remains `./brok --input <file>` only
- M-4 does NOT copy or alter external inputs (observation without interference)

---

## Remediation: Blocking Violations Fixed

### V1: Timestamped Path Leakage (FIXED)

**Issue:** M-4 manifest and trace were embedding M-3 timestamped run directory paths like `artifacts/run/run_20260114T173856Z/stdout.raw.kv`. This violated M-4 determinism requirements.

**Fix Applied:**
- Removed `run_directory_rel` field from trace events
- For `stdout.raw.kv`, manifest now records only `type` and `sha256` (no path)
- Added `validate_no_timestamps()` pattern detection for `run_\d{8}T\d{6}Z`
- Trace events are validated on emit, manifest is validated on build

**Verification:** The validators now detect and reject timestamped patterns in strings:
```python
# Patterns detected:
RUN_DIR_TIMESTAMP_PATTERN = re.compile(r'run_\d{8}T\d{6}Z')
ISO_DATETIME_IN_STRING_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
```

### V2: External Input Copying (FIXED)

**Issue:** M-4 integration was copying input files from outside the repo into `artifacts/inputs/` and then re-pointing the pipeline to that copy. This was a behavior change that violated "observation without interference."

**Fix Applied:**
- Removed file copying from `ensure_input_in_artifacts()` → renamed to `get_input_ref()`
- Pipeline now uses user-provided `--input` path exactly as before
- For external inputs, M-4 records `[external]:<basename>` marker (basename only)
- Input `sha256` is always computed from the actual user-provided file

**Confirmation:** M-4 does NOT:
- Copy any files
- Modify any paths used by the pipeline
- Change what file PoC v2 reads

---

## Updated Manifest Format

After remediation, the manifest no longer contains timestamped paths:

```json
{
  "artifacts": [
    {
      "path": "artifacts/artifacts/run_d357c973b734/artifact.json",
      "sha256": "f5614a1ba207a7e736c7897c73039804d864dd0f1487cb7bfacb609e2e0957e1",
      "type": "artifact"
    },
    {
      "path": "artifacts/proposals/run_d357c973b734/proposal_set.json",
      "sha256": "246d5bb7600bf3343378188d010834c4674a6580cdc52d8bfb9d09caa1de78d4",
      "type": "proposal_set"
    },
    {
      "sha256": "4b5b6abd3673cfb3b1d74db0583209d6aa5945c15743b7a090be1329134f5ef4",
      "type": "stdout.raw.kv"
    }
  ],
  "authority_boundary": {
    "authoritative_outputs": ["stdout.raw.kv"],
    "derived_outputs": [
      "artifacts/artifacts/run_d357c973b734/artifact.json",
      "artifacts/proposals/run_d357c973b734/proposal_set.json"
    ]
  },
  "determinism": {
    "no_absolute_paths": true,
    "no_timestamps": true
  },
  "execution": {
    "executed": true
  },
  "inputs": {
    "input_path_rel": "[external]:m4_test.txt",
    "input_sha256": "003e1fb9c632f6bdfc29e548b660122be0e66a4cedbbf1739b32d6069e7479c8"
  },
  "run_id": "m4_d1f58157e15fa328",
  "schema_version": "m4.0",
  "stages": [
    {"name": "PROPOSAL", "outputs": ["artifacts/proposals/run_d357c973b734/proposal_set.json"], "status": "OK"},
    {"name": "ARTIFACT", "outputs": ["artifacts/artifacts/run_d357c973b734/artifact.json"], "status": "OK"},
    {"name": "EXECUTION", "status": "OK"}
  ]
}
```

**Key changes:**
- `stdout.raw.kv` artifact has no `path` field (avoids timestamped M-3 run dir)
- External inputs use `[external]:<basename>` marker
- `execution.executed` field explicitly records whether PoC v2 ran
- EXECUTION stage has no `outputs` field (avoids timestamped paths)

---

## Updated Trace Format

After remediation, trace events do not contain `run_directory_rel`:

```json
{"detail": {"input_path_rel": "[external]:m4_test.txt", "input_sha256": "003e1fb9c632f6bdfc29e548b660122be0e66a4cedbbf1739b32d6069e7479c8"}, "event": "M4_RUN_START", "seq": 0, "stage": "INIT"}
{"detail": {"path_rel": "artifacts/proposals/run_d357c973b734/proposal_set.json", "proposal_count": 1, "sha256": "..."}, "event": "PROPOSAL_GENERATED", "seq": 1, "stage": "PROPOSAL"}
{"detail": {"decision": "ACCEPT", "path_rel": "artifacts/artifacts/run_d357c973b734/artifact.json", "sha256": "..."}, "event": "ARTIFACT_WRITTEN", "seq": 2, "stage": "ARTIFACT"}
{"detail": {"decision": "ACCEPT"}, "event": "GATE_ACCEPT", "seq": 3, "stage": "GATE"}
{"event": "EXECUTION_STARTED", "seq": 4, "stage": "EXECUTION"}
{"detail": {"executed": true, "exit_code": 0, "stdout_raw_kv_sha256": "4b5b6abd3673cfb3b1d74db0583209d6aa5945c15743b7a090be1329134f5ef4"}, "event": "EXECUTION_COMPLETE", "seq": 5, "stage": "EXECUTION"}
{"detail": {"run_id": "m4_d1f58157e15fa328"}, "event": "M4_RUN_COMPLETE", "seq": 6, "stage": "COMPLETE"}
```

**Key changes:**
- No `run_directory_rel` in EXECUTION_COMPLETE
- `executed: true/false` explicitly recorded
- `stdout_raw_kv_sha256` recorded without path
- External inputs use `[external]:<basename>` marker

---

## Test Results

### M-4 Unit Tests (52 tests)

```
$ python3 -m unittest m4.tests.test_m4 -v
Ran 52 tests in 12.5s
OK
```

| Test Class | Tests | Status |
|------------|-------|--------|
| TestSha256Determinism | 4 | PASS |
| TestRelPathDeterminism | 5 | PASS |
| TestValidationFunctions | 9 | PASS |
| TestStableJson | 5 | PASS |
| TestRunIdDerivation | 4 | PASS |
| TestManifestBuilder | 3 | PASS |
| TestTraceWriter | 4 | PASS |
| TestEndToEndDeterminism | 2 | PASS |
| TestTimestampPatternDetection | 4 | PASS |
| TestE2EDeterminismCLI | 2 | PASS |
| TestRealOutputValidation | 4 | PASS |
| TestStdoutRawKvBinaryOnly | 2 | PASS |
| TestAuthoritativeOutputsW1 | 3 | PASS |
| TestStdoutRawKvBinaryOnlyRuntime | 1 | PASS |
| **Total** | **52** | **All Pass** |

### New Proof Tests Added

1. **E2E Determinism (CLI):** Runs `./brok --input` twice with identical input, verifies `manifest.json` and `trace.jsonl` are byte-for-byte identical.

2. **Real Output Validation:** After CLI run, loads manifest and trace, validates no absolute paths or timestamps in any field.

3. **Binary-Only Enforcement:** Verifies `sha256_file()` uses binary mode (`'rb'`), ensures `stdout.raw.kv` is never opened in text mode.

4. **Timestamp Pattern Detection:** Tests that `run_YYYYMMDDTHHMMSSZ` patterns are detected and rejected.

### M-3 Invariant Tests

```
$ python3 -m unittest m3.tests.test_invariants -v
Ran 29 tests in 13.587s
OK (skipped=1)
```

---

## Determinism Gates

### Gate 1: No Absolute Paths

**Validation:** `utils.validate_no_absolute_paths()` - recursive string scan for Unix (`/`), Windows (`C:\`), and UNC (`\\`) paths.

### Gate 2: No Timestamps

**Validation:** `utils.validate_no_timestamps()` - checks for:
- Timestamp key names (exact match)
- ISO 8601 datetime patterns in strings
- M-3 run directory patterns (`run_\d{8}T\d{6}Z`)
- Epoch-like integers

### Gate 3: Stable JSON Output

**Serialization:** `utils.stable_json_dumps()` - sorted keys, 2-space indent, newline terminated.

### Gate 4: Content-Based Run ID

**Derivation:** `utils.derive_run_id()` - `sha256(input_sha + proposal_sha + artifact_sha + "m4")[:16]`

### Gate 5: Binary-Only File Access

**Enforcement:** `sha256_file()` uses `'rb'` mode only. M-4 never parses `stdout.raw.kv`.

---

## Guardrails Checklist

| # | Constraint | Enforced |
|---|------------|----------|
| G1 | All M-4 outputs are DERIVED, read-only, observational | ✓ |
| G2 | No timestamps in manifest or trace | ✓ Validated on build/emit |
| G3 | No absolute paths in outputs | ✓ Validated on build/emit |
| G4 | No machine identifiers | ✓ |
| G5 | Run ID derived from content hashes | ✓ |
| G6 | stdout.raw.kv only hashed, never parsed | ✓ Binary mode enforced |
| G7 | Public CLI unchanged (`./brok --input <file>`) | ✓ |
| G8 | M-4 optional—graceful degradation if unavailable | ✓ |
| G9 | No behavior changes to M-0 through M-3 | ✓ |
| G10 | All M-4 outputs under artifacts/ and gitignored | ✓ |
| G11 | M-4 does NOT copy external inputs | ✓ Fixed |
| G12 | M-4 does NOT depend on M-3 timestamped run dirs | ✓ Fixed |
| G13 | authoritative_outputs reflects stdout.raw.kv when executed | ✓ W1 Fixed |
| G14 | Binary-only enforcement verified at runtime | ✓ W2 Fixed |

---

## Files Modified in Remediation

| File | Change |
|------|--------|
| `m4/src/utils.py` | Added timestamp pattern detection in strings |
| `m4/src/manifest.py` | Added `omit_path` option, `record_execution()` method, W1 authority fix |
| `m4/src/trace.py` | Removed `run_directory_rel`, added `executed` field, validation on emit |
| `m4/src/observability.py` | Updated to use new manifest/trace interfaces |
| `m3/src/orchestrator.py` | Renamed `ensure_input_in_artifacts` → `get_input_ref` (no copying) |
| `m4/tests/test_m4.py` | Added 16 proof tests total (12 V1/V2 + 4 W1/W2) |

---

## Post-Remediation Tightening

### W1: Authority Boundary Completeness (FIXED)

**Issue:** After V1/V2 remediation, `authoritative_outputs` was empty even when execution occurred and `stdout.raw.kv` was hashed. This contradicted the authority model where `stdout.raw.kv` is the sole authoritative output.

**Fix Applied:**
- Modified `add_artifact()` in `manifest.py` to add `artifact_type` to `_authoritative_outputs` when `authoritative=True` and `omit_path=True`
- For executed runs, `authoritative_outputs` now contains `["stdout.raw.kv"]`
- For skipped runs (no execution), `authoritative_outputs` remains empty

**Authority Model Clarification:**
- `stdout.raw.kv` = **AUTHORITATIVE** (runtime ground truth from PoC v2)
- `artifact.json` = DERIVED (wrapper decision summary)
- `proposal_set.json` = DERIVED (LLM proposals)
- `manifest.json` / `trace.jsonl` = DERIVED (M-4 observability)

### W2: Binary-Only Enforcement Strengthened (FIXED)

**Issue:** The existing binary-only test (`TestStdoutRawKvBinaryOnly`) only did source code inspection. A runtime test that actually monitors file open modes provides stronger guarantees.

**Fix Applied:**
- Added `TestStdoutRawKvBinaryOnlyRuntime` test class
- Uses a wrapper script that monkeypatches `builtins.open()` during CLI execution
- Fails immediately if `stdout.raw.kv` is opened in text mode (without `'b'`)
- Passes if all opens of `stdout.raw.kv` are binary mode

### Tests Added

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestAuthoritativeOutputsW1 | 3 | Verify authority boundary correctness |
| TestStdoutRawKvBinaryOnlyRuntime | 1 | Runtime binary-mode enforcement |
| **Total New** | **4** | |

### Updated Manifest Example

After W1 fix, executed runs show `stdout.raw.kv` in `authoritative_outputs`:

```json
"authority_boundary": {
  "authoritative_outputs": ["stdout.raw.kv"],
  "derived_outputs": [
    "artifacts/artifacts/run_d357c973b734/artifact.json",
    "artifacts/proposals/run_d357c973b734/proposal_set.json"
  ]
}
```

---

## Conclusion

Phase M-4 remediation is complete:

- **V1 FIXED:** M-4 no longer embeds timestamped M-3 run directory paths
- **V2 FIXED:** M-4 no longer copies or alters external inputs
- **W1 FIXED:** `authoritative_outputs` correctly contains `"stdout.raw.kv"` for executed runs
- **W2 FIXED:** Binary-only enforcement verified at runtime with monkeypatched `open()`
- **52 tests** verify determinism properties (16 proof tests total)
- **29 M-3 tests** continue to pass (no regression)
- E2E determinism verified: identical inputs produce byte-for-byte identical outputs

The pipeline now produces fully deterministic, relocatable observability outputs that:
- Do not depend on M-3 timestamped run directories
- Do not interfere with pipeline behavior
- Correctly represent the authority model (`stdout.raw.kv` as authoritative)
- Enforce binary-only access to execution outputs

---

*Report updated after post-remediation tightening (W1/W2)*
*Branch: refactor/migration-phases*
