# Phase V2-6 — Relocatability Validation (Closure)

## Status

- **Phase:** V2-6
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Evidence Files

| File | Purpose |
|------|---------|
| `RELOCATABILITY_TEST_MATRIX.md` | Test matrix with scenario details |
| `PHASE_V2_6_CLOSURE.md` | Closure record (this file) |
| `transcripts/scenario_01_tempdir_reloc.txt` | Scenario 01 verbatim transcript |
| `transcripts/scenario_02_nonroot_invocation.txt` | Scenario 02 verbatim transcript |
| `transcripts/scenario_03_repo_copy.txt` | Scenario 03 verbatim transcript |

---

## Vendored Bundle SHA-256

Observed in transcripts:
```
7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a  poc_v2.tar.gz
```

---

## Scenario Results

### Scenario 01 — Temp Directory Relocation

| Property | Value |
|----------|-------|
| Transcript | `transcripts/scenario_01_tempdir_reloc.txt` |
| run_poc_v2.sh exit code | 0 |
| determinism_test_v2.sh exit code | 0 |
| Final exit code | 0 |

Scenario 01 records exec_bundle mtime epoch before/after run in transcript. Directory listing was empty before run and after run.

### Scenario 02 — Non-Root Invocation

| Property | Value |
|----------|-------|
| Transcript | `transcripts/scenario_02_nonroot_invocation.txt` |
| run_poc_v2.sh exit code (from HOME) | 0 |
| run_poc_v2.sh exit code (from nested temp) | 0 |
| determinism_test_v2.sh exit code | 0 |
| Final exit code | 0 |

### Scenario 03 — Repo Copy

| Property | Value |
|----------|-------|
| Transcript | `transcripts/scenario_03_repo_copy.txt` |
| run_poc_v2.sh exit code | 0 |
| determinism_test_v2.sh exit code | 0 |
| Final exit code | 0 |
| Tarball SHA-256 comparison | MATCH |

---

## Determinism Comparison Method

Reference: `scripts/determinism_test_v2.sh`, line 265
```
        if ! cmp -s "$BASELINE_FILE" "$RUN_SUBDIR/stdout.raw.kv"; then
```

This line is printed in Scenario 01 transcript.

---

## Git Status (after validation)

```
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	evidence/phase_v2_6/
	scripts/phase_v2_6_relocatability_proof.sh

nothing added to commit but untracked files present (use "git add" to track)
```

---

## Code Changes

Files added by Phase V2-6:
- `scripts/phase_v2_6_relocatability_proof.sh`
- `evidence/phase_v2_6/PHASE_V2_6_CLOSURE.md`
- `evidence/phase_v2_6/RELOCATABILITY_TEST_MATRIX.md`
- `evidence/phase_v2_6/transcripts/scenario_01_tempdir_reloc.txt`
- `evidence/phase_v2_6/transcripts/scenario_02_nonroot_invocation.txt`
- `evidence/phase_v2_6/transcripts/scenario_03_repo_copy.txt`

Files not modified:
- `scripts/run_poc_v2.sh`
- `scripts/determinism_test_v2.sh`
- `scripts/verify_poc_v2.sh`
- `vendor/poc_v2/poc_v2.tar.gz`

---

*Generated: 2026-01-07T17:41:16Z*
