# Phase S-0: Semantic Capability Layer — Scope Lock & Contract Definition

**Status:** LOCKED
**Authority:** Authoritative, binding, non-reopenable

---

This document defines the scope, constraints, and contract for the Semantic Capability Layer (Layer 1) of the brok-clu-runtime-demo project.

All subsequent phases (S-1, S-2, S-3) execute under this contract and cannot weaken its constraints.

---

## 1. Project Identity and Purpose

brok-clu-runtime-demo is a demonstration repository for Brok-CLU, a compiled Constrained Language Understanding system.

The demo's purpose is to show:
- how a sealed CLU artifact is verified
- how it is executed deterministically
- how outputs are audit-grade and inspectable
- how semantics are derived from a compiled language, not inferred at runtime

This is a product-facing demo, but with audit-level rigor.

---

## 2. Runtime Layer Status (CRITICAL, FROZEN)

The runtime demo is complete, frozen, and archival.

**PoC v2 Runtime Demo (Final)**
- PoC v2 is a standalone, relocatable demo bundle
- It preserves PoC v1 semantics
- It removes all dependency on the Brok-CLU repo layout
- It is treated as a sealed appliance

You must never:
- modify PoC v2
- inspect or edit files inside the bundle
- fabricate verification artifacts
- bypass verification
- repackage the bundle

**Vendored Artifact**
- Path: `vendor/poc_v2/poc_v2.tar.gz`
- SHA-256: `7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a`
- This hash must never change.

---

## 3. Runtime Guarantees (Non-Negotiable)

The following guarantees are proven and frozen:
- Mandatory verification before execution
- Verification blocks execution on failure
- Deterministic execution
- Byte-for-byte identical output for identical inputs
- No hidden state
- No runtime configurability
- Full relocatability
- Audit-grade artifacts

These are system invariants.

You are not allowed to:
- weaken them
- reinterpret them
- re-prove them
- bypass them

---

## 4. Runtime Output Contract (Authoritative)

**Single Source of Truth**

The only authoritative execution output is:

`stdout.raw.kv`

- Produced by PoC v2
- Captured verbatim
- Byte-for-byte preserved
- No normalization
- No trimming
- No inference

All determinism checks and audits use this file only.

**Derived Output**
- Any JSON or "semantic" view is derived
- Derived outputs are explicitly non-authoritative
- Derived outputs must never be used to assert correctness

---

## 5. Execution & Determinism (Already Implemented)

You must assume the following scripts already exist and are correct:
- Verification wiring (Phase V2-2)
- Single-run execution wiring (Phase V2-3)
- Output capture & presentation (Phase V2-4)
- Determinism validation (Phase V2-5)
- Relocatability proof (Phase V2-6)
- Final validation & freeze (Phase V2-7)

Do not modify these layers.

---

## 6. Layer 1: Semantic Capability — What It Is

Layer 1 is a semantic capability demonstration, not a system proof.

It exists to show:
- paraphrase collapse
- intent routing
- slot consistency
- deterministic rejection

Layer 1 is illustrative.

It demonstrates what a compiled language can do, not what the runtime guarantees universally.

---

## 7. What Layer 1 Is Allowed to Do

Layer 1 may:
- Run PoC v2 via the existing single-run wrapper
- Use a finite, frozen input suite
- Group inputs into semantic equivalence classes
- Derive a functional signature from `stdout.raw.kv`
- Compare those signatures for equality
- Produce summaries and PASS/FAIL results at the semantic layer

All semantic checks are layer-owned and non-authoritative.

---

## 8. What Layer 1 Must NOT Do (CRITICAL)

You must NOT:
- claim general language understanding
- claim paraphrase completeness
- imply NLP robustness
- expand intent sets
- modify PoC v2
- modify verification or execution wiring
- interpret runtime failures as runtime defects
- treat semantic mismatches as determinism failures

Semantic failures are language design outcomes, not system failures.

---

## 9. Semantic Equivalence Definition (Frozen)

For Layer 1 only:

Semantic equivalence is defined as:
- identical functional signature
- extracted mechanically from `stdout.raw.kv`
- using a small, explicitly defined subset of keys

Rules:
- Full `stdout.raw.kv` is always preserved
- Signature extraction is documented and fixed
- Exact string match only
- No normalization
- No inference

---

## 10. Input Suite Constraints

Layer 1 will use a fixed semantic suite:
- Single-line UTF-8 text files
- Compatible with PoC v2
- Grouped into equivalence classes:
  - Same intent + slots (paraphrases)
  - Same intent, different slot values
  - Semantic reject (plausible but disallowed)
  - Structural reject (grammar/schema invalid)

This suite is illustrative, not exhaustive.

---

## 11. Failure Semantics in Layer 1

Layer 1 failure means:
- mismatch inside an equivalence class
- mixed ACCEPT / REJECT where consistency is expected
- verification blocking execution
- wrapper failure

Layer 1 failure does not imply:
- runtime defect
- determinism defect
- verification defect

---

## 12. Artifact Ownership

**PoC v2 owns:**
- verification semantics
- execution semantics
- authoritative outputs

**Layer 1 owns:**
- grouping
- comparison
- derived views
- summaries
- presentation narrative

Never overwrite runtime artifacts.

---

## 13. Operating Mode

When working on Layer 1:
- Treat runtime layers as immutable
- Be explicit about non-claims
- Prefer clarity over cleverness
- Avoid "AI demo" tropes
- Favor auditability over flash
- Assume skeptical technical reviewers

If a requested change would:
- modify PoC v2
- bypass verification
- weaken determinism
- inflate semantic guarantees

You must stop and state that it violates project constraints.

---

## 14. Non-Claims (Explicit)

The Semantic Capability Layer explicitly does NOT claim:
- General language understanding
- Paraphrase completeness
- Production readiness
- Multilingual robustness
- Typo tolerance
- Domain invariance
- Stability across future compiled artifacts

These non-claims are binding and must be preserved in all documentation and presentation.

---

## 15. Contract Finality

This document is:
- **Authoritative** — it defines the scope for all Semantic Layer phases
- **Binding** — all subsequent phases must comply
- **Non-reopenable** — constraints cannot be weakened without explicit version bump and re-audit

Phase S-0 is complete when this contract exists in-repo and is referenced by all semantic layer documentation.

---

*End of Phase S-0 Scope Lock Contract*
