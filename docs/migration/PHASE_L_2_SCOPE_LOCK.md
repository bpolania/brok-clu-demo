# Phase L-2: LLM Proposal Engine Activation - Scope Lock

## Purpose

This document defines the scope constraints and governing rules for Phase L-2.
L-2 activates an offline nondeterministic proposal engine while preserving all frozen contracts.

## Core Property

**Proposal generation may be nondeterministic, but must remain structurally
non-authoritative and REJECT-safe.**

## What L-2 Does

1. Replaces the deterministic M-1 proposal engine with an offline nondeterministic engine
2. Maintains the frozen seam contract: `acquire_proposal_set(raw_input_bytes: bytes) -> bytes`
3. Preserves all downstream determinism and authority guarantees
4. Demonstrates LLM-style variability without external dependencies
5. **Produces REJECT-only outcomes** via unmapped proposals (INVALID_PROPOSALS)

## What L-2 Does NOT Do

- Does NOT modify artifact decision rules or ACCEPT/REJECT logic
- Does NOT add ACCEPT fixtures
- Does NOT add scoring/ranking/confidence/thresholds
- Does NOT add retries/backoff/self-correction loops
- Does NOT add feedback loops from artifact/execution layers
- Does NOT add runtime configuration (no new flags, env vars, config files)
- Does NOT parse or interpret stdout.raw.kv
- Does NOT change CLI beyond `./brok --input <file>`
- Does NOT optimize for acceptance rate
- Does NOT require external services, API keys, or network access

## Why Runtime Secrets Were Removed

The original L-2 implementation used the Anthropic API with `ANTHROPIC_API_KEY`.
This was identified as a closure blocker because:

1. **Runtime Configuration Violation**: Environment variables for API access constitute
   runtime configuration, violating the "no runtime configuration" constraint.

2. **Reproducibility**: Evidence could not demonstrate variability without the secret,
   making the closure evidence incomplete.

3. **Dependency on External Services**: External API calls introduce failure modes
   that are not under build-time control.

The remediation replaces the external API with an offline nondeterministic engine
that uses OS randomness (`secrets` module) to demonstrate variability without
any external dependencies.

## Seam Contract (Frozen)

```
acquire_proposal_set(raw_input_bytes: bytes) -> bytes
```

- Called exactly once per run
- No retries
- All failures collapse to `b""`
- Empty/malformed ProposalSet leads deterministically to REJECT
- REJECT exits with code 0
- Execution happens only on ACCEPT

## Engine Binding

- Engine selection is build/package-time only
- No environment variables for engine selection
- No runtime flags for engine selection
- No config files for engine selection
- No external API keys required

## Failure Model

Any failure in the engine must collapse to empty bytes at the seam:

| Failure | Seam Output | Downstream |
|---------|-------------|------------|
| Empty input | `b""` (empty ProposalSet) | REJECT |
| Malformed input | `b""` (empty ProposalSet) | REJECT |
| Unmapped input | `b""` (empty ProposalSet) | REJECT |
| Any exception | `b""` | REJECT |

## Determinism Boundaries

| Layer | Determinism |
|-------|-------------|
| Proposal Generation | Nondeterministic (expected) |
| Artifact Decision | Deterministic |
| Execution | Deterministic |
| Exit Codes | Deterministic |

## Authority Model (Unchanged)

- Proposals are DERIVED and NON-AUTHORITATIVE
- Artifacts hold WRAPPER-LEVEL DECISION AUTHORITY
- stdout.raw.kv is the ONLY AUTHORITATIVE EXECUTION OUTPUT

## Verification Requirements

Before L-2 closure:
1. CLI surface must be unchanged (`./brok --input <file>` only)
2. Validators/artifact rules must be byte-identical to baseline
3. Failure collapse to REJECT must be demonstrated
4. No prohibited mechanisms must exist in codebase
5. Variability must be demonstrated without external services
6. No runtime secrets or network access required
