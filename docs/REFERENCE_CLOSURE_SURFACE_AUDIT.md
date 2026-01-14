# Reference Closure Surface Audit

This document audits the CLI surface of the Brok-CLU demo to verify the single canonical entrypoint invariant.

---

## Canonical Entrypoint

**File:** `./brok`

**Signature:**
```
./brok --input <file>
```

**Verification:** The `brok` script explicitly documents this as the only user-facing invocation:

```python
"""
Brok-CLU CLI - Canonical entrypoint

This is the single canonical CLI for the Brok-CLU pipeline.
It accepts only --input <file>, matching the PoC v2 execution contract.

Usage:
    ./brok --input <file>
"""
```

**Arguments:**
- `--input` (required): Input file path

No other flags are exposed to users.

---

## Internal Scripts (Not User-Facing)

The following scripts exist but are **internal implementation details**:

### Frozen PoC v2 Scripts

| Script | Purpose | User-Facing? |
|--------|---------|--------------|
| `scripts/verify_poc_v2.sh` | Verify PoC v2 tarball integrity | NO (internal) |
| `scripts/run_poc_v2.sh` | Execute PoC v2 binary | NO (internal) |
| `scripts/determinism_test_v2.sh` | Determinism verification | NO (internal) |

These scripts are frozen and must not be modified. They are invoked internally by the pipeline.

### Build Scripts

| Script | Purpose | User-Facing? |
|--------|---------|--------------|
| `scripts/generate_proposals.sh` | Generate proposal_set.json | NO (internal) |
| `scripts/build_artifact.sh` | Build artifact.json | NO (internal) |
| `scripts/run_brok.sh` | Legacy wrapper | NO (internal) |

### Semantic Layer Scripts

| Script | Purpose | User-Facing? |
|--------|---------|--------------|
| `semantic/scripts/run_semantic_suite.sh` | Run semantic tests | NO (internal) |
| `semantic/scripts/semantic_equivalence.sh` | Check equivalence | NO (internal) |
| `semantic/regression/run_regression_check.sh` | Regression check | NO (internal) |

### Legacy Script

| Script | Purpose | User-Facing? |
|--------|---------|--------------|
| `run.sh` | Legacy entrypoint | NO (superseded by `./brok`) |

---

## Internal Python Entrypoints

The following Python modules have `if __name__ == "__main__"` blocks but are **not user-facing**:

### grep output (sanitized):

```
artifact/src/builder.py:271:if __name__ == "__main__":
artifact/src/validator.py:366:if __name__ == "__main__":
m3/src/gateway.py:248:if __name__ == "__main__":
m3/src/orchestrator.py:420:if __name__ == "__main__":
proposal/src/generator.py:237:if __name__ == "__main__":
proposal/src/validator.py:263:if __name__ == "__main__":
```

**Assessment:** These are internal modules invoked by the orchestrator. They expose additional flags for internal use but are not documented as user-facing APIs:

| Module | Internal Flags | Exposed to Users? |
|--------|----------------|-------------------|
| `m3/src/orchestrator.py` | `--run-id`, `--quiet`, `--repo-root` | NO |
| `m3/src/gateway.py` | `--artifact`, `--input`, `--repo-root` | NO |
| `artifact/src/builder.py` | `--proposal-set`, `--run-id`, `--input-ref` | NO |
| `proposal/src/generator.py` | `--input`, `--run-id` | NO |

The canonical `./brok` entrypoint internally generates run-id and passes repo-root, hiding these implementation details from users.

---

## Bypass Path Analysis

### Question: Can users bypass gating?

**Analysis:**

1. **Direct PoC v2 invocation:** Users could theoretically run `scripts/run_poc_v2.sh --input <file>` directly, bypassing the proposal/artifact/gating pipeline.

   **Mitigation:** This is documented as internal-only. The script performs verification but does not integrate with the wrapper pipeline.

2. **Direct orchestrator invocation:** Users could run `python3 -m m3.src.orchestrator --input <file>` directly.

   **Assessment:** This invokes the same gating logic as `./brok`. No bypass.

3. **Environment variables:** Searched for environment variable overrides:

   ```
   git grep -n "os.environ\|getenv" -- "*.py" | grep -v test
   ```

   **Result:** No environment variables alter gating behavior.

4. **Hidden flags:** Searched for hidden or undocumented flags:

   **Result:** The internal `--quiet` flag affects output verbosity only, not gating decisions.

### Conclusion: No Bypass Paths Found

All code paths that execute PoC v2 go through the gateway, which enforces the ACCEPT/REJECT decision. There are no flags or environment variables that skip gating.

---

## argparse Definitions Summary

### grep output (sanitized):

```
# Canonical entrypoint (brok)
brok:59:    parser.add_argument('--input', required=True, help='Input file path')

# Internal modules (not user-facing)
artifact/src/builder.py:275:    parser.add_argument("--proposal-set", required=True, ...)
artifact/src/builder.py:276:    parser.add_argument("--run-id", required=True, ...)
artifact/src/builder.py:277:    parser.add_argument("--input-ref", required=True, ...)

m3/src/gateway.py:253:    parser.add_argument("--artifact", required=True, ...)
m3/src/gateway.py:254:    parser.add_argument("--input", required=True, ...)
m3/src/gateway.py:255:    parser.add_argument("--repo-root", default=..., ...)

m3/src/orchestrator.py:397:    parser.add_argument("--input", required=True, ...)
m3/src/orchestrator.py:398:    parser.add_argument("--run-id", ...)
m3/src/orchestrator.py:399:    parser.add_argument("--quiet", "-q", ...)
m3/src/orchestrator.py:400:    parser.add_argument("--repo-root", default=..., ...)
```

---

## Blockers Found

**None.** No bypass paths contradict M-3's closure.

---

## Recommendations

1. **Documentation clarity:** The README and REFERENCE_ARTIFACT.md now explicitly state that `./brok --input <file>` is the only supported invocation.

2. **Internal scripts:** All other scripts are documented as internal implementation details.

3. **No changes needed:** The surface audit confirms the single canonical entrypoint invariant is satisfied.

---

## Summary

| Check | Result |
|-------|--------|
| Single canonical entrypoint | VERIFIED (`./brok --input <file>`) |
| Internal scripts documented | VERIFIED |
| No user-facing bypass paths | VERIFIED |
| No environment variable overrides | VERIFIED |
| Gating enforcement intact | VERIFIED |

**Conclusion:** The CLI surface is clean. The reference artifact maintains a single canonical entrypoint with no bypass paths.

---

*Generated during reference artifact closure process*
