# Phase L-10 Prompt 1 Report

## Prompt 1 Scope Statement

Prompt 1 establishes the fixed-path vendored model contract and **proves model load capability**, without activating proposal execution.

**Prompt 1 Deliverables:**
- Fixed-path contract: `models/local_llm/model.bin`
- Real GGUF model file (loadable by llama-cpp-python)
- Positive load tests prove llama-cpp-python can load the model
- Collapse tests prove failure paths return `None`

**Explicit Non-Goals for Prompt 1:**
- Proposal execution is NOT activated
- Proposal generation via LLM is NOT enabled
- No changes to ACCEPT/REJECT semantics
- No changes to downstream behavior

---

## Why Prompt 1 Does Not Activate Proposal Execution

Prompt 1 remains non-activated **structurally**, not via runtime gates. No new gates were added.

**Structural Non-Activation:**

`_get_llm()` in `src/artifact_layer/inference_engine.py:87` returns `None` even when the model loads successfully. This matches pre-Prompt-1 runtime behavior where no model path existed.

```
_get_llm() behavior:
1. Attempts to load model from fixed path (exercises load path)
2. On success: returns None (inference not wired)
3. On failure: returns None (collapse semantics)

inference_engine() behavior:
1. Calls _get_llm()
2. If llm is None: returns b"" (empty bytes)
3. Inference code path is never reached
```

**No New Gates Added:**
- No early return statements were added
- No phase toggles exist
- No "to be removed later" code paths
- Runtime behavior matches pre-Prompt-1 state

**Gating Points (file:line):**
- `src/artifact_layer/inference_engine.py:150-151`: `_get_llm()` called, returns None
- `src/artifact_layer/inference_engine.py:152-154`: `if llm is None: return b""`

---

## 1. Summary

Phase L-10 Prompt 1 establishes:

1. **Fixed-path contract**: `models/local_llm/model.bin` (hard-coded, non-configurable)
2. **Vendored model artifact**: Real GGUF model file at the fixed path
3. **Load capability proof**: `test_positive_model_load` proves llama-cpp-python can load the model
4. **Failure collapse**: Missing/invalid model → `_get_llm()` returns `None`
5. **Structural non-activation**: `_get_llm()` returns `None` (inference not wired)

---

## 2. Fixed-Path Contract

| Property | Value |
|----------|-------|
| Path | `models/local_llm/model.bin` |
| Configuration | Hard-coded, non-configurable |
| Override mechanisms | NONE (no env vars, CLI flags, config files) |
| Failure behavior | Silent collapse to empty bytes (`b""`) |

---

## 3. Vendored Model Artifact

| Property | Value |
|----------|-------|
| File | `models/local_llm/model.bin` |
| Format | GGUF v3 |
| Size | 553,120 bytes |
| Source | See `models/local_llm/README.md` for provenance |
| Type | Real language model (loadable by llama-cpp-python) |

---

## 4. Required Dependency

| Property | Value |
|----------|-------|
| Package | `llama-cpp-python` |
| Tested Version | `0.2.90` |
| Declaration | Test file docstring (no pre-existing dependency system in repo) |
| Status | Required for positive load tests |

**Note:** This repository has no pre-existing dependency management system (no pyproject.toml, requirements.txt, or similar existed before Prompt 1). The dependency is documented in test file comments.

---

## 5. Load Behavior

The `_get_llm()` function:

1. Computes the fixed model path using `_get_model_path()`
2. Attempts to instantiate `llama_cpp.Llama(model_path=...)`
3. **On success**: Returns `None` (inference not wired in Prompt 1)
4. **On ImportError** (llama-cpp-python not installed): Returns `None`
5. **On any load failure** (file missing, unreadable, invalid): Returns `None`

This matches pre-Prompt-1 runtime behavior where `_get_llm()` always returned `None` because no model path existed.

---

## 6. Tests

Tests in `tests/l10/test_l10_model_load_collapse.py`:

**Load Capability Test:**
- **Positive model load**: Calls `Llama()` directly to prove llama-cpp-python can load `model.bin`

**Prompt 1 Behavior Test:**
- **_get_llm() returns None**: Verifies `_get_llm()` returns `None` (inference not wired)

**Collapse Tests:**
- **C1**: Missing model file → `_get_llm()` returns `None`
- **C2**: Unreadable model file → `_get_llm()` returns `None`

**Test Results:**
```
Phase L-10: Model Load Tests
Results: 6 passed, 0 failed
```

---

## 7. Invariants Preserved

| Invariant | Status |
|-----------|--------|
| Seam S contract | UNCHANGED |
| Acceptance semantics | UNCHANGED |
| Artifact validation | UNCHANGED |
| Collapse semantics | UNCHANGED |
| Run discovery | UNCHANGED |
| No new configuration surfaces | CONFIRMED |
| No new runtime gates | CONFIRMED |

---

## 8. Capability vs Activation Status

| Item | Status |
|------|--------|
| Fixed-path constant | Established |
| `_get_model_path()` | Implemented |
| Model file at path | Present (real GGUF) |
| Positive load test | PASS |
| Collapse tests (C1, C2) | PASS |
| `_get_llm()` | Returns `None` (inference not wired) |
| **Proposal execution** | **NOT ACTIVATED** |

---

## 9. Files Changed

| File | Change |
|------|--------|
| `models/local_llm/model.bin` | Real GGUF model (TinyStories-656K) |
| `models/local_llm/README.md` | Contract and provenance |
| `src/artifact_layer/inference_engine.py` | Fixed-path contract, `_get_llm()` |
| `tests/l10/test_l10_model_load_collapse.py` | Positive + collapse tests |
| `docs/migration/PHASE_L_10_PROMPT_1_REPORT.md` | This report |

---

## Note on Canonical Framing Statement

The Phase L-10 canonical framing statement is **reserved for the final closure report (Prompt 3)**. It is intentionally NOT included in this Prompt 1 report.
