# Verification Boundary

This document defines the verification boundary for the Brok-CLU Runtime Demo.

---

## Purpose

Verification is **mandatory** and runs before every execution attempt. It ensures that only unmodified, trusted artifacts are executed.

---

## Trusted Artifact Set

The following artifacts under `bundles/poc_v1/` constitute the trusted payload:

| Path | Description |
|------|-------------|
| `bin/macos-arm64/cmd_interpreter` | Canonical runtime entrypoint (macOS arm64) |
| `VERSION.txt` | Distribution version metadata |

These artifacts are vendored from the sealed Brok-CLU PoC v1 distribution and must not be modified.

---

## Verification Materials

Verification materials are used to validate the trusted set but are not part of the trusted payload:

| File | Purpose |
|------|---------|
| `bundles/poc_v1/MANIFEST.txt` | Enumerates all files in the trusted set (one path per line) |
| `bundles/poc_v1/SHA256SUMS` | SHA-256 checksums for every file in the manifest |

---

## What Verification Confirms

When verification passes:

1. `MANIFEST.txt` exists and is readable
2. `SHA256SUMS` exists and is readable
3. `cmd_interpreter` exists, is readable, and is executable
4. Every file listed in `MANIFEST.txt` exists under `bundles/poc_v1/`
5. No extra regular files exist under `bundles/poc_v1/` (excluding `MANIFEST.txt` and `SHA256SUMS`)
6. Every file's SHA-256 checksum matches the corresponding entry in `SHA256SUMS`

---

## Verification Failure Conditions

Verification fails if any of the following conditions are detected:

| Condition | Meaning |
|-----------|---------|
| MANIFEST.txt missing or unreadable | Cannot enumerate trusted set |
| SHA256SUMS missing or unreadable | Cannot verify checksums |
| cmd_interpreter missing, unreadable, or not executable | Cannot execute runtime |
| Missing file | A file listed in `MANIFEST.txt` does not exist |
| Extra file | A regular file exists under `bundles/poc_v1/` that is not listed in `MANIFEST.txt` |
| Checksum mismatch | A file's computed SHA-256 does not match the value in `SHA256SUMS` |

**Consequence of failure:** Execution is blocked. The runtime demo will not proceed with unverified or tampered artifacts.

---

## Enforcement

Verification is enforced by `run.sh` before any execution attempt. This behavior is defined in Phase 3 and cannot be bypassed, disabled, or configured.

The verification order is:
1. Existence checks (MANIFEST.txt, SHA256SUMS, cmd_interpreter)
2. Manifest completeness (all listed files exist)
3. No extra files check
4. SHA-256 checksum verification

Execution proceeds only after all checks pass.

---

## Artifact Provenance

| Attribute | Value |
|-----------|-------|
| Source | Brok-CLU PoC v1 sealed distribution |
| Platform | macOS arm64 |
| Status | Frozen, immutable |

The artifacts under `bundles/poc_v1/` are vendored copies from the sealed Brok-CLU PoC v1 distribution. They must remain byte-identical to their original form.

---

## What Verification Does NOT Do

| Non-Guarantee | Explanation |
|---------------|-------------|
| Runtime behavior validation | Verification confirms integrity, not correctness |
| Network isolation | No network checks are performed |
| Sandbox enforcement | No process isolation beyond standard OS permissions |
| Cryptographic signature verification | Only SHA-256 checksums are used |

Verification ensures artifact integrity. It does not make claims about runtime security beyond tamper detection.
