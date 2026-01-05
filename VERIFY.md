# Verification Boundary

This document defines the verification boundary for the Brok-CLU Runtime Demo.

---

## Trusted Artifact Set

The following artifacts under `bundles/poc_v1/` constitute the trusted set:

| Path | Description |
|------|-------------|
| `bin/macos-arm64/cmd_interpreter` | Canonical application entrypoint (macOS arm64) |
| `VERSION.txt` | Distribution version metadata |

These artifacts are vendored from the sealed Brok-CLU PoC v1 distribution and must not be modified.

---

## Verification Materials

| File | Purpose |
|------|---------|
| `bundles/poc_v1/MANIFEST.txt` | Enumerates all files in the trusted set (one path per line) |
| `bundles/poc_v1/SHA256SUMS` | SHA-256 checksums for every file in the manifest |

---

## Why Verification Is Mandatory

Verification ensures that:

1. **Artifact integrity** — The vendored binaries are byte-identical to the authoritative Brok-CLU PoC v1 distribution.
2. **Tamper detection** — Any modification, corruption, or substitution of artifacts is detected before execution.
3. **Trust boundary enforcement** — Only verified artifacts may be executed; unverified or mismatched artifacts are rejected.

The Brok-CLU PoC v1 distribution is sealed and immutable. Verification confirms that the local copy matches the authoritative source.

---

## Verification Guarantees

When verification passes:

- Every file listed in `MANIFEST.txt` exists under `bundles/poc_v1/`
- Every file's SHA-256 checksum matches the corresponding entry in `SHA256SUMS`
- No extraneous files exist under `bundles/poc_v1/` that are not listed in the manifest
- The canonical entrypoint at `dist/poc_v1/bin/macos-arm64/cmd_interpreter` is byte-identical to the vendored copy

---

## Verification Failure

Verification fails if any of the following conditions are detected:

| Condition | Meaning |
|-----------|---------|
| Missing file | A file listed in `MANIFEST.txt` does not exist |
| Extra file | A file exists under `bundles/poc_v1/` that is not listed in `MANIFEST.txt` |
| Checksum mismatch | A file's computed SHA-256 does not match the value in `SHA256SUMS` |
| Manifest/checksum desync | The set of paths in `MANIFEST.txt` does not match the set of paths in `SHA256SUMS` |

**Consequence of failure:** Execution is blocked. The runtime demo will not proceed with unverified or tampered artifacts.

---

## Artifact Provenance

| Attribute | Value |
|-----------|-------|
| Source | Brok-CLU PoC v1 sealed distribution |
| Platform | macOS arm64 |
| Status | Frozen, immutable |

The artifacts under `bundles/poc_v1/` are vendored copies. The authoritative source is the Brok-CLU repository's `dist/poc_v1/` distribution.
