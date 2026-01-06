# Brok-CLU Runtime Demo

A sealed runtime demo that consumes the Brok-CLU PoC v1 artifact for deterministic command routing.

---

## What This Repository Is

This repository demonstrates the Brok-CLU runtime routing capability using a frozen, archival artifact. It is a **consumption demo only**.

Key properties:
- **Sealed**: The runtime binary is externally produced and immutable
- **Deterministic**: Identical inputs produce identical outputs
- **Verified**: Mandatory integrity verification before every execution
- **Bounded**: Closed intent set, no extensibility

This is **not** an SDK, framework, or extensible system. The runtime behavior cannot be configured, extended, or modified.

---

## Platform Requirements

| Requirement | Value |
|-------------|-------|
| Platform | macOS arm64 only |
| Runtime | Brok-CLU PoC v1 (sealed, frozen) |

No other platforms are supported.

---

## Domain

Deterministic Command Routing with a closed intent set:

| Intent             | Description                        |
|--------------------|------------------------------------|
| RESTART_SUBSYSTEM  | Restart a target subsystem         |
| STOP_SUBSYSTEM     | Stop a target subsystem            |
| STATUS_QUERY       | Query status of a target subsystem |

Bounded slots:
- `target`: alpha, beta, gamma
- `mode`: graceful, immediate (where applicable)

---

## I/O Contract

### Input

- UTF-8 text file
- Single line
- One command per invocation

### Output

The authoritative runtime output format is `key=value` (one pair per line).

Example output:
```
status=ACCEPT
intent=RESTART_SUBSYSTEM
target=alpha
mode=graceful
```

No partial output. No best-effort parsing.

---

## How to Run

### Single-Run Mode

```sh
./run.sh <input-file>
```

Example:
```sh
./run.sh examples/inputs/accept_restart_alpha_1.txt
```

### Determinism Test Mode

```sh
./run.sh --determinism-test --input <file> --runs <N>
```

Example:
```sh
./run.sh --determinism-test --input examples/inputs/accept_restart_alpha_1.txt --runs 5
```

---

## Output Artifacts

After execution, output artifacts are written to:

| File | Description |
|------|-------------|
| `artifacts/last_run/output.raw.kv` | Authoritative runtime output (key=value format, exact copy of stdout) |
| `artifacts/last_run/output.derived.json` | Derived JSON representation (non-authoritative, for inspection only) |

### Interpreting Outputs

- The `key=value` format in `output.raw.kv` is the **authoritative** runtime output.
- The JSON in `output.derived.json` is **derived** strictly from the raw output and includes explicit markers:
  - `"derived": true`
  - `"source_format": "key=value"`
- On execution failure, no derived JSON is produced.
- Raw output is always captured if the runtime emits stdout, regardless of exit code.

---

## Determinism Validation

After running a determinism test, inspect results:

```sh
cat artifacts/determinism/summary.txt
```

Per-run outputs are preserved for comparison:
```
artifacts/determinism/run_001/output.raw.kv
artifacts/determinism/run_002/output.raw.kv
...
```

Compare any two runs:
```sh
diff artifacts/determinism/run_001/output.raw.kv artifacts/determinism/run_002/output.raw.kv
```

### Determinism Guarantees

- Identical inputs produce byte-identical `output.raw.kv` across runs
- Comparison is byte-for-byte using `diff -q`
- No semantic interpretation or normalization
- PASS: All runs identical, exit 0
- FAIL: Any mismatch or failure, exit 1

---

## Verification

Verification is **mandatory** and runs before every execution attempt.

Verification confirms:
- All files in `MANIFEST.txt` exist
- No extra files exist under `bundles/poc_v1/`
- All SHA-256 checksums match

If verification fails, execution is blocked. See `VERIFY.md` for the complete trust model.

---

## Example Inputs

See `examples/inputs/` for the locked example input set:

| File                        | Expected |
|-----------------------------|----------|
| accept_restart_alpha_1.txt  | ACCEPT   |
| accept_restart_alpha_2.txt  | ACCEPT   |
| accept_status_beta.txt      | ACCEPT   |
| reject_grammar_1.txt        | REJECT   |
| reject_semantic_1.txt       | REJECT   |

---

## What This Demo Does NOT Do

This demo has explicit boundaries:

| Non-Goal | Explanation |
|----------|-------------|
| Runtime configurability | No flags, environment variables, or config files alter behavior |
| Grammar editing | The grammar is sealed inside the binary |
| Intent expansion | The intent set is closed and cannot be extended |
| SDK or API surface | This is a demo, not a library or framework |
| Performance benchmarking | No timing, profiling, or performance metrics |
| Production hardening | No security claims beyond verification |
| Battleship demo | Out of scope for this repository |
| Interactive UX | No REPL, GUI, or interactive modes |

---

## Documentation

| File | Description |
|------|-------------|
| `VERIFY.md` | Trust model and verification boundary |
| `PHASE0_SCOPE_LOCK.md` | Phase 0 scope lock documentation |
| `PHASE0_INPUTS_MANIFEST.json` | Machine-readable inputs manifest |
| `PHASE0_EXIT_ATTESTATION.md` | Phase 0 closure attestation |
| `PHASE3_EXECUTION_LOCK.md` | Verification and execution semantics |
| `evidence/phase5/PHASE5_FINAL_CLOSURE_REPORT.md` | Determinism validation closure |

---

## Repository Structure

```
brok-clu-demo/
├── run.sh                      # Entrypoint (verification + execution)
├── bundles/poc_v1/             # Vendored runtime artifacts (immutable)
│   ├── bin/macos-arm64/cmd_interpreter
│   ├── VERSION.txt
│   ├── MANIFEST.txt
│   └── SHA256SUMS
├── examples/inputs/            # Locked example inputs
├── artifacts/                  # Generated outputs (gitignored)
│   ├── last_run/
│   └── determinism/
└── evidence/                   # Phase closure documentation
```
