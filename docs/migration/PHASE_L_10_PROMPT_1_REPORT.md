# Phase L-10 Prompt 1 Report

## Prompt 1 Scope Statement

Prompt 1 establishes the fixed-path vendored model contract and hard-coded path constant, **without activating model execution**.

**Explicit Non-Goals for Prompt 1:**
- Model execution is NOT activated
- Proposal generation via LLM is NOT enabled
- No changes to ACCEPT/REJECT semantics
- No changes to downstream behavior

**Why Changed (from initial report):** Removed premature activation claims; reserved canonical statement for closure report (Prompt 3).

---

## 1. Summary

Phase L-10 Prompt 1 establishes:

1. **Fixed-path contract**: `models/local_llm/model.bin` (hard-coded, non-configurable)
2. **Vendored model artifact**: Real GGUF model file at the fixed path
3. **Load-failure collapse**: `_get_llm()` attempts load; failures return `None`; inference returns empty bytes

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
| Format | GGUF (compatible with llama-cpp-python) |
| Type | Real model artifact (not a stub) |
| Source | See `models/local_llm/README.md` for attribution |

---

## 4. Load Attempt Behavior

The `_get_llm()` function:

1. Computes the fixed model path using `_get_model_path()`
2. Attempts to instantiate `llama_cpp.Llama(model_path=...)`
3. On ANY failure (file missing, unreadable, parse error, ImportError), returns `None`
4. This causes `inference_engine()` to return `b""` (empty bytes)

**Important**: This load attempt exists but does NOT activate proposal generation. All proposals remain empty bytes in Prompt 1 state.

---

## 5. Tests

Tests in `tests/l10/test_l10_model_load_collapse.py` prove:

- **C1**: Missing model file → `_get_llm()` returns `None`
- **C2**: Unreadable model file → `_get_llm()` returns `None`

---

## 6. Invariants Preserved

| Invariant | Status |
|-----------|--------|
| Seam S contract | UNCHANGED |
| Acceptance semantics | UNCHANGED |
| Artifact validation | UNCHANGED |
| Collapse semantics | UNCHANGED |
| Run discovery | UNCHANGED |
| No new configuration surfaces | CONFIRMED |

---

## 7. Activation Status

| Item | Prompt 1 Status |
|------|-----------------|
| Fixed-path constant | Established |
| `_get_model_path()` | Implemented |
| Model file at path | Present (real GGUF) |
| `_get_llm()` load attempt | Implemented |
| Load-failure tests | Implemented |
| **Proposal generation** | **NOT ACTIVATED** |

---

## 8. Files Changed

| File | Change |
|------|--------|
| `models/local_llm/model.bin` | Real GGUF model (replaces stub) |
| `models/local_llm/README.md` | Updated with attribution |
| `src/artifact_layer/inference_engine.py` | Load attempt in `_get_llm()` |
| `tests/l10/test_l10_model_load_collapse.py` | New test file |
| `docs/migration/PHASE_L_10_PROMPT_1_REPORT.md` | This report |

---

## Note on Canonical Framing Statement

The Phase L-10 canonical framing statement is **reserved for the final closure report (Prompt 3)**. It is intentionally NOT included in this Prompt 1 report.
