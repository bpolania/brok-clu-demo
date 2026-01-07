# Phase V2-6 — Relocatability Test Matrix

## Test Run Information

| Property | Value |
|----------|-------|
| Run timestamp | 2026-01-07T17:41:16Z |
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Tarball SHA-256 | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |

---

## Scenario Results Summary

| Scenario | Description | run_poc_v2.sh exit | determinism_test_v2.sh exit | Final exit |
|----------|-------------|--------------------|-----------------------------|------------|
| 01 | Temp directory relocation | 0 | 0 | 0 |
| 02 | Non-root invocation | 0, 0 | 0 | 0 |
| 03 | Repo copy | 0 | 0 | 0 |

---

## Scenario 01 — Temp Directory Relocation

### Execution Context

| Property | Value |
|----------|-------|
| PWD | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Input argument form | absolute path |
| Resolved input path | /Users/bpolania/Documents/GitHub/brok-clu-demo/examples/inputs/accept_restart_alpha_1.txt |

### Commands Executed

| Command | Exit code |
|---------|-----------|
| `scripts/run_poc_v2.sh --input <resolved_path>` | 0 |
| `scripts/determinism_test_v2.sh --input <resolved_path> --runs 5` | 0 |

### Extraction Path Evidence

| Observation | Value | Transcript location |
|-------------|-------|---------------------|
| exec_bundle directory listing BEFORE run | empty (. and ..) | "Extraction directory mtime BEFORE run" section |
| exec_bundle_mtime_epoch_before | 1767807295 | "Extraction directory mtime BEFORE run" section |
| exec_bundle_mtime_utc_before | 2026-01-07T17:34:55Z | "Extraction directory mtime BEFORE run" section |
| exec_bundle directory listing AFTER run | empty (. and ..) | "Extraction directory mtime AFTER run" section |
| exec_bundle_mtime_epoch_after | 1767807678 | "Extraction directory mtime AFTER run" section |
| exec_bundle_mtime_utc_after | 2026-01-07T17:41:18Z | "Extraction directory mtime AFTER run" section |
| Bundle directories in run directory | none found | "Check for bundle directories" section |

Directory listing was empty before run and after run. exec_bundle mtime epoch before=1767807295; after=1767807678 (see Scenario 01 transcript).

### Artifacts Location

| Artifact type | Path |
|---------------|------|
| Run directory | /Users/bpolania/Documents/GitHub/brok-clu-demo/artifacts/run/run_20260107T174116Z |
| Determinism test | /Users/bpolania/Documents/GitHub/brok-clu-demo/artifacts/determinism/test_20260107T174118Z |

### Transcript Reference

File: `transcripts/scenario_01_tempdir_reloc.txt`

---

## Scenario 02 — Non-Root Invocation

### Test 1: Invoke from HOME

| Property | Value |
|----------|-------|
| PWD | /Users/bpolania |
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Input argument form | absolute path |
| Resolved input path | /Users/bpolania/Documents/GitHub/brok-clu-demo/examples/inputs/accept_restart_alpha_1.txt |
| run_poc_v2.sh exit code | 0 |

### Test 2: Invoke from Nested Temp Directory

| Property | Value |
|----------|-------|
| PWD | /tmp/phase_v2_6_test/deeply/nested/directory |
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Input argument form | absolute path |
| Resolved input path | /Users/bpolania/Documents/GitHub/brok-clu-demo/examples/inputs/accept_restart_alpha_1.txt |
| run_poc_v2.sh exit code | 0 |

### Test 3: Determinism from Non-Root Directory

| Property | Value |
|----------|-------|
| PWD | /tmp/phase_v2_6_test/deeply/nested/directory |
| determinism_test_v2.sh exit code | 0 |

### Artifacts Location

Run artifacts location: /Users/bpolania/Documents/GitHub/brok-clu-demo/artifacts/run/
Determinism artifacts location: /Users/bpolania/Documents/GitHub/brok-clu-demo/artifacts/determinism/

### Transcript Reference

File: `transcripts/scenario_02_nonroot_invocation.txt`

---

## Scenario 03 — Repo Copy

### Original Repository

| Property | Value |
|----------|-------|
| Repo root (git rev-parse) | /Users/bpolania/Documents/GitHub/brok-clu-demo |
| Tarball SHA-256 | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |

### Copied Repository

| Property | Value |
|----------|-------|
| Copy location | /tmp/phase_v2_6_repo_copy_test |
| Repo root (git rev-parse) | /private/tmp/phase_v2_6_repo_copy_test |
| PWD | /tmp/phase_v2_6_repo_copy_test |
| Tarball SHA-256 | 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a |
| SHA-256 comparison | MATCH |

### Commands Executed in Copied Repo

| Command | Exit code |
|---------|-----------|
| `scripts/run_poc_v2.sh --input <resolved_path>` | 0 |
| `scripts/determinism_test_v2.sh --input <resolved_path> --runs 3` | 0 |

### Artifacts Location (in copied repo)

| Artifact type | Path |
|---------------|------|
| Run directory | /tmp/phase_v2_6_repo_copy_test/artifacts/run/run_20260107T174140Z |
| Determinism test | /tmp/phase_v2_6_repo_copy_test/artifacts/determinism/test_20260107T174142Z |

### Transcript Reference

File: `transcripts/scenario_03_repo_copy.txt`

---

## Determinism Comparison Method Evidence

Source: `scripts/determinism_test_v2.sh`, line 265:
```
   265	        if ! cmp -s "$BASELINE_FILE" "$RUN_SUBDIR/stdout.raw.kv"; then
```

This line is printed in Scenario 01 transcript under "Determinism comparison method evidence" section.
