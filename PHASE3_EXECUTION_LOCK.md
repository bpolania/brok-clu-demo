# Phase 3 — Verification Enforcement & Execution Wiring (Complete)

## Status

- **Phase:** 3
- **Status:** COMPLETE
- **Mutability:** FROZEN

## Authoritative Inputs (Inherited, Immutable)

- Repository: brok-clu-runtime-demo (public)
- Platform: macOS arm64 only
- PoC version: Brok-CLU PoC v1 (sealed, frozen)
- Canonical runtime entrypoint: bundles/poc_v1/bin/macos-arm64/cmd_interpreter
- Trusted set definition: bundles/poc_v1/MANIFEST.txt
- Integrity signal: bundles/poc_v1/SHA256SUMS
- Output format: key=value
- run_infer not shipped and not referenced

## Verification Semantics (Locked)

- Verification runs before any execution attempt.
- Verification fails if any of the following occur:
  - MANIFEST.txt missing or unreadable
  - SHA256SUMS missing or unreadable
  - cmd_interpreter missing, unreadable, or not executable
  - Any file listed in MANIFEST.txt is missing
  - Any extra regular file exists anywhere under bundles/poc_v1/ that is not listed in MANIFEST.txt, excluding MANIFEST.txt and SHA256SUMS as verification materials, using relative paths, case-sensitive, with sorted comparison
  - Any SHA-256 checksum mismatch for entries in SHA256SUMS
  - Any symlink exists anywhere under bundles/poc_v1/ (symlinks not expected; presence is a verification failure)
- MANIFEST.txt and SHA256SUMS are verification materials and are not part of the trusted payload set.

## Execution Semantics (Locked)

- Execution is permitted only after successful verification.
- Exactly one input file per invocation.
- Invocation form is fixed:
  - bundles/poc_v1/bin/macos-arm64/cmd_interpreter --input <file>
- No alternate runtime flags.
- No environment-based behavior changes.
- Stateless, atomic invocation.
- Stdout is emitted exactly as produced by the runtime (no transformation).
- On execution failure (nonzero exit):
  - Do not emit captured stdout
  - Surface stderr as-is
  - Exit nonzero (pass through runtime exit code)

## Implementation Reference

- Enforced by: run.sh

## Closure

Phase 3 is complete. Execution and verification semantics are frozen and authoritative inputs for subsequent phases.
