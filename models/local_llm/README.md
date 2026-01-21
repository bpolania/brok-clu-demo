# Phase L-10 Vendored Model Contract

## Fixed Path (Binding)

```
models/local_llm/model.bin
```

This path is **hard-coded** and **non-configurable**.

## Contract Rules

1. **Repository Artifact**: The model is a vendored repository artifact, not downloaded at runtime.

2. **Fixed Path**: The path `models/local_llm/model.bin` is hard-coded in `src/artifact_layer/inference_engine.py`. There is no override mechanism.

3. **No Configuration Surface**: No environment variables, CLI flags, or config files can change the model path.

4. **Failure Collapse**: If the model file is missing, invalid, or fails to load, the inference engine collapses to empty proposal bytes (`b""`). This is silent - no warnings or errors that influence control flow.

5. **No Download Attempts**: The system never attempts to download or locate alternative models.

## Model Format

The vendored model is a GGUF file compatible with `llama-cpp-python`. The file extension is `.bin` but the content is GGUF v3 format.

## Model Provenance

| Property | Value |
|----------|-------|
| File | `model.bin` |
| Format | GGUF v3 |
| Original Name | `TinyStories-656K-Q2_K.gguf` |
| Parameters | ~656K |
| Quantization | Q2_K |
| Size | 553,120 bytes |

### Provenance Chain

| Step | Source | Notes |
|------|--------|-------|
| 1 | Vendored from | `brok-llm-proposals/artifacts/models/phase9/TinyStories-656K-Q2_K.gguf` |
| 2 | GGUF conversion | Unknown converter; GGUF v3 Q2_K quantization |
| 3 | Original weights | Attributed to TinyStories model family |

### Attribution (Best Effort)

The filename suggests this is a quantized version of a TinyStories model:
- **TinyStories** is a model family from Microsoft Research
- **Authors**: Ronen Eldan and Yuanzhi Li
- **Paper**: "TinyStories: How Small Can Language Models Be and Still Speak Coherent English?"

**License Status**: The original TinyStories models from Microsoft Research are typically released under MIT License. However, the exact license for this specific GGUF artifact cannot be conclusively established because:
1. The GGUF conversion source is not documented
2. The intermediate quantization may have additional terms

**For Internal Demo Use**: This artifact is vendored for internal demonstration and testing purposes. Provenance is documented; license is inherited from upstream where applicable.

## Invariants

- Exactly one model file at the fixed path
- No runtime configuration
- Missing/invalid model collapses to empty bytes
- Downstream determinism is preserved regardless of model state

## Note on Model Purpose

This is a minimal language model used for Phase L-10 demonstration and testing. It is deliberately small (~656K parameters) to minimize repository size while providing a real, loadable GGUF model for proof of load capability.
