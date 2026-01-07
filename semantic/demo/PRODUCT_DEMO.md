# Semantic Capability Demonstration

**DERIVED, NON-AUTHORITATIVE**

> **This demo shows behavior, not correctness of meaning.**

This document presents a product-facing demonstration of the Semantic Capability Layer operating on top of the frozen PoC v2 runtime.

---

## 1. What We Are Demonstrating

This demo shows end-to-end behavior when curated semantic inputs are processed through the PoC v2 runtime:

- **Runtime verification** — mandatory integrity check before execution
- **Deterministic execution** — each input produces an authoritative output
- **Semantic variability** — paraphrased inputs may produce different outputs

The demonstration uses a bounded, curated set of 3 inputs from Phase S-1 (SES_001).

**Important**: This demo illustrates behavior, not linguistic coverage or semantic correctness.

### Scope of This Curated Set

This demo uses a **minimal curated set** of 3 inputs for brevity. The set includes:

- 1 baseline input (happy_path)
- 2 paraphrase variants that produced divergent outputs (paraphrase_diverge)

The absence of a "paraphrase_match" example (where paraphrases produce identical outputs) does not imply that such cases cannot occur. It reflects only what was available in the existing SES_001 suite at the time of this demo.

No new semantic inputs were created for Phase S-2. This constraint is intentional and preserves the boundary between phases.

---

## 2. What Is Guaranteed

The following properties are guaranteed by the runtime layer (not this demo):

| Guarantee | Description |
|-----------|-------------|
| **Verification gating** | Execution cannot proceed without passing integrity verification |
| **Deterministic execution** | Given identical verification state and input file, execution produces identical output |
| **Authoritative output** | The only authoritative output is `stdout.raw.kv` |
| **No hidden state** | Runtime behavior is fully observable through captured artifacts |

These guarantees are inherited from the frozen PoC v2 runtime and are not claimed or re-proven by this semantic layer.

---

## 3. What Is Intentionally Not Guaranteed

This demo explicitly does **NOT** guarantee:

| Non-Guarantee | Explanation |
|---------------|-------------|
| Paraphrase equivalence | Different phrasings may produce different outputs |
| Semantic correctness | Outputs reflect compiled behavior, not linguistic "understanding" |
| Typo tolerance | Input variations are not normalized |
| Domain generality | Behavior is bounded to the compiled intent set |
| Production readiness | This is an illustrative demo only |

**Transparency note**: Divergence between paraphrased inputs is shown openly, not hidden.

---

## 4. How to Run This Demo

The demo uses the existing Phase S-1 runner **unchanged**.

### Run the full semantic suite:

```sh
./semantic/scripts/run_semantic_suite.sh
```

### Output locations:

- Suite summary: `semantic/artifacts/SES_SUMMARY.md`
- Per-SES index: `semantic/artifacts/ses_001/execution_index.md`
- Runtime references: `semantic/artifacts/ses_001/runs/input_*/runtime_ref.txt`
- Authoritative outputs: `artifacts/run/run_<timestamp>/stdout.raw.kv`

### View demo-specific documentation:

- Demo set definition: `semantic/demo/DEMO_SET.yaml`
- Per-input explanations: `semantic/demo/explanations/*.md`
- Run index: `semantic/demo/runs/INDEX.md`

---

## 5. Demo Walkthrough

### Scene A: Baseline Happy Path

**Input**: `restart alpha subsystem gracefully`

This input represents a baseline command in the expected format. The runtime:
1. Passes verification
2. Executes the input
3. Produces authoritative output with `status=OK`

See: [demo_input_01.md](explanations/demo_input_01.md)

### Scene B: Paraphrase Variant (Divergent)

**Input**: `graceful restart of alpha`

This input expresses the same intended action using different word order. The runtime:
1. Passes verification
2. Executes the input
3. Produces authoritative output with `status=OK`

However, byte-for-byte comparison with Scene A shows **DIFFER** due to embedded metadata (temp file paths in output header).

See: [demo_input_02.md](explanations/demo_input_02.md)

### Scene C: Extended Paraphrase (Divergent)

**Input**: `please restart the alpha subsystem in graceful mode`

This input adds polite phrasing and explicit mode specification. The runtime:
1. Passes verification
2. Executes the input
3. Produces authoritative output with `status=OK`

Byte-for-byte comparison shows **DIFFER** from baseline for the same reason as Scene B.

See: [demo_input_03.md](explanations/demo_input_03.md)

### Scene D: Divergence Analysis

All three inputs produced:
- Identical semantic key-value fields: `status=OK`, `intent_id=14`, `n_slots=0`, `dispatch=unknown`
- Different full `stdout.raw.kv` files due to varying temp file paths in output header

This divergence is **expected and documented**. The S-1 byte-for-byte comparison correctly flags the files as different because they are literally different files. No semantic interpretation is applied.

---

## 6. Mapping Table

| Input ID | Input String | Authoritative Output | Divergence Notes |
|----------|--------------|----------------------|------------------|
| demo_input_01 | `restart alpha subsystem gracefully` | `artifacts/run/run_20260107T231003Z/stdout.raw.kv` | BASELINE |
| demo_input_02 | `graceful restart of alpha` | `artifacts/run/run_20260107T231005Z/stdout.raw.kv` | DIFFER (line 4: temp path) |
| demo_input_03 | `please restart the alpha subsystem in graceful mode` | `artifacts/run/run_20260107T231007Z/stdout.raw.kv` | DIFFER (line 4: temp path) |

---

## 7. Why Differences Exist

The byte-for-byte divergence between outputs is caused by:

1. **Embedded metadata in stdout**: The PoC v2 bundle's run script writes a header to stdout that includes the input file path
2. **Temp file paths vary**: Each input is written to a unique temp file before execution
3. **Strict comparison**: The S-1 runner uses `cmp -s` which compares every byte

**Observed difference** (excerpt from diff):
```
4c4
< Input:  /var/folders/.../tmp.9S3GalHcRB
---
> Input:  /var/folders/.../tmp.k1F4KREz23
```

The semantic key-value output (lines 20-23) is **identical** across all three inputs:
```
status=OK
intent_id=14
n_slots=0
dispatch=unknown
```

This demonstrates that:
- The semantic layer comparison is strict and honest
- The runtime produces consistent semantic results
- The divergence is in output metadata, not semantic content

---

## 8. Transparency Callouts

This demo is designed with full transparency:

| Callout | Status |
|---------|--------|
| Divergence is shown | **YES** — S-1 classification of DIVERGENT is preserved |
| Divergence is explained | **YES** — Cause documented as temp file path variation |
| Semantic limits stated | **YES** — Non-guarantees listed explicitly |
| Authoritative source identified | **YES** — Always `stdout.raw.kv` |
| Demo labeled as illustrative | **YES** — Header states "DERIVED, NON-AUTHORITATIVE" |

**Key statement**: This demo does not claim that paraphrased inputs will produce identical outputs. It shows what actually happens, including divergence.

---

## References

- Phase S-0 Contract: [PHASE_S_0_SCOPE_LOCK.md](../contract/PHASE_S_0_SCOPE_LOCK.md)
- Phase S-1 Closure: [PHASE_S_1_CLOSURE.md](../evidence/phase_s_1/PHASE_S_1_CLOSURE.md)
- Demo Set Definition: [DEMO_SET.yaml](DEMO_SET.yaml)
- Demo Run Index: [INDEX.md](runs/INDEX.md)

---

*Phase S-2: Curated Product Demonstration*
*Semantic Capability Layer — brok-clu-runtime-demo*
