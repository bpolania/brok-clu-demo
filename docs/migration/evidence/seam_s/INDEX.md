# Seam S Evidence Directory Index (Freeze-Grade)

## Purpose

This directory contains evidence files for Seam S (acquire_proposal_set) freeze-grade enforcement.
The evidence proves the invariants and guards claimed in the Seam S documentation.

## Evidence Files

| File | Proves |
|------|--------|
| `01_seam_call_count_proof.txt` | C1 invariant (exactly one call per run) |
| `02_proposal_variability_proof.txt` | C3 invariant (variability affects only decision) |
| `03_full_test_run_transcript.txt` | All original tests passing |
| `04_accept_path_invariance_proof.txt` | C5 invariant (ACCEPT execution hash unchanged) |
| `05_e2e_transcript.txt` | End-to-end evidence with hash values |

## Seam Contract (Freeze-Grade)

```
acquire_proposal_set(raw_input_bytes: bytes, ctx: RunContext) -> OpaqueProposalBytes
```

Location: `src/artifact_layer/seam_provider.py`

## Freeze-Grade Enforcement

### G1: Runtime Exactly-One-Call Guard
- Implementation: `RunContext` class in `src/artifact_layer/run_context.py`
- Behavior: Raises `SeamSViolation` on second call with same context
- Test coverage: 3 tests

### G2: Mechanical Non-Inspection Boundary
- Implementation: `OpaqueProposalBytes` class in `src/artifact_layer/opaque_bytes.py`
- Disabled affordances: `__str__`, `__len__`, `__bool__`, `__iter__`, `__getitem__`, `__eq__`, `__hash__`
- Only allowed operation: `to_bytes()` at artifact layer boundary
- Test coverage: 6 tests

### G3: Static Analysis (Defense-in-Depth)
- Implementation: AST-based scanning in tests
- Verifies single call site and no retry patterns
- Test coverage: 2 tests

## Invariants Proven

### C1: Call Count Invariant
- Seam is called exactly ONCE per pipeline run
- Runtime enforcement via RunContext
- Static enforcement via AST analysis

### C2: Failure Collapse Invariant
- Engine None → `OpaqueProposalBytes(b"")`
- Engine raises → `OpaqueProposalBytes(b"")`
- Engine wrong type → `OpaqueProposalBytes(b"")`

### C3: Proposal Variability Inert
- Garbage bytes → REJECT (no crash)
- Valid proposals → ACCEPT
- Empty proposals → REJECT (NO_PROPOSALS)
- Variability affects ONLY the decision

### C4: Engine Removed Safety
- System produces valid REJECT when engine is None
- No crashes, no undefined behavior

### C5: ACCEPT Execution Invariance (NEW)
- Different ACCEPT proposals produce identical execution output hash
- REJECT artifacts never execute (no stdout.raw.kv created)
- Proven via hash comparison across runs

## Test Coverage (Freeze-Grade)

| Category | Tests | Result |
|----------|-------|--------|
| G1: Runtime Guard | 3 | PASS |
| G2: Opaque Wrapper | 6 | PASS |
| G3: Static Analysis | 2 | PASS |
| C1: Call Count | 1 | PASS |
| C2: Failure Collapse | 2 | PASS |
| C3: Proposal Variability | 2 | PASS |
| C4: Engine Removed | 1 | PASS |
| C5: ACCEPT Invariance | 2 | PASS |
| **Total** | **19** | **PASS** |

## Test Locations

- Freeze-grade tests: `tests/seam_s/test_seam_s_freeze_grade.py`
- Original tests: `tests/seam_s/test_seam_s_guards_and_invariants.py`

## Verification Commands

```bash
# Run freeze-grade tests
/opt/homebrew/bin/python3 tests/seam_s/test_seam_s_freeze_grade.py

# Run via pytest
/opt/homebrew/bin/pytest tests/seam_s/ -v

# Run all safety tests
/opt/homebrew/bin/pytest tests/seam_s/ tests/l8/ tests/l1/ -v
# Expected: 102 passed
```

## Key Hash Values (Evidence)

| Test | Hash (SHA256, first 16 chars) |
|------|-------------------------------|
| C5: ACCEPT execution action | 44136fa355b3678a |

These hashes prove execution output is invariant across ACCEPT runs.
