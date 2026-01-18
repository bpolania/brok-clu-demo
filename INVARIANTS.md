# Invariants

This document lists the invariants that must never change for this repository to remain a valid reference artifact.

---

## Authority Invariants

1. **`stdout.raw.kv` is the only authoritative execution output.** No other file, log, or data structure may be treated as ground truth for what the runtime decided.

2. **Proposals are non-authoritative.** The proposal generator uses LLM inference and its outputs may be incorrect. Proposals must never be treated as execution truth.

3. **Artifacts record wrapper decisions only.** The artifact's `decision` field reflects the wrapper's choice, not the runtime's actual behavior.

4. **Observability outputs are derived.** Manifest and trace files document execution but do not define it.

---

## Determinism and Relocatability Invariants

5. **Identical inputs produce identical outputs.** Given the same input file content, the pipeline must produce byte-for-byte identical artifacts and execution results.

6. **No absolute paths in committed files.** All paths in artifacts, manifests, and documentation must be relative or use portable markers (e.g., `[external]:<basename>`).

7. **No timestamps in deterministic outputs.** Manifests, traces, and artifacts must not contain timestamps, machine identifiers, or other non-deterministic data.

8. **No machine-specific identifiers.** Hostnames, usernames, process IDs, and similar identifiers must not appear in committed files.

---

## Execution Gating Invariants

9. **Gating is mandatory.** Execution of PoC v2 must only occur after explicit ACCEPT decision. REJECT or gate failure must block execution.

10. **No bypass paths.** There must be no CLI flags, environment variables, or code paths that skip gating enforcement.

11. **Verification before execution.** PoC v2 tarball integrity must be verified before any execution attempt.

12. **Single canonical entrypoint.** The only user-facing invocation is `./brok --input <file>`. All other scripts are internal.

---

## Observability Non-Interference Invariants

13. **Observability does not affect behavior.** Manifest and trace generation must not alter pipeline decisions, execution, or outputs.

14. **Observability is optional.** Pipeline must function correctly even if M-4 observability is disabled or fails.

15. **No parsing of `stdout.raw.kv`.** Observability code may hash but must never parse or interpret execution output content.

16. **Binary-only file access for execution output.** `stdout.raw.kv` must only be opened in binary mode (`'rb'`), never text mode.

---

## Invalidation Triggers

Any of the following changes would invalidate this reference artifact:

| Change | Why It Breaks Reference Status |
|--------|--------------------------------|
| Modify `vendor/poc_v2/poc_v2.tar.gz` | Sealed runtime is immutable |
| Alter `scripts/verify_poc_v2.sh` | Verification boundary changes |
| Alter `scripts/run_poc_v2.sh` | Execution contract changes |
| Alter `scripts/determinism_test_v2.sh` | Determinism test contract changes |
| Add CLI flags that change behavior | Violates single canonical entrypoint |
| Make proposals authoritative | Authority model violation |
| Skip gating for any code path | Gating enforcement violation |
| Add timestamps to artifacts | Determinism violation |
| Add absolute paths to committed files | Relocatability violation |
| Parse `stdout.raw.kv` content | Binary-only access violation |

---

## Verification

These invariants are verified by the test suite:

| Test Suite | Invariants Covered |
|------------|-------------------|
| `m3/tests/test_invariants.py` | 9, 10, 11, 12 |
| `m4/tests/test_m4.py` | 5, 6, 7, 13, 14, 15, 16 |
| `proposal/tests/test_proposals.py` | 2, 5 |
| `artifact/tests/test_artifact_*.py` | 3, 5, 6 |

Run all tests to verify invariants:

```sh
python3 -m unittest discover -s . -p "test*.py"
```

---

*This document is part of the frozen reference artifact.*
