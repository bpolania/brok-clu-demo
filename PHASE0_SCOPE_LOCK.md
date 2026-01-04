# Phase 0: Scope Lock

This document records all locked inputs, assumptions, and boundaries for the Brok-CLU Runtime Demo.

---

## Authoritative Context

- Brok-CLU PoC v1 is complete, frozen, and archival.
- This demo consumes an existing compiled artifact.
- Runtime behavior is deterministic, bounded, sealed, and immutable.
- Grammar-constrained decoding is enforced at inference time.
- Artifact integrity and verification are mandatory.

---

## Domain Definition

### Locked Intent Set

| Intent             | Description                      |
|--------------------|----------------------------------|
| RESTART_SUBSYSTEM  | Restart a target subsystem       |
| STOP_SUBSYSTEM     | Stop a target subsystem          |
| STATUS_QUERY       | Query status of a target subsystem |

No other intents exist.

### Bounded Slots

| Slot   | Valid Values              | Applicable To                       |
|--------|---------------------------|-------------------------------------|
| target | alpha, beta, gamma        | All intents                         |
| mode   | graceful, immediate       | RESTART_SUBSYSTEM, STOP_SUBSYSTEM   |

No other slots exist.

---

## I/O Contract

### Input Specification

- Format: UTF-8 text file
- Structure: Single line
- Cardinality: One command per invocation

### Output Specification

#### ACCEPT Response

```json
{
  "status": "ACCEPT",
  "intent": "<INTENT>",
  "slots": { ... }
}
```

#### REJECT Response

```json
{
  "status": "REJECT",
  "reason": "<REASON>"
}
```

### Contract Guarantees

- No partial output
- No best-effort parsing
- Binary ACCEPT/REJECT decision only

---

## Execution Semantics

| Property    | Value                              |
|-------------|------------------------------------|
| Actions     | No real system actions             |
| Output      | Declarative only                   |
| Execution   | Atomic, stateless per invocation   |
| Side effects| None                               |

---

## Execution Environment

### Supported

| Attribute     | Value          |
|---------------|----------------|
| OS            | macOS          |
| Architecture  | arm64          |
| Mode          | Local execution|

### Unsupported

- Other operating systems
- Other architectures
- Containers
- Cloud deployment
- Auto-detection or fallback logic

---

## Artifact Identity

| Attribute     | Value                                                      |
|---------------|------------------------------------------------------------|
| Identifier    | brok-clu-runtime-routing-poc-v1                            |
| Version       | PoC v1                                                     |
| Platform      | macOS arm64                                                |
| SHA-256       | 9f2c4a8d7e1b0c6a3d5e9a2f4c7b8e0d1a6c9e4b5f2a7d8c0e3b1a4f6 |

### Verification Requirement

Hash verification is mandatory. Recorded in Phase 0; implementation deferred to subsequent phases.

---

## Source Repository Reference

| Attribute     | Value          |
|---------------|----------------|
| Path          | ../Brok-CLU    |
| Access        | Read-only      |
| Status        | Sealed         |

---

## Example Input Inventory

| Filename                    | Content                          | Expected Status |
|-----------------------------|----------------------------------|-----------------|
| accept_restart_alpha_1.txt  | restart alpha subsystem gracefully | ACCEPT        |
| accept_restart_alpha_2.txt  | graceful restart of alpha        | ACCEPT          |
| accept_status_beta.txt      | status of beta                   | ACCEPT          |
| reject_grammar_1.txt        | restart subsystem now alpha      | REJECT          |
| reject_semantic_1.txt       | delete database gamma            | REJECT          |

Location: `examples/inputs/`

---

## Phase 0 Boundary

This document records scope only. No runtime code, build logic, or verification logic is implemented in Phase 0.
