# Phase L-8: Proposal Engine Contract

## Authoritative Contract Document

**Status**: FROZEN
**Version**: L-8.1 (corrected)
**Effective**: Phase L-8 closure

---

## 1. Scope and Authority

### 1.1 Contract Scope

This contract defines the interface between:
- **Upstream**: Raw user input bytes (opaque)
- **Downstream**: Artifact layer validation and decision

The Proposal Engine produces **non-authoritative** output. Proposals have no authority and do not imply execution outcomes.

### 1.2 Authority Classification

| Component | Authority Level |
|-----------|-----------------|
| Proposal Engine output | **NONE** (untrusted, non-authoritative) |
| Artifact layer validation | Deterministic collapse to ACCEPT/REJECT |
| Artifact layer decision | **WRAPPER-LEVEL** (authoritative) |
| stdout.raw.kv | **AUTHORITATIVE** (sole execution truth) |

**The Proposal Engine output MUST NOT be trusted as correct, safe, or valid.**

---

## 2. Exact Interface Definition

### 2.1 Seam Function Signature

```python
def acquire_proposal_set(raw_input_bytes: bytes) -> bytes
```

**Location**: `src/artifact_layer/seam_provider.py`

### 2.2 Input Specification

| Property | Specification |
|----------|---------------|
| Type | `bytes` |
| Encoding | Opaque (passed through without interpretation) |
| Source | User input file content |
| Validation by seam | NONE |

The seam MUST NOT parse, filter, or interpret input bytes.

### 2.3 Output Specification

| Property | Specification |
|----------|---------------|
| Type | `bytes` |
| Content | Opaque bytes produced by Proposal Engine |
| Validity | NOT GUARANTEED |
| On engine failure | Empty bytes `b""` |

**The output bytes MAY be:**
- Empty
- Non-UTF-8
- Non-JSON
- Malformed JSON
- Valid JSON but invalid schema
- Nonsensical content
- Nondeterministic (varying between calls with same input)

**The artifact layer handles ALL of these cases by deterministic validation and collapse to REJECT when invalid.**

---

## 3. What the Proposal Engine Does NOT Guarantee

The Proposal Engine provides **NO GUARANTEES** for:

### 3.1 Output Format
- Output MAY be empty bytes
- Output MAY be non-UTF-8 binary data
- Output MAY be invalid JSON
- Output MAY be valid JSON with invalid schema
- Output MAY contain unexpected fields or missing required fields

### 3.2 Output Correctness
- Proposals MAY be incorrect, incomplete, or nonsensical
- Proposals MAY contradict user intent
- Proposals MAY contain hallucinated content (for LLM engines)

### 3.3 Determinism
- Output MAY vary between calls with identical input
- Output MAY depend on external factors (for LLM engines)
- Only the deterministic engine binding provides determinism

### 3.4 Availability
- Engine MAY fail at any time
- Engine MAY timeout
- Engine MAY return empty bytes for any reason

**All of these cases collapse to REJECT via artifact layer validation.**

---

## 4. What the System MUST NOT Do

### 4.1 Trust Violations
- The system MUST NOT trust Proposal Engine output as valid
- The system MUST NOT trust Proposal Engine output as safe
- The system MUST NOT trust Proposal Engine output as authoritative
- The system MUST NOT bypass artifact layer validation for any Proposal Engine output

### 4.2 Authority Violations
- Proposal Engine output MUST NOT be treated as ACCEPT/REJECT decisions
- Proposal Engine output MUST NOT be treated as execution commands
- Proposal Engine output MUST NOT bypass the artifact layer
- Proposal Engine output MUST NOT directly produce stdout.raw.kv

### 4.3 Seam Behavior
- The seam MUST NOT retry on engine failure
- The seam MUST NOT cache results across runs
- The seam MUST NOT parse or interpret engine output
- The seam MUST collapse all exceptions to empty bytes

---

## 5. Failure Collapse Rules

**Authoritative Invariant**: All invalid Proposal Engine output deterministically collapses to REJECT.

| Failure Mode | What Happens |
|--------------|--------------|
| Engine returns empty bytes | Artifact layer: REJECT |
| Engine returns non-UTF-8 bytes | Artifact layer: REJECT |
| Engine returns invalid JSON | Artifact layer: REJECT |
| Engine returns valid JSON, invalid schema | Artifact layer: REJECT |
| Engine returns zero proposals | Artifact layer: REJECT |
| Engine returns multiple proposals | Artifact layer: REJECT |
| Engine returns proposal outside L-3/L-4 gates | Artifact layer: REJECT |

**The artifact layer decision is DETERMINISTIC**: identical ProposalSet bytes always produce identical ACCEPT/REJECT decision and identical artifact.

---

## 6. Schema Field Constraints

The ProposalSet schema (`proposal_set.schema.json`) defines these constraints on **parsed JSON fields**, not on raw bytes:

### 6.1 Field-Level Constraints

| Field Path | Constraint | Enforcement |
|------------|------------|-------------|
| `input.raw` | maxLength: 4096 characters | Validator rejects if exceeded |
| `proposals` | maxItems: 8 | Validator rejects if exceeded |
| `errors` | maxItems: 16 | Validator rejects if exceeded |
| `errors[*]` | maxLength: 256 characters | Validator rejects if exceeded |
| all objects | additionalProperties: false | Validator rejects unknown fields |

### 6.2 What These Limits Are NOT

These limits are **NOT**:
- A limit on raw input bytes to the Proposal Engine
- A limit on ProposalSet bytes size
- A limit on engine response time
- A limit on engine resource usage

### 6.3 No Explicit ProposalSet Byte Limit

There is no explicit application-level ProposalSet byte limit today. Safety relies on:
1. Deterministic validation of parsed content
2. Execution gating on ACCEPT only
3. Tests using CI-safe sizes (reasonable bounds)

---

## 7. Determinism Guarantees

### 7.1 Proposal Engine: No Determinism Guarantee

The Proposal Engine does NOT guarantee determinism.
- LLM-backed engines produce nondeterministic output by nature
- The deterministic engine binding (if any) is an implementation detail

**Proposal Engine nondeterminism is explicitly tolerated by design.**

### 7.2 Artifact Layer: Determinism Guaranteed

**Authoritative Invariant**: The artifact layer MUST be deterministic.

| Guarantee | Specification |
|-----------|---------------|
| Same ProposalSet bytes → Same decision | Always |
| Same ProposalSet bytes → Same artifact | Byte-for-byte identical |
| Invalid bytes → REJECT | Deterministic |

**Determinism boundary**: ProposalSet bytes (input) to Artifact (output).

### 7.3 Execution: Determinism Guaranteed

| Guarantee | Specification |
|-----------|---------------|
| Same Artifact → Same stdout.raw.kv | Byte-for-byte identical |
| REJECT → No stdout.raw.kv | Always (no execution) |
| ACCEPT → Execution occurs | Always (via gateway) |

---

## 8. Non-Goals (Explicit Exclusions)

Phase L-8 explicitly DOES NOT address:

### 8.1 Excluded Features
- Proposal filtering or ranking
- Confidence scores or probabilities
- Multi-turn proposal refinement
- Proposal caching or memoization
- Async or streaming proposal generation

### 8.2 Excluded Safety Measures
- Input sanitization (beyond schema validation)
- Output sanitization (beyond schema validation)
- Rate limiting
- Content filtering
- Prompt injection defense

### 8.3 Excluded Integrations
- LLM provider failover
- Proposal engine switching at runtime
- A/B testing of engines
- Telemetry or logging of proposal content

**These exclusions are INTENTIONAL and MUST NOT be added without a new phase.**

---

## 9. ASCII Diagram: Trust Boundaries and Authority

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAW INPUT BYTES                                 │
│                      (opaque, from user file)                           │
│                                                                         │
│                    No interpretation, no validation                     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PROPOSAL ENGINE SEAM                               │
│                                                                         │
│  Interface: acquire_proposal_set(bytes) -> bytes                        │
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════╗  │
│  ║ UNTRUSTED: Output bytes MAY be empty, invalid, malformed,         ║  │
│  ║            nonsensical, or nondeterministic. This is expected.    ║  │
│  ╚═══════════════════════════════════════════════════════════════════╝  │
│                                                                         │
│  Constraints enforced by seam:                                          │
│  ├─ Single call, no retries                                             │
│  ├─ All exceptions → empty bytes                                        │
│  └─ No parsing or interpretation of output                              │
│                                                                         │
│  Authority: NONE                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼ ProposalSet bytes (opaque, untrusted)
┌─────────────────────────────────────────────────────────────────────────┐
│                   ARTIFACT LAYER (VALIDATION + DECISION)                │
│                                                                         │
│  Step 1: Parse bytes as JSON                                            │
│          → Invalid? REJECT                                              │
│                                                                         │
│  Step 2: Validate against ProposalSet schema                            │
│          → Invalid? REJECT                                              │
│                                                                         │
│  Step 3: Apply decision rules (M2_RULESET_V1 + L-3/L-4 gates)           │
│          → 0 proposals? REJECT                                          │
│          → 2+ proposals? REJECT                                         │
│          → 1 proposal outside gates? REJECT                             │
│          → 1 proposal matching gate? ACCEPT                             │
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════╗  │
│  ║ DETERMINISTIC: Same bytes always produce same ACCEPT/REJECT       ║  │
│  ║ WRAPPER-LEVEL AUTHORITY: Decision is authoritative                ║  │
│  ╚═══════════════════════════════════════════════════════════════════╝  │
└───────────────────┬─────────────────────────────┬───────────────────────┘
                    │                             │
              ACCEPT│                       REJECT│
                    ▼                             ▼
┌────────────────────────────┐     ┌────────────────────────────────────┐
│    EXECUTION GATEWAY       │     │         NO EXECUTION               │
│                            │     │                                    │
│  Gate: ACCEPT required     │     │  - No stdout.raw.kv produced       │
│  Execution: PoC v2 / L-4   │     │  - Deterministic REJECT recorded   │
└─────────────┬──────────────┘     └────────────────────────────────────┘
              │
              ▼ (ACCEPT only)
┌─────────────────────────────────────────────────────────────────────────┐
│                      stdout.raw.kv                                      │
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════╗  │
│  ║ AUTHORITATIVE: Sole execution truth                               ║  │
│  ╚═══════════════════════════════════════════════════════════════════╝  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Contract Freeze Statement

**This contract is FROZEN as of Phase L-8 closure (v1.1 corrected).**

Changes require:
1. A new phase designation
2. Full closure review
3. Regression test updates
4. Evidence capture

---

## Appendix A: Stable Reject Reason Codes

These reason codes are pre-existing and stable from earlier phases:

| Code | Meaning | Source |
|------|---------|--------|
| INVALID_PROPOSALS | ProposalSet bytes failed validation | M-2 |
| NO_PROPOSALS | Valid ProposalSet with zero proposals | M-2 |
| AMBIGUOUS_PROPOSALS | Valid ProposalSet with 2+ proposals | M-2 |
| INVALID_EVENT_TOKEN | L-4: event_token not in closed set | L-4 |
| ILLEGAL_TRANSITION | L-4: transition not legal from current state | L-4 |

---

## Appendix B: L-3 ACCEPT Envelope Reference

The ONLY ROUTE_CANDIDATE that produces ACCEPT under L-3:

```json
{
  "kind": "ROUTE_CANDIDATE",
  "payload": {
    "intent": "STATUS_QUERY",
    "slots": {
      "target": "alpha"
    }
  }
}
```

All other ROUTE_CANDIDATE proposals → REJECT.

---

## Appendix C: L-4 State Transition Reference

STATE_TRANSITION_REQUEST proposals are validated against:
- Event token closed set (14 tokens)
- State machine transitions from CREATED state
- Legal transitions produce ACCEPT with STATE_TRANSITION payload

Illegal transitions → REJECT with L4_* reason code.
