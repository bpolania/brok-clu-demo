# Brok-CLU Runtime Demo

A sealed runtime demo that consumes the Brok-CLU PoC v2 artifact for deterministic command routing.

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

## Reference Artifact: How to Read This Repo

This repository is a **frozen reference artifact** tagged as `brok-demo-v1`. See [`REFERENCE_ARTIFACT.md`](REFERENCE_ARTIFACT.md) for the complete declaration.

### Pipeline Flow

```
INPUT --> PROPOSAL --> ARTIFACT --> EXECUTION --> OBSERVABILITY
  |          |            |            |              |
  |     (M-1: LLM)   (M-2: decision) (M-3: gate)  (M-4: trace)
  |          |            |            |              |
  v          v            v            v              v
input.txt  proposal_set  artifact   stdout.raw.kv  manifest.json
              .json        .json                   trace.jsonl
```

### Authority Boundaries

| Output | Authority |
|--------|-----------|
| `stdout.raw.kv` | **AUTHORITATIVE** - execution truth |
| `artifact.json` | DERIVED - wrapper decision record |
| `proposal_set.json` | NON-AUTHORITATIVE - may be wrong |
| `manifest.json`, `trace.jsonl` | DERIVED - observability only |

**Non-Goals:** This demo makes no claims about semantic correctness, NLP accuracy, or production readiness. See [`REFERENCE_ARTIFACT.md`](REFERENCE_ARTIFACT.md) for the full non-goals list.

---

## Platform Requirements

| Requirement | Value |
|-------------|-------|
| Platform | macOS arm64 only |
| Runtime | Brok-CLU PoC v2 (sealed, frozen) |

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

### Step 1: Verify Bundle Integrity

```sh
./scripts/verify_poc_v2.sh
```

### Step 2: Execute with Input

```sh
./scripts/run_poc_v2.sh --input <input-file>
```

Example:
```sh
echo "restart alpha subsystem gracefully" > /tmp/test_input.txt
./scripts/run_poc_v2.sh --input /tmp/test_input.txt
```

### Determinism Test Mode

```sh
./scripts/determinism_test_v2.sh --input <file> --runs <N>
```

---

## Output Artifacts

After execution, output artifacts are written to:

| Location | Description |
|----------|-------------|
| `artifacts/run/run_<timestamp>/stdout.raw.kv` | **Authoritative** runtime output |

All other output files are derived and non-authoritative.

To clean generated artifacts (optional):

```sh
rm -rf artifacts/ semantic/regression/runs/ semantic/artifacts/
```

---

## Verification

Verification is **mandatory** and runs before every execution attempt.

Verification confirms:
- Vendored tarball SHA-256 matches `SHA256SUMS.vendor`
- Extracted bundle matches internal checksums

If verification fails, execution is blocked. See `VERIFY.md` for the complete trust model.

The `docs/proofs/` directory contains frozen audit and validation records preserved for traceability. These files are not required to run the demo and are not part of runtime execution.

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
| Interactive UX | No REPL, GUI, or interactive modes |

---

## Documentation

| File | Description |
|------|-------------|
| `VERIFY.md` | Trust model and verification boundary |
| `docs/proofs/phase_v2_7/` | Final validation and freeze attestation |
| `semantic/README.md` | Semantic Capability Layer documentation |

---

## Repository Structure

```
brok-clu-demo/
├── scripts/                    # Entrypoint scripts
│   ├── verify_poc_v2.sh        # Verification script
│   ├── run_poc_v2.sh           # Execution script
│   └── determinism_test_v2.sh  # Determinism test
├── vendor/poc_v2/              # Vendored runtime artifacts (immutable)
│   ├── poc_v2.tar.gz           # Sealed tarball
│   ├── SHA256SUMS.vendor       # Tarball checksum
│   └── PROVENANCE.txt          # Origin metadata
├── examples/inputs/            # Locked example inputs
├── artifacts/                  # Generated outputs (gitignored)
├── docs/proofs/phase_v2_7/     # Freeze attestation
└── semantic/                   # Semantic Capability Layer
    ├── contract/               # Scope lock and contracts
    ├── scripts/                # Semantic tools
    └── regression/             # Regression detection
```
