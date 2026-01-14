# Reference Artifact Declaration

This repository is a **frozen reference artifact** demonstrating deterministic command routing with the Brok-CLU PoC v2 runtime.

**Tag:** `brok-demo-v1`

---

## Authority Model

The authority hierarchy is strict and non-negotiable:

| Output | Authority Level | Description |
|--------|-----------------|-------------|
| `stdout.raw.kv` | **AUTHORITATIVE** | The only source of execution truth |
| `artifact.json` | DERIVED | Wrapper-level decision record |
| `proposal_set.json` | NON-AUTHORITATIVE | LLM-generated proposals (may be wrong) |
| `manifest.json` | DERIVED | Observability metadata |
| `trace.jsonl` | DERIVED | Stage execution trace |

### Authority Rules

1. **Execution truth lives in `stdout.raw.kv` only.** No other output may be treated as authoritative for what the runtime decided.

2. **Proposals are non-authoritative.** The proposal generator uses LLM inference and may produce incorrect or hallucinated mappings. Proposals exist only to feed the artifact builder.

3. **Artifacts are wrapper decisions.** The artifact records the wrapper's accept/reject decision and selected proposal, but this is a derived summary, not ground truth.

4. **Observability outputs are derived.** Manifest and trace files document what happened but do not define what happened.

---

## Canonical CLI Surface

The **only** supported user-facing invocation is:

```sh
./brok --input <file>
```

This single entrypoint:
- Generates proposals (M-1)
- Builds artifact with decision (M-2)
- Enforces gating (M-3)
- Executes PoC v2 if ACCEPT
- Produces observability outputs (M-4)

All other scripts (`scripts/run_poc_v2.sh`, `scripts/verify_poc_v2.sh`) are internal implementation details and should not be invoked directly for normal operation.

---

## Non-Goals

This repository explicitly does **NOT**:

| Non-Goal | Explanation |
|----------|-------------|
| Semantic correctness | Proposals may be wrong; no accuracy claims |
| General NLP | Closed intent set only, not general language understanding |
| Scoring or confidence | No probability scores or confidence metrics |
| Heuristics tuning | No adjustable thresholds or weights |
| Production deployment | Demo artifact only, not production-hardened |
| Performance claims | No latency, throughput, or efficiency guarantees |
| Security claims | Verification is integrity-only, not security hardening |
| Extensibility | Closed system, no plugin or extension mechanism |

### Where Misunderstandings Commonly Occur

1. **"The proposal is correct"** - No. Proposals are LLM-generated guesses. Only `stdout.raw.kv` is authoritative.

2. **"The artifact decides"** - No. The artifact records a decision. The runtime (`stdout.raw.kv`) is the actual decision.

3. **"I can add new intents"** - No. The intent set is sealed in the PoC v2 binary.

4. **"The manifest is the source of truth"** - No. The manifest is derived observability data.

---

## Intended Audience

This reference artifact is intended for:

- **B2B integration engineers** evaluating deterministic routing patterns
- **Edge deployment architects** studying offline-capable inference wrappers
- **Auditors** examining authority boundaries and decision traceability
- **Platform engineers** understanding sealed artifact consumption patterns

This is **not** intended for:
- End users seeking a chatbot or NLP service
- Developers wanting to extend or modify behavior
- Anyone expecting production-ready software

---

## How to Cite

When referencing this artifact:

```
Brok-CLU Reference Demo
Tag: brok-demo-v1
Repository: github.com/bpolania/brok-clu-demo
Commit: <see tag>
```

For academic or formal citations, reference the specific tag commit hash.

---

## What Would Invalidate This Reference Artifact

Changes that would break reference artifact status:

- **Modifying `vendor/poc_v2/poc_v2.tar.gz`** - Sealed runtime must remain unchanged
- **Altering frozen scripts** - `verify_poc_v2.sh`, `run_poc_v2.sh`, `determinism_test_v2.sh`
- **Changing authority boundaries** - Any code that makes proposals or artifacts authoritative
- **Adding CLI flags that alter behavior** - The canonical CLI must remain `./brok --input <file>` only
- **Introducing timestamps or absolute paths in committed files** - Breaks relocatability
- **Modifying gating enforcement** - M-3 invariants must remain intact
- **Changing schema semantics** - Proposal, artifact, and manifest schemas are frozen

Any such change requires a new reference artifact version with explicit documentation of what changed and why.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Usage and quick start |
| `VERIFY.md` | Trust model and verification |
| `INVARIANTS.md` | Invariants that must never change |
| `docs/REFERENCE_CLOSURE_PRECHECK.md` | Closure verification results |
| `docs/REFERENCE_CLOSURE_SURFACE_AUDIT.md` | CLI surface audit |
| `docs/migration/PHASE_M_4_CLOSURE_REPORT.md` | M-4 implementation details |

---

*This document is part of the frozen reference artifact.*
