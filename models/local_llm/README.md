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

The vendored model is a GGUF file compatible with `llama-cpp-python`. The file extension is `.bin` but the content is GGUF format.

## Model Attribution

| Property | Value |
|----------|-------|
| File | `model.bin` |
| Format | GGUF v3 |
| Architecture | controlvector |
| Source | Vendored from brok-llm-proposals Phase 9 artifacts |
| Original file | `happy.gguf` |
| Size | 509,440 bytes |
| License | Model weights for demo/testing purposes only |

**Note**: This is a minimal control vector model used for Phase L-10 demonstration. It is not a production language model.

## Invariants

- Exactly one model file at the fixed path
- No runtime configuration
- Missing/invalid model collapses to empty bytes
- Downstream determinism is preserved regardless of model state
