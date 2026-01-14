# Phase M-2: Artifact Layer

## Overview

The Artifact Layer constructs authoritative wrapper-level decision records from non-authoritative proposals (M-1 output). Artifacts encode explicit ACCEPT/REJECT decisions that gate execution.

**Artifacts are decision records only. They do not override execution truth.**

Execution truth remains solely in `stdout.raw.kv` from PoC v2 runtime.

---

## What Artifacts Are

| Property | Description |
|----------|-------------|
| Decision records | Explicit ACCEPT or REJECT decisions |
| Wrapper-level authority | Gate whether PoC v2 execution occurs |
| Auditable | Schema-validated, bounded, deterministic |
| Non-execution | Do not record execution outcomes |

## What Artifacts Are NOT

| Non-Property | Explanation |
|--------------|-------------|
| Execution truth | `stdout.raw.kv` remains authoritative |
| Runtime output | Artifacts do not replace PoC v2 output |
| Semantic interpretation | No meaning inference or heuristics |

---

## Decision Rules (M2_RULESET_V1)

| Proposal Count | Decision | Reason Code |
|----------------|----------|-------------|
| 0 | REJECT | NO_PROPOSALS |
| 1 | ACCEPT | - |
| 2-8 | REJECT | AMBIGUOUS_PROPOSALS |
| Invalid | REJECT | INVALID_PROPOSALS |

No scoring, ranking, or heuristic selection. Exactly one proposal is required for ACCEPT.

---

## Schema

Schema version: `artifact_v1`

Location: `artifact/schema/artifact.schema.json`

### Structure

```json
{
  "artifact_version": "artifact_v1",
  "run_id": "<user-provided>",
  "input_ref": "<repo-relative-path>",
  "proposal_set_ref": "<repo-relative-path>",
  "decision": "ACCEPT|REJECT",
  "accept_payload": { ... },  // if ACCEPT
  "reject_payload": { ... },  // if REJECT
  "construction": {
    "ruleset_id": "M2_RULESET_V1",
    "proposal_count": 0,
    "selected_proposal_index": null
  }
}
```

---

## Usage

### Build Artifact from Proposal Set

```sh
./scripts/build_artifact.sh \
  --proposal-set artifacts/proposals/run1/proposal_set.json \
  --run-id run1 \
  --input-ref examples/inputs/test.txt
```

### Full Pipeline (Proposals → Artifact → Execution)

```sh
./scripts/run_brok.sh --input examples/inputs/accept_restart_alpha_1.txt --run-id demo1
```

This will:
1. Generate proposals under `artifacts/proposals/demo1/`
2. Build artifact under `artifacts/artifacts/demo1/`
3. If ACCEPT: invoke `scripts/run_poc_v2.sh --input <file>` (exact form, no other parameters)
4. If REJECT: print decision and exit (no PoC v2 invocation)

**Note:** If the input file is outside the repository (e.g., `/tmp/in.txt`), it is copied to `artifacts/inputs/<run-id>/input.raw` and the artifact references this repo-relative path. This ensures artifacts contain no absolute paths.

---

## Output Locations

| Output | Path |
|--------|------|
| Proposals | `artifacts/proposals/<run-id>/proposal_set.json` |
| Input copy (external) | `artifacts/inputs/<run-id>/input.raw` (only for inputs outside repo) |
| Artifact | `artifacts/artifacts/<run-id>/artifact.json` |
| Artifact hash | `artifacts/artifacts/<run-id>/artifact.json.sha256` |
| Execution | `artifacts/run/run_<timestamp>/` (created by PoC v2) |

---

## Running Tests

```sh
# Python tests
python3 artifact/tests/test_artifact_builder.py
python3 artifact/tests/test_artifact_determinism.py

# Shell tests
./artifact/tests/test_run_id_safety.sh
```

---

## File Structure

```
artifact/
├── README.md                          # This file
├── schema/
│   └── artifact.schema.json           # Schema specification
├── src/
│   ├── __init__.py
│   ├── builder.py                     # Artifact builder
│   └── validator.py                   # Schema validator
└── tests/
    ├── __init__.py
    ├── test_artifact_builder.py       # Decision rule tests
    ├── test_artifact_determinism.py   # Determinism tests
    └── test_run_id_safety.sh          # Run-ID safety tests
```

---

## Constraints (Binding)

1. Artifacts do not override execution truth (`stdout.raw.kv`)
2. Decision rules are deterministic (M2_RULESET_V1)
3. No scoring, ranking, or heuristic selection
4. All generated outputs under `artifacts/` (gitignored)
5. No absolute paths in artifact content
6. No timestamps in artifact content
7. Python standard library only (no external dependencies)
