# Phase L-1: Proposal Acquisition Seam Integration

## Purpose

This document provides audit-grade evidence of Phase L-1 compliance.
L-1 is a mechanical wiring phase that introduces the `acquire_proposal_set` seam
and establishes a build-time engine binding mechanism.

**Phase L-1 does not activate an LLM engine.** The current binding targets the
existing deterministic proposal generator (M-1). Engine binding is build/package-time
only; this phase does not authorize adding or activating additional engines.

---

## 1. What Changed

### 1.1 Files Added

| File | Purpose |
|------|---------|
| `src/__init__.py` | Package marker |
| `src/artifact_layer/__init__.py` | Exports `acquire_proposal_set` |
| `src/artifact_layer/seam_provider.py` | Seam implementation |
| `src/artifact_layer/engine_binding.py` | Build-time engine selection |
| `tests/l1/__init__.py` | Test package marker |
| `tests/l1/test_prohibitions.py` | Repo-wide prohibition checks |
| `tests/l1/test_reject_on_failure.py` | REJECT-on-failure tests |

### 1.2 Files Modified

| File | Change |
|------|--------|
| `m3/src/orchestrator.py` | `run_proposal_generator()` now calls seam instead of shell script |

### 1.3 Seam Signature

Located at `src/artifact_layer/seam_provider.py:21`:

```
acquire_proposal_set(raw_input_bytes: bytes) -> bytes
```

### 1.4 Current Binding

The bound engine is `deterministic`, which wraps the existing M-1 proposal generator.
No LLM engine is active. The binding is defined at `src/artifact_layer/engine_binding.py:21`.

---

## 2. What Did NOT Change

### 2.1 Validators (Byte-Identical to Baseline)

Command:
```
git diff brok-demo-v1 -- artifact/src/validator.py proposal/src/validator.py
```

Result: Empty diff. Both validators are unchanged from baseline.

Evidence: `docs/migration/evidence/l1/validator_diff.txt`

### 2.2 CLI Surface

The CLI exposes only `--input` (plus standard `--help`):

```
usage: brok [-h] --input INPUT
```

No new flags were added.

### 2.3 Determinism

- Artifact layer remains deterministic
- Execution layer remains deterministic
- Proposal generation uses the deterministic M-1 generator

### 2.4 Exit Code Semantics

| Outcome | Exit Code |
|---------|-----------|
| REJECT (valid outcome) | 0 |
| Operational failure | Non-zero |

REJECT exits code 0. This is unchanged.

---

## 3. Prohibitions Checked

All prohibitions verified repo-wide via `tests/l1/test_prohibitions.py`:

| Prohibition | Scope | Status |
|-------------|-------|--------|
| No ACCEPT fixtures | Repo-wide | PASS |
| No retry loops | Repo-wide | PASS |
| No scoring/ranking | Repo-wide | PASS |
| No new CLI flags | CLI surface | PASS |
| No environment variables in seam | Seam code | PASS |
| No runtime config | Repo-wide | PASS |

Evidence: `docs/migration/evidence/l1/prohibition_checks.txt`

---

## 4. REJECT-on-Failure Demonstration

Verified via `tests/l1/test_reject_on_failure.py`.

**Tests assert downstream artifact decision = REJECT (NO_PROPOSALS), not only seam output.**

Engine failure tests invoke the real pipeline (`run_proposal_generator` → `build_and_save_artifact`)
with only the seam patched. Validators and artifact builder are NOT mocked.

### 4.1 Input-Based Failure Tests (via CLI subprocess)

| Test Case | Assertion | Result |
|-----------|-----------|--------|
| Unmapped input | `decision=REJECT`, `reason_code=NO_PROPOSALS` | PASS |
| Empty input | `decision=REJECT`, `reason_code=NO_PROPOSALS` | PASS |
| Malformed UTF-8 | `decision=REJECT`, `reason_code=NO_PROPOSALS` | PASS |

### 4.2 Engine Failure Tests (via in-process pipeline with monkeypatch)

| Test Case | Downstream Assertion | Result |
|-----------|---------------------|--------|
| Engine returns None | `artifact["decision"] == "REJECT"`, `artifact["reject_payload"]["reason_code"] == "NO_PROPOSALS"` | PASS |
| Engine raises exception | `artifact["decision"] == "REJECT"`, `artifact["reject_payload"]["reason_code"] == "NO_PROPOSALS"` | PASS |
| Engine returns non-bytes | `artifact["decision"] == "REJECT"`, `artifact["reject_payload"]["reason_code"] == "NO_PROPOSALS"` | PASS |

### 4.3 Seam-Level Unit Tests

| Test Case | Seam Output | Result |
|-----------|-------------|--------|
| Engine None | `b""` | PASS |
| Engine raises | `b""` | PASS |
| Engine non-bytes | `b""` | PASS |

All failure paths deterministically collapse to REJECT without altering
validator semantics.

Evidence: `docs/migration/evidence/l1/reject_on_failure.txt`

---

## 5. Call Chain Documentation

### 5.1 Entry Point

```
./brok --input <path>
```

File: `brok:43` → `main()`

### 5.2 Pipeline Orchestration

```
brok:main()
  → m3/src/orchestrator.py:run_pipeline()
    → run_proposal_generator()
      → src/artifact_layer/seam_provider.py:acquire_proposal_set()
        → src/artifact_layer/engine_binding.py:get_bound_engine()
          → proposal/src/generator.py:generate_proposal_set()
    → artifact/src/builder.py:build_artifact()
    → m3/src/gateway.py:ExecutionGateway.execute_if_accepted()
```

### 5.3 Seam Location

The seam `acquire_proposal_set` is called at:
- `m3/src/orchestrator.py:155` (inside `run_proposal_generator`)

---

## 6. Verification Commands

### 6.1 Prohibition Checks

```bash
python3 tests/l1/test_prohibitions.py
```

### 6.2 REJECT-on-Failure Tests

```bash
python3 tests/l1/test_reject_on_failure.py
```

### 6.3 Validator Diff

```bash
git diff brok-demo-v1 -- artifact/src/validator.py proposal/src/validator.py
```

### 6.4 CLI Surface Check

```bash
./brok --help
```

---

## 7. Compliance Gate

| Requirement | Evidence |
|-------------|----------|
| Seam exists: `acquire_proposal_set(bytes) -> bytes` | `src/artifact_layer/seam_provider.py:21` |
| No retries, feedback, scoring, ranking, confidence | Prohibition checks PASS |
| No acceptance semantics introduced | Prohibition checks PASS |
| No runtime switching | No env vars or flags in seam |
| No new CLI flags beyond --input | CLI help output |
| Validators unchanged | Empty diff vs baseline |
| Proposal failure → REJECT downstream | Engine failure tests PASS |

---

## 8. Evidence Files

| File | Contents |
|------|----------|
| `docs/migration/evidence/l1/validator_diff.txt` | Empty diff proving validators unchanged |
| `docs/migration/evidence/l1/prohibition_checks.txt` | Prohibition check results |
| `docs/migration/evidence/l1/reject_on_failure.txt` | REJECT-on-failure test results |

---

## 9. Branch History

```
phase-l1-llm-integration
├── fd501e2 Phase L-0: scope lock and authority preservation contracts
├── 724ccee L-1: Implement acquire_proposal_set seam
├── 203f617 L-1: Add prohibition checks and REJECT-on-failure tests
└── f99c8b2 L-1: Add compliance documentation and evidence
```

Based on: `brok-demo-v1` (baseline tag)

---

## 10. Remediation Notes

This document was updated during L-1 closure remediation:

1. **Title corrected**: Changed from "LLM Proposal Engine Integration" to "Proposal Acquisition Seam Integration" to accurately reflect that no LLM is active.

2. **Forward-looking guidance removed**: Removed "how to swap engines" instructions. Engine binding is build/package-time only; this phase does not authorize adding or activating additional engines.

3. **Prohibition checks expanded**: Tests now scan repo-wide (excluding docs/evidence, .git, __pycache__) rather than only `src/artifact_layer/`.

4. **Engine failure tests added**: Added tests that verify `get_bound_engine() -> None` and engine exceptions both collapse to REJECT, proving true acquisition failure handling.

5. **Claims aligned with evidence**: All compliance claims now reference specific evidence files or verification commands.
