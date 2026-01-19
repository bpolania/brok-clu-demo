# Phase L-7: Expanded Discovery / Locator Contract

## Summary

Phase L-7 expands the wrapper's locator behavior to handle cases where authoritative
output (`stdout.raw.kv`) already exists under `artifacts/run/` but does not appear
in the filesystem delta. This is achieved through deterministic SHA256 matching
using the manifest written by `./brok`.

**Key Properties:**
- Wrapper is DERIVED and NON-AUTHORITATIVE (unchanged)
- Canonical command remains: `./brok --input <file>` (unchanged)
- `stdout.raw.kv` remains the ONLY authoritative execution output (unchanged)
- L-6 delta-only behavior is preserved and tried first
- Expanded discovery uses SHA256 matching (deterministic, no timestamps)
- Three locator outcomes: unique, none, ambiguous

---

## Immutable Constraints (Carried Forward)

| Constraint | Status |
|------------|--------|
| `./brok` unchanged | UNCHANGED |
| No new invocation flags, env vars, or forms | UNCHANGED |
| Wrapper outputs remain derived, non-authoritative | UNCHANGED |
| `stdout.raw.kv` is sole authoritative execution output | UNCHANGED |
| No timestamps, mtimes, or file ordering used | UNCHANGED |

---

## Authority Model (Unchanged)

| Component | Authority | L-7 Status |
|-----------|-----------|------------|
| `./brok` | Canonical CLI | UNCHANGED |
| Artifact layer | Sole decision authority | UNCHANGED |
| `stdout.raw.kv` | Authoritative execution output | UNCHANGED |
| `./brok-run` | DERIVED wrapper | Expanded locator |
| Console JSON | DERIVED summary | Extended schema |

---

## L-7 Locator Contract

### Discovery Method (Two-Phase)

Given one wrapper invocation:

1. **Phase 1: Delta-only discovery (L-6 behavior)**
   - Compute delta: `new_dirs = after_dirs - before_dirs`
   - Find authoritative dirs: Check each delta dir for `stdout.raw.kv`
   - If exactly 1 found → use it (UNIQUE)
   - If >1 found → fail closed (contract violation)
   - If 0 found → proceed to Phase 2

2. **Phase 2: Expanded discovery (L-7 addition)**
   - Only triggered for ACCEPT decisions when delta-only finds nothing
   - Read manifest from observability directory
   - Extract `stdout.raw.kv` SHA256 from manifest
   - Scan all `stdout.raw.kv` files under `artifacts/run/`
   - Match by SHA256 (deterministic)
   - Apply selection rule

### Locator Outcomes

| Outcome | Condition | discovery_status |
|---------|-----------|------------------|
| UNIQUE | Exactly 1 match (delta or SHA256) | `authoritative_found` |
| NONE | 0 matches | `authoritative_not_found` |
| AMBIGUOUS | >1 SHA256 matches | `authoritative_ambiguous` |

### Selection Rules

| Match Count | Outcome | Wrapper Action |
|-------------|---------|----------------|
| 0 | NONE | Report `authoritative=null` |
| 1 | UNIQUE | Report path and hash |
| >1 | AMBIGUOUS | Report `authoritative=null`, refuse to select |

---

## Allowed Inputs (Governed Inspection)

### What the Wrapper May Read

| Input | Source | Governance | Purpose |
|-------|--------|------------|---------|
| `manifest.json` | Written by `./brok` (m4 observability) | DERIVED | Extract stdout.raw.kv SHA256 hint |
| `stdout.raw.kv` files | Under `artifacts/run/` | AUTHORITATIVE | Compute hashes for matching |
| `artifact.json` | Written by `./brok` | DERIVED | Read decision |

### Manifest Governance Classification

**Status: DERIVED OBSERVABILITY OUTPUT**

The `manifest.json` file:
- **Producer**: Written by `m4/src/manifest.py` (ManifestBuilder class) during `./brok` execution
- **NOT written by**: The wrapper (`brok-run`) - wrapper only reads it
- **Location**: `artifacts/run/{run_id}/manifest.json`
- **Schema version**: `m4.0`

**Key fields used by L-7 expanded discovery**:
```json
{
  "artifacts": [
    {"type": "stdout.raw.kv", "sha256": "<hash>"}
  ]
}
```

**Wrapper treatment**:
- Reads manifest for discovery hints only
- Does NOT trust manifest as authoritative truth
- Uses SHA256 from manifest to search for matching stdout.raw.kv files
- Still reports AMBIGUOUS if multiple files match (conservative)

**When manifest is missing or malformed**:
- Expanded discovery returns `LOCATOR_NONE`
- `discovery_status` becomes `authoritative_not_found`
- Wrapper does NOT fail - it gracefully degrades

### What is Forbidden

| Forbidden | Reason |
|-----------|--------|
| Timestamps (mtime, ctime, atime) | Non-deterministic |
| File ordering from OS | Non-deterministic |
| "Latest", "most recent" selection | Temporal heuristics |
| Directory name patterns for selection | Coupling to implementation |
| Probabilistic or heuristic matching | Non-deterministic |
| Trusting manifest as authoritative | Manifest is derived, not authoritative |

---

## Frozen JSON Schema (L-7)

The JSON summary uses a frozen schema with exactly five fields:

| Field | Type | Description |
|-------|------|-------------|
| `run_dir` | string | Path to observability or authoritative directory |
| `decision` | string | "ACCEPT" or "REJECT" |
| `authoritative_stdout_raw_kv` | string \| null | Path to stdout.raw.kv or null |
| `authoritative_stdout_raw_kv_sha256` | string \| null | SHA-256 hash or null |
| `discovery_status` | string | Locator outcome (see below) |

### discovery_status Values

| Value | Meaning |
|-------|---------|
| `authoritative_found` | Unique stdout.raw.kv located |
| `authoritative_not_found` | No stdout.raw.kv could be located |
| `authoritative_ambiguous` | Multiple candidates, wrapper refuses to select |

---

## UX Truthfulness Rules

### Disclaimer (Mandatory)

The wrapper prints to stderr:
```
Note: This wrapper is non-authoritative. Discovery status does not imply execution truth.
```

### Output Line 2 (Status Line)

| discovery_status | Line 2 Output |
|------------------|---------------|
| `authoritative_found` | `Authoritative output: <path>` |
| `authoritative_not_found` | `Authoritative output: NONE` |
| `authoritative_ambiguous` | `Authoritative output: AMBIGUOUS` |

---

## Behavior Under L-7

### ACCEPT Decision

For an ACCEPT decision:
1. Delta-only discovery attempted first
2. If no authoritative in delta → expanded discovery via SHA256
3. discovery_status reflects locator outcome
4. AMBIGUOUS means multiple stdout.raw.kv files have same content hash

### REJECT Decision

For a REJECT decision:
- No execution expected, no stdout.raw.kv search
- `authoritative_stdout_raw_kv`: null
- `authoritative_stdout_raw_kv_sha256`: null
- `discovery_status`: `authoritative_not_found`

---

## Exit Codes (Unchanged)

| Code | Meaning |
|------|---------|
| 0 | Success (propagated from ./brok) |
| 2 | Wrong arguments (no ./brok invocation) |
| 3 | Wrapper failure (contract violation) |

---

## Test Matrix

### L-7 Test Suite (8 tests)

| Test | Scenario | Assertion |
|------|----------|-----------|
| 1 | Scan determinism | Same results on repeated scans |
| 2 | SHA256 matching | Exact content-based matching |
| 3 | No SHA256 in manifest | NONE outcome |
| 4 | Integration: REJECT | discovery_status = authoritative_not_found |
| 5 | Integration: ACCEPT | Valid discovery_status value |
| 6 | Determinism | Identical inputs → identical outputs |
| 7 | Disclaimer present | stderr contains disclaimer |
| 8 | No timestamps used | Code does not call time functions |

### L-5 Test Suite (14 tests, updated for L-7)

All L-5 tests updated to verify L-7 schema (5 fields) and discovery_status.

---

## Files Changed

| File | Change |
|------|--------|
| `brok-run` | Added expanded discovery functions, discovery_status field |
| `tests/l7/test_l7_locator.py` | New L-7 test suite |
| `tests/l7/__init__.py` | New test package |
| `tests/l5/test_l5_wrapper.py` | Updated for L-7 schema compatibility |
| `docs/migration/PHASE_L_7_LOCATOR_CONTRACT.md` | This documentation |

---

## Explicit Statements

### What L-7 Did NOT Change

1. **`./brok` was NOT modified**: The canonical CLI remains byte-identical
2. **No new authority introduced**: Wrapper remains derived and non-authoritative
3. **No heuristics or timestamps used**: Discovery is deterministic via SHA256
4. **L-6 behavior preserved**: Delta-only discovery is tried first

### Content-Addressed Storage Note

When multiple `stdout.raw.kv` files have identical content (e.g., repeated runs
with identical input), they share the same SHA256 hash. L-7 reports this as
AMBIGUOUS rather than selecting arbitrarily. This is correct behavior: the
wrapper cannot distinguish which execution the user intended to reference.

---

## L-6 Contract Boundary: Conditional Resolution

L-6 Path A documented a correctness gap:
> "brok-run may report decision=ACCEPT while authoritative_stdout_raw_kv is null
> when stdout.raw.kv is not found in the delta set."

### L-7 Resolution (Uniqueness-Conditional)

L-7 provides deterministic discovery **only when contract inputs imply a unique match**.

**When L-7 succeeds** (`authoritative_found`):
- Manifest contains stdout.raw.kv SHA256
- Exactly ONE file under `artifacts/run/*/stdout.raw.kv` matches that hash
- Discovery is deterministic and reproducible

**When L-7 cannot resolve**:
- Multiple files share the same SHA256 → `authoritative_ambiguous`
- No files match the SHA256 → `authoritative_not_found`
- Manifest missing or malformed → `authoritative_not_found`

### Known Limitation (Intentional)

**Identical-content ambiguity cannot be resolved by SHA256 alone.**

When multiple `stdout.raw.kv` files have identical content (e.g., repeated runs
with the same input producing the same output), they share the same SHA256 hash.
L-7 correctly reports this as AMBIGUOUS rather than selecting arbitrarily.

This is correct behavior:
- The wrapper cannot determine which execution the user intended
- Arbitrary selection would be dishonest UX
- AMBIGUOUS is the truthful outcome

### Precise Invariant Statement

> L-7 guarantees deterministic discovery of authoritative output if and only if:
> 1. The manifest contains a stdout.raw.kv SHA256 entry, AND
> 2. Exactly one stdout.raw.kv file under artifacts/run/ matches that SHA256
>
> In all other cases, the wrapper conservatively reports `authoritative_not_found`
> or `authoritative_ambiguous`.

---

## Conclusion

Phase L-7 expands the wrapper's locator contract to handle authoritative output
that is not in the filesystem delta. The implementation uses deterministic SHA256
matching from the manifest, with explicit handling of ambiguous cases. All
immutable constraints are preserved, and the wrapper remains non-authoritative.

**Gap resolution is conditional on uniqueness** - when multiple candidates exist
or no match is found, the wrapper honestly reports the limitation rather than
guessing.
