# Phase M-1: Proposal Layer

## Overview

The Proposal Layer generates non-authoritative proposals from raw user input. This layer is upstream of artifact construction (Phase M-2) and execution (PoC v2). Proposals are structural suggestions only and do not imply decisions or outcomes.

---

## Authority Rules

**Proposals have no authority.**

| Rule | Description |
|------|-------------|
| Non-authoritative | Proposals do not determine ACCEPT/REJECT |
| No confidence scores | No ranking, scoring, or "best" indicators |
| No execution binding | Proposals do not guarantee execution outcomes |
| Derived only | Proposals are derived suggestions, not truth |

Execution truth remains solely in `stdout.raw.kv` from PoC v2 runtime.

---

## Failure Semantics

| Condition | Result |
|-----------|--------|
| Invalid input | Zero proposals (not fallback) |
| Unmapped input | Zero proposals |
| Validation error | Zero proposals with error codes |
| Empty input | Zero proposals |
| Whitespace-only input | Zero proposals |

Zero proposals is a valid outcome. There are no fallback heuristics.

---

## Determinism Requirements

| Requirement | Guarantee |
|-------------|-----------|
| Same input | Byte-for-byte identical JSON output |
| Ordering | Proposal order is deterministic and stable |
| No randomness | No random IDs, timestamps, or UUIDs in output |
| No environment | Output does not depend on environment variables |
| No machine state | Output does not depend on filesystem paths or time |

---

## Boundedness Limits

| Bound | Value | Behavior |
|-------|-------|----------|
| Max input length | 4096 characters | Overlong input produces zero proposals |
| Max proposals | 8 per input | Conservative limit enforced |
| Max errors | 16 entries | Error array bounded |
| Max error length | 256 characters | Individual error message bounded |

---

## Schema and Validation

### Schema Specification

Schema version: `m1.0`

Location: `proposal/schema/proposal_set.schema.json`

The JSON Schema file serves as the **specification reference** for the ProposalSet format. It documents the structural constraints, bounds, and closed enums that define valid ProposalSet documents.

### Validation Implementation

The validator (`proposal/src/validator.py`) performs **spec-aligned structural validation** using Python standard library only (no external dependencies). The validator explicitly checks all constraints defined in the schema specification:

- Required fields and types
- String length bounds
- Array item limits
- Closed enum membership
- Additional properties rejection (`additionalProperties: false` equivalent)

**Implementation note:** The validator does not use a JSON Schema validation engine. It implements deterministic, explicit structural checks equivalent to the schema constraints.

### ProposalSet Structure

```json
{
  "schema_version": "m1.0",
  "input": {
    "raw": "<exact user input>"
  },
  "proposals": [
    {
      "kind": "ROUTE_CANDIDATE",
      "payload": {
        "intent": "RESTART_SUBSYSTEM",
        "slots": {
          "target": "alpha",
          "mode": "graceful"
        }
      }
    }
  ],
  "errors": ["<optional error codes>"]
}
```

### Closed Enums

| Field | Valid Values |
|-------|--------------|
| `kind` | `ROUTE_CANDIDATE` |
| `intent` | `RESTART_SUBSYSTEM`, `STOP_SUBSYSTEM`, `STATUS_QUERY` |
| `target` | `alpha`, `beta`, `gamma` |
| `mode` | `graceful`, `immediate` |

---

## Usage

### Generate Proposals from File

```sh
./scripts/generate_proposals.sh --input examples/inputs/accept_restart_alpha_1.txt
```

### Generate Proposals from Stdin

```sh
echo "restart alpha subsystem gracefully" | ./scripts/generate_proposals.sh --input -
```

### Save to Artifact Directory

```sh
./scripts/generate_proposals.sh --input examples/inputs/accept_restart_alpha_1.txt --run-id test001
# Output written to: artifacts/proposals/test001/proposal_set.json
```

**Run ID constraints:**
- Allowed characters: `A-Za-z0-9._-`
- Maximum length: 64 characters
- No automatic timestamp generation

**Output constraints:**
- All generated outputs MUST live under `artifacts/`
- Output is always written to stdout
- File output only via `--run-id` (writes to `artifacts/proposals/<run-id>/proposal_set.json`)

---

## Running Tests

```sh
python3 proposal/tests/test_proposals.py
```

Tests verify:
- Determinism (byte-for-byte identical output)
- Boundedness (input/output limits enforced)
- Whitespace semantics (preserved exactly)
- Validation (generator output always validates)
- Unknown field rejection (additionalProperties enforcement)

---

## File Structure

```
proposal/
├── README.md                          # This file
├── schema/
│   └── proposal_set.schema.json       # Schema specification (reference)
├── src/
│   ├── __init__.py
│   ├── generator.py                   # Proposal generator
│   └── validator.py                   # Spec-aligned validator (stdlib-only)
└── tests/
    ├── __init__.py
    └── test_proposals.py              # Unit tests
```

---

## Integration Notes

### Phase M-2 Handoff

The artifact construction layer (Phase M-2) will consume `ProposalSet` as untrusted input. Phase M-2 is responsible for:
- Making explicit ACCEPT/REJECT decisions
- Creating sealed, auditable decision records
- Ensuring artifact determinism

### Execution Independence

This layer does not:
- Invoke PoC v2 execution
- Parse `stdout.raw.kv`
- Create authoritative outputs

**Execution truth remains solely in `stdout.raw.kv` from PoC v2.**

---

## Constraints (Binding)

These constraints are binding for Phase M-1 and must not be violated:

1. Proposals must never contain authority indicators
2. Zero proposals must be valid for any input
3. Output must be deterministic and spec-validated
4. No LLMs or learned models in proposal generation
5. No dependency on semantic/ S-phase tooling
6. All generated outputs under `artifacts/` (gitignored)
7. Python standard library only (no external dependencies)

---

## Verification

To verify artifacts are properly gitignored:

```sh
git check-ignore -v artifacts/proposals/test/proposal_set.json
# Expected: .gitignore:2:artifacts/  artifacts/proposals/test/proposal_set.json
```
