# Phase V2-2 — Verification Wiring (Closure)

## Status

- **Phase:** V2-2
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Files Added/Changed

| File | Action | Purpose |
|------|--------|---------|
| `scripts/verify_poc_v2.sh` | Added | Verification wrapper script |
| `evidence/phase_v2_2/PHASE_V2_2_CLOSURE.md` | Added | Phase closure attestation |

---

## Verification Command

To run verification:

```sh
./scripts/verify_poc_v2.sh
```

This can also be invoked from any directory:

```sh
/path/to/repo/scripts/verify_poc_v2.sh
```

---

## Verification Workflow

1. Verifies vendored tarball SHA-256 against `vendor/poc_v2/SHA256SUMS.vendor`
2. Extracts tarball to `artifacts/poc_v2_extracted/run_<UTC_TIMESTAMP>/bundle_root/`
3. Discovers canonical verification entrypoint (searches for `verify.sh`, `VERIFY.sh`, `bin/verify`, `scripts/verify.sh`)
4. Invokes PoC v2 verification entrypoint
5. Captures results to `artifacts/verify/run_<UTC_TIMESTAMP>/`:
   - `stdout.txt`
   - `stderr.txt`
   - `exit_code.txt`
   - `meta.json`
   - `bundle_artifacts/` (if PoC v2 produces artifacts)

---

## Verification Gating Semantics

- **Success:** PoC v2 verification entrypoint exits with code 0
- **Failure:** Any nonzero exit code OR wiring failure (hash mismatch, extraction failure, entrypoint missing/ambiguous)
- Pass/fail determined solely by exit code, not by parsing stdout/stderr

---

## Attestations

- **Runtime execution is NOT wired:** This phase only implements verification; no runtime execution entrypoint is called
- **Bundle remains unmodified:** The vendored tarball `vendor/poc_v2/poc_v2.tar.gz` is never modified; extraction occurs to gitignored `artifacts/` directory
- **No fabricated artifacts:** Verification artifacts are produced only by PoC v2 itself, never by the demo wrapper

### Capture File Semantics

The wrapper writes `stdout.txt`, `stderr.txt`, `exit_code.txt`, and `meta.json` to `artifacts/verify/run_<timestamp>/`. These files are:

- **Demo-owned capture evidence** for audit and debug purposes only
- **NOT PoC v2 verification artifacts** — they are wrapper infrastructure
- **Never used to infer verification success** — pass/fail is determined solely by PoC v2's exit code

---

## Verification Evidence

Tarball SHA-256 (unchanged from Phase V2-1):
```
7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a  vendor/poc_v2/poc_v2.tar.gz
```

---

## Amendment (Post-Review Fixes)

**Date:** 2026-01-07

The following targeted fixes were applied to `scripts/verify_poc_v2.sh`:

| Fix | Description |
|-----|-------------|
| Exit code propagation | Changed `exit 1` to `exit $VERIFY_EXIT_CODE` so wrapper propagates PoC v2's actual exit code N, not a hardcoded 1 |
| Bundle artifact paths in meta.json | Added `bundle_artifact_paths` array to meta.json recording discovered artifact directories (e.g., `["bundles/verified"]`) |
| Testing documentation | Added header comments documenting exit codes and testing procedures |

**Verification of requirements:**

1. **Entrypoint ambiguity:** Already correct (fails on 0 or >1 matches)
2. **Nonzero exit propagation:** Fixed (now exits with actual code N)
3. **Capture under set -e:** Already correct (uses set +e around verify invocation)
4. **Conditional artifact copy:** Already correct (only copies if exists); now also records paths in meta.json

---

## Negative Runtime Test (Wrapper-Internal Failure)

### Testing Hook

A permissions-based testing hook in `scripts/verify_poc_v2.sh` induces wrapper-internal failure:

- **Trigger:** `BROK_CLU_V2_TEST_EXTRACT_READONLY=1`
- **Behavior:** Makes extraction directory read-only before tar runs, causing extraction failure
- **Effect:** tar cannot write → wrapper calls `fail()` with exit code 1
- **Constraints:**
  - **Never touches `vendor/`** — operates only on `artifacts/` paths
  - **Disabled by default** — inert unless env var explicitly set
  - **Permissions restored via trap** — cleanup runs on exit regardless of pass/fail
  - **Capture files written** — VERIFY_DIR remains writable so fail() produces all artifacts

### Commands

```sh
# 1. Success run (baseline)
./scripts/verify_poc_v2.sh
echo "Exit code: $?"

# 2. Negative test: force extraction failure (exit 1)
BROK_CLU_V2_TEST_EXTRACT_READONLY=1 ./scripts/verify_poc_v2.sh
echo "Exit code: $?"

# 3. Verify capture artifacts exist
ls -la artifacts/verify/run_20260107T072348Z/
cat artifacts/verify/run_20260107T072348Z/exit_code.txt

# 4. Confirm vendor unchanged
shasum -a 256 vendor/poc_v2/poc_v2.tar.gz
```

### Observed Exit Code

```
EXIT_CODE=1
```

### Capture Directory

```
artifacts/verify/run_20260107T072348Z/
```

### Artifact Verification

| File | Exists | Content |
|------|--------|---------|
| `stdout.txt` | ✅ | (empty) |
| `stderr.txt` | ✅ | `Extraction failed (tar could not write to .../bundle_root)` |
| `exit_code.txt` | ✅ | `1` |
| `meta.json` | ✅ | See below |

**meta.json contents:**
```json
{
  "tarball_sha256": "7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a",
  "extraction_path": ".../run_20260107T072348Z/bundle_root",
  "bundle_root": "unknown",
  "entrypoint_path": null,
  "utc_timestamp": "20260107T072348Z",
  "invocation_cwd": "/Users/bpolania/Documents/GitHub/brok-clu-demo",
  "exit_code": 1,
  "bundle_artifact_paths": [],
  "wrapper_failure": "Extraction failed (tar could not write to .../bundle_root)"
}
```

### Vendor Integrity Confirmation

**`vendor/poc_v2/` was NOT modified:**

```
$ shasum -a 256 vendor/poc_v2/poc_v2.tar.gz
7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a  vendor/poc_v2/poc_v2.tar.gz
```

Hash matches `SHA256SUMS.vendor` — vendored bundle remains immutable.

### Permissions Restoration

After script exit, extraction directory permissions are restored to original (755):

```
$ ls -ld artifacts/poc_v2_extracted/run_20260107T072348Z/bundle_root/
drwxr-xr-x  2 user  staff  64 Jan  7 01:23 .../bundle_root/
```

---

## Closure

Phase V2-2 complete and frozen.

Verification wiring is operational. The demo repo can now invoke PoC v2's canonical verification workflow in a faithful, mandatory, blocking, relocatable, and auditable manner.

Phase V2-3 (Execution Wiring) may proceed.
