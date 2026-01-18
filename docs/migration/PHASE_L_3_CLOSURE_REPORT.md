# Phase L-3: Single-Envelope Controlled Acceptance - Closure Report

## Summary

Phase L-3 demonstrates controlled acceptance through a **single explicitly enumerated
ACCEPT envelope**. The authoritative acceptance gate is in `artifact/src/builder.py`.

**Key Property:** Schema-valid alternatives REJECT. Only ONE exact envelope can ACCEPT.

---

## L-3 Single ACCEPT Envelope (Authoritative)

The L-3 envelope gate enforces exactly ONE acceptance case:

```
Envelope Definition:
  - kind == "ROUTE_CANDIDATE"
  - payload.intent == "STATUS_QUERY"
  - payload.slots == {"target": "alpha"}  # No mode, no extra keys
```

**Gate Location:** `artifact/src/builder.py:_check_l3_envelope()`

**Acceptance Predicate (L-3):**

```
IF ProposalSet.proposals.length == 0:
    REJECT (NO_PROPOSALS)
ELIF ProposalSet.proposals.length == 1:
    IF proposal matches L-3 envelope EXACTLY:
        ACCEPT
    ELSE:
        REJECT (L3_ENVELOPE_MISMATCH)
ELIF ProposalSet.proposals.length >= 2:
    REJECT (AMBIGUOUS_PROPOSALS)
ELSE:
    REJECT (INVALID_PROPOSALS)
```

---

## Schema-Valid Alternatives REJECT

The following are schema-valid proposals that intentionally REJECT:

| Proposal | Reason |
|----------|--------|
| STATUS_QUERY target=beta | L3_ENVELOPE_MISMATCH (wrong target) |
| STATUS_QUERY target=gamma | L3_ENVELOPE_MISMATCH (wrong target) |
| STOP_SUBSYSTEM target=alpha | L3_ENVELOPE_MISMATCH (wrong intent) |
| RESTART_SUBSYSTEM target=alpha | L3_ENVELOPE_MISMATCH (wrong intent) |
| RESTART_SUBSYSTEM target=beta mode=graceful | L3_ENVELOPE_MISMATCH (wrong intent+target) |
| STATUS_QUERY target=alpha mode=graceful | L3_ENVELOPE_MISMATCH (extra key in slots) |

This is intentional: L-3 demonstrates that the wrapper can restrict acceptance
to an explicitly enumerated subset of schema-valid proposals.

---

## Authority Model

| Component | Authority | Location |
|-----------|-----------|----------|
| LLM Engine | NON-AUTHORITATIVE | `src/artifact_layer/llm_engine.py` |
| L-3 Envelope Gate | AUTHORITATIVE | `artifact/src/builder.py:_check_l3_envelope()` |
| Artifact Builder | AUTHORITATIVE | `artifact/src/builder.py:build_artifact()` |
| Execution | AUTHORITATIVE | `stdout.raw.kv` only |

The LLM engine's demo input check is a **proposal generator convenience**.
The authoritative decision is made by the envelope gate in `builder.py`.

---

## Files Modified

### Core Implementation

| File | Change |
|------|--------|
| `artifact/src/builder.py` | Added L-3 envelope gate (`L3_ENVELOPE_ENABLED`, `_check_l3_envelope()`) |
| `src/artifact_layer/llm_engine.py` | Updated docs to clarify non-authoritative status |

### Tests

| File | Change |
|------|--------|
| `tests/l3/test_l3_acceptance.py` | 17 tests proving single-envelope contract |

### Evidence

| File | Content |
|------|---------|
| `docs/migration/evidence/l3/accept_run.txt` | ACCEPT run evidence |
| `docs/migration/evidence/l3/reject_run.txt` | REJECT run evidence (L3_ENVELOPE_MISMATCH) |
| `docs/migration/evidence/l3/test_results.txt` | All 17 tests PASS |
| `docs/migration/evidence/l3/cli_invariants_proof.txt` | CLI surface verified |

---

## Test Results Summary

```
===========================================================================
Phase L-3 Single-Envelope Acceptance Tests
===========================================================================

L-3 SINGLE ACCEPT ENVELOPE (AUTHORITATIVE):
  - kind == 'ROUTE_CANDIDATE'
  - payload.intent == 'STATUS_QUERY'
  - payload.slots == {'target': 'alpha'} (no mode, no extras)

Schema-valid alternatives are REJECTED by the authoritative gate.
Gate location: artifact/src/builder.py

[PASS] Exact L-3 envelope → ACCEPT
[PASS] STATUS_QUERY beta → REJECT
[PASS] STATUS_QUERY gamma → REJECT
[PASS] STOP_SUBSYSTEM alpha → REJECT
[PASS] RESTART_SUBSYSTEM alpha → REJECT
[PASS] RESTART_SUBSYSTEM beta graceful → REJECT
[PASS] Extra mode slot → REJECT
[PASS] Zero proposals → REJECT
[PASS] Two proposals → REJECT
[PASS] Invalid intent → REJECT
[PASS] Extra field in proposal → REJECT
[PASS] Demo input via CLI → ACCEPT
[PASS] Non-demo input via CLI → REJECT
[PASS] Determinism of ACCEPT gate
[PASS] Determinism of REJECT gate
[PASS] CLI rejects unknown flags
[PASS] CLI requires --input

===========================================================================
All L-3 single-envelope tests PASSED
```

---

## Prohibition Compliance

| Prohibition | Status |
|-------------|--------|
| No new CLI flags | COMPLIANT |
| No env vars | COMPLIANT |
| No runtime configuration | COMPLIANT |
| No retries | COMPLIANT |
| LLM engine remains non-authoritative | COMPLIANT |
| Deterministic decisions | COMPLIANT |
| REJECT exits with code 0 | COMPLIANT |

---

## Verification Commands

```bash
# Run L-3 tests
python3 tests/l3/test_l3_acceptance.py

# ACCEPT run (exact L-3 envelope)
python3 brok --input inputs/l3_accept_demo.txt

# REJECT run (schema-valid alternative)
echo "status beta" > /tmp/test.txt
python3 brok --input /tmp/test.txt

# CLI surface verification
python3 brok --unknown-flag --input inputs/l3_accept_demo.txt
```

---

## Conclusion

Phase L-3 is complete with closure-grade evidence. The single-envelope contract
ensures that **exactly ONE explicitly enumerated envelope can ACCEPT**, and all
schema-valid alternatives REJECT with `L3_ENVELOPE_MISMATCH`.

This demonstrates the wrapper's ability to enforce brittle acceptance criteria
beyond schema validation alone.

**This is a demonstration, not a production system.**
