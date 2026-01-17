# L-0 Binding Constraints

## Purpose

This document enumerates the absolutely binding constraints for L-phase LLM integration. These constraints define what must not change, what triggers invalidation, and how to verify compliance mechanically.

**Violations of any constraint invalidate the implementation.**

---

## 1. Authority Model (Absolutely Binding)

### 1.1 Sole Authoritative Runtime Truth

**stdout.raw.kv is the sole authoritative runtime output.**

| Constraint | Binding |
|------------|---------|
| stdout.raw.kv determines execution truth | YES |
| Wrapper may parse stdout.raw.kv | NO |
| Wrapper may interpret stdout.raw.kv semantics | NO |
| Other outputs may override stdout.raw.kv | NO |

### 1.2 Authoritative Wrapper Decision Record

**artifact.json is the authoritative wrapper-level decision record.**

| Constraint | Binding |
|------------|---------|
| artifact.json records ACCEPT or REJECT | YES |
| artifact.json determines execution gating | YES |
| Proposals may override artifact decision | NO |
| Observability may override artifact decision | NO |

### 1.3 Non-Authoritative Layers

**Proposals and observability are derived and non-authoritative.**

| Layer | Authority Level |
|-------|-----------------|
| Raw input | User-provided, uninterpreted |
| Proposals | Derived, non-authoritative |
| Artifact | Authoritative wrapper decision |
| Execution | Authoritative runtime truth |
| Observability | Derived, non-authoritative, inert |

---

## 2. Observability Constraints

### 2.1 Derived and Inert

Observability outputs:

- Are derived from authoritative sources
- Must not affect pipeline behavior
- Must not influence ACCEPT/REJECT decisions
- Must not be read by execution logic
- Must not create feedback loops

### 2.2 No Parsing of Authoritative Output

Observability:

- Must not parse stdout.raw.kv
- Must not interpret execution results semantically
- Must not derive "quality" metrics from execution
- May only record byte-level facts (hashes, sizes)

### 2.3 Default State

Observability is OFF by default. If enabled:

- Enablement is a packaging-level decision
- No runtime toggle exists
- Behavior with observability OFF vs ON must be identical for authoritative outputs

---

## 3. Forbidden Changes

The following changes are absolutely forbidden:

### 3.1 CLI Surface

| Forbidden | Rationale |
|-----------|-----------|
| New flags | CLI is frozen at `--input` only |
| New arguments | Surface is complete |
| New modes | No batch, interactive, or daemon modes |
| Subcommands | Single command only |

### 3.2 Runtime Configuration

| Forbidden | Rationale |
|-----------|-----------|
| Engine selection flags | Binding is packaging-level |
| Environment variable behavior changes | No runtime switches |
| Configuration files | No external configuration |
| Feature toggles | No conditional behavior |

### 3.3 Decision Logic

| Forbidden | Rationale |
|-----------|-----------|
| New ACCEPT conditions | Artifact rules are frozen |
| New REJECT conditions | Artifact rules are frozen |
| Scoring or ranking | Authority is binary |
| Confidence thresholds | No graduated decisions |
| New decision states | Only ACCEPT and REJECT exist |

### 3.4 Authority Boundaries

| Forbidden | Rationale |
|-----------|-----------|
| Proposals gaining authority | Non-authoritative by definition |
| Observability affecting behavior | Inert by definition |
| Wrapper interpreting stdout.raw.kv | Sole authoritative truth |
| Execution creating authority | Execution enforces, not creates |

### 3.5 Behavioral Patterns

| Forbidden | Rationale |
|-----------|-----------|
| Retries | Single-call seam |
| Feedback loops | Feedforward only |
| Self-correction | No iteration |
| Learning from outcomes | No adaptation |
| Optimization for ACCEPT | REJECT is valid |

---

## 4. Invalidation Triggers

An implementation is invalidated if any of the following occur:

### 4.1 Structural Violations

- [ ] New CLI flag or argument added
- [ ] Runtime engine selection introduced
- [ ] Environment variable changes behavior
- [ ] Configuration file read at runtime
- [ ] New decision state introduced (beyond ACCEPT/REJECT)

### 4.2 Authority Violations

- [ ] Proposal metadata influences artifact decision
- [ ] Observability output affects pipeline behavior
- [ ] Wrapper parses or interprets stdout.raw.kv
- [ ] New authoritative output channel created
- [ ] artifact.json semantics modified

### 4.3 Behavioral Violations

- [ ] Seam called more than once per run
- [ ] Retry logic implemented
- [ ] Feedback from downstream to upstream exists
- [ ] Exit code semantics changed (REJECT must be 0)
- [ ] Execution occurs without ACCEPT artifact

### 4.4 Scope Violations

- [ ] M-0..M-4 artifacts modified
- [ ] Frozen contracts amended
- [ ] Baseline tag moved
- [ ] New mandatory dependencies introduced

---

## 5. Regression Criteria

Compliance is verified by checking all of the following:

### 5.1 CLI Unchanged

```
./brok --input <file>
```

- This is the only invocation form
- `--help` may exist but adds no behavioral flags
- No other arguments accepted

### 5.2 Exit Codes Unchanged

| Scenario | Expected Exit Code |
|----------|-------------------|
| ACCEPT, execution succeeds | 0 |
| REJECT (any reason) | 0 |
| Missing input file | Non-zero |
| Internal error | Non-zero |

### 5.3 Invalid Proposals → REJECT Code 0

| Proposal State | Expected Outcome |
|----------------|------------------|
| Empty bytes | REJECT, exit 0 |
| Malformed JSON | REJECT, exit 0 |
| Valid but ambiguous | REJECT, exit 0 |
| Valid but non-conformant | REJECT, exit 0 |

### 5.4 Execution Only on ACCEPT

- Execution layer invoked if and only if artifact decision is ACCEPT
- REJECT must not invoke execution
- No "partial execution" or "dry run" modes

### 5.5 Authority Boundary Unchanged

- stdout.raw.kv = sole authoritative runtime truth
- artifact.json = authoritative wrapper decision
- Proposals = derived, non-authoritative
- Observability = derived, non-authoritative, inert

---

## 6. Mechanical Compliance Checklist

An implementer must verify each item with no discretion:

### 6.1 Seam Compliance

- [ ] Seam signature is `acquire_proposal_set(raw_input_bytes: bytes) -> bytes`
- [ ] Seam is called exactly once per invocation
- [ ] No exceptions escape the seam boundary
- [ ] Non-bytes returns collapse to empty bytes
- [ ] Engine failures collapse to empty bytes

### 6.2 CLI Compliance

- [ ] Only `--input` flag exists (besides `--help`)
- [ ] No environment variables alter behavior
- [ ] No configuration files read
- [ ] No runtime engine selection

### 6.3 Decision Compliance

- [ ] ACCEPT and REJECT are the only decisions
- [ ] No scoring, ranking, or confidence
- [ ] No new decision rules added
- [ ] Existing rules unchanged from baseline

### 6.4 Exit Code Compliance

- [ ] REJECT exits with code 0
- [ ] ACCEPT with successful execution exits with code 0
- [ ] Only operational failures exit non-zero

### 6.5 Authority Compliance

- [ ] stdout.raw.kv not parsed by wrapper
- [ ] Proposals do not influence artifact decision via metadata
- [ ] Observability does not affect behavior
- [ ] No new authoritative outputs

### 6.6 Behavioral Compliance

- [ ] No retry logic
- [ ] No feedback loops
- [ ] No self-correction
- [ ] No multi-turn generation
- [ ] No optimization for ACCEPT rate

---

## 7. Verification Commands

The following commands verify regression criteria:

### 7.1 CLI Surface

```bash
# Must succeed
./brok --input examples/inputs/accept_restart_alpha_1.txt

# Must fail (no --input)
./brok 2>&1 | grep -q "required"

# Must not have extra flags
./brok --help 2>&1 | grep -v "input\|help" | grep -c "\-\-" | grep -q "^0$"
```

### 7.2 Exit Codes

```bash
# REJECT must exit 0
./brok --input examples/inputs/reject_grammar_1.txt; echo $?  # Must print 0

# Missing file must exit non-zero
./brok --input /nonexistent 2>/dev/null; [ $? -ne 0 ] && echo "PASS"
```

### 7.3 No Runtime Toggles

```bash
# These must not change behavior
BROK_ENGINE=foo ./brok --input examples/inputs/accept_restart_alpha_1.txt
# Output must be identical to without the variable
```

---

## Document Control

| Attribute | Value |
|-----------|-------|
| Status | BINDING |
| Phase | L-0 |
| Companion Documents | PHASE_L_0_SCOPE_LOCK.md, LLM_INTEGRATION_CONTRACT.md |
| Checklist Authority | Items in Section 6 are exhaustive and binding |
