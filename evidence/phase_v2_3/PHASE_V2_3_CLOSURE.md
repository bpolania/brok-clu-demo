# Phase V2-3 — Execution Wiring (Closure)

## Status

- **Phase:** V2-3
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Files Added/Changed

| File | Action | Purpose |
|------|--------|---------|
| `scripts/run_poc_v2.sh` | Added | Execution wrapper with V2-2 verification gating |
| `evidence/phase_v2_3/PHASE_V2_3_CLOSURE.md` | Added | Phase closure attestation |

---

## Execution Command

To run PoC v2 with verification-gated execution:

```sh
./scripts/run_poc_v2.sh --input <PATH_TO_INPUT_FILE>
```

This can also be invoked from any directory:

```sh
/path/to/repo/scripts/run_poc_v2.sh --input /path/to/input.txt
```

---

## Execution Workflow

1. Creates timestamped run directory: `artifacts/run/run_<UTC_TIMESTAMP>/`
2. **Invokes V2-2 verification (`scripts/verify_poc_v2.sh`) as authoritative black box**
3. **Only if V2-2 passes (exit 0)**, extracts tarball to `artifacts/run/run_<timestamp>/bundle_root/`
4. Runs bundle's internal verify.sh to set up verification state (output discarded)
5. Discovers run entrypoint from allowlist: `run.sh`, `RUN.sh`, `bin/run`, `scripts/run.sh`
6. Invokes run entrypoint exactly once with input file path
7. Captures results to `artifacts/run/run_<UTC_TIMESTAMP>/`:
   - `stdout.txt` (verbatim execution stdout)
   - `stderr.txt` (verbatim execution stderr)
   - `exit_code.txt` (numeric exit code)
   - `meta.txt` (plain text, factual fields only)
   - `verify_stdout.txt`, `verify_stderr.txt`, `verify_exit_code.txt` (V2-2 capture)

---

## V2-2 as Single Source of Truth

V2-3 does **NOT** re-implement verification logic. Instead:

- V2-3 invokes `scripts/verify_poc_v2.sh` (V2-2) as an opaque black box
- V2-3 trusts V2-2's exit code as the sole gate for execution
- V2-3 does **NOT** verify tarball SHA-256 (that is V2-2's responsibility)
- V2-3 does **NOT** discover verification entrypoints (V2-2 handles that)

This architecture ensures:
- No logic duplication between V2-2 and V2-3
- V2-2 remains the authoritative verification implementation
- Changes to verification semantics require only V2-2 modifications

---

## Verification Gating Semantics

- **Verification is MANDATORY:** Execution cannot proceed without V2-2 success
- **Black box invocation:** V2-3 calls V2-2 without knowing its internals
- **No shortcuts:** No "already verified" caching, no skip flags, no fallbacks
- **Exit code determines success:** Execution proceeds only if V2-2 exits with code 0
- **Blocking:** If V2-2 fails, execution is never attempted

---

## Double Extraction Architecture

V2-2 and V2-3 each extract the tarball independently:

- **V2-2 extraction:** To `artifacts/poc_v2_extracted/run_<timestamp>/` for verification
- **V2-3 extraction:** To `artifacts/run/run_<timestamp>/bundle_root/` for execution

This is intentional:
- Each phase owns its extraction directory
- No shared state between verification and execution paths
- V2-3 runs bundle's internal verify.sh to recreate verification state files

---

## Bundle Internal Verify Step Justification

V2-3 runs the bundle's internal `verify.sh` after V2-2 passes **because PoC v2 documentation explicitly requires verify-before-run ordering in the same extraction**.

**Primary evidence sources (operator workflow documentation):**
- `brok-clu-poc_v2-standalone/README.md` lines 86-97: Numbered steps showing extract → verify → run sequence
- `brok-clu-poc_v2-standalone/VERIFY.md` lines 131-154: Numbered steps showing extract → verify → run sequence
- `brok-clu-poc_v2-standalone/VERIFY.md` lines 9-11: States run.sh checks `bundles/verified/verify.status.txt`

Since V2-3 extracts fresh (separate from V2-2's extraction), it must run the bundle's verify.sh to create the required `bundles/verified/verify.status.txt` file that run.sh checks.

**Evidence file:** `evidence/phase_v2_3/POC_V2_RUN_ORDER_EVIDENCE.md`

This step:
- Does NOT duplicate V2-2's verification role (V2-2 remains the authoritative gate)
- Merely satisfies PoC v2's documented internal requirement
- Output is discarded (only side effect is state file creation)

---

## Entrypoint Discovery Rules

### Run Entrypoint (V2-3)
Searched in order: `run.sh`, `RUN.sh`, `bin/run`, `scripts/run.sh`
- 0 matches: hard failure (no execution)
- 1 match: invoke that entrypoint
- >1 matches: hard failure (ambiguous, no execution)

---

## Failure Model

| Failure | Exit Code | Behavior |
|---------|-----------|----------|
| Input file missing | 2 | Usage error, no run directory created |
| V2-2 verification failed | N | Propagate V2-2 exit code, no execution attempted |
| Extraction failed | 1 | Wrapper failure, meta.txt written |
| Bundle internal verify failed | 1 | Wrapper failure, meta.txt written |
| Run entrypoint missing | 1 | Wrapper failure, meta.txt written |
| Run entrypoint ambiguous | 1 | Wrapper failure, meta.txt written |
| Execution nonzero | N | Propagate execution exit code, capture all outputs |

---

## meta.txt Format

meta.txt contains **factual fields only** — no derived booleans:

```
utc_timestamp: 20260107T150634Z
verify_invocation: /path/to/scripts/verify_poc_v2.sh
verify_exit_code: 0
extraction_path: /path/to/artifacts/run/run_<timestamp>/bundle_root
bundle_root: /path/to/bundle_root/brok-clu-poc_v2-standalone
run_entrypoint: scripts/run.sh
input_file: /path/to/input.txt
working_directory: /path/to/bundle_root/brok-clu-poc_v2-standalone
execution_exit_code: 0
```

**Not included:**
- `verification_passed: true` — derived from exit code
- `execution_attempted: true` — implicit from execution_exit_code presence
- `poc_outputs: [...]` — no output heuristics

---

## Console Output

V2-3 emits **minimal status lines only**:

```
run_directory: /path/to/artifacts/run/run_<timestamp>
verification: invoking /path/to/scripts/verify_poc_v2.sh
verification: exit_code=0
execution: running bundle verify to set internal state
execution: run_entrypoint=scripts/run.sh
execution: invoking with input=/path/to/input.txt
execution: exit_code=0
```

**Not emitted:**
- Captured stdout/stderr (written to files only)
- PoC v2 output content

---

## Attestations

- **V2-2 is the single source of verification truth:** V2-3 does not re-implement verification
- **No SHA-256 verification in V2-3:** Tarball integrity is V2-2's responsibility
- **No output heuristics:** No copying of guessed output directories
- **No console mirroring:** Captured stdout/stderr are not echoed to console
- **Factual meta.txt only:** No derived booleans or computed fields
- **No determinism logic exists:** This phase implements single-run only
- **No output transformation exists:** stdout/stderr are captured verbatim
- **Bundle remains unmodified:** The vendored tarball is never modified

### Capture File Semantics

The files `stdout.txt`, `stderr.txt`, `exit_code.txt`, and `meta.txt` in `artifacts/run/run_<timestamp>/` are:

- **Demo-owned capture evidence** for audit and debug purposes only
- **NOT PoC v2 execution artifacts** — they are wrapper infrastructure
- **Never used to infer execution success** — pass/fail is determined solely by exit code

---

## Verification Evidence

### Success Run

```sh
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
# Exit code: 0
```

Run directory: `artifacts/run/run_20260107T150634Z/`

**Console output:**
```
run_directory: /Users/.../artifacts/run/run_20260107T150634Z
verification: invoking /Users/.../scripts/verify_poc_v2.sh
verification: exit_code=0
execution: running bundle verify to set internal state
execution: run_entrypoint=scripts/run.sh
execution: invoking with input=/tmp/test_input.txt
execution: exit_code=0
```

**meta.txt contents:**
```
utc_timestamp: 20260107T150634Z
verify_invocation: /Users/.../scripts/verify_poc_v2.sh
verify_exit_code: 0
extraction_path: /Users/.../artifacts/run/run_20260107T150634Z/bundle_root
bundle_root: /Users/.../bundle_root/brok-clu-poc_v2-standalone
run_entrypoint: scripts/run.sh
input_file: /tmp/test_input.txt
working_directory: /Users/.../bundle_root/brok-clu-poc_v2-standalone
execution_exit_code: 0
```

### Verification Failure Run

```sh
# With corrupted SHA256SUMS.vendor (simulated)
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
# Exit code: 1
```

**Console output:**
```
run_directory: /Users/.../artifacts/run/run_20260107T150854Z
verification: invoking /Users/.../scripts/verify_poc_v2.sh
verification: exit_code=1
```

**meta.txt contents:**
```
utc_timestamp: 20260107T150854Z
verify_invocation: /Users/.../scripts/verify_poc_v2.sh
verify_exit_code: 1
input_file: /tmp/test_input.txt
working_directory: /Users/...
```

### Vendor Integrity

Tarball SHA-256 (unchanged):
```
7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a  vendor/poc_v2/poc_v2.tar.gz
```

---

## Structural Guarantees

### V2-2 Black Box Invocation

The script structure guarantees V2-2 is called as black box:

1. V2-2 is invoked at line ~107: `"$VERIFY_SCRIPT" >"$VERIFY_STDOUT" 2>"$VERIFY_STDERR"`
2. Exit code captured at line ~108: `VERIFY_EXIT_CODE=$?`
3. If `VERIFY_EXIT_CODE -ne 0`, the script exits at line ~129
4. No tarball hash verification in V2-3 (removed)
5. No verification entrypoint discovery in V2-3 (removed)

### Single Execution Path

After V2-2 passes, there is exactly one path:
1. Extract tarball for execution
2. Run bundle's internal verify.sh (output discarded)
3. Discover run entrypoint from allowlist
4. Fail if 0 or >1 matches
5. Invoke exactly once with input file

No loops, no retries, no conditional execution paths.

---

## Closure

Phase V2-3 complete and frozen.

Execution wiring is operational with corrected architecture:
1. V2-2 is the single source of verification truth (black box invocation)
2. No re-implementation of verification logic in V2-3
3. No SHA-256 verification in V2-3
4. No output heuristics or console mirroring
5. Factual-only meta.txt

The demo repo can now:
1. Run V2-2 verification (mandatory, blocking, black box)
2. Run PoC v2 execution (single-run, post-verification only)
3. Capture all outputs verbatim for audit
