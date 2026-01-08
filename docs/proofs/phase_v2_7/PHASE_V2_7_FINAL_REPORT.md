# Phase V2-7 — Final Validation Report

## Status

- **Phase:** V2-7
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Validation Run Information

| Property | Value |
|----------|-------|
| Validation timestamp (start) | 2026-01-07T18:33:10Z |
| Validation timestamp (end) | 2026-01-07T18:41:11Z |
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Transcript file | `transcripts/VALIDATION_TRANSCRIPT.txt` |
| Numbered transcript | `transcripts/VALIDATION_TRANSCRIPT.numbered.txt` |

---

## Vendored Bundle Checksums

| File | SHA-256 |
|------|---------|
| poc_v2.tar.gz | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |
| PROVENANCE.txt | 51fec5be8eea6fd1c8d689a5646c86b32e016d670ba20f1b70afe68f0c860f67 |

Checksum verification: Recorded value in `SHA256SUMS.vendor` matches computed value.

---

## Checklist Results

### A) Fresh Clone Sanity

| Check | Result |
|-------|--------|
| A.1: Repo root matches git rev-parse | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| A.2: Git status clean except phase_v2_7 | Untracked: evidence/phase_v2_7/ |
| A.3: SHA256SUMS.vendor file present | Yes |
| A.4: Computed tarball checksum | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |
| A.5: Checksum match | MATCH |

### B) Verification Path

| Check | Result |
|-------|--------|
| B.1: verify_poc_v2.sh exit code | 0 |
| B.2: Verification artifacts created | artifacts/verify/run_20260107T183310Z |

### C) Single-Run Execution

| Check | Result |
|-------|--------|
| C.1: Input files present | 5 files in examples/inputs/ |
| C.2: Input file used | accept_restart_alpha_1.txt |
| C.3: run_poc_v2.sh exit code | 0 |
| C.4: Run directory created | artifacts/run/run_20260107T183310Z |
| C.5: Run directory contents | 7 files + verify/ subdirectory |
| C.6: Verification subdirectory present | Yes (verify/) |
| C.7: exit_code.txt content | 0 |

### D) Output Semantics

| Check | Result |
|-------|--------|
| D.1: stdout.raw.kv present | Yes |
| D.2: DERIVED_VIEW_NOTICE.txt present | Yes |
| D.3: execution.meta.json present | Yes |
| D.3: execution.meta.json verification_passed | true |
| D.3: execution.meta.json execution_attempted | true |

### E) Determinism Validation

| Check | Result |
|-------|--------|
| E.1: determinism_test_v2.sh exit code | 0 |
| E.1: Run count | 5 |
| E.2: Test directory | artifacts/determinism/test_20260107T183312Z |
| E.4: result.txt | PASS: All 5 runs produced identical stdout.raw.kv |
| E.5: Baseline SHA-256 | 06fbb25336bbee1f3dfef9b7777385785db387b7ef695f25b34bb49aea5a21d3 |
| E.6: cmp exit codes (all 5) | 0, 0, 0, 0, 0 |

### F) Relocatability Spot Check

| Check | Result |
|-------|--------|
| F.1: Invocation PWD | /tmp |
| F.1: run_poc_v2.sh exit code (from /tmp) | 0 |
| F.2: Artifacts location | artifacts/run/run_20260107T183322Z (in repo) |

### G) Failure Handling

#### G.prior) Non-Failing Boundary Observation (PROVENANCE.txt)

The initial test renamed `vendor/poc_v2/PROVENANCE.txt` to `PROVENANCE.txt.bak`. This did **not** induce verification failure because PROVENANCE.txt is metadata documentation, not part of the tarball integrity verification boundary. See transcript lines 522–673.

| Check | Result |
|-------|--------|
| G.prior.1: PROVENANCE.txt renamed | vendor/poc_v2/PROVENANCE.txt.bak |
| G.prior.2: verify_poc_v2.sh exit code | 0 (did not fail) |
| G.prior.3: run_poc_v2.sh exit code | 0 (did not block) |

This observation does **not** satisfy the G requirement.

---

#### G.corrected) True Verification Failure Test

**Method:** `chmod 000 vendor/poc_v2/poc_v2.tar.gz` (make tarball unreadable)

This test is documented in transcript lines 733–1052.

| Check | Transcript Line | Result |
|-------|-----------------|--------|
| G.0.3: Baseline tarball permissions | 758 | 644 (rw-r--r--) |
| G.0.4: Baseline tarball SHA-256 | 765 | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |
| G.1.1: Failure induction method | 783 | chmod 000 vendor/poc_v2/poc_v2.tar.gz |
| G.1.2: Permissions after chmod | 793 | 0 (----------) |
| **G.2.1: verify_poc_v2.sh exit code** | **817** | **1 (FAILED)** |
| **G.3.1: run_poc_v2.sh exit code** | **839** | **1 (BLOCKED)** |
| G.3.3: Run directory contents | 856–861 | execution.meta.json, execution.SKIPPED, verify/ |
| **G.3.4: execution.meta.json verification_passed** | **871** | **false** |
| **G.3.4: execution.meta.json execution_attempted** | **872** | **false** |
| **G.3.5: stdout.raw.kv** | **885** | **ABSENT (execution blocked)** |
| G.3.6: verify/exit_code.txt | 900 | 1 |
| G.4.1: Permissions restored | 914 | chmod 644 applied |
| G.4.2: Permissions after restore | 920 | 644 (rw-r--r--) |
| G.4.3: Tarball SHA-256 after restore | 925 | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |
| **G.5.1: verify_poc_v2.sh exit code after restore** | **991** | **0 (PASSED)** |
| G.6.1: Git status (final) | 1002 | Untracked: evidence/phase_v2_7/ |
| G.6.2: Vendor listing matches baseline | 1008–1012 | Yes |

**Summary (transcript line 1041):**
```
RESULT: PASS - Verification failure induced, execution blocked, restoration successful
```

**Evidence of execution blocked:**

1. `execution.meta.json` contains:
   ```json
   {
     "verification_passed": false,
     "execution_attempted": false,
     "notes": "Verification failed (exit 1). Execution not attempted."
   }
   ```

2. `execution.SKIPPED` sentinel file present (line 860)

3. `stdout.raw.kv` is absent (line 885)

4. `verify/exit_code.txt` contains `1` (line 900)

**G) Failure Handling: PASS**

---

## Final Git Status

```
## main...origin/main
?? evidence/phase_v2_7/
```

---

## Evidence Files

| File | Purpose |
|------|---------|
| `PHASE_V2_7_FINAL_REPORT.md` | This report |
| `PHASE_V2_7_FREEZE_ATTESTATION.md` | Freeze attestation document |
| `transcripts/VALIDATION_TRANSCRIPT.txt` | Verbatim validation transcript |
| `transcripts/VALIDATION_TRANSCRIPT.numbered.txt` | Line-numbered transcript for reference |

---

## Checklist Summary

| Item | Description | Status |
|------|-------------|--------|
| A | Fresh Clone Sanity | PASS |
| B | Verification Path | PASS |
| C | Single-Run Execution | PASS |
| D | Output Semantics | PASS |
| E | Determinism Validation | PASS |
| F | Relocatability Spot Check | PASS |
| G | Failure Handling | PASS |

**All checklist items A–G: PASS**

---

*Generated: 2026-01-07T18:41:11Z*
