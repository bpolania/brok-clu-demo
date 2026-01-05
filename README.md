# Brok-CLU Runtime Demo

A sealed runtime demo that consumes the Brok-CLU PoC v1 artifact for deterministic command routing.

---

## What This Repository Is

This repository demonstrates the Brok-CLU runtime routing capability using a frozen, archival artifact. The runtime behavior is deterministic, bounded, sealed, and immutable. Grammar-constrained decoding is enforced at inference time.

This is a consumption demo only. It does not modify or extend the Brok-CLU artifact.

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

**ACCEPT:**
```json
{
  "status": "ACCEPT",
  "intent": "<INTENT>",
  "slots": { ... }
}
```

**REJECT:**
```json
{
  "status": "REJECT",
  "reason": "<REASON>"
}
```

No partial output. No best-effort parsing.

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

## Output Artifacts (Demo Layer)

After successful execution via `./run.sh <input-file>`, output artifacts are written to:

| File | Description |
|------|-------------|
| `artifacts/last_run/output.raw.kv` | Authoritative runtime output (key=value format, exact copy of stdout) |
| `artifacts/last_run/output.derived.json` | Derived JSON representation (non-authoritative, for inspection only) |

**Important:**
- The `key=value` format in `output.raw.kv` is the authoritative runtime output.
- The JSON in `output.derived.json` is derived strictly from the raw output and includes explicit markers (`"derived": true`, `"source_format": "key=value"`).
- On execution failure, no derived JSON is produced.

---

## Documentation

- `PHASE0_SCOPE_LOCK.md` - Complete scope lock documentation
- `PHASE0_INPUTS_MANIFEST.json` - Machine-readable manifest
- `PHASE0_EXIT_ATTESTATION.md` - Phase 0 closure attestation
