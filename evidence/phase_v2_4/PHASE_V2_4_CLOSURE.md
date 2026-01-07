# Phase V2-4 — Output Capture & Presentation (Closure)

## Status

- **Phase:** V2-4
- **Status:** COMPLETE
- **Mutability:** FROZEN

---

## Authoritative Output Definition

**The single source of truth for PoC v2 execution output is `stdout.raw.kv`.**

This file contains the exact bytes emitted by PoC v2 to stdout, in order, without modification. The wrapper does not:
- Trim, normalize, or reorder output
- Interpret ACCEPT/REJECT or status meanings
- Collapse or annotate the output
- Invent fields or infer semantics

---

## Artifact Schema

For each run, artifacts are created under:
```
artifacts/run/run_<UTC_TIMESTAMP>/
```

### Execution Success (verification passed, PoC invoked)

| File | Type | Description |
|------|------|-------------|
| `stdout.raw.kv` | Authoritative | Verbatim PoC v2 stdout bytes |
| `stderr.raw.txt` | Supporting | Verbatim PoC v2 stderr bytes |
| `exit_code.txt` | Supporting | Decimal exit code with trailing newline |
| `execution.meta.json` | Metadata | Non-authoritative run metadata |
| `stdout.derived.json` | Derived | Mechanically parsed view (non-authoritative) |
| `DERIVED_VIEW_NOTICE.txt` | Notice | States derived outputs are non-authoritative |
| `verify/` | Directory | V2-2 verification capture |

**Note:** No extracted bundle content is stored in the run directory. Bundle extraction occurs in a separate temporary location and is cleaned up after execution.

### Verification Failure (execution not attempted)

| File | Type | Description |
|------|------|-------------|
| `execution.SKIPPED` | Sentinel | Empty file indicating verification failed |
| `execution.meta.json` | Metadata | Shows `verification_passed: false`, `execution_attempted: false` |
| `verify/` | Directory | V2-2 verification capture |

### Wrapper Failure (before PoC invocation)

| File | Type | Description |
|------|------|-------------|
| `execution.NOT_RUN` | Sentinel | Empty file indicating wrapper failed before PoC invocation |
| `execution.meta.json` | Metadata | Shows `execution_attempted: false` |
| `verify/` | Directory | V2-2 verification capture (if verification passed) |

---

## Verification Capture (inherited from Phase V2-2)

The `verify/` subdirectory contains verification capture artifacts **inherited unchanged from Phase V2-2**. File names are exactly as defined by V2-2:

| File | Description |
|------|-------------|
| `verify/stdout.txt` | V2-2 verification stdout |
| `verify/stderr.txt` | V2-2 verification stderr |
| `verify/exit_code.txt` | V2-2 verification exit code |

These names are not modified by V2-4. Any changes to verification capture naming would require a Phase V2-2 change.

---

## exit_code.txt Format Specification

The `exit_code.txt` file (both in run directory and `verify/`) has a strict format:

```
<decimal_integer>\n
```

Where:
- `<decimal_integer>` is the exit code as a base-10 integer (e.g., `0`, `1`, `10`)
- `\n` is exactly one newline character (LF, 0x0A)
- No leading/trailing whitespace
- No additional content

Examples:
- Success: `0\n` (2 bytes)
- Failure: `1\n` (2 bytes)
- PoC error code: `10\n` (3 bytes)

---

## execution.meta.json Schema

Allowed fields only (no semantic interpretation):

```json
{
  "run_dir": "<absolute path>",
  "created_at_utc": "<ISO 8601 timestamp>",
  "verification_passed": <boolean>,
  "execution_attempted": <boolean>,
  "exit_code": <integer or null>,
  "stdout_path": "<relative path or null>",
  "stderr_path": "<relative path or null>",
  "derived_stdout_json_path": "<relative path or null>",
  "notes": "<wrapper state only, no PoC output interpretation>"
}
```

**Prohibited fields:**
- Any field interpreting ACCEPT/REJECT
- Any field interpreting status meaning
- Any "normalized outcome" or "final result" field

---

## Derived Output Specification

### stdout.derived.json

Mechanically derived from `stdout.raw.kv` only:

```json
{
  "derived": true,
  "authoritative_source": "stdout.raw.kv",
  "note": "This file is derived for convenience only. Authoritative output is stdout.raw.kv.",
  "items": [
    {"type": "kv", "key": "<key>", "value": "<value>", "raw": "<original line>"},
    {"type": "unparsed_line", "raw": "<line without '='>"}
  ]
}
```

Rules:
- Lines containing `=` are split on first `=` only
- Lines without `=` are emitted as `unparsed_line`
- Order is preserved
- No semantic interpretation

### DERIVED_VIEW_NOTICE.txt

Required when any derived artifact exists. States:
- Outputs are derived and non-authoritative
- Source is `stdout.raw.kv`
- Derived views must not be used for determinism checks

---

## Attestations

### No Semantic Interpretation
- The wrapper does not interpret PoC v2 output meanings
- ACCEPT/REJECT status is not collapsed or normalized
- No "success" or "failure" fields beyond raw exit code

### No Determinism Logic
- No multi-run comparison
- No output diffing
- Single-run capture only

### No Changes to Verification/Execution Order
- Phase V2-2 verification remains mandatory and first
- Phase V2-3 execution ordering preserved exactly
- V2-2 is still the single source of truth for verification

### Derived Artifacts Are Non-Authoritative
- `stdout.derived.json` cannot be used for determinism checks
- `stdout.derived.json` cannot affect later phases
- Discrepancies resolve in favor of `stdout.raw.kv`

---

## Verification Procedure (for auditors)

### 1. Run the wrapper once

```sh
echo "turn on the lights" > /tmp/test_input.txt
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
```

### 2. Locate newest run directory

```sh
ls -lt artifacts/run/ | head -5
RUN_DIR=$(ls -td artifacts/run/run_* | head -1)
```

### 3. Verify authoritative output exists and is verbatim

```sh
cat "$RUN_DIR/stdout.raw.kv"
# Should show exact PoC v2 stdout
```

### 4. Verify no extracted bundle content in run directory

```sh
[ ! -d "$RUN_DIR/bundle_root" ] && echo "OK: No bundle_root directory"
ls "$RUN_DIR" | grep -v -E '^(stdout\.raw\.kv|stderr\.raw\.txt|exit_code\.txt|execution\.meta\.json|stdout\.derived\.json|DERIVED_VIEW_NOTICE\.txt|verify)$' && echo "FAIL: Unexpected files" || echo "OK: Only allowed files"
```

### 5. Verify derived notice exists when derived JSON exists

```sh
[ -f "$RUN_DIR/stdout.derived.json" ] && [ -f "$RUN_DIR/DERIVED_VIEW_NOTICE.txt" ] && echo "OK"
```

### 6. Verify execution.meta.json has only allowed fields

```sh
cat "$RUN_DIR/execution.meta.json"
# Must contain only: run_dir, created_at_utc, verification_passed, execution_attempted,
# exit_code, stdout_path, stderr_path, derived_stdout_json_path, notes
```

### 7. Verify verification failure produces SKIPPED and no execution files

```sh
# Temporarily corrupt vendor checksum
ORIG=$(cat vendor/poc_v2/SHA256SUMS.vendor)
echo "bad" > vendor/poc_v2/SHA256SUMS.vendor
./scripts/run_poc_v2.sh --input /tmp/test_input.txt 2>&1 || true
echo "$ORIG" > vendor/poc_v2/SHA256SUMS.vendor

FAIL_DIR=$(ls -td artifacts/run/run_* | head -1)
[ -f "$FAIL_DIR/execution.SKIPPED" ] && echo "SKIPPED sentinel exists"
[ ! -f "$FAIL_DIR/stdout.raw.kv" ] && echo "No execution files created"
```

### 8. Manual diff example (for future determinism phases)

```sh
# Run twice, compare authoritative outputs
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
RUN1=$(ls -td artifacts/run/run_* | head -1)
sleep 2
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
RUN2=$(ls -td artifacts/run/run_* | head -1)
diff -u "$RUN1/stdout.raw.kv" "$RUN2/stdout.raw.kv"
```

---

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `scripts/run_poc_v2.sh` | Modified | Implement V2-4 artifact schema |
| `evidence/phase_v2_4/PHASE_V2_4_CLOSURE.md` | Added | Phase closure attestation |

---

## Closure

Phase V2-4 complete and frozen.

Output capture and presentation is operational:
1. `stdout.raw.kv` is the single authoritative output (verbatim)
2. Derived outputs are mechanically generated and labeled non-authoritative
3. Sentinel files distinguish verification failure from wrapper failure
4. `execution.meta.json` contains only allowed fields
5. No semantic interpretation introduced
6. No determinism logic introduced
7. Prior phase constraints preserved exactly
