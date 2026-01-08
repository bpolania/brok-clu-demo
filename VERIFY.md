# Verification Boundary

This document defines the verification boundary for the Brok-CLU Runtime Demo.

---

## Purpose

Verification is **mandatory** and runs before every execution attempt. It ensures that only unmodified, trusted artifacts are executed.

---

## Trusted Artifact Set

The following artifacts under `vendor/poc_v2/` constitute the trusted payload:

| Path | Description |
|------|-------------|
| `poc_v2.tar.gz` | Sealed PoC v2 tarball containing the runtime |
| `PROVENANCE.txt` | Origin metadata |

These artifacts are vendored from the sealed Brok-CLU PoC v2 distribution and must not be modified.

---

## Verification Materials

Verification materials are used to validate the trusted set:

| File | Purpose |
|------|---------|
| `vendor/poc_v2/SHA256SUMS.vendor` | SHA-256 checksum for the vendored tarball |

The tarball contains its own internal `SHA256SUMS` for extracted contents.

---

## What Verification Confirms

When verification passes:

1. `vendor/poc_v2/poc_v2.tar.gz` exists and is readable
2. `vendor/poc_v2/SHA256SUMS.vendor` exists and is readable
3. Tarball SHA-256 checksum matches `SHA256SUMS.vendor`
4. Extracted bundle passes internal integrity checks

---

## Verification Failure Conditions

Verification fails if any of the following conditions are detected:

| Condition | Meaning |
|-----------|---------|
| Tarball missing or unreadable | Cannot extract runtime |
| SHA256SUMS.vendor missing or unreadable | Cannot verify tarball integrity |
| Checksum mismatch | Tarball has been modified |
| Internal integrity failure | Extracted contents are corrupted |

**Consequence of failure:** Execution is blocked. The runtime demo will not proceed with unverified or tampered artifacts.

---

## Enforcement

Verification is enforced by `scripts/verify_poc_v2.sh` before any execution attempt. This behavior cannot be bypassed, disabled, or configured.

Execution proceeds only after all checks pass.

---

## Artifact Provenance

| Attribute | Value |
|-----------|-------|
| Source | Brok-CLU PoC v2 sealed distribution |
| Platform | macOS arm64 |
| Status | Frozen, immutable |

The artifacts under `vendor/poc_v2/` are vendored copies from the sealed Brok-CLU PoC v2 distribution. They must remain byte-identical to their original form.

---

## What Verification Does NOT Do

| Non-Guarantee | Explanation |
|---------------|-------------|
| Runtime behavior validation | Verification confirms integrity, not correctness |
| Network isolation | No network checks are performed |
| Sandbox enforcement | No process isolation beyond standard OS permissions |
| Cryptographic signature verification | Only SHA-256 checksums are used |

Verification ensures artifact integrity. It does not make claims about runtime security beyond tamper detection.
