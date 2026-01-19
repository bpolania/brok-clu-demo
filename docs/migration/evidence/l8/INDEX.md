# L-8 Evidence Directory Index (Corrected)

## Purpose

This directory contains evidence files for Phase L-8 Proposal Engine Contract Freeze.
Evidence has been restructured to directly prove the claimed safety properties.

## Evidence Files

| File | Proves |
|------|--------|
| `01_contract_freeze.txt` | Contract document exists with correct non-guarantees and authority boundaries |
| `02_torture_bytes_injection.txt` | Tests inject raw bytes and malformed data; all invalid inputs → REJECT |
| `03_reject_gate_no_execution.txt` | REJECT artifacts do not trigger execution; no stdout.raw.kv created |
| `04_accept_baseline_stability.txt` | Fixture-based ACCEPT envelopes produce byte-stable artifacts |
| `05_production_parse_path.txt` | Test injection method matches exact production parsing sequence |
| `06_accept_fixture_provenance.txt` | ACCEPT fixtures trace to canonical L-3/L-4 phase evidence |

## Summary of Properties Proven

### 1. Contract Correctness
- Proposal Engine output is explicitly untrusted
- Output MAY be empty, invalid, malformed, nonsensical, or nondeterministic
- All invalid output collapses to REJECT
- Authority boundary is clear: PE has NONE, artifact layer has WRAPPER-LEVEL

### 2. Torture Test Coverage (35 tests)
| Category | Tests | Result |
|----------|-------|--------|
| Empty/Garbage Bytes | 3 | PASS |
| Invalid JSON Bytes | 2 | PASS |
| Valid JSON Invalid Schema | 9 | PASS |
| Unexpected Fields | 5 | PASS |
| Multiple Proposals | 3 | PASS |
| Schema Limit Violations | 5 | PASS |
| Control Cases (ACCEPT) | 3 | PASS |
| L-4 State Transition | 2 | PASS |
| Determinism | 3 | PASS |

### 3. REJECT Execution Gate (3 tests)
- Gateway does not execute for REJECT artifacts
- No stdout.raw.kv is created for REJECT
- Multiple reject reasons tested: INVALID_PROPOSALS, NO_PROPOSALS, AMBIGUOUS_PROPOSALS

### 4. ACCEPT Stability (21 tests)
- Fixture-based envelopes produce ACCEPT
- Artifacts are byte-stable across runs
- Prior REJECT runs do not affect subsequent ACCEPT (isolation)

### 5. Production Parse Path Proof
- Test injection method uses exact same parsing sequence as production
- Production: `proposal_bytes.decode('utf-8')` then `json.loads()`
- Test: `json.loads(proposal_bytes.decode('utf-8'))`
- Code pointers: m3/src/orchestrator.py:160-172, tests/l8/test_l8_proposal_seam_torture.py:78-111

### 6. ACCEPT Fixture Provenance
- L-3 fixture derived from docs/migration/evidence/l3/accept_run.txt
- L-4 create_payment derived from docs/migration/evidence/l4/accept_run.txt
- L-4 cancel_order derived from docs/migration/evidence/l4/terminal_state_run.txt
- All fixtures have documented SHA256 hashes

## Fixture Files

Canonical ACCEPT envelopes are stored in `tests/fixtures/l8/`:
- `l3_accept_envelope.json`
- `l4_create_payment_envelope.json`
- `l4_cancel_order_envelope.json`

## Total Test Count

**56 tests, all passing**

## Red Flags Addressed

1. Contract no longer claims PE must output valid JSON/schema
2. 4096 limit correctly documented as schema field constraint
3. Tests now inject actual bytes via _inject_bytes() helper
4. "Invalid JSON" tests use actual malformed byte sequences
5. REJECT gate tests prove gateway does not execute
6. AMBIGUOUS_PROPOSALS confirmed as pre-existing stable code
7. Determinism tested on decision/payload, not arbitrary dict hashing
8. Evidence files now directly map to claimed properties
