# Phase L-7 Closure Report

## Executive Summary

Phase L-7 implements expanded discovery for the brok-run wrapper. When delta-only
discovery (L-6 behavior) fails to locate authoritative output for an ACCEPT decision,
the wrapper uses deterministic SHA256 matching from the manifest to search for
`stdout.raw.kv` files under `artifacts/run/`.

**Closure Status: READY (conditional on uniqueness)**

---

## 1. L-7 Contract Scope

### What Changed (Wrapper-Only)

| Component | Change |
|-----------|--------|
| `brok-run` | Added expanded discovery via SHA256 matching |
| `brok-run` | Added `discovery_status` field to JSON schema |
| `brok-run` | Added disclaimer to stderr |
| Tests | New L-7 test suite (12 tests) |
| Docs | Updated contract and closure documentation |
| Evidence | New evidence directory with captured outputs |

### What Did NOT Change

- `./brok` remains byte-identical to L-4 closure
- No new CLI flags, environment variables, or invocation forms
- No new authoritative outputs
- Wrapper remains derived and non-authoritative

---

## 2. Frozen JSON Schema (5 Fields)

The wrapper JSON schema is frozen with exactly 5 keys:

| Field | Type | Description |
|-------|------|-------------|
| `run_dir` | string | Path to observability or authoritative directory |
| `decision` | string | "ACCEPT" or "REJECT" |
| `authoritative_stdout_raw_kv` | string \| null | Path to stdout.raw.kv or null |
| `authoritative_stdout_raw_kv_sha256` | string \| null | SHA-256 hash or null |
| `discovery_status` | string | Locator outcome |

**Schema lock test**: `test_l7_schema_lock()` asserts exact key set.

---

## 3. Manifest Governance Status

### Classification: DERIVED OBSERVABILITY OUTPUT

**Producer**: `m4/src/manifest.py` (ManifestBuilder class)
- Written during `./brok` execution
- NOT written by the wrapper (`brok-run`)

**Wrapper Treatment**:
- Reads manifest for discovery hints only
- Does NOT trust manifest as authoritative truth
- Uses SHA256 from manifest to search for matching files

**Evidence**: `test_l7_manifest_origin_proof()` verifies:
- ManifestBuilder exists in `m4/src/manifest.py`
- ManifestBuilder does NOT exist in `brok-run`
- Wrapper only reads manifest, does not write

**When Manifest is Missing/Malformed**:
- Expanded discovery returns NONE
- `discovery_status` becomes `authoritative_not_found`
- Wrapper gracefully degrades (no failure)

---

## 4. Verification Results

### Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| L-5 | 14 | PASS |
| L-6 | 10 | PASS |
| L-7 | 12 | PASS |
| **Total** | **36** | **PASS** |

### Constraint Checks

| Check | Result | Evidence |
|-------|--------|----------|
| ./brok unchanged | PASS | SHA256: `1dc5ddfd2cd95f2b7c9836bd17014f2713e4aae1fead556144fd74ec4b996944` |
| No new CLI flags | PASS | Only `--input <file>` |
| No timestamps used | PASS | grep for mtime/ctime/atime: 0 matches |
| sorted() for determinism | PASS | Line 221: `sorted(os.listdir(root))` |
| Schema has 5 fields | PASS | Schema lock test |
| Disclaimer on stderr | PASS | Integration tests |

---

## 5. Evidence Directory

**Location**: `docs/proofs/l7/`

| File | Scenario | What It Proves |
|------|----------|----------------|
| `01_reject_not_found.txt` | REJECT | discovery_status=authoritative_not_found |
| `02_accept_ambiguous.txt` | ACCEPT + multiple matches | Correct AMBIGUOUS handling |
| `03_expanded_success_unit.txt` | Expanded discovery (unit) | Algorithm correctness proof |
| `04_determinism.txt` | Determinism | Identical inputs → identical outputs |
| `05_delta_only_success.txt` | **Delta-only success (E2E)** | authoritative_found via delta |
| `06_expanded_discovery_success.txt` | **Expanded success (E2E)** | authoritative_found via SHA256 |
| `INDEX.md` | Index | Maps files to scenarios + demo procedure |

---

## 6. Gap Resolution Statement (Uniqueness-Conditional)

### Original L-6 Gap

> "brok-run may report decision=ACCEPT while authoritative_stdout_raw_kv is null
> when stdout.raw.kv is not found in the delta set."

### L-7 Resolution

L-7 provides deterministic discovery **only when contract inputs imply a unique match**.

**When L-7 succeeds** (`authoritative_found`):
- Manifest contains stdout.raw.kv SHA256
- Exactly ONE file under `artifacts/run/*/stdout.raw.kv` matches that hash
- Discovery is deterministic and reproducible

**When L-7 cannot resolve**:
- Multiple files share same SHA256 → `authoritative_ambiguous`
- No files match SHA256 → `authoritative_not_found`
- Manifest missing/malformed → `authoritative_not_found`

### Precise Invariant

> L-7 guarantees deterministic discovery of authoritative output if and only if:
> 1. The manifest contains a stdout.raw.kv SHA256 entry, AND
> 2. Exactly one stdout.raw.kv file under artifacts/run/ matches that SHA256
>
> In all other cases, the wrapper conservatively reports `authoritative_not_found`
> or `authoritative_ambiguous`.

### Known Limitation (Intentional)

**Identical-content ambiguity cannot be resolved by SHA256 alone.**

When multiple `stdout.raw.kv` files have identical content, they share the same
SHA256 hash. L-7 correctly reports AMBIGUOUS rather than selecting arbitrarily.

---

## 7. Demo Success Case Proof (END-TO-END)

### Delta-Only Success (L-6 Behavior)

**Evidence File**: `docs/proofs/l7/05_delta_only_success.txt`

When the l4_run directory does NOT exist, ./brok creates it with stdout.raw.kv.
Delta-only discovery finds it in the filesystem delta.

```bash
# Precondition: l4_run directory must NOT exist
rm -rf artifacts/run/l4_run_run_3e707cb5d43d/

./brok-run "cancel order"
# Result: discovery_status=authoritative_found, run_dir=l4_run_*
```

### Expanded Discovery Success (L-7 Behavior)

**Evidence File**: `docs/proofs/l7/06_expanded_discovery_success.txt`

When the l4_run directory ALREADY exists (not in delta), delta-only fails.
Expanded discovery searches via SHA256 and finds the unique match.

```bash
# Precondition: l4_run directory must EXIST (run delta-only test first)
ls artifacts/run/l4_run_run_3e707cb5d43d/

./brok-run "cancel order"
# Result: discovery_status=authoritative_found, run_dir=m4_*, authoritative_stdout_raw_kv=l4_run_*
```

### Why "cancel order"?

The "cancel order" input produces a stdout.raw.kv with a UNIQUE SHA256 hash.
This enables unambiguous expanded discovery.

"create payment" produces identical output on each run, leading to AMBIGUOUS
when multiple files match the same hash.

---

## 8. Files Changed

| File | Purpose |
|------|---------|
| `brok-run` | Expanded discovery implementation (no changes in this closure fix) |
| `tests/l7/test_l7_locator.py` | Added 4 new tests (12 total) |
| `docs/migration/PHASE_L_7_LOCATOR_CONTRACT.md` | Manifest governance, invariant scope |
| `docs/migration/PHASE_L_7_CLOSURE_REPORT.md` | This report |
| `docs/proofs/l7/*.txt` | Evidence captures |
| `docs/proofs/l7/INDEX.md` | Evidence index |

---

## 9. Explicit Statements

### ./brok Unchanged
```
SHA256: 1dc5ddfd2cd95f2b7c9836bd17014f2713e4aae1fead556144fd74ec4b996944
```

### No New Authority
- Wrapper remains derived and non-authoritative
- stdout.raw.kv remains sole authoritative execution output
- discovery_status is UX convenience, not authority
- Manifest is derived input, not authoritative pointer

### No Heuristics or Timestamps
- No calls to getmtime/getctime/getatime/os.stat
- Directory iteration uses sorted() for determinism
- Matching is exact SHA256 comparison
- No "latest", "most recent", or temporal selection

### L-6 Behavior Preserved
- Delta-only discovery runs first
- Expanded discovery only triggers when delta-only fails AND decision=ACCEPT
- All L-6 test scenarios continue to pass

---

## Conclusion

Phase L-7 closure fixes are complete. The expanded locator contract is implemented,
tested (36 tests passing), documented, and evidenced. The invariant is correctly
scoped to uniqueness conditions. The manifest governance status is proven and
documented. All immutable constraints are preserved.
