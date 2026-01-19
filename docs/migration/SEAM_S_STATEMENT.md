# Seam S Statement: acquire_proposal_set (Freeze-Grade)

## 1. Seam Definition

**Name**: Seam S
**Function**: `acquire_proposal_set`
**Contract**: `acquire_proposal_set(raw_input_bytes: bytes, ctx: RunContext) -> OpaqueProposalBytes`
**Location**: `src/artifact_layer/seam_provider.py`

### Purpose

Seam S is the single integration point for acquiring proposal bytes from the bound proposal engine. This is the ONLY place where proposal generation is invoked.

### Guarantees

1. **Single call per run** - Enforced at runtime by RunContext (raises on second call)
2. **Failure collapse** - All failures deterministically return empty bytes (b"")
3. **Opaque passthrough** - Proposal bytes are opaque by construction (OpaqueProposalBytes)
4. **Build-time binding** - Engine selection is fixed at build time, not runtime

---

## 2. Contract Specification (Freeze-Grade)

```python
def acquire_proposal_set(
    raw_input_bytes: bytes,
    ctx: Optional[RunContext] = None
) -> OpaqueProposalBytes:
    """
    Acquire proposal set from the bound engine.

    Args:
        raw_input_bytes: Opaque bytes from user input file
        ctx: Run context for enforcing single-call invariant.
             If provided, raises SeamSViolation on second call.

    Returns:
        OpaqueProposalBytes wrapping the proposal output.
        On ANY failure, returns OpaqueProposalBytes(b"") which will
        deterministically collapse to REJECT downstream.

    Raises:
        SeamSViolation: If called more than once with the same RunContext.

    Guarantees:
        - Single call per run (when ctx provided)
        - All exceptions collapse to empty bytes
        - No parsing or interpretation of input
        - No filtering or modification of output
        - Output is opaque by construction
    """
```

---

## 3. Invariants (Frozen)

### C1: Call Count Invariant
- `acquire_proposal_set` is called **exactly once** per pipeline run
- **Runtime enforcement**: RunContext raises SeamSViolation on second call
- **Static enforcement**: AST analysis verifies single call site

### C2: Failure Collapse Invariant
- Engine None → returns `OpaqueProposalBytes(b"")`
- Engine raises → returns `OpaqueProposalBytes(b"")`
- Engine returns non-bytes → returns `OpaqueProposalBytes(b"")`
- All failures collapse deterministically to empty bytes

### C3: Proposal Variability Inert
- Proposal content affects **ONLY** the ACCEPT/REJECT decision
- No code paths branch on proposal content (except empty-bytes mapping)
- Garbage, valid, empty, malformed → only decision changes, not behavior

### C4: Engine Removed Safety
- System produces valid REJECT when engine is None/removed
- No crashes, no undefined behavior
- Pipeline completes normally with `decision=REJECT`

### C5: ACCEPT Execution Invariance
- When ACCEPT occurs, authoritative execution output is identical
- Proven via stdout.raw.kv hash comparison across runs
- Different proposal bytes that produce ACCEPT → same execution hash

---

## 4. Guards (Freeze-Grade Enforcement)

### G1: Exactly-One-Call Guard (Runtime)
Prevents multiple seam invocations at runtime.

**Implementation**: `RunContext` class with `mark_seam_s_called()` method

**Behavior**:
- First call: marks context, proceeds normally
- Second call: raises `SeamSViolation` deterministically

**Location**: `src/artifact_layer/run_context.py`

### G2: Non-Inspection Guard (Mechanical Boundary)
Prevents inspection of proposal bytes by construction.

**Implementation**: `OpaqueProposalBytes` wrapper class

**Disabled affordances**:
- No `__str__` (prevents string conversion)
- No `decode()` (prevents UTF-8 interpretation)
- No `__iter__` (prevents iteration)
- No `__getitem__` (prevents indexing)
- No `__len__` (prevents length-based logic)
- No `__bool__` (prevents truthiness-based logic)
- No `__eq__` (prevents equality comparison)

**Only allowed operation**: `to_bytes()` at artifact layer boundary

**Location**: `src/artifact_layer/opaque_bytes.py`

### G3: Static Analysis (Defense-in-Depth)
Secondary enforcement via AST scanning.

**Implementation**: Static tests verify single call site and no inspection patterns

**Location**: `tests/seam_s/test_seam_s_guards_and_invariants.py`

---

## 5. Authority Classification

| Component | Authority Level |
|-----------|----------------|
| Seam S output (proposal bytes) | NONE (opaque, untrusted) |
| Artifact layer decision | WRAPPER-LEVEL (sole ACCEPT/REJECT authority) |
| stdout.raw.kv | AUTHORITATIVE (execution output) |

---

## 6. Empty Bytes Mapping

When the seam returns `OpaqueProposalBytes(b"")`, the orchestrator extracts the bytes at the artifact layer boundary and maps this to a canonical empty ProposalSet:

```
{
  "schema_version": "m1.0",
  "input": {"raw": ""},
  "proposals": []
}
```

This is documented in Phase L-8 contract Section 5a.

**Result**: Empty bytes → REJECT with `reason_code=NO_PROPOSALS`

---

## 7. Test Coverage

| Category | Tests | Result |
|----------|-------|--------|
| G1: Runtime Guard | 2 | PASS |
| G2: Opaque Wrapper | 3 | PASS |
| G3: Static Analysis | 4 | PASS |
| C1: Call Count | 1 | PASS |
| C2: Failure Collapse | 3 | PASS |
| C3: Proposal Variability | 4 | PASS |
| C4: Engine Removed | 2 | PASS |
| C5: ACCEPT Invariance | 2 | PASS |

**Test Location**: `tests/seam_s/test_seam_s_freeze_grade.py`

---

## 8. Evidence

Evidence files are located in `docs/migration/evidence/seam_s/`:

| File | Proves |
|------|--------|
| `01_seam_call_count_proof.txt` | C1 invariant (exactly one call) |
| `02_proposal_variability_proof.txt` | C3 invariant (variability inert) |
| `03_full_test_run_transcript.txt` | All tests passing |
| `04_accept_path_invariance_proof.txt` | C5 invariant (ACCEPT execution unchanged) |
| `05_e2e_transcript.txt` | End-to-end evidence with hashes |
| `INDEX.md` | Evidence index |

---

## 9. Safety Questionnaire (Required for Changes)

Any change touching Seam S MUST answer these questions:

1. Does this change touch Seam S directly or indirectly?
2. If yes, does it preserve exact byte-in / byte-out behavior?
3. Can proposal output now influence downstream behavior?
4. Does this correlate inference success with ACCEPT?
5. Would deleting the proposal engine break this code?
6. Can garbage or malicious proposal bytes cause harm?
7. Does this introduce more than one Seam S call?
8. Does this inspect or interpret proposal bytes?

**If any answer is "yes" (except Q1-2 with proper justification), the change must be rejected.**

---

## 10. Verification Commands

```bash
# Run freeze-grade Seam S tests
/opt/homebrew/bin/pytest tests/seam_s/ -v

# Run all safety tests (seam_s + l8 + l1)
/opt/homebrew/bin/pytest tests/seam_s/ tests/l8/ tests/l1/ -v
```

---

*Seam S Statement: Freeze-Grade*
*Date: 2026-01-19*
