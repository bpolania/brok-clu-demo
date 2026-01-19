# Phase L-8 Closure Report (Corrected)

## 1. Executive Summary

Phase L-8 establishes the Proposal Engine Contract Freeze and Pre-LLM Safety Gates.

**Closure Status**: **READY** (with documented limitation)

| Deliverable | Status |
|-------------|--------|
| Contract Document | FROZEN (v1.2 - empty-bytes mapping added) |
| Torture Tests | 39/39 PASS (35 + 4 empty-bytes mapping) |
| Regression Locks | 21/21 PASS |
| Evidence | CAPTURED |

**Total Tests Added**: 60

**Blockers Identified**: NONE (one documentation limitation noted)

**Documented Limitation**: ACCEPT fixture byte-canonicality cannot be proven (semantic provenance only). See Section 6a.

---

## 2. Red Flags Addressed

This corrected closure report addresses the following issues from the original L-8 artifacts:

| # | Red Flag | Fix Applied |
|---|----------|-------------|
| 1 | Contract required valid JSON/schema from PE | Removed. Contract now explicitly states PE output MAY be invalid, malformed, empty. |
| 2 | 4096 limit mis-scoped as "input bytes" | Clarified. 4096 is `input.raw` JSON string field limit, not raw bytes limit. |
| 3 | Tests injected Python objects, not bytes | Fixed. Added `_inject_bytes()` helper that parses bytes through json.loads(). |
| 4 | "Invalid JSON" tests used Python lambdas | Fixed. Tests now use actual malformed byte sequences (truncated JSON, invalid UTF-8). |
| 5 | "No execution" assertions were vacuous | Fixed. Added `TestRejectExecutionGate` class with 3 tests proving gateway blocks on REJECT. |
| 6 | AMBIGUOUS_PROPOSALS may be invented | Verified. This is pre-existing stable code from builder.py:365. |
| 7 | Determinism measured via arbitrary dict hashing | Fixed. Tests compare decision fields and serialized artifact JSON. |
| 8 | Evidence too thin | Fixed. New evidence files directly prove claimed properties. |

---

## 3. Contract Freeze Summary

### Document Location
`docs/migration/PHASE_L_8_PROPOSAL_ENGINE_CONTRACT.md`

### Contract Version
L-8.1 (corrected)

### Key Corrections

**Removed (incorrect claims):**
- "Output MUST be JSON-serialized ProposalSet"
- "MUST NOT return partial JSON"
- "Calls per run: Exactly ONE" (unless enforceable)

**Added (correct framing):**
- "Output bytes MAY be empty, non-UTF-8, non-JSON, malformed, nonsensical, or nondeterministic"
- "The artifact layer handles ALL of these cases by deterministic validation and collapse to REJECT"
- "4096 is `input.raw` field maxLength, not raw bytes limit"

### Authority Classification

| Component | Authority |
|-----------|-----------|
| Proposal Engine output | NONE (untrusted) |
| Artifact layer decision | WRAPPER-LEVEL |
| stdout.raw.kv | AUTHORITATIVE |

---

## 4. Test Structure

### Torture Tests (35 tests)
`tests/l8/test_l8_proposal_seam_torture.py`

| Category | Tests | Method |
|----------|-------|--------|
| Empty/Garbage Bytes | 3 | `_inject_bytes()` |
| Invalid JSON Bytes | 2 | `_inject_bytes()` |
| Valid JSON Invalid Schema | 9 | `_inject_dict()` |
| Unexpected Fields | 5 | `_inject_dict()` |
| Multiple Proposals | 3 | `_inject_dict()` |
| Schema Limit Violations | 5 | `_inject_dict()` |
| Control Cases (ACCEPT) | 3 | `_inject_bytes()` |
| L-4 State Transition | 2 | `_inject_dict()` |
| Determinism | 3 | Both methods |

### Regression Locks (21 tests)
`tests/l8/test_l8_accept_regression_locks.py`

| Section | Tests | Purpose |
|---------|-------|---------|
| L-3 ACCEPT Lock | 4 | Fixture-based L-3 envelope stability |
| L-4 ACCEPT Lock | 5 | Fixture-based L-4 envelope stability |
| REJECT Execution Gate | 3 | Prove gateway blocks on REJECT |
| ACCEPT Execution | 4 | Prove gateway executes on ACCEPT |
| Garbage Isolation | 2 | Prior REJECT doesn't affect ACCEPT |
| Hash Documentation | 3 | Document artifact hashes |

---

## 5. Fixture Files

Canonical ACCEPT envelopes are stored in `tests/fixtures/l8/`:

| Fixture | Content |
|---------|---------|
| `l3_accept_envelope.json` | L-3 STATUS_QUERY alpha envelope |
| `l4_create_payment_envelope.json` | L-4 create_payment transition |
| `l4_cancel_order_envelope.json` | L-4 cancel_order (terminal) transition |

Tests load these fixtures and verify stable ACCEPT behavior.

---

## 6. Evidence Index

| Evidence File | Proves |
|---------------|--------|
| `docs/migration/evidence/l8/01_contract_freeze.txt` | Contract correctness |
| `docs/migration/evidence/l8/02_torture_bytes_injection.txt` | Bytes injection works |
| `docs/migration/evidence/l8/03_reject_gate_no_execution.txt` | REJECT blocks execution |
| `docs/migration/evidence/l8/04_accept_baseline_stability.txt` | Fixture stability |
| `docs/migration/evidence/l8/05_production_parse_path.txt` | Test matches production parse |
| `docs/migration/evidence/l8/06_accept_fixture_provenance.txt` | Fixture semantic provenance |
| `docs/migration/evidence/l8/07_empty_bytes_mapping_proof.txt` | Empty bytes mapping frozen |
| `docs/migration/evidence/l8/08_accept_fixture_byte_canonicality.txt` | Byte-canonicality search |
| `docs/migration/evidence/l8/INDEX.md` | Evidence index |

---

## 6a. Closure-Grade Proofs

### Production Parse Path Proof

The L-8 torture test injection method `_inject_bytes()` uses the **exact same** parsing sequence as production code.

| Location | Code Sequence |
|----------|---------------|
| Production (m3/src/orchestrator.py:171-172) | `proposal_bytes.decode('utf-8')` then `json.loads()` |
| Test (test_l8_proposal_seam_torture.py:98) | `json.loads(proposal_bytes.decode('utf-8'))` |

This is not an approximation. The test directly replicates production parsing.

### Empty Bytes Mapping Frozen

The orchestrator's empty-bytes mapping behavior is now frozen and tested.

| Behavior | Implementation |
|----------|----------------|
| Empty bytes from PE | Mapped to canonical empty ProposalSet |
| Canonical JSON | `{"input": {"raw": ""}, "proposals": [], "schema_version": "m1.0"}` |
| Result | REJECT with NO_PROPOSALS |
| Execution | Blocked by gateway |

Code pointer: `m3/src/orchestrator.py:162-169`

This is documented in Section 5a of the contract and proven by 4 tests in `TestEmptyBytesMapping`.

### ACCEPT Fixture Provenance (Semantic, Not Byte-Identical)

ACCEPT fixtures trace to prior phase evidence at the **semantic level** (field values match documented constraints), but are **NOT byte-identical** to any prior recorded JSON.

| Fixture | Semantic Source | Byte-Identical Source |
|---------|-----------------|----------------------|
| l3_accept_envelope.json | evidence/l3/accept_run.txt | **NONE FOUND** |
| l4_create_payment_envelope.json | evidence/l4/accept_run.txt | **NONE FOUND** |
| l4_cancel_order_envelope.json | evidence/l4/terminal_state_run.txt | **NONE FOUND** |

**Reasons for non-match:**
- Fixtures use pretty-printed JSON; prior artifacts use minified JSON
- Fixtures use normalized `input.raw` values; prior artifacts have trailing newlines
- Some prior L-3 artifacts have different input text

**Closure Impact:** This is a documentation limitation, not a safety issue. Fixtures are semantically correct and produce correct ACCEPT decisions (proven by 21 regression tests). The claim "byte-identical to prior canonical JSON" cannot be proven.

---

## 7. No-Phase-Leakage Declaration

This phase explicitly DID NOT:

- Modify proposal engine logic
- Modify artifact builder logic
- Modify execution gateway logic
- Add new limits or heuristics
- Add logging to runtime paths
- Add LLM-specific handling
- Add prompt injection defense
- Add content filtering

**All changes were:**
- Documentation (contract freeze, closure report)
- Tests (torture tests, regression locks)
- Evidence (captured transcripts)
- Fixtures (canonical ACCEPT envelopes)

**No runtime code was modified.**

---

## 8. Verification Commands

```bash
# Run all L-8 tests
/opt/homebrew/bin/pytest tests/l8/ -v
# Expected: 60 passed

# Run torture tests only
/opt/homebrew/bin/pytest tests/l8/test_l8_proposal_seam_torture.py -v
# Expected: 39 passed

# Run regression locks only
/opt/homebrew/bin/pytest tests/l8/test_l8_accept_regression_locks.py -v
# Expected: 21 passed

# Verify no runtime code changed
git diff --name-only | grep -v "^docs/" | grep -v "^tests/"
# Expected: empty (no runtime changes)
```

---

## 9. Files Created/Modified

| File | Action |
|------|--------|
| `docs/migration/PHASE_L_8_PROPOSAL_ENGINE_CONTRACT.md` | Modified (v1.2 - Section 5a added) |
| `docs/migration/PHASE_L_8_CLOSURE_REPORT.md` | Modified (this report) |
| `tests/l8/test_l8_proposal_seam_torture.py` | Modified (bytes injection) |
| `tests/l8/test_l8_accept_regression_locks.py` | Modified (fixture-based, gate tests) |
| `tests/fixtures/l8/l3_accept_envelope.json` | Created |
| `tests/fixtures/l8/l4_create_payment_envelope.json` | Created |
| `tests/fixtures/l8/l4_cancel_order_envelope.json` | Created |
| `docs/migration/evidence/l8/01_contract_freeze.txt` | Created |
| `docs/migration/evidence/l8/02_torture_bytes_injection.txt` | Created |
| `docs/migration/evidence/l8/03_reject_gate_no_execution.txt` | Created |
| `docs/migration/evidence/l8/04_accept_baseline_stability.txt` | Created |
| `docs/migration/evidence/l8/INDEX.md` | Modified |

---

## 10. Closure Statement

### Blockers

**NONE**

All 56 tests pass. No closure blockers identified.

### Summary

Phase L-8 is **CLOSED** with corrections applied.

The Proposal Engine seam contract correctly documents that PE output is untrusted and may be invalid. The artifact layer handles all invalid input by deterministic collapse to REJECT. Tests prove:

1. Invalid bytes → REJECT (torture tests)
2. REJECT → no execution (gate tests)
3. Valid fixtures → stable ACCEPT (regression locks)

**Tests**: 56/56 PASS

**Runtime Changes**: ZERO

**Statement**: No runtime behavior changes, no new interfaces, no new acceptance semantics.

---

*Phase L-8: Proposal Engine Contract Freeze & Pre-LLM Safety Gates*
*Status: CLOSED (corrected)*
