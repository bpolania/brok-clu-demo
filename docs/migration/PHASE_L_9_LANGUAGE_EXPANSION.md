# Phase L-9: Language Acceptance Expansion

## Overview

Phase L-9 expands the accepted language of the proposal engine via a **closed, explicit phrase-mapping contract** (Option A: Narrow, Fixed Synonym Contract). This enables users to use natural synonym phrases that are transparently mapped to canonical forms before proposal generation.

## Design Choice: Option A Only

L-9 implements **Option A: Narrow, Fixed Synonym Contract**:

- Static mapping table: `expanded_phrase -> canonical_phrase`
- Trivial normalization: trim whitespace, collapse internal whitespace, lowercase ASCII only
- Exact match requirement (no pattern/regex/wildcard)
- No chaining (mapped output is NEVER re-mapped)
- No fallbacks, retries, scoring, ranking, fuzzy matching, or heuristics
- Unknown inputs pass through unchanged

## Scope: L-9 Minimal Set

Phase L-9 is limited to the **payment synonym minimal set**:

| Expanded Phrase | Canonical Phrase |
|-----------------|------------------|
| `submit payment` | `create payment` |
| `new payment` | `create payment` |
| `make a payment` | `create payment` |

**No other mappings are authorized for Phase L-9.**

## Contract Location

```
proposal/src/language_acceptance_contract.py
```

## Frozen Contract

```python
normalize_and_map(raw_input: str) -> str
```

### Behavior

1. Normalize input for lookup only (trim, collapse whitespace, lowercase ASCII)
2. Exact lookup in static mapping table
3. If match found: return canonical phrase
4. If no match: return original `raw_input` unchanged

### Guarantees

- **Deterministic**: Same raw input always produces same output
- **Identity preservation**: Unknown inputs returned verbatim
- **No side effects**: Pure function, no state mutation
- **Single-pass**: No chaining or recursive mapping

## Allowed Transformations

| Transformation | Description |
|----------------|-------------|
| Strip whitespace | Remove leading/trailing whitespace |
| Collapse whitespace | Replace consecutive whitespace with single space |
| Lowercase ASCII | Convert A-Z to a-z (ASCII only) |

## Forbidden Behaviors

| Behavior | Status |
|----------|--------|
| Pattern/regex/wildcard matching | FORBIDDEN |
| Fuzzy matching or edit distance | FORBIDDEN |
| Scoring, ranking, or "best match" | FORBIDDEN |
| Chaining (re-mapping canonical values) | FORBIDDEN |
| Punctuation removal | FORBIDDEN |
| Non-ASCII case conversion | FORBIDDEN |
| Fallback or heuristic behavior | FORBIDDEN |
| Runtime configuration | FORBIDDEN |

## Integration Point (B1 Outcome)

L-9 is integrated at a **single** proposal engine entry point:

**`src/artifact_layer/llm_engine.py`** - LLM engine path (bound at build time)

### B1 Outcome: Single Integration Point

Under the current build (`BOUND_ENGINE_NAME = "llm"`), only the LLM engine path is executed.
The deterministic generator path (`proposal/src/generator.py`) is **never invoked**.

To eliminate dead code and reduce risk, L-9 integration was **removed** from `generator.py`.
L-9 now exists at exactly ONE location in the codebase.

### Exactly-Once Guarantee

- `engine_binding.BOUND_ENGINE_NAME = "llm"` selects llm_engine at build time
- `seam_provider.acquire_proposal_set()` calls `get_bound_engine()` exactly once
- RunContext enforces exactly-one-call semantics via SeamSViolation
- L-9 mapping is applied exactly ONCE per run, in llm_engine.py

### Call Graph

```
orchestrator.run_pipeline()
    └── seam_provider.acquire_proposal_set()
            └── engine_binding.get_bound_engine()
                    └── llm_engine()        [BOUND_ENGINE_NAME="llm"]
                            └── normalize_and_map()  ← L-9 applied (single location)
```

**NOTE**: The deterministic generator path (`generator.py`) does NOT have L-9 integration.
If the binding is changed to `"deterministic"` in the future, L-9 would need to be added there.

## What L-9 Does NOT Change

| Component | Status |
|-----------|--------|
| Seam S contract | UNCHANGED |
| Validation logic | UNCHANGED |
| Artifact structure | UNCHANGED |
| Execution logic | UNCHANGED |
| Authority model | UNCHANGED |

## Closure Evidence

### Closure-Grade Requirements

L-9 closure evidence must satisfy ALL of the following:

1. **Fresh run environment**: All run directories MUST be NEW (created during evidence run)
2. **JSON-parsed output**: Decision and run_dir captured from `./brok-run` JSON output (no grep on human text)
3. **No wildcard hashing**: sha256 computed only for explicitly captured stdout.raw.kv paths
4. **REJECT verification**: decision=REJECT parsed from JSON, stdout.raw.kv absent

**CRITICAL**: Rerun/reuse is FORBIDDEN for closure evidence. The script FAILS if any run_dir existed before the evidence run.

### Fresh Environment Strategy: Move-aside (Strategy 2)

The evidence script implements Strategy 2:
- Quarantines existing `artifacts/run` to `artifacts/run.__l9_quarantine__/<unique_id>`
- Creates fresh empty `artifacts/run`
- Runs 5 inputs via `./brok-run` (JSON output)
- Verifies all run directories are NEW (delta method)
- Restores original `artifacts/run` on exit

### Evidence File Location

`artifacts/evidence/l9/stdout_raw_kv_evidence.txt`

### ACCEPT Path Evidence

| Input | SHA256 of stdout.raw.kv | new_run_dir |
|-------|-------------------------|-------------|
| `create payment` (canonical) | `382dc31811e5097c64f0de4909e1c4a2248fd93ff1b1e8d5e2ddeaebe3af0288` | true |
| `submit payment` (expanded) | `382dc31811e5097c64f0de4909e1c4a2248fd93ff1b1e8d5e2ddeaebe3af0288` | true |
| `new payment` (expanded) | `382dc31811e5097c64f0de4909e1c4a2248fd93ff1b1e8d5e2ddeaebe3af0288` | true |
| `make a payment` (expanded) | `382dc31811e5097c64f0de4909e1c4a2248fd93ff1b1e8d5e2ddeaebe3af0288` | true |

**Result**: ACCEPT_HASHES_ALL_EQUAL=true - Byte-identical authoritative output.

### REJECT Path Evidence

| Input | Decision (JSON) | stdout.raw.kv | new_run_dir |
|-------|-----------------|---------------|-------------|
| `payment` | REJECT | N/A (absent) | true |

**Result**: REJECT_STDOUT_RAW_KV_PRESENT=false - No authoritative output (expected).

### Verification Summary

| Check | Required | Status |
|-------|----------|--------|
| ACCEPT_HASHES_ALL_EQUAL | true | true |
| REJECT_STDOUT_RAW_KV_PRESENT | false | false |
| ALL_RUN_DIRS_NEW | true | true |
| OVERALL_PASS | true | true |

**Closure status**: CLOSED

## Test Coverage

Tests are in `tests/l9/test_language_acceptance_contract.py`:

| Category | Count | Description |
|----------|-------|-------------|
| Unit | 10 | Contract function behavior |
| Integration | 3 | Engine integration (B1 single entry point) |
| Safety | 2 | No regression on existing behavior |
| **Total** | **15** | |

## Reproduction Commands

```bash
# From repository root:

# Run L-9 tests
python3 tests/l9/test_language_acceptance_contract.py

# Generate closure-grade evidence
# (automatically quarantines existing runs, creates fresh environment)
./artifacts/evidence/l9/generate_evidence.sh

# The script will:
# - Quarantine existing artifacts/run
# - Create fresh empty artifacts/run
# - Run 5 inputs via ./brok-run (JSON output)
# - Parse JSON to extract run_dir and decision
# - Verify all run_dirs are NEW (FAIL if any reused)
# - Compute sha256 only for captured paths (no wildcards)
# - Restore original artifacts/run on exit
```

**NOTE**: Manual verification with wildcards like `shasum -a 256 artifacts/run/l4_run_*/stdout.raw.kv` is NOT valid for closure evidence. Use the evidence script which captures exact paths from JSON output.

## Summary

Phase L-9 provides:

1. **Closed scope**: Only payment synonyms authorized
2. **Deterministic mapping**: Same input always produces same output
3. **Closure-grade evidence**: Fresh environment, JSON-parsed, no wildcards
4. **No governance drift**: Documentation matches implementation exactly
5. **Full test coverage**: 15 tests covering all invariants
6. **Single integration point**: B1 outcome (llm_engine.py only)
