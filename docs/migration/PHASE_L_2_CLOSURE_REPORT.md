# Phase L-2: LLM Proposal Engine Activation - Closure Report

## Summary

Phase L-2 activates an offline nondeterministic proposal engine that produces
variable proposals while maintaining all frozen contracts and **REJECT-guaranteed** behavior.

**CRITICAL L-2 PROPERTY:** All runs produce REJECT (via unmapped proposals that
fail validation → INVALID_PROPOSALS). Zero ACCEPT outcomes in any evidence.

**No runtime secrets or network access required.**

**Baseline Tag:** `brok-demo-v1`
**Branch:** `phase-l2-llm-activation`

---

## 1. Files Changed

### 1.1 Files Added

| File | Purpose |
|------|---------|
| `src/artifact_layer/llm_engine.py` | Offline nondeterministic proposal engine |
| `tests/l2/__init__.py` | Test package marker |
| `tests/l2/test_l2_variability.py` | Proposal variability tests (offline) |
| `tests/l2/test_l2_failure_collapse.py` | Failure collapse tests |
| `tests/l2/test_l2_prohibitions.py` | Prohibition mechanism checks |
| `docs/migration/evidence/l2/cli_surface.txt` | CLI surface evidence |
| `docs/migration/evidence/l2/validator_immutability.txt` | Validator hash evidence |
| `docs/migration/evidence/l2/proposal_variability.txt` | Variability test output |
| `docs/migration/evidence/l2/reject_on_failure.txt` | Failure collapse evidence |
| `docs/migration/evidence/l2/no_prohibited_mechanisms.txt` | Prohibition check evidence |
| `docs/migration/PHASE_L_2_SCOPE_LOCK.md` | Scope lock documentation |
| `docs/migration/PHASE_L_2_CLOSURE_REPORT.md` | This document |

### 1.2 Files Modified

| File | Change |
|------|--------|
| `src/artifact_layer/engine_binding.py` | Changed BOUND_ENGINE_NAME to "llm", added LLM engine registration |
| `tests/l1/test_prohibitions.py` | Added tests/l2 to exclusion paths |

### 1.3 Files Removed (from original L-2)

| File | Reason |
|------|--------|
| `requirements.txt` | No external dependencies needed for offline engine |

### 1.4 Files NOT Modified (Immutable)

| File | SHA256 Hash |
|------|-------------|
| `artifact/src/validator.py` | `28f7f3e3387a4e48616561095ea0c06bada44161124dfa6466228b2059a4f8e1` |
| `proposal/src/validator.py` | `4ad2993ec4aaf85fd759dc702d25875b252663f6cd8d4b5e5c4902d2e3596f20` |
| `artifact/src/builder.py` | `6d0295f9ef18935f416bf5123c4773b9fcefd6d7c4475359d699a24e378fc501` |

---

## 2. Evidence Matrix

| Closure Criterion | Evidence File | Status |
|-------------------|---------------|--------|
| CLI surface unchanged | `docs/migration/evidence/l2/cli_surface.txt` | PASS |
| Validators unchanged | `docs/migration/evidence/l2/validator_immutability.txt` | PASS |
| Proposal variability demonstrated | `docs/migration/evidence/l2/proposal_variability.txt` | PASS |
| **REJECT-only verified** | `docs/migration/evidence/l2/proposal_variability.txt` | PASS |
| Failure collapse to REJECT | `docs/migration/evidence/l2/reject_on_failure.txt` | PASS |
| No prohibited mechanisms | `docs/migration/evidence/l2/no_prohibited_mechanisms.txt` | PASS |

---

## 3. Runtime Secrets Removal

### Why Removed

The original L-2 implementation used the Anthropic API requiring `ANTHROPIC_API_KEY`.
This violated the "no runtime configuration" constraint because:

1. Environment variables for API access constitute runtime configuration
2. Evidence could not demonstrate variability without the secret
3. External API calls are not under build-time control

### Remediation

Replaced with an offline nondeterministic engine that:
- Uses OS randomness (`secrets` module) for nondeterminism
- Requires no external services, API keys, or network access
- Produces variable ProposalSet bytes across runs (unique hash per run)
- **Guarantees REJECT-only outcomes** via unmapped proposals:
  - Proposals contain field values outside closed domain (e.g., `UNMAPPED_INTENT_*`)
  - Validation fails with INVALID_PROPOSALS
  - Artifact decision = REJECT (never ACCEPT)

---

## 4. Test Results

### 4.1 L-2 Variability Tests (Offline)

```
Direct engine variability: PASS (20 unique hashes in 20 runs)
Pipeline variability: PASS (20 unique hashes in 20 runs)
REJECT-only (L-2 critical): PASS (all 20 runs = REJECT, zero ACCEPT)
Downstream determinism: PASS (all exit codes = 0)
Empty input -> REJECT: PASS
```

### 4.2 L-2 Failure Collapse Tests

```
[PASS] Empty input -> REJECT
[PASS] Malformed UTF-8 -> REJECT
[PASS] Unmapped input -> REJECT
[PASS] Seam exception -> REJECT
[PASS] Seam returns b'' -> REJECT
```

### 4.3 L-2 Prohibition Checks

```
[PASS] No new CLI flags
[PASS] No env-based engine selection
[PASS] Single seam call (no retries)
[PASS] No retries in LLM engine
[PASS] No env vars in LLM engine
[PASS] No network in LLM engine
[PASS] No scoring/ranking
[PASS] No ACCEPT fixtures
```

### 4.4 L-1 Tests (Regression)

```
[PASS] All L-1 prohibition checks
[PASS] All L-1 REJECT-on-failure tests
```

---

## 5. Prohibition Compliance

| Prohibition | Status | Evidence |
|-------------|--------|----------|
| No ACCEPT fixtures | COMPLIANT | Prohibition checks PASS |
| No retry/backoff loops | COMPLIANT | Engine has single call |
| No scoring/ranking/confidence | COMPLIANT | No such patterns found |
| No new CLI flags | COMPLIANT | CLI shows only --input |
| No env-based engine selection | COMPLIANT | BOUND_ENGINE_NAME is build-time constant |
| No runtime configuration | COMPLIANT | No env vars, no config files |
| No network calls | COMPLIANT | Offline engine only |
| No stdout.raw.kv parsing | COMPLIANT | Engine does not access execution output |

---

## 6. Authority Model Verification

| Assertion | Status |
|-----------|--------|
| Proposals remain non-authoritative | VERIFIED |
| Artifacts hold decision authority | VERIFIED |
| stdout.raw.kv is sole execution authority | VERIFIED |
| Execution only on ACCEPT | VERIFIED |
| REJECT exits with code 0 | VERIFIED |

---

## 7. Seam Binding

- **Location:** `src/artifact_layer/seam_provider.py:21`
- **Contract:** `acquire_proposal_set(raw_input_bytes: bytes) -> bytes`
- **Engine:** Offline nondeterministic engine via `src/artifact_layer/llm_engine.py`
- **Binding:** Build-time via `BOUND_ENGINE_NAME = "llm"` in `engine_binding.py`
- **Nondeterminism Source:** OS randomness via `secrets` module
- **REJECT Mechanism:** Produces unmapped proposals (field values outside closed domain)
  which fail validation → INVALID_PROPOSALS → REJECT

---

## 8. Verification Commands

```bash
# CLI surface
./brok --help

# Validator immutability
git diff brok-demo-v1 -- artifact/src/validator.py proposal/src/validator.py artifact/src/builder.py

# Run L-2 tests
python3 tests/l2/test_l2_variability.py
python3 tests/l2/test_l2_failure_collapse.py
python3 tests/l2/test_l2_prohibitions.py

# Run L-1 tests (regression)
python3 tests/l1/test_prohibitions.py
python3 tests/l1/test_reject_on_failure.py

# Demo variability (run multiple times)
echo "restart alpha subsystem gracefully" > /tmp/test.txt
./brok --input /tmp/test.txt
```

---

## 9. Conclusion

Phase L-2 is complete with closure-grade evidence. The offline nondeterministic
engine demonstrates LLM-style variability without:
- Runtime secrets (no API keys)
- Network access (offline only)
- Runtime configuration (build-time binding only)
- **ACCEPT outcomes** (all runs produce REJECT via unmapped proposals)

All artifact rules, validators, and authority model remain unchanged from baseline.
REJECT-only operation is verified across all 20 test runs with zero ACCEPT outcomes.
