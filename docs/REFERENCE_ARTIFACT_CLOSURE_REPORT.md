# Reference Artifact Closure Report

This document records the closure of the Brok-CLU demo repository as a frozen reference artifact.

**Tag:** `brok-demo-v1`
**Date:** 2026-01-14

---

## Summary of Changes

### Files Created

| File | Purpose |
|------|---------|
| `REFERENCE_ARTIFACT.md` | Frozen reference artifact declaration |
| `INVARIANTS.md` | Invariants that must never change |
| `docs/REFERENCE_CLOSURE_PRECHECK.md` | Precheck verification results |
| `docs/REFERENCE_CLOSURE_SURFACE_AUDIT.md` | CLI surface audit |
| `docs/REFERENCE_ARTIFACT_CLOSURE_REPORT.md` | This closure report |

### Files Modified

| File | Change |
|------|--------|
| `README.md` | Added "Reference Artifact: How to Read This Repo" section |

### Files Unchanged

All runtime code, scripts, and schemas remain unchanged. This closure pass added **documentation only**.

---

## Explicit Statement: No Runtime Behavior Changes

This closure pass made **zero changes** to:

- PoC v2 tarball (`vendor/poc_v2/poc_v2.tar.gz`)
- Verification script (`scripts/verify_poc_v2.sh`)
- Execution script (`scripts/run_poc_v2.sh`)
- Determinism test (`scripts/determinism_test_v2.sh`)
- Proposal generator semantics (M-1)
- Artifact builder semantics (M-2)
- Gateway enforcement semantics (M-3)
- Observability semantics (M-4)
- Any Python code
- Any shell script logic

The repository behavior is identical before and after this closure pass.

---

## Precheck Results Summary

Full details: [`docs/REFERENCE_CLOSURE_PRECHECK.md`](REFERENCE_CLOSURE_PRECHECK.md)

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| M-1 (Proposal) | 26 | PASS |
| M-2 (Artifact) | 30 | PASS |
| M-3 (Invariants) | 29 | PASS (1 skip) |
| M-4 (Observability) | 52 | PASS |
| **Total** | **137** | **All Pass** |

The skipped test (`test_stdout_golden_match`) requires an optional baseline file and is not a functional issue.

### Surface Audit Results

Full details: [`docs/REFERENCE_CLOSURE_SURFACE_AUDIT.md`](REFERENCE_CLOSURE_SURFACE_AUDIT.md)

| Check | Result |
|-------|--------|
| Single canonical entrypoint | VERIFIED |
| No bypass paths | VERIFIED |
| No environment variable overrides | VERIFIED |
| Gating enforcement intact | VERIFIED |

---

## Confirmations

### Frozen Files Unchanged

| File | SHA-256 |
|------|---------|
| `vendor/poc_v2/poc_v2.tar.gz` | `7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a` |

Frozen scripts verified unchanged via `git diff` (empty output):
- `scripts/verify_poc_v2.sh`
- `scripts/run_poc_v2.sh`
- `scripts/determinism_test_v2.sh`

### Gitignore Coverage

All generated artifact directories are properly ignored:

| Directory | Status |
|-----------|--------|
| `artifacts/` | IGNORED |
| `semantic/regression/runs/` | IGNORED |
| `semantic/artifacts/` | IGNORED |

### No Absolute Paths or Timestamps

Verified that no committed documentation files contain:
- Absolute paths (e.g., `/Users/...`, `C:\...`)
- Timestamps
- Machine identifiers

### Canonical CLI Path Documented

The canonical invocation is documented in:
- `REFERENCE_ARTIFACT.md` (Canonical CLI Surface section)
- `README.md` (Reference Artifact section)
- `docs/REFERENCE_CLOSURE_SURFACE_AUDIT.md` (full audit)

**Canonical invocation:** `./brok --input <file>`

### Tag Created

```
Tag:     brok-demo-v1
Message: Frozen reference artifact (M-0 through M-4 closed)
Commit:  <see tag>
```

---

## Known Limitations

### Non-Goals (Repeated for Clarity)

This demo explicitly does **NOT** provide:

| Non-Goal | Explanation |
|----------|-------------|
| Semantic correctness | Proposals may be wrong |
| General NLP | Closed intent set only |
| Scoring or confidence | No probability scores |
| Heuristics tuning | No adjustable thresholds |
| Production deployment | Demo artifact only |
| Performance claims | No guarantees |
| Security claims | Integrity-only verification |
| Extensibility | Closed system |

### Where Misunderstandings Commonly Occur

1. **"The proposal is correct"** - No. Proposals are LLM-generated guesses.

2. **"The artifact decides"** - No. The artifact records a decision; `stdout.raw.kv` is the actual decision.

3. **"I can add new intents"** - No. The intent set is sealed in the PoC v2 binary.

4. **"The manifest is the source of truth"** - No. The manifest is derived observability data.

5. **"This is production-ready"** - No. This is a reference demo for evaluation purposes only.

---

## Authority Model Summary

| Output | Authority Level |
|--------|-----------------|
| `stdout.raw.kv` | **AUTHORITATIVE** |
| `artifact.json` | DERIVED |
| `proposal_set.json` | NON-AUTHORITATIVE |
| `manifest.json` | DERIVED |
| `trace.jsonl` | DERIVED |

Only `stdout.raw.kv` may be treated as ground truth for execution results.

---

## Deliverables Checklist

| Deliverable | Status |
|-------------|--------|
| `REFERENCE_ARTIFACT.md` | CREATED |
| `INVARIANTS.md` | CREATED |
| `docs/REFERENCE_CLOSURE_PRECHECK.md` | CREATED |
| `docs/REFERENCE_CLOSURE_SURFACE_AUDIT.md` | CREATED |
| `docs/REFERENCE_ARTIFACT_CLOSURE_REPORT.md` | CREATED |
| `README.md` updated | MODIFIED |
| Tag `brok-demo-v1` created | CREATED |

---

## How to Verify

```sh
# Verify tag exists
git tag -v brok-demo-v1

# Run all tests
python3 -m unittest discover -s . -p "test*.py"

# Verify frozen tarball hash
shasum -a 256 vendor/poc_v2/poc_v2.tar.gz

# Run canonical entrypoint
./brok --input examples/inputs/accept_restart_alpha_1.txt
```

---

## Conclusion

The Brok-CLU demo repository is now a frozen reference artifact:

- **137 tests** verify invariants
- **Zero runtime changes** in this closure pass
- **Single canonical entrypoint** documented and verified
- **Authority boundaries** clearly defined
- **Non-goals** explicitly stated
- **Tag `brok-demo-v1`** marks the frozen state

This reference artifact is suitable for:
- B2B integration evaluation
- Edge deployment architecture studies
- Audit and compliance review
- Academic reference

---

*Reference Artifact Closure Complete*
