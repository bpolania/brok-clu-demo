# Phase L-7 Baseline Findings (Read-Only Reconnaissance)

## 1. Wrapper Entrypoint Location

**File**: `brok-run` (repo root)
**Type**: Python 3 script (shebang: `#!/usr/bin/env python3`)

## 2. Current Delta-Only Discovery Implementation (L-6)

### Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `_snapshot_run_dirs()` | brok-run:58-63 | Snapshot immediate child directories of `artifacts/run/` |
| `_compute_delta()` | brok-run:66-68 | Compute `after - before` directory set |
| `_find_authoritative_dirs()` | brok-run:71-87 | Find directories in delta containing `stdout.raw.kv` |
| `_get_stdout_raw_kv()` | brok-run:141-149 | Get path and SHA256 of `stdout.raw.kv` in a directory |

### Discovery Flow (L-6 Path A)

1. Snapshot `artifacts/run/` before `./brok` invocation
2. Invoke `./brok --input <file>`
3. Snapshot `artifacts/run/` after invocation
4. Compute delta (new directories)
5. Find directories in delta containing `stdout.raw.kv`
6. Selection rule:
   - 0 authoritative dirs in delta → `authoritative_stdout_raw_kv: null`
   - 1 authoritative dir in delta → use it
   - >1 authoritative dirs in delta → fail closed (contract violation)

## 3. Output Schema Location

**Location**: brok-run:263-269

```python
summary = {
    "run_dir": run_dir,
    "decision": decision,
    "authoritative_stdout_raw_kv": authoritative_path,
    "authoritative_stdout_raw_kv_sha256": authoritative_hash,
}
```

## 4. Artifacts/Run Layout

### Directory Structure

```
artifacts/run/
├── l4_run_run_<hash>/          # Execution directories (contain stdout.raw.kv)
│   ├── execution.meta.json
│   ├── exit_code.txt
│   ├── stderr.raw.txt
│   └── stdout.raw.kv           # Authoritative execution output
├── m4_<hash>/                  # Observability directories (contain manifest)
│   ├── manifest.json
│   └── trace.jsonl
└── run_<timestamp>/            # Legacy run directories
    └── stdout.raw.kv
```

### Key Files

| File | Location | Written By | Contains |
|------|----------|------------|----------|
| `stdout.raw.kv` | `l4_run_run_*/` or `run_*/` | `./brok` | Authoritative execution output |
| `manifest.json` | `m4_*/` | `./brok` | Run metadata including SHA256 of stdout.raw.kv |
| `trace.jsonl` | `m4_*/` | `./brok` | Execution trace with SHA256 references |
| `execution.meta.json` | `l4_run_run_*/` | `./brok` | Execution metadata |

## 5. Stable Pointer in Manifest

The `manifest.json` written by `./brok` contains a **deterministic pointer** to the authoritative output:

```json
{
  "artifacts": [
    {
      "sha256": "3ecd09728ac483be4f8ed500114fd0458efa7005d8c54fa0a6730ecad58a3f2a",
      "type": "stdout.raw.kv"
    }
  ]
}
```

This SHA256 hash is:
- Deterministic (content-based)
- Written by `./brok` (not wrapper)
- Immutable once written
- Can be used to match against actual `stdout.raw.kv` files

## 6. Current Failure Mode

**Condition**: ACCEPT decision but `authoritative_stdout_raw_kv: null`

**Cause**: Delta-only discovery (L-6 Path A) does not find `stdout.raw.kv` in newly created directories when:
- The execution directory already existed (content-addressed idempotent storage)
- The execution directory is not in the filesystem delta

**Current Behavior**:
- Warning printed to stderr
- JSON reports `authoritative_stdout_raw_kv: null`
- Console shows `Authoritative output: NONE`

## 7. L-7 Opportunity

The manifest contains a SHA256 hash of `stdout.raw.kv`. This enables expanded discovery:

1. If delta-only fails, read the SHA256 from the manifest
2. Scan all `stdout.raw.kv` files under `artifacts/run/`
3. Match by SHA256 (deterministic, no timestamps)
4. Report outcome: UNIQUE (exactly 1 match), NONE (0 matches), AMBIGUOUS (>1 matches)

## 8. Counts

| Item | Count |
|------|-------|
| Total `stdout.raw.kv` files under `artifacts/run/` | 498 |
| Observability directories (`m4_*`) | ~700 |
| Execution directories (`l4_run_run_*`) | 7 |

---

**Baseline established. No changes made to codebase.**
