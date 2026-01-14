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
- No absolute paths—all paths are repo-relative
- No parsing of `stdout.raw.kv`—only hashing permitted
- Public CLI remains `./brok --input <file>` only

---

## Artifacts Created

### Source Files

| File | Purpose |
|------|---------|
| `m4/src/__init__.py` | Package marker |
| `m4/src/utils.py` | Deterministic utilities (sha256, stable JSON, rel path) |
| `m4/src/manifest.py` | ManifestBuilder class |
| `m4/src/trace.py` | TraceWriter class |
| `m4/src/observability.py` | PipelineObserver unified interface |
| `m4/tests/__init__.py` | Test package marker |
| `m4/tests/test_m4.py` | Determinism and regression tests (36 tests) |

### Integration Points

| File | Change |
|------|--------|
| `m3/src/orchestrator.py` | Added `_get_observer()` and observer hook calls |

### Runtime Outputs (Generated, Gitignored)

| Output | Location |
|--------|----------|
| Run Manifest | `artifacts/run/<run_id>/manifest.json` |
| Stage Trace | `artifacts/run/<run_id>/trace.jsonl` |

---

## Determinism Gates

### Gate 1: No Absolute Paths

**Validation Function:** `utils.validate_no_absolute_paths()`

Checks for:
- Unix paths starting with `/`
- Windows drive paths (e.g., `C:\...`)
- UNC paths (e.g., `\\server\...`)

```python
def is_absolute_path(path: str) -> bool:
    if os.path.isabs(path):
        return True
    if len(path) >= 2 and path[1] == ':':
        return True
    if path.startswith('\\\\'):
        return True
    return False
```

### Gate 2: No Timestamps

**Validation Function:** `utils.validate_no_timestamps()`

Checks for:
- Exact timestamp key names (`timestamp`, `created_at`, `modified_at`, etc.)
- ISO 8601 datetime strings (`YYYY-MM-DDTHH:MM:SS`)
- Unix epoch integers (1000000000 < value < 4000000000)

### Gate 3: Stable JSON Output

**Serialization Function:** `utils.stable_json_dumps()`

Properties:
- Keys sorted alphabetically at all levels
- Consistent 2-space indentation
- Newline at end of file
- UTF-8 encoding

### Gate 4: Content-Based Run ID

**Derivation Function:** `utils.derive_run_id()`

```python
def derive_run_id(input_sha, proposal_sha, artifact_sha) -> str:
    hasher = hashlib.sha256()
    hasher.update(input_sha.encode('utf-8'))
    hasher.update((proposal_sha or '').encode('utf-8'))
    hasher.update((artifact_sha or '').encode('utf-8'))
    hasher.update(b'm4')
    return f"m4_{hasher.hexdigest()[:16]}"
```

---

## Test Results

### M-4 Unit Tests

```
$ python3 -m unittest m4.tests.test_m4 -v
Ran 36 tests in 0.007s
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
| **Total** | **36** | **All Pass** |

### M-3 Invariant Tests

```
$ python3 -m unittest m3.tests.test_invariants -v
Ran 29 tests in 12.938s
OK (skipped=1)
```

### Repository Invariants

| Check | Result |
|-------|--------|
| PoC v2 tarball hash | `7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a` ✓ |
| Frozen scripts unchanged | ✓ |
| artifacts/ gitignored | ✓ |

---

## Integration Verification

### Test Run: ACCEPT Path

```
$ echo "restart alpha subsystem gracefully" > /tmp/m4_test.txt
$ ./brok --input /tmp/m4_test.txt
```

**Output (stderr excerpt):**
```
========================================================================
[DERIVED] M-4 Observability Summary
========================================================================
  Run ID: m4_c2e43c1666211f7c
  Manifest: artifacts/run/m4_c2e43c1666211f7c/manifest.json
  Trace: artifacts/run/m4_c2e43c1666211f7c/trace.jsonl

  NOTE: This summary is DERIVED and non-authoritative.
        Only stdout.raw.kv is authoritative for runtime truth.
========================================================================
```

**Generated manifest.json:**
```json
{
  "artifacts": [...],
  "authority_boundary": {
    "authoritative_outputs": ["artifacts/run/.../stdout.raw.kv"],
    "derived_outputs": ["artifacts/artifacts/.../artifact.json", ...]
  },
  "determinism": {
    "no_absolute_paths": true,
    "no_timestamps": true
  },
  "inputs": {
    "input_path_rel": "artifacts/inputs/.../input.raw",
    "input_sha256": "..."
  },
  "run_id": "m4_c2e43c1666211f7c",
  "schema_version": "m4.0",
  "stages": [...]
}
```

**Generated trace.jsonl:**
```
{"detail": {...}, "event": "M4_RUN_START", "seq": 0, "stage": "INIT"}
{"detail": {...}, "event": "PROPOSAL_GENERATED", "seq": 1, "stage": "PROPOSAL"}
{"detail": {...}, "event": "ARTIFACT_WRITTEN", "seq": 2, "stage": "ARTIFACT"}
{"detail": {...}, "event": "GATE_ACCEPT", "seq": 3, "stage": "GATE"}
{"event": "EXECUTION_STARTED", "seq": 4, "stage": "EXECUTION"}
{"detail": {...}, "event": "EXECUTION_COMPLETE", "seq": 5, "stage": "EXECUTION"}
{"detail": {...}, "event": "M4_RUN_COMPLETE", "seq": 6, "stage": "COMPLETE"}
```

---

## Guardrails Checklist

| # | Constraint | Enforced |
|---|------------|----------|
| G1 | All M-4 outputs are DERIVED, read-only, observational | ✓ |
| G2 | No timestamps in manifest or trace | ✓ Validated on build |
| G3 | No absolute paths in outputs | ✓ Validated on build |
| G4 | No machine identifiers | ✓ |
| G5 | Run ID derived from content hashes | ✓ |
| G6 | stdout.raw.kv only hashed, never parsed | ✓ |
| G7 | Public CLI unchanged (`./brok --input <file>`) | ✓ |
| G8 | M-4 optional—graceful degradation if unavailable | ✓ |
| G9 | No behavior changes to M-0 through M-3 | ✓ |
| G10 | All M-4 outputs under artifacts/ and gitignored | ✓ |

---

## Authority Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Authority Hierarchy                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AUTHORITATIVE (Runtime Truth)                                      │
│  └── stdout.raw.kv                                                  │
│                                                                     │
│  WRAPPER DECISION (Boundary Authority)                              │
│  └── artifact.json                                                  │
│                                                                     │
│  DERIVED (Observational, Non-Authoritative)                         │
│  ├── manifest.json    (M-4)                                         │
│  ├── trace.jsonl      (M-4)                                         │
│  ├── proposal_set.json                                              │
│  └── CLI output summaries                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Files Summary

### Added (7 files)

- `m4/src/__init__.py`
- `m4/src/utils.py`
- `m4/src/manifest.py`
- `m4/src/trace.py`
- `m4/src/observability.py`
- `m4/tests/__init__.py`
- `m4/tests/test_m4.py`

### Modified (1 file)

- `m3/src/orchestrator.py` (added observer integration)

---

## Conclusion

Phase M-4 is complete. Deterministic observability has been added to the pipeline:

- **36 unit tests** verify determinism properties
- **29 M-3 tests** continue to pass (no regression)
- All outputs are **DERIVED** and clearly marked as non-authoritative
- No changes to frozen files or PoC v2 behavior
- Public CLI surface unchanged

The pipeline now produces reproducible manifest and trace files that can be used for debugging, auditing, and operational visibility—while maintaining strict separation from authoritative runtime truth.

---

*Report generated for Phase M-4 implementation*
*Branch: main*
