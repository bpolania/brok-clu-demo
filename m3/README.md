# Phase M-3: End-to-End CLI Integration, Observability, and Invariant Enforcement

## Overview

Phase M-3 provides the pipeline orchestration layer that connects Proposals (M-1) to Artifacts (M-2) to Execution (frozen PoC v2). It enforces structural invariants and makes authority boundaries visible via structured CLI output.

**Key property: Execution can only occur through a validated ACCEPT artifact.**

---

## Canonical CLI

The canonical entrypoint for the Brok-CLU pipeline is the `./brok` command at the repository root:

```sh
./brok --input <file>
```

The CLI accepts only `--input <file>`, matching the PoC v2 execution contract. Run IDs are generated internally and deterministically from input content. The legacy `scripts/run_brok.sh` wrapper also routes through M-3.

---

## Authority Model

```
+-------------------+     +-------------------+     +-------------------+
|      INPUT        |     |     PROPOSAL      |     |     ARTIFACT      |
|                   |     |                   |     |                   |
|  User-provided    | --> |  DERIVED          | --> |  AUTHORITATIVE    |
|  text/command     |     |  NON-AUTHORITATIVE|     |  WRAPPER DECISION |
|                   |     |  May be empty     |     |  ACCEPT or REJECT |
+-------------------+     +-------------------+     +-------------------+
                                                            |
                                                            v
                                              +-------------------+
                                              |    EXECUTION      |
                                              |                   |
                                              |  FROZEN PoC v2    |
                                              |  stdout.raw.kv    |
                                              |  = AUTHORITATIVE  |
                                              |    OUTPUT         |
                                              +-------------------+
```

| Layer | Authority Level | Description |
|-------|-----------------|-------------|
| Proposals | NON-AUTHORITATIVE | Derived suggestions, do not constitute decisions |
| Artifacts | WRAPPER AUTHORITY | Authoritative ACCEPT/REJECT gating decision |
| Execution | OUTPUT AUTHORITY | `stdout.raw.kv` is the ONLY authoritative output |

---

## How to Run

### Canonical CLI

```sh
./brok --input <file>
```

Example (ACCEPT case):
```sh
echo "restart alpha subsystem gracefully" > /tmp/accept.txt
./brok --input /tmp/accept.txt
```

Example (REJECT case):
```sh
echo "nonsense gibberish xyzzy" > /tmp/reject.txt
./brok --input /tmp/reject.txt
```

### Options

| Flag | Description |
|------|-------------|
| `--input` | Required. Path to input file |

Run IDs are generated internally from input content (deterministic, hash-based).

### Internal/Test Invocation

The orchestrator module can be invoked directly for testing:

```sh
python3 m3/src/orchestrator.py --input <file> [--run-id <id>] [--repo-root <path>]
```

Note: `--run-id` and `--repo-root` are internal parameters not exposed on the public CLI.

---

## CLI Output Structure

The CLI output has three labeled sections that make authority boundaries visible:

```
[1/3] PROPOSAL (DERIVED, NON-AUTHORITATIVE)
      - Proposal count and kind
      - Disclaimer about non-authoritative status

[2/3] ARTIFACT (AUTHORITATIVE WRAPPER DECISION)
      - Decision: ACCEPT or REJECT
      - Ruleset: M2_RULESET_V1
      - Status: EXECUTION PERMITTED or NOT PERMITTED

[3/3] EXECUTION (FROZEN, AUTHORITATIVE OUTPUT = stdout.raw.kv)
      - Status: INVOKED, NOT INVOKED, or FAILED TO INVOKE
      - Run directory location (if executed)
      - Authoritative output path

Final line (stdout): decision=ACCEPT executed=true
             or: decision=REJECT reason_code=NO_PROPOSALS
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (includes REJECT decisions) |
| 1 | Operational failure (missing files, IO errors) |
| 2 | Boundary violation (structural error - should not occur) |

**Note:** REJECT is not a failure. Exit code 0 indicates the pipeline completed successfully and made a valid decision.

---

## Output Artifacts

| Output | Path | Authority |
|--------|------|-----------|
| Proposals | `artifacts/proposals/<run-id>/proposal_set.json` | Non-authoritative |
| Artifact | `artifacts/artifacts/<run-id>/artifact.json` | Wrapper decision |
| Execution output | `artifacts/run/run_<ts>/stdout.raw.kv` | **AUTHORITATIVE** |

---

## Execution Gateway

The `ExecutionGateway` class (in `m3/src/gateway.py`) is the **sole gateway** to PoC v2 execution. It enforces:

1. Artifacts must be structurally valid
2. Decision must be ACCEPT to proceed
3. Invalid or REJECT artifacts block execution

Direct invocation of `scripts/run_poc_v2.sh` outside the gateway is forbidden in M-3 workflows.

```python
from m3.src.gateway import ExecutionGateway, ExecutionBoundaryViolation

gateway = ExecutionGateway(repo_root)
result = gateway.execute_if_accepted(artifact, input_file)

if result.executed:
    print(f"Output at: {result.run_directory}")
else:
    print(f"Blocked: {result.decision}")
```

---

## Invariants (Tested)

These invariants are enforced by `m3/tests/test_invariants.py`:

| ID | Invariant | Test |
|----|-----------|------|
| I1 | REJECT never triggers PoC v2 execution | Observable: no new `stdout.raw.kv` |
| I2 | ACCEPT always triggers PoC v2 execution | Observable: `stdout.raw.kv` exists |
| I3 | Zero proposals yield REJECT | Artifact decision check |
| I4 | Multiple proposals yield REJECT | Artifact decision check |
| I5 | Artifact tampering blocks execution | Gateway raises exception |
| I6 | Execution output unchanged by wrapper | Golden file comparison |

Additional structural tests:
- CLI integration (sections appear in order, authority labels present)
- stdout/stderr contract (result line to stdout, sections to stderr)
- No test stubs reachable from CLI
- Gateway import safety (only loads from known paths)
- Cleanup safety (only operates under artifacts/)

Run tests:
```sh
python3 -m unittest m3.tests.test_invariants -v
```

All 29 tests must pass (1 skipped for optional baseline).

---

## Contributor Guardrails

### DO NOT modify these files (frozen, immutable):
- `vendor/poc_v2/poc_v2.tar.gz`
- `scripts/verify_poc_v2.sh`
- `scripts/run_poc_v2.sh`
- `scripts/determinism_test_v2.sh`

### DO NOT:
- Add timestamps to artifacts or run IDs
- Add machine identifiers to any output
- Parse or interpret `stdout.raw.kv` content
- Treat proposals as decisions
- Bypass the execution gateway

### MUST:
- Use ExecutionGateway for all execution paths
- Maintain deterministic run ID generation
- Keep all authority boundary labels
- Test invariants before modifying pipeline

---

## File Structure

```
brok-clu-demo/
├── brok                         # Canonical CLI entrypoint
├── m3/
│   ├── README.md                # This file
│   ├── src/
│   │   ├── __init__.py
│   │   ├── gateway.py           # Execution gateway (sole PoC v2 access)
│   │   ├── cli_output.py        # CLI output formatting
│   │   └── orchestrator.py      # Pipeline orchestrator
│   └── tests/
│       ├── __init__.py
│       └── test_invariants.py   # 28 tests (invariants + structural)
└── scripts/
    └── run_brok.sh              # Legacy wrapper (routes to M-3)
```

---

## Dependencies

Python standard library only. No external packages required.

---

## Constraints (Binding)

1. PoC v2 execution ONLY through validated ACCEPT artifact
2. REJECT is exit code 0 (not a failure)
3. `stdout.raw.kv` is the only authoritative execution output
4. All outputs under `artifacts/` (gitignored)
5. No absolute paths in artifacts
6. Deterministic run IDs (hash-based, no timestamps)
7. Authority boundary labels are mandatory in CLI output
