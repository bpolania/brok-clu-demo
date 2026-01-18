# Phase L-5: Wrapper UX + Derived JSON Summary

## Summary

Phase L-5 adds an optional convenience wrapper (`./brok-run`) that provides a
simplified interface for interactive use while preserving all authority invariants.

**Key Properties:**
- Wrapper is DERIVED and NON-AUTHORITATIVE
- Canonical command remains: `./brok --input <file>`
- `stdout.raw.kv` remains the ONLY authoritative execution output
- Console JSON summary is derived, not authoritative
- Run identification uses filesystem delta (black-box, no internal coupling)

---

## Authority Model (Unchanged)

| Component | Authority | L-5 Status |
|-----------|-----------|------------|
| `./brok` | Canonical CLI | UNCHANGED |
| Artifact layer | Sole decision authority | UNCHANGED |
| `stdout.raw.kv` | Authoritative execution output | UNCHANGED |
| `./brok-run` | DERIVED wrapper | NEW (non-authoritative) |
| Console JSON | DERIVED summary | NEW (non-authoritative) |

---

## Canonical Command

The canonical command remains:

```bash
./brok --input <file>
```

This command:
- Is the ONLY authoritative way to invoke the pipeline
- Has NOT been modified by L-5
- Produces `stdout.raw.kv` as the sole authoritative output

---

## Wrapper Command (Optional, Derived)

The new wrapper command is:

```bash
./brok-run "<input string>"
```

This wrapper:
1. Accepts a single quoted string argument
2. Creates a temporary input file internally
3. Snapshots run directories before invocation
4. Invokes: `./brok --input <tempfile>`
5. Snapshots run directories after invocation
6. Identifies new directory via filesystem delta
7. Prints a derived JSON summary (frozen schema)
8. Prints the authoritative output path
9. Cleans up the temporary file

### Output Contract (Exactly Two Lines)

For successful wrapper invocation, the wrapper produces exactly two lines of output:

**Line 1**: JSON with frozen schema (all fields always present)
**Line 2**: `Authoritative output: <path>` or `Authoritative output: NONE`

### Example Usage

```bash
# ACCEPT case (L-4 state transition)
$ ./brok-run "create payment"
{"run_dir":"/path/to/artifacts/run/m4_abc123...","decision":"ACCEPT","authoritative_stdout_raw_kv":"/path/to/l4_run_run_.../stdout.raw.kv","authoritative_stdout_raw_kv_sha256":"382dc31811e5097c..."}
Authoritative output: /path/to/artifacts/run/l4_run_run_.../stdout.raw.kv

# REJECT case
$ ./brok-run "payment succeeded"
{"run_dir":"/path/to/artifacts/run/m4_def456...","decision":"REJECT","authoritative_stdout_raw_kv":null,"authoritative_stdout_raw_kv_sha256":null}
Authoritative output: NONE
```

---

## Frozen JSON Schema

The JSON summary uses a frozen schema with exactly four fields (all derived, non-authoritative):

| Field | Type | ACCEPT | REJECT |
|-------|------|--------|--------|
| `run_dir` | string | Path to new m4_* directory | Path to new m4_* directory |
| `decision` | string | "ACCEPT" | "REJECT" |
| `authoritative_stdout_raw_kv` | string \| null | Path to stdout.raw.kv | null |
| `authoritative_stdout_raw_kv_sha256` | string \| null | SHA-256 hash | null |

**Important**:
- All four fields are ALWAYS present (frozen schema)
- `run_dir` is always non-null (the filesystem delta directory)
- For REJECT: `authoritative_stdout_raw_kv` and `authoritative_stdout_raw_kv_sha256` are null
- This JSON is DERIVED. It does NOT influence pipeline behavior.

---

## Frozen Exclusions

**L-5 intentionally does NOT surface the following fields:**

| Excluded Field | Reason |
|----------------|--------|
| `previous_state` | L-4 workflow semantics |
| `current_state` | L-4 workflow semantics |
| `terminal` | L-4 workflow semantics |

**Rationale**: L-5 is a UX wrapper only. It must not expose L-4 state machine
semantics as part of its stable interface. These fields are implementation
details of L-4 and are explicitly out of scope for L-5.

**This exclusion is FROZEN**: These fields must not be added to the L-5 JSON
schema without a new phase that explicitly addresses the authority and
compatibility implications.

---

## Run Directory Identification

The wrapper uses **filesystem delta** to identify the run created by each invocation:

### Method

1. **Snapshot before**: Enumerate immediate child directories of `artifacts/run/`
2. **Invoke ./brok**: Execute `./brok --input <tempfile>` unchanged
3. **Snapshot after**: Enumerate immediate child directories again
4. **Compute delta**: `new_directories = after - before`
5. **Verify exactly 1**: If delta != 1, treat as wrapper failure
6. **Use delta as run_dir**: The single new directory becomes `run_dir`

### Properties

- **Black-box**: Treats ./brok as opaque; does not depend on internal algorithms
- **No console parsing**: Does not parse ./brok's stdout/stderr
- **No run_id recomputation**: Does not reimplement ./brok's run_id algorithm
- **No timestamp heuristics**: Does not use file modification times
- **Deterministic**: Filesystem state before/after is the only input

### Wrapper Failure

If the delta is not exactly 1 (0 or >1 new directories), the wrapper:
- Prints a minimal error to stderr (single line)
- Exits with code 3 (distinct from success=0 and wrong_args=2)
- Does NOT print JSON (run_dir cannot be trusted)
- Still cleans up the temp file

---

## What the Wrapper Does NOT Do

The wrapper explicitly does NOT:
- Make decisions (artifact layer is sole authority)
- Influence control flow
- Add semantics or interpretation
- Cache, persist, or retry
- Modify `./brok` or its behavior
- Add new authoritative outputs
- Parse ./brok console output for path detection
- Recompute run_id from input content
- Use timestamps to identify runs
- Expose L-4 workflow state semantics

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (propagated from ./brok) |
| 2 | Wrong arguments (no ./brok invocation) |
| 3 | Wrapper failure (ambiguous delta, cannot read decision, etc.) |

---

## Guardrails

The L-5 implementation includes multi-layer guardrails:

1. **Hash file verification**: `proofs/brok_hash.txt` records expected SHA-256
2. **Byte-level integrity check**: Verifies ./brok hash matches expected value
3. **Git diff check**: Verifies no uncommitted changes to ./brok
4. **Git status check**: Verifies ./brok not marked as modified
5. **Argument validation**: Wrapper rejects wrong argument counts (single usage line only)
6. **Exit code propagation**: Wrapper exit code equals underlying `./brok` exit code
7. **Temp file cleanup**: Temporary input files are always removed
8. **Delta validation**: Exactly 1 new directory required

---

## Test Coverage

Tests verify (14 tests total):

1. `./brok` remains unchanged (byte-level hash check)
2. Wrapper rejects zero arguments (single usage line, empty stdout)
3. Wrapper rejects too many arguments (single usage line, empty stdout)
4. ACCEPT produces valid JSON with frozen schema (4 fields, non-null values)
5. ACCEPT run_dir equals filesystem delta directory
6. ACCEPT paths actually exist
7. ACCEPT SHA-256 matches actual file content
8. ACCEPT authoritative line exact format
9. REJECT produces valid JSON with frozen schema (4 fields, null for auth paths)
10. REJECT run_dir equals filesystem delta directory
11. REJECT authoritative line exactly "Authoritative output: NONE"
12. Exit code propagation (0 for both ACCEPT and REJECT)
13. Temp file cleanup
14. Exit codes are distinct (0, 2, 3)

---

## Files Added/Modified

| File | Purpose |
|------|---------|
| `brok-run` | Wrapper entrypoint (filesystem delta based) |
| `tests/l5/test_l5_wrapper.py` | Closure-grade tests (14 tests) |
| `docs/migration/PHASE_L_5_WRAPPER_UX.md` | This documentation |
| `scripts/verify_brok_unchanged.py` | Multi-layer guardrail script |
| `proofs/brok_hash.txt` | Authoritative ./brok hash with provenance |

---

## Conclusion

Phase L-5 provides a convenience wrapper without compromising authority invariants.
The canonical command `./brok --input <file>` remains the authoritative interface,
and `stdout.raw.kv` remains the only authoritative execution output.

The wrapper identifies runs using filesystem delta (black-box, no internal coupling),
and the intentional exclusion of L-4 workflow semantics is frozen as an explicit
design decision.
