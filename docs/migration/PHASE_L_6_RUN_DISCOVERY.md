# Phase L-6 Path A: Wrapper Run Discovery Contract (Delta-Only Selection)

## Summary

Phase L-6 Path A implements the frozen contract for wrapper run discovery.
Authority selection is based **solely** on the filesystem delta and the presence
of `stdout.raw.kv` within newly created directories.

**Key Properties:**
- Authority selection is **delta-only**
- NO manifest-based derivation of execution directories
- NO selection outside the delta set
- NO run ID extraction or directory name construction

---

## Frozen Contract (Path A)

### Run Discovery Rules

Given one wrapper invocation:

1. **Compute delta**: `new_dirs = after_dirs - before_dirs`
2. **Find authoritative dirs**: Check each `new_dir` for `stdout.raw.kv`
3. **Apply selection rule**:

| Authoritative Count | Outcome |
|---------------------|---------|
| 0 | stdout.raw.kv not found in delta (authoritative=null) |
| 1 | Use that directory |
| >1 | Fail closed (contract violation) |

### What Path A Does NOT Do

- Does NOT parse manifests to find execution directories
- Does NOT extract run IDs from artifact paths
- Does NOT construct directory names like `l4_run_*`
- Does NOT search outside the delta set
- Does NOT use timestamps, ordering, or naming heuristics

---

## Authority Model (Unchanged)

| Component | Authority | Status |
|-----------|-----------|--------|
| `./brok` | Canonical CLI | UNCHANGED |
| Artifact layer | Sole decision authority | UNCHANGED |
| `stdout.raw.kv` | Authoritative execution output | UNCHANGED |
| `./brok-run` | DERIVED wrapper | Path A contract |
| Console JSON | DERIVED summary | UNCHANGED |

---

## Behavior Under Path A

### ACCEPT Decision

For an ACCEPT decision:
- If `stdout.raw.kv` is in a delta directory: authoritative output is reported
- If `stdout.raw.kv` is NOT in delta: authoritative=null

**Path A does NOT search outside the delta set.**
This is a contract boundary of the delta-only approach.

### REJECT Decision

For a REJECT decision:
- `stdout.raw.kv` is not expected in the delta set
- `authoritative_stdout_raw_kv`: null
- `authoritative_stdout_raw_kv_sha256`: null

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (propagated from ./brok) |
| 2 | Wrong arguments (no ./brok invocation) |
| 3 | Wrapper failure (contract violation: >1 authoritative) |

---

## Test Coverage

### Required Scenarios (Path A)

| Scenario | Test | Assertion |
|----------|------|-----------|
| 1: Multi-dir, single auth | `test_l6_scenario1_*` | Exactly 1 selected |
| 2: Observability-only | `test_l6_scenario2_*` | authoritative=null, no failure |
| 3: Contract violation | `test_l6_scenario3_*` | Fail closed |

### Path A Limitations Documented

The integration tests document the Path A contract boundary:
- If stdout.raw.kv is not found in newly created run directories (delta set), authoritative will be null
- brok-run does not search outside the delta set under Path A

---

## Files Changed (Path A Remediation)

| File | Change |
|------|--------|
| `brok-run` | Removed manifest-derived execution directory logic |
| `tests/l6/test_l6_run_discovery.py` | Rewritten for Path A contract |
| `tests/l5/test_l5_wrapper.py` | Updated for Path A compatibility |
| `docs/migration/PHASE_L_6_RUN_DISCOVERY.md` | This documentation |

---

## Drift Removed

The following drift was removed from the prior implementation:

1. **Function `_extract_run_id_from_manifest`**: Deleted
2. **Function `_find_execution_dir_from_manifest`**: Deleted
3. **Main logic**: Removed code path that searched outside delta via manifest

---

## What L-6 Path A Fixes

Phase L-6 Path A addresses the following issues from the prior implementation:

1. **Contract drift**: Prior implementation used manifest-based derivation to find
   execution directories outside the delta set. This violated the frozen contract.

2. **Function creep**: Functions `_extract_run_id_from_manifest` and
   `_find_execution_dir_from_manifest` were added outside the contract scope.

3. **Selection ambiguity**: Prior implementation could select directories not in
   the delta, creating undocumented behavior paths.

**Path A restores contract alignment** by removing all manifest-based derivation
and implementing strict delta-only selection.

---

## Known Wrapper Correctness Gap Under Path A (Blocking for UX Correctness)

### Observed Condition

Observed condition: brok-run may report decision=ACCEPT while authoritative_stdout_raw_kv is null.

Path A explanation (contract-level): delta-only discovery did not find stdout.raw.kv in newly created run directories.

Contract boundary: brok-run does not search outside the delta set under Path A, so it cannot locate authoritative output that is not in the delta set.

### Observable Behavior Table

| Condition | Wrapper Reports | Path A Observation |
|-----------|-----------------|-------------------|
| ACCEPT + stdout.raw.kv in delta | authoritative=path | Located in delta |
| ACCEPT + stdout.raw.kv not in delta | authoritative=null | Not found in delta |
| REJECT + no stdout.raw.kv in delta | authoritative=null | Not found in delta |

### Reproduction Scenario

```
# First invocation: "create payment" → ACCEPT, stdout.raw.kv found in delta
# Wrapper reports authoritative_stdout_raw_kv = <path>

# Second invocation: "create payment"
# Wrapper sees 0 new directories with stdout.raw.kv in delta
# Wrapper reports authoritative_stdout_raw_kv = null
# Out of scope for Path A; brok-run cannot establish execution from delta-only discovery.
```

### Impact

- **UX impact**: Users see `Authoritative output: NONE` for ACCEPT decisions when stdout.raw.kv is not in delta
- **Contract boundary**: brok-run does not search outside the delta set under Path A

### What This Gap Is NOT

- This is NOT a bug in `./brok` (canonical CLI is correct)
- This is NOT a contract violation (Path A contract is upheld)
- This IS a contract boundary of the delta-only approach

---

## Why We Do Not Fix This in L-6 Path A

### Reason 1: Contract Scope

The frozen contract for L-6 specifies delta-only selection. Any fix that
searches outside the delta set would violate the contract.

### Reason 2: Avoiding Unaudited Drift

The prior attempt to address this gap introduced manifest-based derivation,
which was identified as drift. Path A explicitly removes this drift.

### Reason 3: Contract Boundary Documentation

Phase L-6 Path A documents the contract boundary rather than papering
over it with undocumented workarounds. This creates a clear record for
follow-on phases.

### Reason 4: Separation of Concerns

Addressing this gap requires a design decision about how the wrapper should
locate authoritative output outside the delta. This decision belongs in
a follow-on phase with explicit contract expansion.

---

## Follow-On Phase Requirement

Follow-on requirement: A subsequent phase must define and freeze an expanded, audit-safe locator contract for authoritative output that may not appear in the delta set. This phase must explicitly specify what inputs brok-run may read for that locator and what constitutes a contract violation.

### Blocking Status

The correctness gap is **blocking for UX correctness** but **not blocking
for Phase L-6 Path A closure**. Path A is complete and correct per its
frozen contract.

---

## Conclusion

Phase L-6 Path A implements the frozen delta-only contract. Authority selection
is based solely on the presence of `stdout.raw.kv` in newly created directories.
The wrapper does NOT derive authoritative output locations from manifests.

**Contract Boundary Documented**: brok-run may report decision=ACCEPT while
authoritative_stdout_raw_kv is null when stdout.raw.kv is not found in the
delta set. brok-run does not search outside the delta set under Path A.
A follow-on phase is required to address this gap.
