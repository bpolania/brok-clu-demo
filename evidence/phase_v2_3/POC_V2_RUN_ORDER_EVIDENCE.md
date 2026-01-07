# PoC v2 Run Order Evidence

**Purpose:** Document explicit PoC v2 documentation requiring verify-before-run in the same extraction.

---

## Primary Evidence (operator sequence in the extracted bundle)

These sources explicitly describe the verify-then-run sequence as operator steps within an extracted bundle.

---

### Primary 1: README.md (Tarball Workflow)

**Path:** `brok-clu-poc_v2-standalone/README.md`
**Lines:** 86-97

**Excerpt:**
```
# 1. Extract
tar -xzf brok-clu-poc_v2-standalone.tar.gz

# 2. Enter the extracted directory
cd brok-clu-poc_v2-standalone

# 3. Verify bundle integrity (MANDATORY)
./scripts/verify.sh

# 4. Run inference
./scripts/run.sh examples/input_valid.txt
```

**Explanation:** This describes the required verify-before-run sequence within an extracted bundle. Steps are explicitly numbered: extract (1-2), verify (3), then run (4).

---

### Primary 2: VERIFY.md (Tarball Workflow)

**Path:** `brok-clu-poc_v2-standalone/VERIFY.md`
**Lines:** 131-154

**Excerpt:**
```
Step 1: Extract the Tarball
...
Step 2: Run Verification
./scripts/verify.sh
...
Step 3: Run Inference
./scripts/run.sh examples/input_valid.txt
```

**Explanation:** This describes the required verify-before-run sequence within an extracted bundle. Steps are explicitly numbered: extract (1), verify (2), then run (3).

---

### Primary 3: VERIFY.md (Verification Gate)

**Path:** `brok-clu-poc_v2-standalone/VERIFY.md`
**Lines:** 9-11

**Excerpt:**
> "Verification MUST pass before any execution"
> "The run.sh script refuses to execute without prior verification"
> "Verification status is checked by reading `bundles/verified/verify.status.txt`"

**Explanation:** This describes the required verify-before-run sequence within an extracted bundle. The run.sh script checks for verification state in the same bundle where it executes.

---

## Supporting Evidence (reinforces, not relied on)

These sources reinforce the primary evidence but are not relied upon as justification.

---

### Supporting 1: README.md (Verification Section)

**Path:** `brok-clu-poc_v2-standalone/README.md`
**Line:** 234

**Excerpt:**
> "Verification is MANDATORY before execution."

**Note:** Generic gating statement. Does not explicitly describe same-extraction sequence.

---

### Supporting 2: scripts/run.sh (Header Comment)

**Path:** `brok-clu-poc_v2-standalone/scripts/run.sh`
**Lines:** 4-5

**Excerpt:**
> "Requires prior successful verification."

**Note:** Implementation comment confirming the requirement. Not operator-facing workflow documentation.

---

### Supporting 3: scripts/run.sh (Error Message)

**Path:** `brok-clu-poc_v2-standalone/scripts/run.sh`
**Lines:** 54-56

**Excerpt:**
```
echo "Run verification first:"
echo "  ./scripts/verify.sh"
```

**Note:** Runtime error message. Confirms enforcement but is not primary workflow documentation.

---

## Conclusion

Primary evidence (README.md lines 86-97, VERIFY.md lines 131-154, VERIFY.md lines 9-11) explicitly documents the required operator workflow:

1. Extract the tarball
2. Run `./scripts/verify.sh` in the extracted bundle
3. Run `./scripts/run.sh` in the same extracted bundle

This justifies V2-3's "bundle internal verify" step: since V2-3 extracts fresh (separate from V2-2's extraction), it must run the bundle's verify.sh to create the required `bundles/verified/verify.status.txt` state file before run.sh will execute.

---

## Attestation

- Evidence extracted from: `vendor/poc_v2/poc_v2.tar.gz` (SHA-256: 7aa008f23f5fed51cb40c28ac8ec84fe036c3500ff2b9c51da1bb954bb74ed9a)
- Evidence verified: 2026-01-07
- Primary evidence consists of explicit operator workflow documentation only
